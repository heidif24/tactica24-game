from backend.parser import deterministic_parse
from backend.models import SelectionTarget


def test_parser_recognises_full_match_goals():
    rule = deterministic_parse("Find under 2.5 goals, minimum 75%, max 3 legs")
    assert rule.market_category == "goals"
    assert rule.sub_market == "total_goals"
    assert rule.time_window == "full_match"
    assert rule.line == 2.5


def test_parser_recognises_first_five_corner_interval():
    rule = deterministic_parse("No corner in first 5 minutes, minimum 80%")
    assert rule.market_category == "corners"
    assert rule.time_window == "00:00-04:59"
    assert rule.sub_market == "team_interval_corners"


def test_parser_recognises_btts_no():
    rule = deterministic_parse("BTTS No, minimum 70%")
    assert rule.market_category == "btts"
    assert rule.outcome == "No"


def test_parser_recognises_1x2_draw():
    rule = deterministic_parse("1X2 draw, minimum 30%")
    assert rule.market_category == "result"
    assert rule.selection_target == SelectionTarget.DRAW


def test_parser_recognises_double_chance_1x():
    rule = deterministic_parse("Double chance 1X, minimum 80%")
    assert rule.market_category == "double_chance"
    assert rule.outcome == "1X"
