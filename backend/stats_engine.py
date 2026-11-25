"""Pluggable stats providers + Poisson early-interval corner engine."""

from __future__ import annotations

import logging
import math
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


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

DEFAULT_FIRST15_SHARE = 0.22


def window_bounds(window: str) -> tuple[float, float]:
    if window in ("full_match", "90", "match"):
        return 0.0, 90.0
    if window == "00:00-44:59":
        return 0.0, 45.0
    if window == "45:00-89:59":
        return 45.0, 90.0
    m = re.match(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", window)
    if not m:
        raise ValueError(f"Invalid interval: {window}")
    start = int(m.group(1)) * 60 + int(m.group(2))
    end = int(m.group(3)) * 60 + int(m.group(4))
    if end < start:
        raise ValueError(f"Invalid interval: {window}")
    return start / 60.0, (end + 1) / 60.0


def window_minutes(window: str) -> float:
    start, end = window_bounds(window)
    return max(end - start, 0.5)


def _live_fixture_window_is_future(fixture: Fixture, window: str) -> bool:
    """Do not recommend a live interval once it has started."""
    if fixture.status != MatchStatus.LIVE:
        return True
    if window in ("full_match", "90", "match"):
        return False
    try:
        kickoff = datetime.fromisoformat(fixture.kickoff_utc.replace("Z", "+00:00"))
        if kickoff.tzinfo is None:
            kickoff = kickoff.replace(tzinfo=timezone.utc)
        elapsed = max((datetime.now(timezone.utc) - kickoff.astimezone(timezone.utc)).total_seconds() / 60.0, 0.0)
        start_min, _ = window_bounds(window)
        return elapsed < start_min
    except (TypeError, ValueError):
        logger.warning("Skipping live fixture with invalid kickoff time: %s", fixture.fixture_id)
        return False


def poisson_zero(lambda_: float) -> float:
    return math.exp(-max(lambda_, 0.0))


def fair_odds(prob: float) -> float:
    if prob <= 0:
        return 999.0
    return round(1.0 / prob, 3)


def interval_lambda(
    c90_for: float,
    c90_against: float | None,
    window_min: float,
    first15_share: float = DEFAULT_FIRST15_SHARE,
    blend: float = 0.55,
) -> float:
    if c90_against is None:
        return 0.0
    rate_90 = blend * c90_for + (1 - blend) * c90_against
    if window_min >= 89.5:
        share = 1.0
    else:
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
    """Realistic offline sample set — full pipeline works with zero API keys."""

    name = "mock"

    async def fetch_fixtures(self, status: MatchStatus) -> list[Fixture]:
        now = datetime.now(timezone.utc)
        samples = [
            _fx("m1", "Atletico Madrid", "Getafe", now + timedelta(hours=2),
                "La Liga", MatchStatus.UPCOMING, 3.8, 3.2, 3.1, 4.0),
            _fx("m2", "Burnley", "Sheffield United", now + timedelta(hours=3),
                "Championship", MatchStatus.UPCOMING, 4.1, 4.5, 3.9, 4.8),
            _fx("m3", "Inter Milan", "Torino", now + timedelta(hours=1),
                "Serie A", MatchStatus.UPCOMING, 5.2, 3.4, 3.6, 4.9),
            _fx("m4", "Nantes", "Reims", now + timedelta(minutes=40),
                "Ligue 1", MatchStatus.UPCOMING, 4.0, 4.2, 3.8, 4.4),
            _fx("m5", "Mainz 05", "Augsburg", now + timedelta(hours=4),
                "Bundesliga", MatchStatus.UPCOMING, 4.6, 5.1, 4.3, 5.0),
            _fx("m6", "Liverpool", "Brighton", now + timedelta(hours=2),
                "Premier League", MatchStatus.UPCOMING, 7.1, 4.8, 5.9, 6.2),
            _fx("m7", "Manchester City", "Newcastle", now + timedelta(hours=5),
                "Premier League", MatchStatus.UPCOMING, 7.8, 4.2, 5.5, 6.8),
            _fx("m8", "Bayern Munich", "Wolfsburg", now + timedelta(hours=3),
                "Bundesliga", MatchStatus.UPCOMING, 7.4, 3.9, 4.7, 6.5),
            _fx("m9", "Osasuna", "Celta Vigo", now - timedelta(minutes=8),
                "La Liga", MatchStatus.LIVE, 4.2, 4.0, 4.5, 4.3),
            _fx("m10", "Lazio", "Empoli", now - timedelta(minutes=15),
                "Serie A", MatchStatus.LIVE, 5.0, 3.7, 3.5, 5.1),
            _fx("m11", "Brentford", "Crystal Palace", now + timedelta(hours=6),
                "Premier League", MatchStatus.UPCOMING, 5.3, 5.0, 4.9, 5.4),
            _fx("m12", "Strasbourg", "Lorient", now + timedelta(hours=1),
                "Ligue 1", MatchStatus.UPCOMING, 4.4, 4.6, 4.1, 4.7),
        ]
        if status == MatchStatus.LIVE:
            return [f for f in samples if f.status == MatchStatus.LIVE]
        if status == MatchStatus.UPCOMING:
            return [f for f in samples if f.status == MatchStatus.UPCOMING]
        return samples


def _fx(
    fid: str, home: str, away: str, kickoff: datetime, league: str,
    status: MatchStatus, h_for: float, h_against: float, a_for: float, a_against: float,
) -> Fixture:
    return Fixture(
        fixture_id=fid,
        home_team=home,
        away_team=away,
        kickoff_utc=kickoff.isoformat(),
        league=league,
        status=status,
        home_stats=TeamCornerStats(team_id=f"{fid}_h", team_name=home, c90_for=h_for, c90_against=h_against),
        away_stats=TeamCornerStats(team_id=f"{fid}_a", team_name=away, c90_for=a_for, c90_against=a_against),
    )


def get_provider() -> StatsProvider:
    """Legacy local stats engine is disabled for production research.

    Only explicit mock mode is permitted for isolated development/tests.
    Live analysis must use backend.research_engine, which requires grounded
    Gemini/Groq web evidence and never substitutes mock fixtures.
    """
    name = os.getenv("STATS_PROVIDER", "disabled").lower()
    if name == "mock":
        return MockStatsProvider()
    raise RuntimeError(
        "The legacy fixture-statistics engine is disabled. "
        "Use the Gemini/Groq grounded web-research pipeline; no API-Football, "
        "FootyStats or demonstration statistics are used for live analysis."
    )


# ── Scouting engine ─────────────────────────────────────────────────────────

def _poisson_cdf(lam: float, line: float) -> float:
    k = int(math.floor(line))
    return sum(math.exp(-lam) * lam**i / math.factorial(i) for i in range(k + 1))


def _goal_rate(for_rate: float | None, against_rate: float | None) -> float | None:
    if for_rate is None or against_rate is None:
        return None
    return max(0.05, 0.55 * for_rate + 0.45 * against_rate)


def _result_probabilities(home_lam: float, away_lam: float) -> dict[str, float]:
    def dist(lam: float) -> list[float]:
        values = [math.exp(-lam)]
        for i in range(1, 13):
            values.append(values[-1] * lam / i)
        total = sum(values)
        return [v / total for v in values]
    hp, ap = dist(home_lam), dist(away_lam)
    result = {"home": 0.0, "draw": 0.0, "away": 0.0}
    for h, ph in enumerate(hp):
        for a, pa in enumerate(ap):
            result["home" if h > a else "draw" if h == a else "away"] += ph * pa
    return result


async def scout_matches(rule: ParsedRule) -> ScoutResponse:
    from backend.calibration import calibrate_probability

    provider = get_provider()
    fixtures = await provider.fetch_fixtures(rule.match_status)
    candidates: list[Selection] = []
    category = rule.market_category.lower()
    is_full_match = rule.time_window in ("full_match", "90", "match")

    for fx in fixtures:
        if not _live_fixture_window_is_future(fx, rule.time_window):
            continue
        h, a = fx.home_stats, fx.away_stats
        computed: list[tuple[str, str, float, float, str]] = []

        if category == "corners":
            w_min = window_minutes(rule.time_window)
            for side, team_name, c_for, c_against, first15 in _candidate_sides(rule, fx):
                if c_against is None:
                    continue
                lam = interval_lambda(c_for, c_against, w_min, first15)
                prob = _poisson_cdf(lam, rule.line)
                if rule.direction == Direction.OVER:
                    prob = 1.0 - prob
                computed.append((side, team_name, lam, prob, "over" if rule.direction == Direction.OVER else "under"))
        elif category in ("goals", "btts", "result", "double_chance"):
            # Season aggregates cannot support exact minute-interval predictions.
            if not is_full_match:
                continue
            h_lam = _goal_rate(h.g90_for, a.g90_against)
            a_lam = _goal_rate(a.g90_for, h.g90_against)
            if h_lam is None or a_lam is None:
                continue
            if category == "goals":
                if rule.selection_target == SelectionTarget.HOME:
                    lam, side, team_name = h_lam, "home", h.team_name
                elif rule.selection_target == SelectionTarget.AWAY:
                    lam, side, team_name = a_lam, "away", a.team_name
                else:
                    lam, side, team_name = h_lam + a_lam, "total", f"{h.team_name} + {a.team_name}"
                prob = _poisson_cdf(lam, rule.line)
                if rule.direction == Direction.OVER:
                    prob = 1.0 - prob
                computed.append((side, team_name, lam, prob, "over" if rule.direction == Direction.OVER else "under"))
            elif category == "btts":
                yes_prob = (1.0 - math.exp(-h_lam)) * (1.0 - math.exp(-a_lam))
                outcome = (rule.outcome or "Yes").lower()
                prob = yes_prob if outcome == "yes" else 1.0 - yes_prob
                computed.append(("both", f"{h.team_name} + {a.team_name}", h_lam + a_lam, prob, outcome))
            elif category == "result":
                side = rule.selection_target.value
                probs = _result_probabilities(h_lam, a_lam)
                if side not in probs:
                    continue
                computed.append((side, f"{h.team_name} vs {a.team_name}", h_lam + a_lam, probs[side], side))
            else:
                probs = _result_probabilities(h_lam, a_lam)
                outcome = (rule.outcome or "1X").upper()
                double_chance = {
                    "1X": probs["home"] + probs["draw"],
                    "X2": probs["draw"] + probs["away"],
                    "12": probs["home"] + probs["away"],
                }
                if outcome not in double_chance:
                    continue
                computed.append((outcome.lower(), f"{h.team_name} vs {a.team_name}", h_lam + a_lam, double_chance[outcome], outcome))
        else:
            # Cards and other categories require observed event-level data.
            continue

        if rule.selection_target in (SelectionTarget.HIGHEST_PROBABILITY_TEAM, SelectionTarget.LOWEST_PROBABILITY_TEAM) and computed:
            # Probability is for the requested market outcome (Over or Under),
            # so choose the side with the highest probability of that outcome.
            computed = [max(computed, key=lambda item: item[3])]

        for side, team_name, lam, raw_prob, outcome in computed:
            if raw_prob < rule.min_probability:
                continue
            calibrated, sample_count = calibrate_probability(
                category, rule.sub_market, rule.time_window, raw_prob, "tactica24-poisson-v2"
            )
            final_prob = calibrated if calibrated is not None else raw_prob
            status = "calibrated" if calibrated is not None else "uncalibrated"
            reason = (
                f"{category} model: lambda={lam:.3f}; raw P={raw_prob:.1%}; "
                + (f"conservative calibrated P={final_prob:.1%} from {sample_count} historical forecasts"
                   if calibrated is not None else "insufficient out-of-sample calibration evidence")
            )
            candidates.append(Selection(
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
                probability=round(final_prob, 4),
                fair_odds=fair_odds(final_prob),
                reasoning=reason,
                market_category=category,
                sub_market=rule.sub_market,
                bookmaker_outcome=rule.outcome or outcome.title(),
                calibration_status=status,
                calibration_samples=sample_count,
                raw_probability=round(raw_prob, 4),
                calibrated_probability=round(calibrated, 4) if calibrated is not None else None,
                model_version="tactica24-poisson-v2",
            ))

    candidates.sort(key=lambda s: (s.calibration_status == "calibrated", s.probability), reverse=True)
    return ScoutResponse(selections=candidates[: rule.max_legs], scanned_fixtures=len(fixtures), provider=provider.name)

def _candidate_sides(
    rule: ParsedRule, fx: Fixture
) -> list[tuple[str, str, float, float, float]]:
    h, a = fx.home_stats, fx.away_stats
    if rule.selection_target == SelectionTarget.HOME:
        return [("home", h.team_name, h.c90_for, h.c90_against, h.first15_share)]
    if rule.selection_target == SelectionTarget.AWAY:
        return [("away", a.team_name, a.c90_for, a.c90_against, a.first15_share)]
    if rule.selection_target == SelectionTarget.TOTAL:
        if h.c90_against is None or a.c90_against is None:
            return []
        total_for = h.c90_for + a.c90_for
        total_against = h.c90_against + a.c90_against
        return [("total", f"{h.team_name} + {a.team_name}", total_for, total_against,
                 (h.first15_share + a.first15_share) / 2)]
    return [
        ("home", h.team_name, h.c90_for, h.c90_against, h.first15_share),
        ("away", a.team_name, a.c90_for, a.c90_against, a.first15_share),
    ]
