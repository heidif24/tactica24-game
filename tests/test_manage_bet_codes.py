"""Manage Bet Codes adapter safety and end-to-end contract tests."""
import asyncio
import os

import pytest

from backend.builders import manage_bet_codes as builder_module
from backend.builders.manage_bet_codes import ManageBetCodesBuilder
from backend.market_discovery import ManageBetCodesMarketDiscovery
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
        "time_window": "full_match",
        "line": 0.5,
        "direction": "under",
        "lambda": 0.1,
        "probability": 0.9,
        "fair_odds": 1.111,
        "reasoning": "unit test",
        "market_category": "corners",
        "sub_market": "team_corners",
        "bookmaker_outcome": "Under",
        "calibration_status": "calibrated",
        "calibration_samples": 200,
    }
    data.update(updates)
    return Selection(**data)


def test_missing_exact_market_is_rejected(monkeypatch):
    monkeypatch.setenv("MANAGE_BET_CODES_API_KEY", "test-placeholder")
    monkeypatch.setenv("T24_REQUIRE_CALIBRATED", "false")
    async def no_market(*args, **kwargs):
        return None
    monkeypatch.setattr(ManageBetCodesMarketDiscovery, "discover", no_market)
    result = asyncio.run(ManageBetCodesBuilder().build([selection()]))
    assert result.booking_code is None
    assert result.legs[0].status == "unavailable"
    assert "No unique, exact" in result.logs[-1]


def test_interval_without_bookmaker_market_is_never_substituted(monkeypatch):
    monkeypatch.setenv("MANAGE_BET_CODES_API_KEY", "test-placeholder")
    monkeypatch.setenv("T24_REQUIRE_CALIBRATED", "false")
    async def no_market(*args, **kwargs):
        return None
    monkeypatch.setattr(ManageBetCodesMarketDiscovery, "discover", no_market)
    result = asyncio.run(ManageBetCodesBuilder().build([
        selection(time_window="00:00-04:59", sub_market="team_interval_corners")
    ]))
    assert result.booking_code is None
    assert "period 00:00-04:59" in result.logs[-1]
    assert "No substitute market" in result.logs[-1]


def test_calibration_gate_prevents_provider_calls(monkeypatch):
    monkeypatch.setenv("MANAGE_BET_CODES_API_KEY", "test-placeholder")
    monkeypatch.setenv("T24_REQUIRE_CALIBRATED", "true")
    async def should_not_search(*args, **kwargs):
        raise AssertionError("provider search must not run without calibration")
    monkeypatch.setattr(ManageBetCodesMarketDiscovery, "discover", should_not_search)
    result = asyncio.run(ManageBetCodesBuilder().build([
        selection(calibration_status="uncalibrated", calibration_samples=0)
    ]))
    assert result.booking_code is None
    assert "calibration is required" in result.logs[-1]


class FakeResponse:
    def __init__(self, body):
        self.body = body
    def raise_for_status(self):
        return None
    def json(self):
        return self.body


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.calls = []
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        return False
    async def post(self, url, headers=None, json=None):
        self.calls.append((url, json))
        if url.endswith("/resolve"):
            return FakeResponse({
                "plan_id": "plan-test",
                "picks": [{"status": "resolved", "bookable": True}],
            })
        return FakeResponse({
            "success": True,
            "verified": True,
            "code": "A1B2C",
            "picks": [{"event_id": "evt-1"}],
            "failures": [],
        })


def test_resolve_book_returns_only_provider_verified_complete_code(monkeypatch):
    monkeypatch.setenv("MANAGE_BET_CODES_API_KEY", "test-placeholder")
    monkeypatch.setenv("T24_REQUIRE_CALIBRATED", "false")
    async def exact_market(*args, **kwargs):
        return {
            "event_id": "evt-1", "key": "pick-1", "market": "Team Corners",
            "outcome": "Under", "line": "0.5", "odds": "1.80",
        }
    monkeypatch.setattr(ManageBetCodesMarketDiscovery, "discover", exact_market)
    monkeypatch.setattr(builder_module.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(ManageBetCodesBuilder().build([selection()]))
    assert result.booking_code == "A1B2C"
    assert result.legs[0].status == "matched"


def test_unverified_provider_code_is_never_released(monkeypatch):
    monkeypatch.setenv("MANAGE_BET_CODES_API_KEY", "test-placeholder")
    monkeypatch.setenv("T24_REQUIRE_CALIBRATED", "false")
    async def exact_market(*args, **kwargs):
        return {
            "event_id": "evt-1", "key": "pick-1", "market": "Team Corners",
            "outcome": "Under", "line": "0.5", "odds": "1.80",
        }
    class UnverifiedClient(FakeClient):
        async def post(self, url, headers=None, json=None):
            if url.endswith("/resolve"):
                return FakeResponse({"plan_id": "plan-test", "picks": [{"status": "resolved"}]})
            return FakeResponse({
                "success": True, "verified": False, "code": "A1B2C",
                "picks": [{"event_id": "evt-1"}], "failures": [],
            })
    monkeypatch.setattr(ManageBetCodesMarketDiscovery, "discover", exact_market)
    monkeypatch.setattr(builder_module.httpx, "AsyncClient", UnverifiedClient)
    result = asyncio.run(ManageBetCodesBuilder().build([selection()]))
    assert result.booking_code is None
    assert result.legs[0].status == "unavailable"
