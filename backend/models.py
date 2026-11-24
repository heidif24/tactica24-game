"""Pydantic schemas for Tactica24."""
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
    DRAW = "draw"
    TOTAL = "total"

class ParsedRule(BaseModel):
    sport: str = "football"
    market_category: str = "corners"
    sub_market: str = "team_interval_corners"
    outcome: Optional[str] = None
    time_window: str = Field(default="00:00-04:59", description="Interval in MM:SS-MM:SS or shorthand")
    selection_target: SelectionTarget = SelectionTarget.LOWEST_PROBABILITY_TEAM
    line: float = 0.5
    direction: Direction = Direction.UNDER
    min_probability: float = Field(default=0.75, ge=0.0, le=1.0)
    max_legs: int = Field(default=1, ge=1, le=20)
    match_status: MatchStatus = MatchStatus.UPCOMING

    @field_validator("time_window")
    @classmethod
    def normalize_window(cls, v: str) -> str:
        aliases = {"first_5":"00:00-04:59","first5":"00:00-04:59","first_15":"00:00-14:59","first15":"00:00-14:59","0-5":"00:00-04:59","0-15":"00:00-14:59"}
        key = v.strip().lower().replace(" ", "_")
        return aliases.get(key, v.strip())

class ParseRuleRequest(BaseModel):
    prompt: str = Field(..., min_length=5)
    max_legs: Optional[int] = None
    min_probability: Optional[float] = None

class ParseRuleResponse(BaseModel):
    rule: ParsedRule
    raw_prompt: str
    parser_used: str

class TeamCornerStats(BaseModel):
    team_id: str
    team_name: str
    c90_for: float
    c90_against: Optional[float]
    first15_share: float = 0.22
    g90_for: Optional[float] = None
    g90_against: Optional[float] = None

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
    selection_side: str
    team_name: str
    time_window: str
    line: float
    direction: str
    lambda_: float = Field(..., alias="lambda")
    probability: float
    fair_odds: float
    reasoning: str
    status: str = "pending"
    found_odds: Optional[float] = None
    market_note: Optional[str] = None
    # Explicit canonical market mapping is required for real booking.
    # The interval scout does not populate these until an exact market has
    # been discovered at the selected bookmaker.
    bookmaker_market: Optional[str] = None
    bookmaker_outcome: Optional[str] = None
    bookmaker_line: Optional[str] = None
    market_category: str = "corners"
    sub_market: str = "team_interval_corners"
    bookmaker_event_id: Optional[str] = None
    bookmaker_pick_key: Optional[str] = None
    calibration_status: str = "uncalibrated"
    calibration_samples: int = 0
    raw_probability: Optional[float] = None
    calibrated_probability: Optional[float] = None
    model_version: str = "tactica24-poisson-v2"
    model_config = {"populate_by_name": True}

class ScoutRequest(BaseModel):
    rule: ParsedRule

class ScoutResponse(BaseModel):
    selections: list[Selection]
    scanned_fixtures: int
    provider: str

class GenerateCodeRequest(BaseModel):
    selections: list[Selection]
    base_url: Optional[str] = None
    bookmaker: Optional[str] = None

class GenerateCodeResponse(BaseModel):
    booking_code: Optional[str]
    legs: list[Selection]
    screenshot_b64: Optional[str] = None
    builder_used: str
    logs: list[str] = []

class PipelineProgress(BaseModel):
    stage: int
    stage_name: str
    message: str
    detail: Optional[dict[str, Any]] = None
    done: bool = False
    error: Optional[str] = None
