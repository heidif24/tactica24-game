"""Grounded football research using Gemini Google Search.

This module deliberately returns no picks when web evidence is absent or cannot
be parsed. It does not fall back to demo fixtures or fabricate statistics.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from backend.models import ParsedRule, ScoutResponse, Selection

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^\`\`\`(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*\`\`\`$", "", cleaned)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Research model did not return a JSON object")
    value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("Research response must be a JSON object")
    return value


def _grounding_sources(candidate: dict[str, Any]) -> list[dict[str, str]]:
    metadata = candidate.get("groundingMetadata") or {}
    chunks = metadata.get("groundingChunks") or []
    sources: list[dict[str, str]] = []
    seen: set[str] = set()
    for chunk in chunks:
        web = chunk.get("web") or {}
        uri, title = web.get("uri"), web.get("title") or "Source"
        if uri and uri.startswith("http") and uri not in seen:
            seen.add(uri)
            sources.append({"title": str(title), "url": str(uri)})
    return sources


def _research_prompt(rule: ParsedRule) -> str:
    return f"""
You are Tactica24, a cautious football research and prediction analyst.
Today's UTC date is {datetime.now(timezone.utc).date().isoformat()}.
Research current and upcoming football fixtures on the public web using Google Search.
The user's exact request has already been parsed as:
{rule.model_dump_json()}

Find real fixtures relevant to this request, then analyse only evidence that you
can support from the web pages you found. Prefer official league/club sources,
reputable sports data providers, and established sports news/statistics sites.
Check fixture date, competition, team names, current form and relevant statistics.
Do not invent fixtures, dates, team statistics, odds, injuries, lineups, or citations.
Do not claim that a full-match statistic proves a minute-specific market.
If reliable evidence for the requested market/period is insufficient, return
an empty candidates array and explain the limitation.

Return ONLY valid JSON with this shape:
{{
 "summary": "brief research summary",
 "candidates": [
  {{
   "home_team": "exact home team",
   "away_team": "exact away team",
   "kickoff_utc": "ISO-8601 UTC timestamp with Z",
   "league": "competition",
   "selection_side": "home|away|total|both|draw|1x|x2|12",
   "team_name": "team or market label",
   "market_category": "{rule.market_category}",
   "sub_market": "{rule.sub_market}",
   "time_window": "{rule.time_window}",
   "line": {rule.line},
   "direction": "{rule.direction.value}",
   "outcome": "exact requested outcome label",
   "probability": 0.0,
   "match_status": "upcoming|live",
   "reasoning": "evidence-based analysis; distinguish facts from inference",
   "evidence": ["short fact with source context"],
   "source_urls": ["exact URL copied from Google Search grounding sources"]
  }}
 ],
 "limitations": ["any material data limitations"]
}}

Probability must be an honest model estimate from 0 to 1, not a bookmaker price
and not a guarantee. Do not include candidates below {rule.min_probability}.
Return no more than {rule.max_legs} candidates. Preserve the requested market
and time interval exactly. Do not substitute another market or period.
"""


async def _gemini_grounded_research(rule: ParsedRule) -> tuple[dict[str, Any], list[dict[str, str]]]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to the Vercel server environment.")
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": _research_prompt(rule)}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.2},
    }
    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(url, params={"key": key}, json=payload)
        if response.status_code >= 400:
            detail = response.text[:700]
            raise RuntimeError(f"Gemini web research failed ({response.status_code}): {detail}")
        data = response.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no research candidate")
    candidate = candidates[0]
    parts = ((candidate.get("content") or {}).get("parts") or [])
    text = "\n".join(p.get("text", "") for p in parts if p.get("text"))
    if not text:
        raise RuntimeError("Gemini returned no research text")
    parsed = _extract_json(text)
    sources = _grounding_sources(candidate)
    return parsed, sources

async def _groq_browser_research(rule: ParsedRule) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Use Groq GPT-OSS browser search as an independent live-research fallback."""
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key: raise RuntimeError("GROQ_API_KEY is missing")
    model = os.getenv("GROQ_RESEARCH_MODEL", os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")).strip()
    prompt = _research_prompt(rule) + "\nUse browser_search. Include literal https:// source_urls for pages visited, at least one per candidate. Return only the requested JSON."
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "max_completion_tokens": 6000, "tool_choice": "required", "tools": [{"type": "browser_search"}]}
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=payload)
        if response.status_code >= 400: raise RuntimeError(f"Groq browser research failed ({response.status_code}): {response.text[:700]}")
        data = response.json()
    message = ((data.get("choices") or [{}])[0].get("message") or {})
    raw = message.get("content") or ""
    if not raw: raise RuntimeError("Groq browser search returned no research text")
    parsed = _extract_json(raw)
    urls = []
    for item in parsed.get("candidates") or []:
        for value in item.get("source_urls") or []:
            url = str(value).strip()
            if url.startswith("https://") and url not in urls: urls.append(url)
    return parsed, [{"title": "Groq browser-search source", "url": url} for url in urls]

