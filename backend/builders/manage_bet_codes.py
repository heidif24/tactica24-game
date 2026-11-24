"""Manage Bet Codes adapter with exact discovery and verified code creation."""
from __future__ import annotations

import logging
import os
import uuid
from typing import Optional

import httpx

from backend.market_discovery import ManageBetCodesMarketDiscovery
from backend.models import GenerateCodeResponse, Selection

logger = logging.getLogger(__name__)


class ManageBetCodesBuilder:
    def __init__(self, bookmaker: Optional[str] = None) -> None:
        self.base = os.getenv("MANAGE_BET_CODES_BASE_URL", "https://api.managebetcodes.app/v1").rstrip("/")
        self.key = os.getenv("MANAGE_BET_CODES_API_KEY", "")
        self.bookmaker = bookmaker or os.getenv("MANAGE_BET_CODES_BOOKMAKER", "sportybet")
        self.timeout = float(os.getenv("MANAGE_BET_CODES_TIMEOUT_SECONDS", "35"))
        self.require_calibrated = os.getenv("T24_REQUIRE_CALIBRATED", "true").lower() in ("1", "true", "yes")
        if not self.key:
            raise RuntimeError("MANAGE_BET_CODES_API_KEY is required")

    @staticmethod
    def _unavailable(selections: list[Selection], note: str, logs: list[str]) -> GenerateCodeResponse:
        updated = [
            item.model_copy(update={"status": "unavailable", "market_note": note})
            for item in selections
        ]
        return GenerateCodeResponse(
            booking_code=None, legs=updated, builder_used="manage_bet_codes", logs=logs + [note]
        )

    async def build(
        self, selections: list[Selection], base_url: Optional[str] = None
    ) -> GenerateCodeResponse:
        logs = [f"[manage-bet-codes] bookmaker={self.bookmaker}"]
        if not selections:
            return GenerateCodeResponse(
                booking_code=None, legs=[], builder_used="manage_bet_codes",
                logs=logs + ["No selections were supplied."],
            )

        if self.require_calibrated:
            uncalibrated = [s for s in selections if s.calibration_status != "calibrated"]
            if uncalibrated:
                return self._unavailable(
                    selections,
                    "Booking blocked: probability calibration is required, but one or more selections lack a sufficiently large out-of-sample historical calibration sample. Add verified historical forecasts before live code creation.",
                    logs,
                )

        discovery = ManageBetCodesMarketDiscovery(self.base, self.key, self.timeout)
        picks: list[dict] = []
        try:
            for item in selections:
                # Exact event and market discovery happens before resolving.
                descriptor = await discovery.discover(item, self.bookmaker)
                if descriptor is None:
                    note = (
                        f"No unique, exact {item.market_category} market was found for "
                        f"{item.home_team} vs {item.away_team} at {self.bookmaker} "
                        f"for period {item.time_window}, line {item.line}, "
                        f"outcome {item.bookmaker_outcome or item.direction}. "
                        "No substitute market was selected."
                    )
                    return self._unavailable(selections, note, logs)
                item.bookmaker_event_id = descriptor["event_id"]
                item.bookmaker_pick_key = descriptor.get("key")
                item.bookmaker_market = descriptor.get("market")
                item.bookmaker_outcome = descriptor.get("outcome") or item.bookmaker_outcome
                item.bookmaker_line = descriptor.get("line")
                item.found_odds = float(descriptor["odds"]) if descriptor.get("odds") else item.found_odds

                if item.bookmaker_pick_key:
                    pick = {
                        "event_id": item.bookmaker_event_id,
                        "key": item.bookmaker_pick_key,
                    }
                    if item.found_odds is not None:
                        pick["odds"] = str(item.found_odds)
                else:
                    pick = {
                        "event_id": item.bookmaker_event_id,
                        "home_team": item.home_team,
                        "away_team": item.away_team,
                        "league": item.league,
                        "kickoff": item.kickoff_utc,
                        "market": item.bookmaker_market,
                        "outcome": item.bookmaker_outcome,
                        "line": item.bookmaker_line,
                    }
                    if item.found_odds is not None:
                        pick["odds"] = str(item.found_odds)
                picks.append(pick)
                logs.append(
                    f"Discovered exact market: {item.home_team} vs {item.away_team} · "
                    f"{item.bookmaker_market} · {item.bookmaker_outcome} · {item.time_window}"
                )
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:800]
            return self._unavailable(selections, f"Market discovery API error {exc.response.status_code}: {detail}", logs)
        except Exception as exc:
            logger.exception("Manage Bet Codes market discovery failed")
            return self._unavailable(selections, f"Market discovery failed: {exc}", logs)

        headers = {
            "X-API-Key": self.key,
            "Content-Type": "application/json",
            "Idempotency-Key": f"tactica24-resolve-{uuid.uuid4()}",
        }
        timeout = httpx.Timeout(self.timeout, connect=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resolve_response = await client.post(
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
                resolve_response.raise_for_status()
                resolved = resolve_response.json()
                plan_id = resolved.get("plan_id")
                resolved_picks = resolved.get("picks") or []
                statuses = [p.get("status") for p in resolved_picks]
                all_bookable = all(p.get("bookable", True) is True for p in resolved_picks)
                if (
                    not plan_id
                    or len(resolved_picks) != len(picks)
                    or any(status != "resolved" for status in statuses)
                    or not all_bookable
                ):
                    logs.append(f"Resolve rejected one or more picks: {statuses}")
                    updated = []
                    for index, item in enumerate(selections):
                        provider_pick = resolved_picks[index] if index < len(resolved_picks) else {}
                        status = provider_pick.get("status", "missing")
                        updated.append(item.model_copy(update={
                            "status": "unavailable",
                            "market_note": f"Provider resolution: {status}",
                        }))
                    return GenerateCodeResponse(
                        booking_code=None, legs=updated, builder_used="manage_bet_codes", logs=logs
                    )

                headers["Idempotency-Key"] = f"tactica24-book-{uuid.uuid4()}"
                book_response = await client.post(
                    f"{self.base}/book",
                    headers=headers,
                    json={
                        "bookmaker": self.bookmaker,
                        "plan_id": plan_id,
                        "strict": True,
                        "accept_odds_change": False,
                    },
                )
                book_response.raise_for_status()
                booked = book_response.json()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:1000]
            logs.append(f"Provider HTTP {exc.response.status_code}: {detail}")
            return self._unavailable(selections, detail, logs)
        except Exception as exc:
            logger.exception("Manage Bet Codes booking failed")
            return self._unavailable(selections, f"Provider request failed: {exc}", logs)

        # Current API contract returns these fields at the response root.
        code = booked.get("code")
        verified = booked.get("verified") is True
        failures = booked.get("failures") or []
        booked_picks = booked.get("picks") or []
        complete = len(booked_picks) == len(selections) and not failures
        if not (
            booked.get("success") is True
            and verified
            and complete
            and isinstance(code, str)
            and code.strip()
        ):
            return self._unavailable(
                selections,
                "Provider did not verify every requested selection; no code was released.",
                logs + [
                    f"Book response: success={booked.get('success')}, verified={verified}, "
                    f"picks={len(booked_picks)}/{len(selections)}, failures={len(failures)}"
                ],
            )

        logs.append(f"Provider verified all {len(selections)} selections by loading the code back.")
        updated = [item.model_copy(update={"status": "matched"}) for item in selections]
        return GenerateCodeResponse(
            booking_code=code.strip(),
            legs=updated,
            builder_used="manage_bet_codes",
            logs=logs,
        )
