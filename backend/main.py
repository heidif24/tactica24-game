"""SlipForge FastAPI application — complete E2E with SSE + static UI."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import AsyncGenerator, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.builders import get_builder
from backend.models import (
    GenerateCodeRequest,
    GenerateCodeResponse,
    ParseRuleRequest,
    ParseRuleResponse,
    PipelineProgress,
    ScoutRequest,
    ScoutResponse,
)
from backend.parser import parse_rule
from backend.research_engine import research_matches

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tactica24")

app = FastAPI(
    title="Tactica24",
    description="Conversational football analysis, exact market validation, and verified booking codes",
    version="1.0.0",
)

origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins != ["*"] else ["*"],
    allow_credentials=origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    stats_provider = "gemini_google_search"
    slip_builder = os.getenv("SLIP_BUILDER", "manage_bet_codes").lower()
    demo_mode = slip_builder == "mock"
    stats_configured = bool(os.getenv("GEMINI_API_KEY"))
    builder_configured = (
        slip_builder == "mock"
        or (slip_builder == "api" and bool(os.getenv("BOOKING_API_URL")))
        or (slip_builder in ("manage_bet_codes", "mbc") and bool(os.getenv("MANAGE_BET_CODES_API_KEY")))
    )
    market_mapping_ready = slip_builder not in ("manage_bet_codes", "mbc") or bool(os.getenv("MANAGE_BET_CODES_API_KEY"))
    from backend.calibration import calibration_dataset_status
    calibration_status = calibration_dataset_status()
    calibration_data_ready = calibration_status["ready"]
    llm_provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    llm_configured = bool(os.getenv("GEMINI_API_KEY")) or bool(os.getenv("GROQ_API_KEY"))
    setup_requirements = []
    if not stats_configured:
        setup_requirements.append("Gemini API key for grounded web research")
    if not builder_configured:
        setup_requirements.append("Manage Bet Codes API key")
    if not llm_configured:
        setup_requirements.append("Gemini or Groq API key")
    if not calibration_data_ready and os.getenv("T24_REQUIRE_CALIBRATED", "false").lower() in ("1", "true", "yes"):
        setup_requirements.append("out-of-sample calibration dataset (required by current safety setting)")
    operational = (
        not demo_mode and stats_configured and builder_configured
        and market_mapping_ready and llm_configured
    )
    return {
        "status": "ok" if operational else "degraded",
        "operational": operational,
        "market_mapping_ready": market_mapping_ready,
        "calibration_data_ready": calibration_data_ready,
        "calibration_rows": calibration_status["rows"],
        "calibration_profiles": calibration_status["profiles"],
        "llm_provider": llm_provider,
        "llm_configured": llm_configured,
        "setup_requirements": setup_requirements,
        "demo_mode": demo_mode,
        "stats_configured": stats_configured,
        "builder_configured": builder_configured,
        "stats_provider": stats_provider,
        "slip_builder": slip_builder,
        "llm_provider": os.getenv("LLM_PROVIDER", "none"),
    }


# ── Stage 1: Parse ──────────────────────────────────────────────────────────

@app.post("/api/parse-rule", response_model=ParseRuleResponse)
async def api_parse_rule(body: ParseRuleRequest):
    try:
        return await parse_rule(body)
    except Exception as exc:
        logger.exception("parse-rule failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Stage 2: Scout ──────────────────────────────────────────────────────────

@app.post("/api/scout-matches", response_model=ScoutResponse)
async def api_scout_matches(body: ScoutRequest):
    try:
        return await research_matches(body.rule)
    except Exception as exc:
        logger.exception("scout-matches failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Stage 3: Generate code ──────────────────────────────────────────────────

@app.post("/api/generate-code", response_model=GenerateCodeResponse)
async def api_generate_code(body: GenerateCodeRequest):
    try:
        builder = get_builder(bookmaker=body.bookmaker)
        return await builder.build(body.selections, base_url=body.base_url)
    except Exception as exc:
        logger.exception("generate-code failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Full pipeline with SSE ──────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    prompt: str
    max_legs: Optional[int] = None
    min_probability: Optional[float] = None
    base_url: Optional[str] = None
    bookmaker: Optional[str] = None
    context: list[str] = Field(default_factory=list)


def _sse(event: PipelineProgress) -> str:
    return f"data: {event.model_dump_json()}\n\n"


@app.post("/api/pipeline")
@app.post("/api/chat")
async def api_pipeline(body: PipelineRequest):
    """Run all 4 stages and stream progress via Server-Sent Events."""

    async def generator() -> AsyncGenerator[str, None]:
        try:
            yield _sse(PipelineProgress(
                stage=1, stage_name="Parsing Rule",
                message="Translating natural-language prompt into filter criteria…",
            ))
            await asyncio.sleep(0.1)
            parse_prompt = body.prompt
            if body.context and os.getenv('LLM_PROVIDER', 'none').lower() != 'none':
                parse_prompt = '\n'.join(body.context[-8:] + [f'Current request: {body.prompt}'])
            parsed = await parse_rule(ParseRuleRequest(
                prompt=parse_prompt,
                max_legs=body.max_legs,
                min_probability=body.min_probability,
            ))
            yield _sse(PipelineProgress(
                stage=1, stage_name="Parsing Rule",
                message=(
                    f"Understood your request: {parsed.rule.market_category} / {parsed.rule.sub_market}; "
                    f"period {parsed.rule.time_window}; target {parsed.rule.selection_target.value}; "
                    f"{parsed.rule.direction.value} {parsed.rule.line}; "
                    f"minimum probability {parsed.rule.min_probability:.0%}; "
                    f"up to {parsed.rule.max_legs} selections. Parsed via {parsed.parser_used}."
                ),
                detail=parsed.rule.model_dump(),
            ))

            yield _sse(PipelineProgress(
                stage=2, stage_name="Online Web Research",
                message=f"Searching current public sources and analysing {parsed.rule.market_category} for {parsed.rule.time_window}…",
            ))
            await asyncio.sleep(0.1)
            scout = await research_matches(parsed.rule)
            yield _sse(PipelineProgress(
                stage=2, stage_name="Online Web Research",
                message=(
                    f"Researched {scout.scanned_fixtures} candidates via {scout.provider}; "
                    f"{len(scout.selections)} met the request. {scout.research_summary or ''}"
                ),
                detail={"selections": [s.model_dump(by_alias=True) for s in scout.selections], "sources": scout.evidence_sources, "limitations": scout.limitations},
            ))

            if not scout.selections:
                yield _sse(PipelineProgress(
                    stage=4, stage_name="Complete",
                    message="No evidence-backed selections met the requested threshold. No demo fixtures or substitute markets were used.",
                    done=True,
                ))
                return

            yield _sse(PipelineProgress(
                stage=3, stage_name="Resolving Bookmaker Markets",
                message=f"Discovering exact {parsed.rule.market_category} markets at {body.bookmaker or os.getenv('MANAGE_BET_CODES_BOOKMAKER', 'configured bookmaker')} before strict resolution…",
            ))
            await asyncio.sleep(0.05)
            builder = get_builder(bookmaker=body.bookmaker)
            result = await builder.build(scout.selections, base_url=body.base_url)
            yield _sse(PipelineProgress(
                stage=3, stage_name="Resolving Bookmaker Markets",
                message=f"Provider={result.builder_used}. " + " | ".join(result.logs[-5:]),
                detail={
                    "legs": [l.model_dump(by_alias=True) for l in result.legs],
                    "logs": result.logs,
                },
            ))

            code_msg = (
                f"Booking code: {result.booking_code}"
                if result.booking_code
                else "No verified booking code (markets unavailable, incomplete, or provider not configured)"
            )
            yield _sse(PipelineProgress(
                stage=4, stage_name="Verifying Booking Code",
                message=code_msg,
                detail={
                    "booking_code": result.booking_code,
                    "legs": [l.model_dump(by_alias=True) for l in result.legs],
                    "screenshot_b64": result.screenshot_b64,
                    "builder_used": result.builder_used,
                    "logs": result.logs,
                },
                done=True,
            ))

        except Exception as exc:
            logger.exception("pipeline failed")
            yield _sse(PipelineProgress(
                stage=0, stage_name="Error",
                message=str(exc),
                error=str(exc),
                done=True,
            ))

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Serve dashboard ─────────────────────────────────────────────────────────

@app.get("/")
async def serve_ui():
    index = FRONTEND_DIR / "index.html"
    if not index.exists():
        raise HTTPException(404, "frontend/index.html not found")
    return FileResponse(index)


if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
