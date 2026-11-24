"""Safety tests for the Manage Bet Codes adapter."""
import asyncio
import os

from backend.builders.manage_bet_codes import ManageBetCodesBuilder
from backend.models import Selection


def selection(**updates):
    data = {
        "fixture_id": "fx-1",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "kickoff_utc": "2026-11-25T18:00:00Z",
        "league": "Test League",
        "selection_side": "home",
        "team_name": "Home FC",
        "time_window": "00:00-04:59",
        "line": 0.5,
        "direction": "under",
        "lambda": 0.1,
        "probability": 0.9,
        "fair_odds": 1.111,
        "reasoning": "unit test",
    }
    data.update(updates)
    return Selection(**data)


def test_interval_market_is_never_silently_changed():
    os.environ["MANAGE_BET_CODES_API_KEY"] = "test-placeholder"
    builder = ManageBetCodesBuilder()
    result = asyncio.run(builder.build([selection()]))
    assert result.booking_code is None
    assert result.legs[0].status == "unavailable"
    assert "not a full-match market mapping" in result.logs[-1]


def test_missing_exact_market_mapping_is_rejected():
    os.environ["MANAGE_BET_CODES_API_KEY"] = "test-placeholder"
    builder = ManageBetCodesBuilder()
    item = selection(time_window="full_match")
    result = asyncio.run(builder.build([item]))
    assert result.booking_code is None
    assert result.legs[0].status == "unavailable"
    assert "No exact bookmaker market mapping" in result.logs[-1]
