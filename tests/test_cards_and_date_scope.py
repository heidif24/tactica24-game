from backend.market_discovery import ManageBetCodesMarketDiscovery
from backend.parser import deterministic_parse


def test_unqualified_first_half_cards_means_total_cards_and_today():
    rule = deterministic_parse("find upcoming today matches and select under 1.5 cards first half")
    assert rule.market_category == "cards"
    assert rule.sub_market == "total_interval_cards"
    assert rule.selection_target.value == "total"
    assert rule.direction.value == "under"
    assert rule.line == 1.5
    assert rule.time_window == "00:00-44:59"
    assert rule.date_scope == "today"


def test_total_cards_market_does_not_match_team_cards_market():
    matches = ManageBetCodesMarketDiscovery._market_matches
    assert matches("Total Cards First Half", "cards", "total_interval_cards")
    assert not matches("Home Team Cards First Half", "cards", "total_interval_cards")
    assert matches("Home Team Cards First Half", "cards", "team_interval_cards")
