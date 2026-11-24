"""Offline-only builder. It must never mint a fake bookmaker booking code."""

from __future__ import annotations

from typing import Optional

from backend.models import GenerateCodeResponse, Selection


class MockSlipBuilder:
    async def build(
        self, selections: list[Selection], base_url: Optional[str] = None
    ) -> GenerateCodeResponse:
        legs = [
            sel.model_copy(update={
                "status": "skipped",
                "found_odds": None,
                "market_note": "DEMO ONLY — no bookmaker market was checked or added",
            })
            for sel in selections
        ]
        return GenerateCodeResponse(
            booking_code=None,
            legs=legs,
            builder_used="mock",
            logs=[
                "[mock] Simulation mode only.",
                "[mock] No live bookmaker was contacted; no real booking code can be generated.",
                "[mock] Configure an authorised booking API to create a real slip.",
            ],
        )
