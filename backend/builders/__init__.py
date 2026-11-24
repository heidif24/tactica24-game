"""Slip builders: mock, playwright, external API."""

from __future__ import annotations

import os
from typing import Protocol

from backend.models import GenerateCodeResponse, Selection


class SlipBuilder(Protocol):
    async def build(self, selections: list[Selection], base_url: str | None = None) -> GenerateCodeResponse:
        ...


def get_builder() -> SlipBuilder:
    name = os.getenv("SLIP_BUILDER", "mock").lower()
    if name == "playwright":
        from backend.builders.playwright_builder import Playwright1xBetBuilder
        return Playwright1xBetBuilder()
    if name == "api":
        from backend.builders.api_builder import ExternalCodeApiBuilder
        return ExternalCodeApiBuilder()
    from backend.builders.mock_builder import MockSlipBuilder
    return MockSlipBuilder()
