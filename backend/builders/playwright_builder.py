"""
Playwright-based 1xBet betslip builder.

WARNING: Automating a bookmaker site typically violates ToS.
Use only on accounts / jurisdictions where you accept the risk.
All DOM selectors are centralized in SELECTORS so they can be updated
without touching flow logic.
"""

from __future__ import annotations

import base64
import logging
import os
import re
from typing import Optional

from backend.models import GenerateCodeResponse, Selection

logger = logging.getLogger(__name__)

# ── Centralized selectors (update here when 1xBet DOM changes) ──────────────
SELECTORS = {
    "search_input": [
        "input[placeholder*='Search']",
        "input[placeholder*='search']",
        "input.search-input",
        "#search-input",
        "input[type='search']",
    ],
    "search_result_item": [
        ".search-popup .search-popup-events__item",
        ".search-results .event-item",
        "[class*='search'] [class*='event']",
    ],
    "corners_tab": [
        "button:has-text('Corners')",
        "div[class*='tab']:has-text('Corners')",
        "span:has-text('Corners')",
        "[data-market*='corner']",
    ],
    "odds_button": [
        "span.koeff",
        "[class*='odds']",
        "button[class*='coeff']",
        ".bet-btn",
    ],
    "betslip_toggle": [
        ".betslip-counter",
        "[class*='betslip']",
        "#betslip",
    ],
    "save_load_button": [
        "button:has-text('Save')",
        "button:has-text('Save / Load')",
        "[class*='save']",
        "span:has-text('Save')",
    ],
    "save_confirm": [
        "button:has-text('Save')",
        ".coupon-save-btn",
    ],
    "booking_code": [
        ".coupon-code",
        "[class*='booking-code']",
        "[class*='coupon'] input",
        "input[readonly]",
    ],
}

DEFAULT_TIMEOUT_MS = 12_000
NAV_TIMEOUT_MS = 25_000


