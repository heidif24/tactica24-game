"""Live bookmaker market discovery through the documented Manage Bet Codes API.

The adapter deliberately fails closed: a market must be found for the exact
fixture, period, category, line and outcome before a pick can be resolved.
"""
from __future__ import annotations

import re
from typing import Any

import httpx


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _get_first(obj: dict, *keys: str):
    for key in keys:
        value = obj.get(key)
        if value not in (None, ""):
            return value
    return None


class ManageBetCodesMarketDiscovery:
    def __init__(self, base: str, api_key: str, timeout: float = 25.0):
        self.base = base.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def _catalog(self, client: httpx.AsyncClient, path: str) -> Any:
        response = await client.get(f"{self.base}/{path}")
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _items(payload: Any, *names: str) -> list[dict]:
        for node in _walk_dicts(payload):
            for name in names:
                value = node.get(name)
                if isinstance(value, list):
                    return [x for x in value if isinstance(x, dict)]
        return []

    @staticmethod
    def _event_matches(event: dict, home: str, away: str, league: str) -> bool:
        home_value = _get_first(event, "home_team", "home", "home_name")
        away_value = _get_first(event, "away_team", "away", "away_name")
        teams = event.get("teams")
        if isinstance(teams, dict):
            home_value = home_value or _get_first(teams, "home", "home_team")
            away_value = away_value or _get_first(teams, "away", "away_team")
            if isinstance(home_value, dict):
                home_value = _get_first(home_value, "name", "team")
            if isinstance(away_value, dict):
                away_value = _get_first(away_value, "name", "team")
        if not home_value or not away_value:
            return False
        h, a = _norm(home_value), _norm(away_value)
        wanted_h, wanted_a = _norm(home), _norm(away)
        teams_match = (wanted_h in h or h in wanted_h) and (wanted_a in a or a in wanted_a)
        if not teams_match:
            return False
        event_league = _norm(_get_first(event, "league", "competition", "league_name"))
        return not league or not event_league or _norm(league) in event_league or event_league in _norm(league)

    @staticmethod
    def _period_matches(label: str, period: str) -> bool:
        if period in ("full_match", "90", "match"):
            # A period-specific market is not a full-match market.
            return not re.search(r"first half|second half|1st half|2nd half|\bht\b|\bminute\b|min\s*\d", label)
        if period == "00:00-44:59":
            return any(term in label for term in ("first half", "1st half", "half time", "ht"))
        if period == "45:00-89:59":
            return any(term in label for term in ("second half", "2nd half", "2h"))
        start_end = re.search(r"(\d{1,2}):(\d{2})\s*[-–]\s*(\d{1,2}):(\d{2})", period)
        if not start_end:
            return False
        start = int(start_end.group(1)) * 60 + int(start_end.group(2))
        end = int(start_end.group(3)) * 60 + int(start_end.group(4))
        # Accept explicit minute ranges only; do not infer an interval from a
        # generic "first half" or full-match market.
        minute_ranges = [
            (int(a), int(b))
            for a, b in re.findall(r"(\d{1,3})\s*(?:-|to)\s*(\d{1,3})\s*(?:min|minute)", label)
        ]
        if minute_ranges:
            return any(a * 60 == start and b * 60 - 1 == end for a, b in minute_ranges)
        compact = _norm(period)
        if compact and compact in _norm(label):
            return True
        first_minute = re.search(r"first\s*(\d+)\s*(?:minutes?|mins?)", label)
        if first_minute:
            minutes = int(first_minute.group(1))
            return start == 0 and end == minutes * 60 - 1
        return False

    @staticmethod
    def _market_matches(label: str, category: str, sub_market: str) -> bool:
        text = _norm(label)
        if category == "corners":
            if "corner" not in text:
                return False
            if "team_interval" in sub_market or "team_corners" in sub_market:
                return "team" in text or "home" in text or "away" in text
            if "total_interval" in sub_market or "total_corners" in sub_market:
                return "team" not in text
            return True
        if category == "goals":
            return "goal" in text and "player" not in text
        if category == "btts":
            return ("both teams" in text and "score" in text) or "btts" in text
        if category == "result":
            return any(term in text for term in ("1x2", "match result", "full time result", "winner"))
        if category == "cards":
            return "card" in text
        return False

    async def discover(self, selection, bookmaker: str) -> dict | None:
        """Return an exact provider pick descriptor or None when not found."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, connect=8.0)) as client:
            bookmakers = await self._catalog(client, "bookmakers")
            book_items = self._items(bookmakers, "bookmakers", "items")
            book = next(
                (b for b in book_items if _norm(_get_first(b, "key", "id", "slug", "name")) == _norm(bookmaker)),
                None,
            )
            if book is not None and (
                book.get("supports_book") is False
                or book.get("supports_resolve") is False
                or book.get("supports_search") is False
            ):
                return None

            search_response = await client.post(
                f"{self.base}/events/search",
                headers=self._headers(),
                json={"bookmaker": bookmaker, "queries": [f"{selection.home_team} vs {selection.away_team}"]},
            )
            search_response.raise_for_status()
            search_payload = search_response.json()
            events = self._items(search_payload, "events", "results", "matches", "items", "data")
            matching = [
                event for event in events
                if self._event_matches(event, selection.home_team, selection.away_team, selection.league)
            ]
            if len(matching) != 1:
                return None
            event = matching[0]
            event_id = _get_first(event, "event_id", "id", "fixture_id")
            if not event_id:
                return None

            wanted_category = getattr(selection, "market_category", "corners")
            wanted_sub = getattr(selection, "sub_market", "team_interval_corners")
            period = selection.time_window
            supports_markets = book.get("supports_markets", True) if book else True

            if supports_markets:
                response = await client.get(
                    f"{self.base}/events/{event_id}/markets",
                    headers=self._headers(),
                    params={"bookmaker": bookmaker},
                )
                response.raise_for_status()
                payload = response.json()
                markets = self._items(payload, "markets", "items", "data")
            else:
                # Some bookmakers support search/resolve but do not expose a
                # per-event market catalogue. Use the provider's canonical
                # market catalogue, then let resolve perform the final exact
                # event-specific validation.
                payload = await self._catalog(client, "markets")
                markets = self._items(payload, "markets", "items", "data")

            candidates = []
            for market in markets:
                label = str(_get_first(market, "canonical", "name", "label", "market", "title") or "")
                if not self._market_matches(label, wanted_category, wanted_sub):
                    continue
                if not self._period_matches(label, period):
                    continue
                candidates.append((market, label))
            if len(candidates) != 1:
                return None

            market, label = candidates[0]
            outcomes = market.get("outcomes") or market.get("selections") or []
            if not isinstance(outcomes, list):
                return None
            expected = _norm(getattr(selection, "bookmaker_outcome", None) or selection.direction)
            if selection.selection_side == "home" and wanted_category == "result":
                expected = "home"
            elif selection.selection_side == "away" and wanted_category == "result":
                expected = "away"
            elif selection.selection_side == "draw":
                expected = "draw"
            elif selection.selection_side == "total" and wanted_category in ("goals", "corners"):
                expected = "over" if selection.direction == "over" else "under"

            matched = []
            for outcome in outcomes:
                if not isinstance(outcome, dict):
                    continue
                name = _norm(_get_first(outcome, "canonical", "name", "label", "outcome"))
                line = _get_first(outcome, "line", "handicap", "total")
                if expected and expected not in name:
                    continue
                if line is not None:
                    try:
                        if abs(float(str(line).replace(",", ".")) - float(selection.line)) > 1e-6:
                            continue
                    except ValueError:
                        continue
                matched.append(outcome)
            if len(matched) != 1:
                return None

            outcome = matched[0]
            key = _get_first(outcome, "key", "selection_key", "id")
            odds = _get_first(outcome, "odds", "price", "decimal_odds")
            canonical_market = _get_first(market, "canonical", "name", "label") or label
            canonical_outcome = _get_first(outcome, "canonical", "name", "label", "outcome")
            if not key and not canonical_outcome:
                return None
            return {
                "event_id": str(event_id),
                "key": str(key) if key else None,
                "market": str(canonical_market),
                "outcome": str(canonical_outcome) if canonical_outcome else None,
                "line": str(_get_first(outcome, "line", "handicap", "total") or selection.line),
                "odds": str(odds) if odds is not None else None,
            }
