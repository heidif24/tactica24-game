from backend.research_engine import _extract_json, _grounding_sources


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
