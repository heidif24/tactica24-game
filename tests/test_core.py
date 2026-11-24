import asyncio
import math

from backend.builders.mock_builder import MockSlipBuilder
from backend.models import Direction, Fixture, MatchStatus, ParsedRule, Selection, SelectionTarget, TeamCornerStats
from backend.parser import deterministic_parse
from backend.stats_engine import _candidate_sides, _live_fixture_window_is_future, interval_lambda, poisson_zero, window_minutes


def test_first_five_minute_window_is_five_minutes():
    assert window_minutes("00:00-04:59") == 5.0


def test_poisson_zero_probability():
    assert math.isclose(poisson_zero(0.5), math.exp(-0.5), rel_tol=1e-12)


def test_interval_lambda_uses_for_and_against_rates():
    expected = (0.55 * 4.0 + 0.45 * 6.0) * (0.22 * 5 / 15)
    assert math.isclose(interval_lambda(4.0, 6.0, 5.0), expected, rel_tol=1e-12)


def test_home_selection_uses_home_teams_own_against_rate():
    fx = Fixture(
        fixture_id="x", home_team="Home", away_team="Away",
        kickoff_utc="2026-11-24T12:00:00+00:00", league="Test",
        status=MatchStatus.UPCOMING,
        home_stats=TeamCornerStats(team_id="h", team_name="Home", c90_for=4.0, c90_against=2.0),
        away_stats=TeamCornerStats(team_id="a", team_name="Away", c90_for=7.0, c90_against=6.0),
    )
    rule = ParsedRule(selection_target=SelectionTarget.HOME)
    assert _candidate_sides(rule, fx)[0][3] == 2.0


def test_deterministic_parser_defaults_to_one_leg():
    rule = deterministic_parse("No corner in first 5 minutes, minimum 80% probability")
    assert rule.max_legs == 1
    assert rule.min_probability == 0.8


def test_mock_builder_never_mints_a_bookmaker_code():
    selection = Selection(
        fixture_id="x", home_team="Home", away_team="Away",
        kickoff_utc="2026-11-24T12:00:00+00:00", league="Test",
        selection_side="home", team_name="Home", time_window="00:00-04:59",
        line=0.5, direction=Direction.UNDER.value, lambda_=0.2,
        probability=0.8187, fair_odds=1.221, reasoning="test",
    )
    result = asyncio.run(MockSlipBuilder().build([selection]))
    assert result.booking_code is None
    assert result.legs[0].status == "skipped"
    assert "no bookmaker" in " ".join(result.logs).lower()


def test_live_fixture_is_skipped_when_requested_window_has_started():
    from datetime import datetime, timedelta, timezone
    kickoff = (datetime.now(timezone.utc) - timedelta(minutes=12)).isoformat()
    fx = Fixture(
        fixture_id="live", home_team="Home", away_team="Away",
        kickoff_utc=kickoff, league="Test", status=MatchStatus.LIVE,
        home_stats=TeamCornerStats(team_id="h", team_name="Home", c90_for=4, c90_against=4),
        away_stats=TeamCornerStats(team_id="a", team_name="Away", c90_for=4, c90_against=4),
    )
    assert not _live_fixture_window_is_future(fx, "00:00-04:59")
    assert _live_fixture_window_is_future(fx, "15:00-19:59")


def test_total_market_uses_both_teams_rates():
    fx = Fixture(
        fixture_id="total", home_team="Home", away_team="Away",
        kickoff_utc="2026-11-24T12:00:00+00:00", league="Test",
        status=MatchStatus.UPCOMING,
        home_stats=TeamCornerStats(team_id="h", team_name="Home", c90_for=4.0, c90_against=3.0),
        away_stats=TeamCornerStats(team_id="a", team_name="Away", c90_for=6.0, c90_against=5.0),
    )
    rule = ParsedRule(selection_target=SelectionTarget.TOTAL)
    side = _candidate_sides(rule, fx)[0]
    assert side[2] == 10.0
    assert side[3] == 10.0
