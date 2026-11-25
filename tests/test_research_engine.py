from backend.research_engine import _extract_json, _grounding_sources, _groq_sources


def test_extracts_json_from_model_fenced_response():
    parsed = _extract_json('```json\n{"summary":"ok","candidates":[]}\n```')
    assert parsed["summary"] == "ok"
    assert parsed["candidates"] == []


def test_grounding_sources_deduplicates_urls():
    candidate = {
        "groundingMetadata": {
            "groundingChunks": [
                {"web": {"uri": "https://example.com/a", "title": "A"}},
                {"web": {"uri": "https://example.com/a", "title": "A duplicate"}},
                {"web": {"uri": "https://example.com/b", "title": "B"}},
                {"web": {"uri": "not-a-url", "title": "Invalid"}},
            ]
        }
    }
    sources = _grounding_sources(candidate)
    assert [source["url"] for source in sources] == [
        "https://example.com/a", "https://example.com/b"
    ]


def test_grounding_sources_empty_when_metadata_missing():
    assert _grounding_sources({}) == []


def test_legacy_stats_provider_is_disabled_by_default(monkeypatch):
    import pytest
    from backend.stats_engine import get_provider
    monkeypatch.delenv("STATS_PROVIDER", raising=False)
    with pytest.raises(RuntimeError, match="legacy fixture-statistics engine is disabled"):
        get_provider()

def test_api_football_provider_cannot_be_selected(monkeypatch):
    import pytest
    from backend.stats_engine import get_provider
    monkeypatch.setenv("STATS_PROVIDER", "api_football")
    with pytest.raises(RuntimeError, match="legacy fixture-statistics engine is disabled"):
        get_provider()

def test_mock_stats_provider_requires_explicit_opt_in(monkeypatch):
    from backend.stats_engine import MockStatsProvider, get_provider
    monkeypatch.setenv("STATS_PROVIDER", "mock")
    assert isinstance(get_provider(), MockStatsProvider)


def test_groq_sources_reads_message_annotations():
    message = {
        "annotations": [
            {"type": "url_citation", "url_citation": {
                "url": "https://sports.example/match", "title": "Fixture report"
            }}
        ]
    }
    sources = _groq_sources(message, "Research summary", {"candidates": []})
    assert sources == [{
        "title": "Fixture report",
        "url": "https://sports.example/match",
    }]


def test_groq_sources_reads_candidate_urls_and_deduplicates():
    message = {"citations": [{"url": "https://sports.example/stats", "title": "Stats"}]}
    parsed = {"candidates": [{"source_urls": ["https://sports.example/stats"]}]}
    sources = _groq_sources(message, "See https://sports.example/stats", parsed)
    assert len(sources) == 1
    assert sources[0]["url"] == "https://sports.example/stats"



def test_groq_sources_extracts_urls_from_answer_text():
    sources = _groq_sources({}, "Evidence: https://league.example/fixtures?id=4.", {"candidates": []})
    assert sources
    assert sources[0]["url"] == "https://league.example/fixtures?id=4"

def test_groq_sources_reads_nested_executed_tool_urls():
    message = {"executed_tools": [{
        "type": "browser_search",
        "results": [{"url": "https://league.example/fixtures", "title": "Fixtures"}],
    }]}
    sources = _groq_sources(message, "Research summary", {"candidates": []})
    assert sources == [{
        "title": "Fixtures",
        "url": "https://league.example/fixtures",
    }]