async def research_matches(rule: ParsedRule) -> ScoutResponse:
    """Search the live web, analyse sourced fixtures, and produce auditable picks."""
    failures: list[str] = []
    report = None
    sources: list[dict[str, str]] = []
    providers = []
    if os.getenv("GEMINI_API_KEY", "").strip(): providers.append(("gemini_google_search", _gemini_grounded_research))
    if os.getenv("GROQ_API_KEY", "").strip(): providers.append(("groq_browser_search", _groq_browser_research))
    if not providers: raise RuntimeError("No live research provider is configured. Add GEMINI_API_KEY or GROQ_API_KEY.")
    provider_used = ""
    for provider_name, research_fn in providers:
        try:
            candidate_report, candidate_sources = await research_fn(rule)
            if candidate_sources:
                report, sources, provider_used = candidate_report, candidate_sources, provider_name
                break
            failures.append(f"{provider_name}: no verifiable source URLs returned")
        except Exception as exc:
            logger.warning("%s research attempt failed: %s", provider_name, exc)
            failures.append(f"{provider_name}: {exc}")
    if report is None: raise RuntimeError("All configured live research providers failed: " + " | ".join(failures))
    if not sources:
        logger.warning("Gemini response had no Google Search grounding sources")
        return ScoutResponse(
            selections=[], scanned_fixtures=0, provider=provider_used,
            research_summary="No verifiable web sources were returned; no selections generated.",
            evidence_sources=[],
            limitations=["Google Search grounding returned no source URLs."],
        )

    selections: list[Selection] = []
    allowed_urls = {source["url"] for source in sources}
    now = datetime.now(timezone.utc)
    for index, item in enumerate(report.get("candidates") or []):
        try:
            home, away = str(item["home_team"]).strip(), str(item["away_team"]).strip()
            kickoff = str(item["kickoff_utc"]).strip()
            kickoff_dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))
            if kickoff_dt.tzinfo is None:
                kickoff_dt = kickoff_dt.replace(tzinfo=timezone.utc)
            match_status = str(item.get("match_status") or "upcoming").lower()
            if rule.match_status.value == "upcoming" and (match_status != "upcoming" or kickoff_dt <= now):
                continue
            if rule.match_status.value == "live" and (match_status != "live" or kickoff_dt > now):
                continue
            if rule.match_status.value == "upcoming_or_live":
                if match_status not in ("upcoming", "live"): continue
                if match_status == "upcoming" and kickoff_dt <= now: continue
                if match_status == "live" and kickoff_dt > now: continue
            evidence = item.get("evidence") or []
            candidate_urls = [str(url) for url in (item.get("source_urls") or [])]
            matched_sources = [source for source in sources if source["url"] in allowed_urls and source["url"] in candidate_urls]
            if not evidence or not matched_sources:
                continue
            probability = float(item["probability"])
            if not home or not away or home.lower() == "unknown" or away.lower() == "unknown":
                continue
            if not 0 < probability <= 1 or probability < rule.min_probability:
                continue
            # Preserve fixed sides and exact requested market/interval.
            requested_side = rule.selection_target.value
            candidate_side = str(item.get("selection_side") or requested_side).lower()
            if requested_side in ("home", "away", "draw") and candidate_side != requested_side: continue
            if str(item.get("market_category", rule.market_category)).lower() != rule.market_category.lower():
                continue
            if str(item.get("time_window", rule.time_window)) != rule.time_window:
                continue
            if float(item.get("line", rule.line)) != float(rule.line):
                continue
            reasoning = str(item.get("reasoning") or "No detailed reasoning supplied.")
            selections.append(Selection(
                fixture_id=f"web-research-{index + 1}",
                home_team=home,
                away_team=away,
                kickoff_utc=kickoff,
                league=str(item.get("league") or "Competition not stated"),
                selection_side=candidate_side,
                team_name=str(item.get("team_name") or f"{home} vs {away}"),
                time_window=rule.time_window,
                line=rule.line,
                direction=rule.direction.value,
                lambda_=0.0,
                probability=round(probability, 4),
                fair_odds=round(1 / probability, 3),
                reasoning=reasoning + (" Evidence: " + "; ".join(map(str, evidence[:5])) if evidence else ""),
                market_category=rule.market_category,
                sub_market=rule.sub_market,
                bookmaker_outcome=(
                    rule.direction.value if rule.market_category in ("corners", "goals")
                    else (rule.outcome or str(item.get("outcome") or "")).lower()
                    if rule.market_category in ("btts", "double_chance")
                    else candidate_side
                ),
                calibration_status="uncalibrated",
                calibration_samples=0,
                raw_probability=round(probability, 4),
                model_version="tactica24-gemini-grounded-v1",
                evidence_sources=matched_sources,
                evidence_summary=str(report.get("summary") or ""),
            ))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Rejecting malformed web-research candidate: %s", exc)
            continue

    selections.sort(key=lambda s: s.probability, reverse=True)
    limitations = [str(x) for x in (report.get("limitations") or [])]
    return ScoutResponse(
        selections=selections[:rule.max_legs],
        scanned_fixtures=len(selections),
        provider="gemini_google_search",
        research_summary=str(report.get("summary") or "Grounded web research completed."),
        evidence_sources=sources,
        limitations=limitations,
    )
