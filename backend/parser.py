"""Natural-language rule parser with LLM + deterministic fallback."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from backend.models import (
    Direction,
    MatchStatus,
    ParsedRule,
    ParseRuleRequest,
    ParseRuleResponse,
    SelectionTarget,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a strict sports-betting rule parser.
Convert the user prompt into a single JSON object matching this schema exactly:
{
  "sport": "football",
  "market_category": "corners",
  "sub_market": "team_interval_corners",
  "time_window": "00:00-04:59",
  "selection_target": "lowest_probability_team",
  "line": 0.5,
  "direction": "under",
  "min_probability": 0.75,
  "max_legs": 3,
  "match_status": "upcoming_or_live"
}
Only output valid JSON. No markdown, no commentary."""


def _parse_window_minutes(window: str) -> float:
    """Return duration in minutes from a window string."""
    m = re.match(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})", window)
    if not m:
        return 5.0
    start = int(m.group(1)) * 60 + int(m.group(2))
    end = int(m.group(3)) * 60 + int(m.group(4))
    return max((end - start + 1) / 60.0, 0.5)


def deterministic_parse(prompt: str, overrides: Optional[dict] = None) -> ParsedRule:
    """Rule-based parser that covers the common corner-interval patterns."""
    text = prompt.lower()

    # time window
    window = "00:00-04:59"
    if any(k in text for k in ("first 15", "first15", "0-15", "00:00-14")):
        window = "00:00-14:59"
    elif any(k in text for k in ("first 10", "first10", "0-10")):
        window = "00:00-09:59"
    elif any(k in text for k in ("first 5", "first5", "0-5", "00:00-04")):
        window = "00:00-04:59"

    # line
    line = 0.5
    line_m = re.search(r"under\s*(\d+(?:\.\d+)?)", text) or re.search(
        r"(\d+(?:\.\d+)?)\s*corners?", text
    )
    if line_m:
        line = float(line_m.group(1))
        if line >= 1 and "0.5" not in text and "under 0" not in text:
            # "under 1.5" style
            pass

    # direction
    direction = Direction.UNDER
    if "over" in text and "under" not in text:
        direction = Direction.OVER

    # target
    target = SelectionTarget.LOWEST_PROBABILITY_TEAM
    if "total" in text:
        target = SelectionTarget.TOTAL
    elif "home" in text and "away" not in text:
        target = SelectionTarget.HOME
    elif "away" in text and "home" not in text:
        target = SelectionTarget.AWAY

    # probability
    min_prob = 0.75
    prob_m = re.search(r"(\d{2,3})\s*%", text) or re.search(
        r"min(?:imum)?\s*(?:prob(?:ability)?)?\s*[:=]?\s*(0?\.\d+)", text
    )
    if prob_m:
        raw = prob_m.group(1)
        min_prob = float(raw) / 100 if float(raw) > 1 else float(raw)

    # legs
    max_legs = 3
    legs_m = re.search(r"max\s*(\d+)\s*legs?", text) or re.search(
        r"(\d+)\s*legs?", text
    )
    if legs_m:
        max_legs = int(legs_m.group(1))

    # status
    status = MatchStatus.UPCOMING_OR_LIVE
    if "live only" in text or "only live" in text:
        status = MatchStatus.LIVE
    elif "upcoming only" in text or "pre-match" in text:
        status = MatchStatus.UPCOMING

    data = {
        "sport": "football",
        "market_category": "corners",
        "sub_market": "team_interval_corners" if target != SelectionTarget.TOTAL else "total_interval_corners",
        "time_window": window,
        "selection_target": target,
        "line": line,
        "direction": direction,
        "min_probability": min_prob,
        "max_legs": max_legs,
        "match_status": status,
    }
    if overrides:
        data.update({k: v for k, v in overrides.items() if v is not None})
    return ParsedRule(**data)


async def llm_parse(prompt: str) -> Optional[ParsedRule]:
    """Try OpenAI / Anthropic structured parse. Returns None on any failure."""
    provider = os.getenv("LLM_PROVIDER", "none").lower()
    if provider == "none":
        return None

    try:
        if provider == "openai":
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or "{}"
            return ParsedRule(**json.loads(raw))

        if provider == "anthropic":
            import anthropic

            client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            resp = await client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text
            # strip possible markdown fences
            raw = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
            return ParsedRule(**json.loads(raw))

    except Exception as exc:
        logger.warning("LLM parse failed: %s", exc)
    return None


async def parse_rule(req: ParseRuleRequest) -> ParseRuleResponse:
    overrides = {}
    if req.max_legs is not None:
        overrides["max_legs"] = req.max_legs
    if req.min_probability is not None:
        overrides["min_probability"] = req.min_probability

    rule = await llm_parse(req.prompt)
    if rule is not None:
        if overrides:
            data = rule.model_dump()
            data.update(overrides)
            rule = ParsedRule(**data)
        return ParseRuleResponse(rule=rule, raw_prompt=req.prompt, parser_used="llm")

    rule = deterministic_parse(req.prompt, overrides)
    return ParseRuleResponse(rule=rule, raw_prompt=req.prompt, parser_used="deterministic")
