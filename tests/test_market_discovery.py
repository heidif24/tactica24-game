from backend.market_discovery import ManageBetCodesMarketDiscovery


def test_interval_match_requires_exact_period_label():
    assert ManageBetCodesMarketDiscovery._period_matches("Team Corners First 5 Minutes", "00:00-04:59")
    assert not ManageBetCodesMarketDiscovery._period_matches("Team Corners", "00:00-04:59")
    assert not ManageBetCodesMarketDiscovery._period_matches("Team Corners First 10 Minutes", "00:00-04:59")


def test_full_match_does_not_accept_half_time_market():
    assert ManageBetCodesMarketDiscovery._period_matches("Total Goals Over Under", "full_match")
    assert not ManageBetCodesMarketDiscovery._period_matches("First Half Total Goals", "full_match")
