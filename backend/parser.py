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

SYSTEM_PROMPT = """You are Tactica24's football market request parser.
Convert the user's natural-language request into one JSON object matching this schema:
{
  "sport": "football",
  "market_category": "corners",
  "sub_market": "team_interval_corners",
  "outcome": null,
  "time_window": "full_match",
  "selection_target": "lowest_probability_team",
  "line": 0.5,
  "direction": "under",
  "min_probability": 0.75,
  "max_legs": 1,
  "match_status": "upcoming"
}
Allowed market_category values: corners, goals, btts, result, double_chance, cards.
Allowed selection_target values: lowest_probability_team, highest_probability_team, home, away, both, draw, total. Team 1 means the home team; Team 2 means the away team. If the user asks which team is more likely to record an event, use highest_probability_team; if they ask which team is least likely, use lowest_probability_team.
Use an exact MM:SS-MM:SS interval only when the user requests one; otherwise use full_match.
For BTTS, set outcome to Yes or No. For 1X2, set outcome to Home, Draw, or Away. For double chance, set outcome to 1X, X2, or 12.
Never invent fixtures, bookmaker markets, odds, or statistics. Do not convert a requested interval into a full-match market.
If the requested market/period cannot be supported by the data engine, preserve the request exactly; the application will return no pick.
Only output valid JSON, without markdown or commentary."""


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

    # Explicit period only. A missing period defaults to full match for
    # mainstream markets; interval markets require an explicit interval.
    explicit_period = bool(re.search(r"first\s*\d+|\d{1,2}:\d{2}\s*[-–]\s*\d{1,2}:\d{2}|first half|second half", text))
    window = "full_match"
    period_m = re.search(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})", text)
    if period_m:
        window = f"{period_m.group(1)}-{period_m.group(2)}"
    elif "second half" in text:
        window = "45:00-89:59"
    elif "first half" in text:
        window = "00:00-44:59"
    else:
        first_m = re.search(r"first\s*(\d+)\s*(?:minutes?|mins?|m)?", text)
        if first_m:
            mins = max(1, min(int(first_m.group(1)), 90))
            last = mins * 60 - 1
            window = f"00:00-{last // 60:02d}:{last % 60:02d}"

    # line
    line = 0.5
    line_m = re.search(r"(?:under|over)\s*(\d+(?:\.\d+)?)", text) or re.search(
        r"(\d+(?:\.\d+)?)\s*(?:corners?|goals?|cards?)", text
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
    elif re.search(r"\bmost likely\b|\bmore likely\b|\bhighest probability\b|\bmost probable\b", text):
        direction = Direction.OVER

    # Market family and requested outcome.
    category = "corners"
    outcome = None
    if "both teams to score" in text or "btts" in text:
        category = "btts"
        outcome = "No" if re.search(r"\bno\b|not score", text) else "Yes"
    elif "double chance" in text:
        category = "double_chance"
        outcome = "1X" if "1x" in text else "X2" if "x2" in text else "12"
    elif "1x2" in text or "match result" in text or "to win" in text or "winner" in text or "home win" in text or "away win" in text or "draw" in text:
        category = "result"
    elif "card" in text:
        category = "cards"
    elif "goal" in text:
        category = "goals"
    elif "corner" in text:
        category = "corners"

    target = SelectionTarget.LOWEST_PROBABILITY_TEAM
    if category == "result":
        if "draw" in text:
            target, outcome = SelectionTarget.DRAW, "Draw"
        elif "away" in text:
            target, outcome = SelectionTarget.AWAY, "Away"
        else:
            target, outcome = SelectionTarget.HOME, "Home"
    elif category == "btts":
        target = SelectionTarget.BOTH
    elif category == "double_chance":
        target = SelectionTarget.BOTH
    elif "total" in text or category == "goals":
        target = SelectionTarget.TOTAL
    elif re.search(r"\bteam\s*1\b|\bteam\s*one\b", text) or ("home" in text and "away" not in text):
        target = SelectionTarget.HOME
    elif re.search(r"\bteam\s*2\b|\bteam\s*two\b", text) or ("away" in text and "home" not in text):
        target = SelectionTarget.AWAY
    elif re.search(r"\bmost likely\b|\bmore likely\b|\bhighest probability\b|\bmost probable\b", text):
        target = SelectionTarget.HIGHEST_PROBABILITY_TEAM

    if category == "corners":
        sub_market = "total_interval_corners" if target == SelectionTarget.TOTAL else "team_interval_corners"
    elif category == "goals":
        sub_market = "interval_goals" if explicit_period else "total_goals"
    elif category == "btts":
        sub_market = "interval_btts" if explicit_period else "btts"
    elif category == "double_chance":
        sub_market = "interval_double_chance" if explicit_period else "double_chance"
    elif category == "result":
        sub_market = "interval_result" if explicit_period else "match_result"
    else:
        sub_market = "interval_cards" if explicit_period else "total_cards"
    if not explicit_period and category != "corners":
        window = "full_match"

    # probability
    min_prob = 0.75
    prob_m = re.search(r"(\d{2,3})\s*%", text) or re.search(
        r"min(?:imum)?\s*(?:prob(?:ability)?)?\s*[:=]?\s*(0?\.\d+)", text
    )
    if prob_m:
        raw = prob_m.group(1)
        min_prob = float(raw) / 100 if float(raw) > 1 else float(raw)

    # legs
    max_legs = 1
    legs_m = re.search(r"max\s*(\d+)\s*legs?", text) or re.search(
        r"(\d+)\s*legs?", text
    )
    if legs_m:
        max_legs = int(legs_m.group(1))

    # status
    status = MatchStatus.UPCOMING
    if "live only" in text or "only live" in text:
        status = MatchStatus.LIVE
    elif "upcoming only" in text or "pre-match" in text:
        status = MatchStatus.UPCOMING

    data = {
        "sport": "football",
        "market_category": category,
        "sub_market": sub_market,
        "outcome": outcome,
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
