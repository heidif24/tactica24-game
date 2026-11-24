"""Deterministic mock builder for offline demos."""

from __future__ import annotations

import hashlib
import random
from typing import Optional

from backend.models import GenerateCodeResponse, Selection


class MockSlipBuilder:
    async def build(
        self, selections: list[Selection], base_url: Optional[str] = None
    ) -> GenerateCodeResponse:
        logs: list[str] = ["[mock] Using MockSlipBuilder — no browser launched"]
        legs: list[Selection] = []

        for i, sel in enumerate(selections):
            # simulate occasional unavailable market
            if i == 1 and len(selections) > 2 and random.random() < 0.25:
                updated = sel.model_copy(
                    update={
                        "status": "unavailable",
                        "market_note": "Mock: micro-interval market suspended",
                    }
                )
                logs.append(f"[mock] SKIP {sel.team_name} — market unavailable")
            else:
                # slightly juiced book odds vs fair
                found = round(sel.fair_odds * random.uniform(0.88, 0.97), 2)
                updated = sel.model_copy(
                    update={
                        "status": "matched",
                        "found_odds": found,
                        "market_note": "Mock matched",
                    }
                )
                logs.append(
                    f"[mock] MATCHED {sel.team_name} @ {found} (fair {sel.fair_odds})"
                )
            legs.append(updated)

        valid = [l for l in legs if l.status == "matched"]
        if not valid:
            return GenerateCodeResponse(
                booking_code=None,
                legs=legs,
                builder_used="mock",
                logs=logs + ["[mock] No valid legs — no code generated"],
            )

        seed = "|".join(f"{l.fixture_id}:{l.selection_side}" for l in valid)
        digest = hashlib.sha1(seed.encode()).hexdigest()[:8].upper()
        code = f"SF{digest}"
        logs.append(f"[mock] Booking code generated: {code}")

        return GenerateCodeResponse(
            booking_code=code,
            legs=legs,
            screenshot_b64=None,
            builder_used="mock",
            logs=logs,
        )
