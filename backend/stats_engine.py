"""Pluggable stats providers + Poisson early-interval corner engine."""

from __future__ import annotations

import logging
import math
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.models import (
    Direction,
    Fixture,
    MatchStatus,
    ParsedRule,
    ScoutResponse,
    Selection,
    SelectionTarget,
    TeamCornerStats,
)

logger = logging.getLogger(__name__)

# Default share of full-match corners that occur in the first 15 minutes
DEFAULT_FIRST15_SHARE = 0.22


def window_minutes(window: str) -> float:
    m = re.match(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", window)
    if not m:
        return 5.0
    start = int(m.group(1)) * 60 + int(m.group(2))
    end = int(m.group(3)) * 60 + int(m.group(4))
    return max((end - start + 1) / 60.0, 0.5)


def poisson_zero(lambda_: float) -> float:
    """P(X = 0) under Poisson(λ)."""
    return math.exp(-max(lambda_, 0.0))


def fair_odds(prob: float) -> float:
    if prob <= 0:
        return 999.0
    return round(1.0 / prob, 3)


def interval_lambda(
    c90_for: float,
    c90_against: float,
    window_min: float,
    first15_share: float = DEFAULT_FIRST15_SHARE,
    blend: float = 0.55,
) -> float:
    """
    Weighted corner rate for a team in a short early window.

    blend: weight given to team's own attack vs opponent's concession rate.
    first15_share: empirical fraction of corners in first 15 min; scaled linearly
                   for shorter/longer windows relative to 15.
    """
    rate_90 = blend * c90_for + (1 - blend) * c90_against
    # scale the first-15 share to the actual window length
    share = first15_share * (window_min / 15.0)
    share = min(max(share, 0.02), 0.45)
    return rate_90 * share


# ── Provider interface ──────────────────────────────────────────────────────

class StatsProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def fetch_fixtures(self, status: MatchStatus) -> list[Fixture]:
        ...


class MockStatsProvider(StatsProvider):
    """Realistic offline sample set so the pipeline works without API keys."""

    name = "mock"

    async def fetch_fixtures(self, status: MatchStatus) -> list[Fixture]:
        now = datetime.now(timezone.utc)
        samples = [
            # low-corner defensive sides → high P(0) in first 5
            _fx("m1", "Atletico Madrid", "Getafe", now + timedelta(hours=2),
                "La Liga", MatchStatus.UPCOMING,
                3.8, 3.2, 3.1, 4.0),
            _fx("m2", "Burnley", "Sheffield United", now + timedelta(hours=3),
                "Championship", MatchStatus.UPCOMING,
                4.1, 4.5, 3.9, 4.8),
            _fx("m3", "Inter Milan", "Torino", now + timedelta(hours=1),
                "Serie A", MatchStatus.UPCOMING,
                5.2, 3.4, 3.6, 4.9),
            _fx("m4", "Nantes", "Reims", now + timedelta(minutes=40),
                "Ligue 1", MatchStatus.UPCOMING,
                4.0, 4.2, 3.8, 4.4),
            _fx("m5", "Mainz 05", "Augsburg", now + timedelta(hours=4),
                "Bundesliga", MatchStatus.UPCOMING,
                4.6, 5.1, 4.3, 5.0),
            # higher corner teams → lower P(0)
            _fx("m6", "Liverpool", "Brighton", now + timedelta(hours=2),
                "Premier League", MatchStatus.UPCOMING,
                7.1, 4.8, 5.9, 6.2),
            _fx("m7", "Manchester City", "Newcastle", now + timedelta(hours=5),
                "Premier League", MatchStatus.UPCOMING,
                7.8, 4.2, 5.5, 6.8),
            _fx("m8", "Bayern Munich", "Wolfsburg", now + timedelta(hours=3),
                "Bundesliga", MatchStatus.UPCOMING,
                7.4, 3.9, 4.7, 6.5),
            # live fixtures
            _fx("m9", "Osasuna", "Celta Vigo", now - timedelta(minutes=8),
                "La Liga", MatchStatus.LIVE,
                4.2, 4.0, 4.5, 4.3),
            _fx("m10", "Lazio", "Empoli", now - timedelta(minutes=15),
                "Serie A", MatchStatus.LIVE,
                5.0, 3.7, 3.5, 5.1),
            _fx("m11", "Brentford", "Crystal Palace", now + timedelta(hours=6),
                "Premier League", MatchStatus.UPCOMING,
                5.3, 5.0, 4.9, 5.4),
            _fx("m12", "Strasbourg", "Lorient", now + timedelta(hours=1),
                "Ligue 1", MatchStatus.UPCOMING,
                4.4, 4.6, 4.1, 4.7),
        ]

        if status == MatchStatus.LIVE:
            return [f for f in samples if f.status == MatchStatus.LIVE]
        if status == MatchStatus.UPCOMING:
            return [f for f in samples if f.status == MatchStatus.UPCOMING]
        return samples


def _fx(
    fid: str,
    home: str,
    away: str,
    kickoff: datetime,
    league: str,
    status: MatchStatus,
    h_for: float,
    h_against: float,
    a_for: float,
    a_against: float,
) -> Fixture:
    return Fixture(
        fixture_id=fid,
        home_team=home,
        away_team=away,
        kickoff_utc=kickoff.isoformat(),
        league=league,
        status=status,
        home_stats=TeamCornerStats(
            team_id=f"{fid}_h", team_name=home,
            c90_for=h_for, c90_against=h_against,
        ),
        away_stats=TeamCornerStats(
            team_id=f"{fid}_a", team_name=away,
            c90_for=a_for, c90_against=a_against,
        ),
    )


class ApiFootballProvider(StatsProvider):
    """Live adapter skeleton for API-Football (RapidAPI)."""

    name = "api_football"

    def __init__(self) -> None:
        self.key = os.getenv("API_FOOTBALL_KEY", "")
        if not self.key:
            raise RuntimeError("API_FOOTBALL_KEY is required for api_football provider")

    async def fetch_fixtures(self, status: MatchStatus) -> list[Fixture]:
        # Placeholder: real implementation would call
        # https://v3.football.api-sports.io/fixtures + team statistics endpoints.
        # For now fall back to mock so the app never crashes.
        logger.warning(
            "ApiFootballProvider: live fetch not fully wired — returning mock data. "
            "Add real HTTP calls when you have a key and rate-limit budget."
        )
        return await MockStatsProvider().fetch_fixtures(status)


class FootyStatsProvider(StatsProvider):
    name = "footystats"

    def __init__(self) -> None:
        self.key = os.getenv("FOOTYSTATS_KEY", "")
        if not self.key:
            raise RuntimeError("FOOTYSTATS_KEY is required for footystats provider")

    async def fetch_fixtures(self, status: MatchStatus) -> list[Fixture]:
        logger.warning(
            "FootyStatsProvider: live fetch not fully wired — returning mock data."
        )
        return await MockStatsProvider().fetch_fixtures(status)


def get_provider() -> StatsProvider:
    name = os.getenv("STATS_PROVIDER", "mock").lower()
    if name == "api_football":
        return ApiFootballProvider()
    if name == "footystats":
        return FootyStatsProvider()
    return MockStatsProvider()


# ── Scouting engine ─────────────────────────────────────────────────────────

async def scout_matches(rule: ParsedRule) -> ScoutResponse:
    provider = get_provider()
    fixtures = await provider.fetch_fixtures(rule.match_status)
    w_min = window_minutes(rule.time_window)
    candidates: list[Selection] = []

    for fx in fixtures:
        sides = _candidate_sides(rule, fx)
        for side, team_name, c_for, c_against, first15 in sides:
            lam = interval_lambda(c_for, c_against, w_min, first15)
            if rule.direction == Direction.UNDER and rule.line <= 0.5:
                prob = poisson_zero(lam)
            elif rule.direction == Direction.UNDER:
                # P(X <= floor(line)) via cumulative Poisson
                k = int(math.floor(rule.line))
                prob = sum(
                    math.exp(-lam) * lam**i / math.factorial(i) for i in range(k + 1)
                )
            else:  # over
                k = int(math.floor(rule.line))
                prob = 1.0 - sum(
                    math.exp(-lam) * lam**i / math.factorial(i) for i in range(k + 1)
                )

            if prob < rule.min_probability:
                continue

            reasoning = (
                f"{team_name}: c90_for={c_for:.1f}, opp c90_against≈{c_against:.1f}, "
                f"window={w_min:.1f}m → λ={lam:.3f}, P={prob:.1%}, fair={fair_odds(prob)}"
            )
            candidates.append(
                Selection(
                    fixture_id=fx.fixture_id,
                    home_team=fx.home_team,
                    away_team=fx.away_team,
                    kickoff_utc=fx.kickoff_utc,
                    league=fx.league,
                    selection_side=side,
                    team_name=team_name,
                    time_window=rule.time_window,
                    line=rule.line,
                    direction=rule.direction.value,
                    lambda_=round(lam, 4),
                    probability=round(prob, 4),
                    fair_odds=fair_odds(prob),
                    reasoning=reasoning,
                )
            )

    # rank by probability descending, take top max_legs
    candidates.sort(key=lambda s: s.probability, reverse=True)
    top = candidates[: rule.max_legs]

    return ScoutResponse(
        selections=top,
        scanned_fixtures=len(fixtures),
        provider=provider.name,
    )


def _candidate_sides(
    rule: ParsedRule, fx: Fixture
) -> list[tuple[str, str, float, float, float]]:
    """Return list of (side, team_name, c90_for, c90_against, first15_share)."""
    h, a = fx.home_stats, fx.away_stats
    if rule.selection_target == SelectionTarget.HOME:
        return [("home", h.team_name, h.c90_for, a.c90_against, h.first15_share)]
    if rule.selection_target == SelectionTarget.AWAY:
        return [("away", a.team_name, a.c90_for, h.c90_against, a.first15_share)]
    if rule.selection_target == SelectionTarget.TOTAL:
        # combined attack rates
        total_for = h.c90_for + a.c90_for
        return [("total", f"{h.team_name} + {a.team_name}", total_for, 0.0, (h.first15_share + a.first15_share) / 2)]
    # lowest_probability_team / both → evaluate both and let ranking decide
    return [
        ("home", h.team_name, h.c90_for, a.c90_against, h.first15_share),
        ("away", a.team_name, a.c90_for, h.c90_against, a.first15_share),
    ]
