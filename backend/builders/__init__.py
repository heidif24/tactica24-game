"""Slip builders: mock simulation and authorised external booking API."""

from __future__ import annotations

import os
from typing import Protocol

from backend.models import GenerateCodeResponse, Selection


class SlipBuilder(Protocol):
    async def build(self, selections: list[Selection], base_url: str | None = None) -> GenerateCodeResponse:
        ...


def get_builder() -> SlipBuilder:
    name = os.getenv("SLIP_BUILDER", "mock").lower()
    if name == "api":
        from backend.builders.api_builder import ExternalCodeApiBuilder
        return ExternalCodeApiBuilder()
    if name == "playwright":
        raise RuntimeError(
            "Unverified bookmaker browser automation is disabled. "
            "Use an authorised booking API; do not rely on generic odds-button selectors."
        )
    if name == "mock":
        from backend.builders.mock_builder import MockSlipBuilder
        return MockSlipBuilder()
    raise RuntimeError(f"Unsupported SLIP_BUILDER={name!r}; choose 'mock' or 'api'")
