"""Pydantic schemas for SlipForge."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class MatchStatus(str, Enum):
    UPCOMING = "upcoming"
    LIVE = "live"
    UPCOMING_OR_LIVE = "upcoming_or_live"


class Direction(str, Enum):
    UNDER = "under"
    OVER = "over"


class SelectionTarget(str, Enum):
    LOWEST_PROBABILITY_TEAM = "lowest_probability_team"
    HOME = "home"
    AWAY = "away"
    BOTH = "both"
    TOTAL = "total"


class ParsedRule(BaseModel):
    sport: str = "football"
    market_category: str = "corners"
    sub_market: str = "team_interval_corners"
    time_window: str = Field(
        default="00:00-04:59",
        description="Interval in MM:SS-MM:SS or shorthand like first_5 / first_15",
    )
    selection_target: SelectionTarget = SelectionTarget.LOWEST_PROBABILITY_TEAM
    line: float = 0.5
    direction: Direction = Direction.UNDER
    min_probability: float = Field(default=0.75, ge=0.0, le=1.0)
    max_legs: int = Field(default=3, ge=1, le=20)
    match_status: MatchStatus = MatchStatus.UPCOMING_OR_LIVE

    @field_validator("time_window")
    @classmethod
    def normalize_window(cls, v: str) -> str:
        aliases = {
            "first_5": "00:00-04:59",
            "first5": "00:00-04:59",
            "first_15": "00:00-14:59",
            "first15": "00:00-14:59",
            "0-5": "00:00-04:59",
            "0-15": "00:00-14:59",
        }
        key = v.strip().lower().replace(" ", "_")
        return aliases.get(key, v.strip())


class ParseRuleRequest(BaseModel):
    prompt: str = Field(..., min_length=5)
    max_legs: Optional[int] = None
    min_probability: Optional[float] = None


class ParseRuleResponse(BaseModel):
    rule: ParsedRule
    raw_prompt: str
    parser_used: str  # "llm" | "deterministic"


class TeamCornerStats(BaseModel):
    team_id: str
    team_name: str
    c90_for: float
    c90_against: float
    first15_share: float = 0.22  # fraction of corners in first 15 min


class Fixture(BaseModel):
    fixture_id: str
    home_team: str
    away_team: str
    kickoff_utc: str
    league: str
    status: MatchStatus
    home_stats: TeamCornerStats
    away_stats: TeamCornerStats


class Selection(BaseModel):
    fixture_id: str
    home_team: str
    away_team: str
    kickoff_utc: str
    league: str
    selection_side: str  # "home" | "away" | "total"
    team_name: str
    time_window: str
    line: float
    direction: str
    lambda_: float = Field(..., alias="lambda")
    probability: float
    fair_odds: float
    reasoning: str
    status: str = "pending"  # pending | matched | unavailable | skipped
    found_odds: Optional[float] = None
    market_note: Optional[str] = None

    model_config = {"populate_by_name": True}


class ScoutRequest(BaseModel):
    rule: ParsedRule


class ScoutResponse(BaseModel):
    selections: list[Selection]
    scanned_fixtures: int
    provider: str


class GenerateCodeRequest(BaseModel):
    selections: list[Selection]
    base_url: Optional[str] = None  # override ONEXBET_BASE_URL


class GenerateCodeResponse(BaseModel):
    booking_code: Optional[str]
    legs: list[Selection]
    screenshot_b64: Optional[str] = None
    builder_used: str
    logs: list[str] = []


class PipelineProgress(BaseModel):
    stage: int  # 1-4
    stage_name: str
    message: str
    detail: Optional[dict[str, Any]] = None
    done: bool = False
    error: Optional[str] = None