class Playwright1xBetBuilder:
    def __init__(self) -> None:
        self.base_url = os.getenv("ONEXBET_BASE_URL", "https://1xbet.ng").rstrip("/")
        self.headless = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")

    async def build(
        self, selections: list[Selection], base_url: Optional[str] = None
    ) -> GenerateCodeResponse:
        from playwright.async_api import async_playwright, TimeoutError as PwTimeout

        url = (base_url or self.base_url).rstrip("/")
        logs: list[str] = [f"[pw] Launching Chromium (headless={self.headless}) → {url}"]
        legs: list[Selection] = []
        screenshot_b64: Optional[str] = None
        booking_code: Optional[str] = None

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
            )
            context = await browser.new_context(
                viewport={"width": 1400, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            # light stealth
            await context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            page = await context.new_page()
            page.set_default_timeout(DEFAULT_TIMEOUT_MS)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT_MS)
                logs.append("[pw] Homepage loaded")

                for sel in selections:
                    try:
                        matched = await self._add_leg(page, sel, logs)
                        legs.append(matched)
                    except Exception as exc:
                        logs.append(f"[pw] ERROR on {sel.team_name}: {exc}")
                        legs.append(
                            sel.model_copy(
                                update={
                                    "status": "skipped",
                                    "market_note": str(exc)[:200],
                                }
                            )
                        )

                valid = [l for l in legs if l.status == "matched"]
                if valid:
                    booking_code, screenshot_b64 = await self._save_slip(page, logs)
                else:
                    logs.append("[pw] No matched legs — skipping save")

            except PwTimeout as exc:
                logs.append(f"[pw] Timeout: {exc}")
            except Exception as exc:
                logs.append(f"[pw] Fatal: {exc}")
            finally:
                await browser.close()
                logs.append("[pw] Browser closed")

        return GenerateCodeResponse(
            booking_code=booking_code,
            legs=legs,
            screenshot_b64=screenshot_b64,
            builder_used="playwright",
            logs=logs,
        )

    async def _click_first(self, page, keys: list[str], timeout: int = 5000) -> bool:
        for sel in keys:
            try:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    await loc.click(timeout=timeout)
                    return True
            except Exception:
                continue
        return False

    async def _add_leg(self, page, sel: Selection, logs: list[str]) -> Selection:
        query = f"{sel.home_team} {sel.away_team}"
        logs.append(f"[pw] Searching: {query}")

        # focus search
        found_search = False
        for s in SELECTORS["search_input"]:
            try:
                inp = page.locator(s).first
                if await inp.count() > 0:
                    await inp.click()
                    await inp.fill(query)
                    await page.wait_for_timeout(800)
                    found_search = True
                    break
            except Exception:
                continue

        if not found_search:
            return sel.model_copy(
                update={"status": "skipped", "market_note": "Search input not found"}
            )

        # click first result
        clicked = await self._click_first(page, SELECTORS["search_result_item"])
        if not clicked:
            return sel.model_copy(
                update={"status": "unavailable", "market_note": "Fixture not found in search"}
            )
        await page.wait_for_timeout(1200)
        logs.append("[pw] Opened fixture")

        # Corners tab
        tab_ok = await self._click_first(page, SELECTORS["corners_tab"])
        if not tab_ok:
            logs.append("[pw] Corners tab not found — trying page content")
        await page.wait_for_timeout(600)

        # Try to locate an odds button that roughly matches the interval / under line
        # This is deliberately tolerant; real production needs tighter market matching.
        odds_clicked = False
        found_odds_val: Optional[float] = None
        for s in SELECTORS["odds_button"]:
            try:
                buttons = page.locator(s)
                count = await buttons.count()
                for i in range(min(count, 40)):
                    btn = buttons.nth(i)
                    txt = (await btn.inner_text()).strip()
                    # crude filter: look for decimal odds near fair range
                    m = re.search(r"(\d+[.,]\d{2})", txt)
                    if not m:
                        continue
                    val = float(m.group(1).replace(",", "."))
                    if 1.01 <= val <= 50:
                        await btn.click()
                        odds_clicked = True
                        found_odds_val = val
                        logs.append(f"[pw] Clicked odds {val} for {sel.team_name}")
                        break
                if odds_clicked:
                    break
            except Exception:
                continue

        if not odds_clicked:
            return sel.model_copy(
                update={
                    "status": "unavailable",
                    "market_note": "Matching corner interval market not found / suspended",
                }
            )

        await page.wait_for_timeout(400)
        return sel.model_copy(
            update={
                "status": "matched",
                "found_odds": found_odds_val,
                "market_note": "Added via Playwright",
            }
        )

    async def _save_slip(self, page, logs: list[str]) -> tuple[Optional[str], Optional[str]]:
        logs.append("[pw] Opening Save / Load modal")
        await self._click_first(page, SELECTORS["betslip_toggle"])
        await page.wait_for_timeout(500)
        await self._click_first(page, SELECTORS["save_load_button"])
        await page.wait_for_timeout(700)
        await self._click_first(page, SELECTORS["save_confirm"])
        await page.wait_for_timeout(1000)

        code: Optional[str] = None
        for s in SELECTORS["booking_code"]:
            try:
                loc = page.locator(s).first
                if await loc.count() > 0:
                    raw = await loc.input_value() if await loc.evaluate("el => el.tagName") == "INPUT" else await loc.inner_text()
                    raw = raw.strip()
                    if re.match(r"^[A-Z0-9]{4,20}$", raw, re.I):
                        code = raw.upper()
                        break
            except Exception:
                continue

        screenshot_b64 = None
        try:
            png = await page.screenshot(full_page=False)
            screenshot_b64 = base64.b64encode(png).decode()
            logs.append("[pw] Screenshot captured")
        except Exception as exc:
            logs.append(f"[pw] Screenshot failed: {exc}")

        if code:
            logs.append(f"[pw] Booking code: {code}")
        else:
            logs.append("[pw] Could not extract booking code from modal")

        return code, screenshot_b64
