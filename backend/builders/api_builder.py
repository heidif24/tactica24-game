"""HTTP adapter for third-party bet-code / slip-booking APIs."""

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from backend.models import GenerateCodeResponse, Selection

logger = logging.getLogger(__name__)


class ExternalCodeApiBuilder:
    """
    Clean REST wrapper.

    Expected external API contract (configurable):
      POST {BOOKING_API_URL}/book
      Authorization: Bearer {BOOKING_API_KEY}
      Body: { "legs": [ { "home": ..., "away": ..., "market": ..., "selection": ... } ] }
      Response: { "code": "ABC123", "legs": [ { "status": "matched"|"unavailable", ... } ] }
    """

    def __init__(self) -> None:
        self.url = os.getenv("BOOKING_API_URL", "").rstrip("/")
        self.key = os.getenv("BOOKING_API_KEY", "")
        if not self.url:
            raise RuntimeError("BOOKING_API_URL is required for api builder")

    async def build(
        self, selections: list[Selection], base_url: Optional[str] = None
    ) -> GenerateCodeResponse:
        logs: list[str] = [f"[api] POST {self.url}/book"]
        payload = {
            "legs": [
                {
                    "home": s.home_team,
                    "away": s.away_team,
                    "kickoff": s.kickoff_utc,
                    "market": f"corners_{s.time_window}",
                    "selection": s.selection_side,
                    "line": s.line,
                    "direction": s.direction,
                }
                for s in selections
            ]
        }
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(f"{self.url}/book", json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logs.append(f"[api] ERROR: {exc}")
            return GenerateCodeResponse(
                booking_code=None,
                legs=[s.model_copy(update={"status": "skipped", "market_note": str(exc)}) for s in selections],
                builder_used="api",
                logs=logs,
            )

        code = data.get("code") or data.get("booking_code")
        remote_legs = data.get("legs") or []
        updated: list[Selection] = []
        for i, s in enumerate(selections):
            remote = remote_legs[i] if i < len(remote_legs) else {}
            status = remote.get("status", "matched" if code else "unavailable")
            updated.append(
                s.model_copy(
                    update={
                        "status": status,
                        "found_odds": remote.get("odds"),
                        "market_note": remote.get("note", "via external API"),
                    }
                )
            )
            logs.append(f"[api] {s.team_name} → {status}")

        logs.append(f"[api] Booking code: {code}")
        return GenerateCodeResponse(
            booking_code=code,
            legs=updated,
            builder_used="api",
            logs=logs,
        )
