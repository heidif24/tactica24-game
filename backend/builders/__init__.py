"""Slip builders: demo-only mock and verified partner APIs."""
from __future__ import annotations
import os
from typing import Protocol
from backend.models import GenerateCodeResponse, Selection

class SlipBuilder(Protocol):
    async def build(self, selections: list[Selection], base_url: str | None = None) -> GenerateCodeResponse: ...

def get_builder() -> SlipBuilder:
    name = os.getenv("SLIP_BUILDER", "mock").lower()
    if name in ("manage_bet_codes", "mbc"):
        from backend.builders.manage_bet_codes import ManageBetCodesBuilder
        return ManageBetCodesBuilder()
    if name == "api":
        from backend.builders.api_builder import ExternalCodeApiBuilder
        return ExternalCodeApiBuilder()
    if name == "playwright":
        raise RuntimeError("Unverified bookmaker browser automation is disabled; use a verified partner API.")
    if name == "mock":
        from backend.builders.mock_builder import MockSlipBuilder
        return MockSlipBuilder()
    raise RuntimeError(f"Unsupported SLIP_BUILDER={name!r}; choose mock, manage_bet_codes, or api")
