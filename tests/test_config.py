from youtuber_analysis import config


def test_config_loads():
    assert list(config.youtubers()) == ["joseph", "tom_nash", "fin_tek", "henry", "paul"]
    assert config.periods() == {"1month": 1, "3months": 3, "6months": 6, "1year": 12, "2years": 24}
    assert len(config.settings()["dataset"]["features"]) == 12
    assert "Stock" in config.search_tags()
