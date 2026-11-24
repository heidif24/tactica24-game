"""Manage Bet Codes adapter.

Uses the documented resolve -> strict book -> load-back verification flow.
It never places a stake. A code is returned only after the provider confirms
that the code is verified and every requested pick was included.
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

import httpx

from backend.models import GenerateCodeResponse, Selection

logger = logging.getLogger(__name__)


class ManageBetCodesBuilder:
    def __init__(self, bookmaker: Optional[str] = None) -> None:
        self.base = os.getenv(
            "MANAGE_BET_CODES_BASE_URL",
            "https://api.managebetcodes.app/v1",
        ).rstrip("/")
        self.key = os.getenv("MANAGE_BET_CODES_API_KEY", "")
        self.bookmaker = bookmaker or os.getenv("MANAGE_BET_CODES_BOOKMAKER", "sportybet")
        self.timeout = float(os.getenv("MANAGE_BET_CODES_TIMEOUT_SECONDS", "35"))
        if not self.key:
            raise RuntimeError("MANAGE_BET_CODES_API_KEY is required")

    async def build(
        self, selections: list[Selection], base_url: Optional[str] = None
    ) -> GenerateCodeResponse:
        logs = [f"[manage-bet-codes] bookmaker={self.bookmaker}"]
        if not selections:
            return GenerateCodeResponse(
                booking_code=None, legs=[], builder_used="manage_bet_codes",
                logs=logs + ["No selections were supplied."],
            )

        picks = []
        for item in selections:
            market = getattr(item, "bookmaker_market", None)
            outcome = getattr(item, "bookmaker_outcome", None)
            line = getattr(item, "bookmaker_line", None)
            # An interval prediction cannot be silently converted into a
            # full-match corner market. Check the requested time period first.
            if item.time_window not in ("full_match", "00:00-89:59", "00:00-90:00"):
                note = (
                    f"Requested interval {item.time_window} is not a full-match "
                    "market mapping. Booking was stopped rather than changing "
                    "the time period."
                )
                legs = [s.model_copy(update={"status": "unavailable", "market_note": note}) for s in selections]
                return GenerateCodeResponse(
                    booking_code=None, legs=legs, builder_used="manage_bet_codes",
                    logs=logs + [note],
                )
            if not market or not outcome:
                note = (
                    "No exact bookmaker market mapping is attached to this "
                    "selection. The requested market must be discovered and "
                    "matched explicitly; no substitute market was selected."
                )
                legs = [s.model_copy(update={"status": "unavailable", "market_note": note}) for s in selections]
                return GenerateCodeResponse(
                    booking_code=None, legs=legs, builder_used="manage_bet_codes",
                    logs=logs + [note],
                )
            pick = {
                "home_team": item.home_team,
                "away_team": item.away_team,
                "league": item.league,
                "kickoff": item.kickoff_utc,
                "market": market,
                "outcome": outcome,
            }
            if line is not None:
                pick["line"] = str(line)
            if item.found_odds is not None:
                pick["odds"] = str(item.found_odds)
            picks.append(pick)

        headers = {
            "X-API-Key": self.key,
            "Content-Type": "application/json",
            "Idempotency-Key": f"tactica24-resolve-{uuid.uuid4()}",
        }
        timeout = httpx.Timeout(self.timeout, connect=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resolve_resp = await client.post(
                    f"{self.base}/resolve",
                    headers=headers,
                    json={
                        "bookmaker": self.bookmaker,
                        "picks": picks,
                        "strict": True,
                        "accept_odds_change": False,
                        "detail": "agent",
                    },
                )
                resolve_resp.raise_for_status()
                resolved = resolve_resp.json()
                plan_id = resolved.get("plan_id")
                statuses = [p.get("status") for p in resolved.get("picks", [])]
                if not plan_id or len(statuses) != len(picks) or any(s != "resolved" for s in statuses):
                    logs.append(f"Resolve did not produce a complete plan: {statuses}")
                    updated = [
                        s.model_copy(update={
                            "status": "unavailable",
                            "market_note": f"Provider resolution status: {statuses[i] if i < len(statuses) else 'missing'}",
                        }) for i, s in enumerate(selections)
                    ]
                    return GenerateCodeResponse(
                        booking_code=None, legs=updated, builder_used="manage_bet_codes", logs=logs,
                    )

                headers["Idempotency-Key"] = f"tactica24-book-{uuid.uuid4()}"
                book_resp = await client.post(
                    f"{self.base}/book",
                    headers=headers,
                    json={
                        "bookmaker": self.bookmaker,
                        "plan_id": plan_id,
                        "strict": True,
                        "accept_odds_change": False,
                    },
                )
                book_resp.raise_for_status()
                booked = book_resp.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:1000]
            logs.append(f"Provider HTTP {exc.response.status_code}: {detail}")
            updated = [s.model_copy(update={"status": "unavailable", "market_note": detail}) for s in selections]
            return GenerateCodeResponse(
                booking_code=None, legs=updated, builder_used="manage_bet_codes", logs=logs,
            )
        except Exception as exc:
            logger.exception("Manage Bet Codes request failed")
            logs.append(f"Provider request failed: {exc}")
            updated = [s.model_copy(update={"status": "unavailable", "market_note": str(exc)}) for s in selections]
            return GenerateCodeResponse(
                booking_code=None, legs=updated, builder_used="manage_bet_codes", logs=logs,
            )

        code = booked.get("code")
        verified = booked.get("verified") is True
        failures = booked.get("failures") or []
        booked_picks = booked.get("picks") or []
        complete = len(booked_picks) == len(selections) and not failures
        if not (booked.get("success") is True and verified and complete and isinstance(code, str) and code.strip()):
            logs.append(
                "No code released: provider response was not fully verified "
                f"(success={booked.get('success')}, verified={verified}, "
                f"booked_picks={len(booked_picks)}/{len(selections)}, failures={len(failures)})."
            )
            updated = [s.model_copy(update={
                "status": "unavailable",
                "market_note": "Provider did not verify every requested selection.",
            }) for s in selections]
            return GenerateCodeResponse(
                booking_code=None, legs=updated, builder_used="manage_bet_codes", logs=logs,
            )

        logs.append(f"Provider load-back verified all {len(selections)} selections.")
        updated = [s.model_copy(update={"status": "matched"}) for s in selections]
        return GenerateCodeResponse(
            booking_code=code.strip(), legs=updated,
            builder_used="manage_bet_codes", logs=logs,
        )
