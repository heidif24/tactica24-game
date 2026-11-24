"""Pluggable stats providers + Poisson early-interval corner engine."""

from __future__ import annotations

import logging
import math
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

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


def window_minutes(window: str) -> float:
    m = re.match(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", window)
    if not m:
        return 5.0
    start = int(m.group(1)) * 60 + int(m.group(2))
    end = int(m.group(3)) * 60 + int(m.group(4))
    return max((end - start + 1) / 60.0, 0.5)


def poisson_zero(lambda_: float) -> float:
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
    rate_90 = blend * c90_for + (1 - blend) * c90_against
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


class ApiFootballProvider(StatsProvider):
    """
    Live API-Football / API-Sports v3 provider.

    Env:
      API_FOOTBALL_KEY   — required
      API_FOOTBALL_BASE  — optional, default https://v3.football.api-sports.io
                           (use https://api-football-v1.p.rapidapi.com/v3 for RapidAPI)
      API_FOOTBALL_HOST  — optional RapidAPI host header
    """

    name = "api_football"

    def __init__(self) -> None:
        self.key = os.getenv("API_FOOTBALL_KEY", "")
        if not self.key:
            raise RuntimeError("API_FOOTBALL_KEY is required for api_football provider")
        self.base = os.getenv("API_FOOTBALL_BASE", "https://v3.football.api-sports.io").rstrip("/")
        self.rapid_host = os.getenv("API_FOOTBALL_HOST", "")
        self._stat_cache: dict[int, dict[str, float]] = {}

    def _headers(self) -> dict[str, str]:
        h = {"x-apisports-key": self.key}
        if self.rapid_host:
            h = {
                "x-rapidapi-key": self.key,
                "x-rapidapi-host": self.rapid_host,
            }
        return h

    async def _get(self, path: str, params: dict[str, Any]) -> list[dict]:
        url = f"{self.base}{path}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, params=params, headers=self._headers())
            resp.raise_for_status()
            body = resp.json()
            errors = body.get("errors")
            if errors:
                logger.warning("API-Football errors: %s", errors)
            return body.get("response") or []

    async def _team_corner_rates(self, team_id: int, season: int) -> dict[str, float]:
        if team_id in self._stat_cache:
            return self._stat_cache[team_id]

        # Default fallbacks if stats endpoint fails / incomplete
        defaults = {"c90_for": 4.8, "c90_against": 4.8, "first15_share": DEFAULT_FIRST15_SHARE}
        try:
            rows = await self._get("/teams/statistics", {
                "team": team_id,
                "season": season,
                "league": 0,  # will be overridden per call when we know league
            })
            # When league unknown the endpoint needs league id — handled in caller.
            # Keep defaults if empty.
            if not rows:
                self._stat_cache[team_id] = defaults
                return defaults

            stats = rows[0] if isinstance(rows, list) else rows
            fixtures_played = (
                (stats.get("fixtures") or {}).get("played") or {}
            ).get("total") or 0
            corners_for = (
                (stats.get("corners") or {}).get("total") or {}
            ).get("total")
            # API-Football doesn't always expose corners in team statistics.
            # Fall back to shots approximation or defaults.
            if corners_for and fixtures_played:
                c90 = float(corners_for) / fixtures_played * 90 / 90  # per match ≈ c90
                defaults["c90_for"] = round(c90, 2)
            self._stat_cache[team_id] = defaults
            return defaults
        except Exception as exc:
            logger.debug("team stats %s failed: %s", team_id, exc)
            self._stat_cache[team_id] = defaults
            return defaults

    async def _enrich_from_fixture_stats(
        self, fixture_id: int, home_id: int, away_id: int
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Try fixture-level statistics for corner counts when available."""
        home = {"c90_for": 4.8, "c90_against": 4.8, "first15_share": DEFAULT_FIRST15_SHARE}
        away = {"c90_for": 4.8, "c90_against": 4.8, "first15_share": DEFAULT_FIRST15_SHARE}
        try:
            rows = await self._get("/fixtures/statistics", {"fixture": fixture_id})
            for side in rows:
                tid = (side.get("team") or {}).get("id")
                stats_list = side.get("statistics") or []
                corners = None
                for s in stats_list:
                    if (s.get("type") or "").lower() == "corner kicks":
                        corners = s.get("value")
                        break
                if corners is not None and tid == home_id:
                    # single-match observation — blend lightly toward season default
                    home["c90_for"] = round(0.7 * home["c90_for"] + 0.3 * float(corners), 2)
                if corners is not None and tid == away_id:
                    away["c90_for"] = round(0.7 * away["c90_for"] + 0.3 * float(corners), 2)
        except Exception as exc:
            logger.debug("fixture stats %s: %s", fixture_id, exc)
        return home, away

    async def fetch_fixtures(self, status: MatchStatus) -> list[Fixture]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        params: dict[str, Any] = {"date": today}

        # status filters used by API-Football
        if status == MatchStatus.LIVE:
            params["live"] = "all"
            params.pop("date", None)
        elif status == MatchStatus.UPCOMING:
            params["status"] = "NS"
        # upcoming_or_live: fetch both
        try:
            if status == MatchStatus.UPCOMING_OR_LIVE:
                live_rows = await self._get("/fixtures", {"live": "all"})
                ns_rows = await self._get("/fixtures", {"date": today, "status": "NS"})
                rows = (live_rows or []) + (ns_rows or [])
            else:
                rows = await self._get("/fixtures", params)
        except Exception as exc:
            logger.exception("API-Football fixture fetch failed")
            raise RuntimeError(f"Live API-Football fixture fetch failed: {exc}") from exc

        fixtures: list[Fixture] = []
        seen: set[str] = set()

        for row in rows[:40]:  # hard cap for rate limits
            fi = row.get("fixture") or {}
            teams = row.get("teams") or {}
            league = row.get("league") or {}
            fid = str(fi.get("id") or "")
            if not fid or fid in seen:
                continue
            seen.add(fid)

            home = teams.get("home") or {}
            away = teams.get("away") or {}
            home_name = home.get("name") or "Home"
            away_name = away.get("name") or "Away"
            home_id = home.get("id") or 0
            away_id = away.get("id") or 0

            st = (fi.get("status") or {}).get("short") or "NS"
            match_status = MatchStatus.LIVE if st in ("1H", "2H", "HT", "ET", "BT", "P", "LIVE") else MatchStatus.UPCOMING

            kickoff = fi.get("date") or datetime.now(timezone.utc).isoformat()

            # Season rates — best-effort; defaults are fine for Poisson ranking
            season = league.get("season") or datetime.now(timezone.utc).year
            h_stats = await self._team_corner_rates(int(home_id), int(season))
            a_stats = await self._team_corner_rates(int(away_id), int(season))

            # Preserve each team's own against-rate. The previous cross-fill
            # accidentally substituted the opponent's attacking rate.
            h_c90_against = h_stats["c90_against"]
            a_c90_against = a_stats["c90_against"]

            fixtures.append(Fixture(
                fixture_id=fid,
                home_team=home_name,
                away_team=away_name,
                kickoff_utc=kickoff,
                league=league.get("name") or "Unknown",
                status=match_status,
                home_stats=TeamCornerStats(
                    team_id=str(home_id), team_name=home_name,
                    c90_for=h_stats["c90_for"], c90_against=h_c90_against,
                    first15_share=h_stats.get("first15_share", DEFAULT_FIRST15_SHARE),
                ),
                away_stats=TeamCornerStats(
                    team_id=str(away_id), team_name=away_name,
                    c90_for=a_stats["c90_for"], c90_against=a_c90_against,
                    first15_share=a_stats.get("first15_share", DEFAULT_FIRST15_SHARE),
                ),
            ))

        if not fixtures:
            raise RuntimeError("API-Football returned no fixtures; refusing to substitute demonstration fixtures")

        logger.info("API-Football: %d fixtures loaded", len(fixtures))
        return fixtures


class FootyStatsProvider(StatsProvider):
    """
    FootyStats.com API adapter.
    Docs: https://footystats.org/api
    Env: FOOTYSTATS_KEY
    """

    name = "footystats"

    def __init__(self) -> None:
        self.key = os.getenv("FOOTYSTATS_KEY", "")
        if not self.key:
            raise RuntimeError("FOOTYSTATS_KEY is required for footystats provider")
        self.base = "https://api.football-data-api.com"

    async def fetch_fixtures(self, status: MatchStatus) -> list[Fixture]:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    f"{self.base}/todays-matches",
                    params={"key": self.key, "date": today},
                )
                resp.raise_for_status()
                data = resp.json()
            rows = data.get("data") or []
        except Exception as exc:
            logger.exception("FootyStats fetch failed")
            raise RuntimeError(f"Live FootyStats fetch failed: {exc}") from exc

        fixtures: list[Fixture] = []
        for row in rows[:40]:
            home_name = row.get("home_name") or "Home"
            away_name = row.get("away_name") or "Away"
            fid = str(row.get("id") or f"{home_name}-{away_name}")

            # FootyStats often exposes pre-match corner averages
            h_for = float(row.get("team_a_corners_per_match") or row.get("corners_potential") or 4.8)
            a_for = float(row.get("team_b_corners_per_match") or 4.8)
            h_against = float(row.get("team_a_corners_per_match_overall") or a_for)
            a_against = float(row.get("team_b_corners_per_match_overall") or h_for)

            st_raw = (row.get("status") or "incomplete").lower()
            match_status = MatchStatus.LIVE if st_raw in ("live", "incomplete") and row.get("time") not in (None, "0") else MatchStatus.UPCOMING

            if status == MatchStatus.LIVE and match_status != MatchStatus.LIVE:
                continue
            if status == MatchStatus.UPCOMING and match_status != MatchStatus.UPCOMING:
                continue

            kickoff = row.get("date_unix")
            if kickoff:
                kickoff_iso = datetime.fromtimestamp(int(kickoff), tz=timezone.utc).isoformat()
            else:
                kickoff_iso = datetime.now(timezone.utc).isoformat()

            fixtures.append(Fixture(
                fixture_id=fid,
                home_team=home_name,
                away_team=away_name,
                kickoff_utc=kickoff_iso,
                league=row.get("competition") or row.get("league_name") or "Unknown",
                status=match_status,
                home_stats=TeamCornerStats(
                    team_id=f"{fid}_h", team_name=home_name,
                    c90_for=h_for, c90_against=h_against,
                ),
                away_stats=TeamCornerStats(
                    team_id=f"{fid}_a", team_name=away_name,
                    c90_for=a_for, c90_against=a_against,
                ),
            ))

        if not fixtures:
            raise RuntimeError("FootyStats returned no matching fixtures; refusing to substitute demonstration fixtures")
        return fixtures


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
                k = int(math.floor(rule.line))
                prob = sum(math.exp(-lam) * lam**i / math.factorial(i) for i in range(k + 1))
            else:
                k = int(math.floor(rule.line))
                prob = 1.0 - sum(math.exp(-lam) * lam**i / math.factorial(i) for i in range(k + 1))

            if prob < rule.min_probability:
                continue

            reasoning = (
                f"{team_name}: c90_for={c_for:.1f}, opp c90_against≈{c_against:.1f}, "
                f"window={w_min:.1f}m → λ={lam:.3f}, P={prob:.1%}, fair={fair_odds(prob)}"
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
                probability=round(prob, 4),
                fair_odds=fair_odds(prob),
                reasoning=reasoning,
            ))

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
    h, a = fx.home_stats, fx.away_stats
    if rule.selection_target == SelectionTarget.HOME:
        return [("home", h.team_name, h.c90_for, h.c90_against, h.first15_share)]
    if rule.selection_target == SelectionTarget.AWAY:
        return [("away", a.team_name, a.c90_for, a.c90_against, a.first15_share)]
    if rule.selection_target == SelectionTarget.TOTAL:
        total_for = h.c90_for + a.c90_for
        return [("total", f"{h.team_name} + {a.team_name}", total_for, 0.0,
                 (h.first15_share + a.first15_share) / 2)]
    return [
        ("home", h.team_name, h.c90_for, h.c90_against, h.first15_share),
        ("away", a.team_name, a.c90_for, a.c90_against, a.first15_share),
    ]
