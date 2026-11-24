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
    c90_against: float,
    window_min: float,
    first15_share: float = DEFAULT_FIRST15_SHARE,
    blend: float = 0.55,
) -> float:
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
        self._stat_cache: dict[tuple[int, int, int], dict[str, float]] = {}

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

    async def _team_corner_rates(self, team_id: int, season: int, league_id: int) -> dict[str, float]:
        cache_key = (team_id, season, league_id)
        if cache_key in self._stat_cache:
            return self._stat_cache[cache_key]

        rows = await self._get("/teams/statistics", {
            "team": team_id,
            "season": season,
            "league": league_id,
        })
        if not rows:
            raise RuntimeError(
                f"API-Football returned no season statistics for team {team_id} in league {league_id}"
            )
        stats = rows[0] if isinstance(rows, list) else rows
        fixtures_played = ((stats.get("fixtures") or {}).get("played") or {}).get("total") or 0
        corners_for = ((stats.get("corners") or {}).get("total") or {}).get("total")
        if not corners_for or not fixtures_played:
            raise RuntimeError(
                f"API-Football did not supply usable corner totals for team {team_id}; "
                "the app will not substitute assumed team averages"
            )
        goals = stats.get("goals") or {}
        goals_for = ((goals.get("for") or {}).get("total") or {}).get("total")
        goals_against = ((goals.get("against") or {}).get("total") or {}).get("total")
        rates = {
            "c90_for": round(float(corners_for) / float(fixtures_played), 2),
            "c90_against": 4.8,
            "first15_share": DEFAULT_FIRST15_SHARE,
            "g90_for": round(float(goals_for) / float(fixtures_played), 3) if goals_for is not None else None,
            "g90_against": round(float(goals_against) / float(fixtures_played), 3) if goals_against is not None else None,
        }
        self._stat_cache[cache_key] = rates
        return rates

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
            league_id = int(league.get("id") or 0)
            if not league_id:
                raise RuntimeError("API-Football fixture is missing its league identifier")
            h_stats = await self._team_corner_rates(int(home_id), int(season), league_id)
            a_stats = await self._team_corner_rates(int(away_id), int(season), league_id)

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
                    g90_for=h_stats.get("g90_for"), g90_against=h_stats.get("g90_against"),
                ),
                away_stats=TeamCornerStats(
                    team_id=str(away_id), team_name=away_name,
                    c90_for=a_stats["c90_for"], c90_against=a_c90_against,
                    first15_share=a_stats.get("first15_share", DEFAULT_FIRST15_SHARE),
                    g90_for=a_stats.get("g90_for"), g90_against=a_stats.get("g90_against"),
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
            required = ("team_a_corners_per_match", "team_b_corners_per_match")
            if any(row.get(key) is None for key in required):
                logger.warning("Skipping FootyStats fixture %s: corner averages missing", fid)
                continue
            h_for = float(row["team_a_corners_per_match"])
            a_for = float(row["team_b_corners_per_match"])
            h_against = float(row.get("team_a_corners_against_per_match") or 4.8)
            a_against = float(row.get("team_b_corners_against_per_match") or 4.8)
            h_goals = row.get("team_a_goals_per_match")
            a_goals = row.get("team_b_goals_per_match")
            h_goals_against = row.get("team_a_goals_against_per_match")
            a_goals_against = row.get("team_b_goals_against_per_match")

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
                    g90_for=float(h_goals) if h_goals is not None else None,
                    g90_against=float(h_goals_against) if h_goals_against is not None else None,
                ),
                away_stats=TeamCornerStats(
                    team_id=f"{fid}_a", team_name=away_name,
                    c90_for=a_for, c90_against=a_against,
                    g90_for=float(a_goals) if a_goals is not None else None,
                    g90_against=float(a_goals_against) if a_goals_against is not None else None,
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
                lam = interval_lambda(c_for, c_against, w_min, first15)
                prob = _poisson_cdf(lam, rule.line)
                if rule.direction == Direction.OVER:
                    prob = 1.0 - prob
                computed.append((side, team_name, lam, prob, "over" if rule.direction == Direction.OVER else "under"))
        elif category in ("goals", "btts", "result"):
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
            else:
                side = rule.selection_target.value
                probs = _result_probabilities(h_lam, a_lam)
                if side not in probs:
                    continue
                computed.append((side, f"{h.team_name} vs {a.team_name}", h_lam + a_lam, probs[side], side))
        else:
            # Cards and other categories require observed event-level data.
            continue

        for side, team_name, lam, raw_prob, outcome in computed:
            if raw_prob < rule.min_probability:
                continue
            calibrated, sample_count = calibrate_probability(
                category, rule.sub_market, rule.time_window, raw_prob
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
        total_for = h.c90_for + a.c90_for
        return [("total", f"{h.team_name} + {a.team_name}", total_for, total_for,
                 (h.first15_share + a.first15_share) / 2)]
    return [
        ("home", h.team_name, h.c90_for, h.c90_against, h.first15_share),
        ("away", a.team_name, a.c90_for, a.c90_against, a.first15_share),
    ]
