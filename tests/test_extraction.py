from pathlib import Path

import pytest

from career_ai_core.components import render_compact_header
from career_ai_core.knowledge import load_knowledge

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample-data"


def test_sample_candidate_loads():
    knowledge = load_knowledge(SAMPLE)
    assert knowledge["profile"]["personal"]["name"] == "Alex Example"


def test_render_is_candidate_specific():
    html = render_compact_header(load_knowledge(SAMPLE)["profile"])
    assert "Alex Example" in html


def test_missing_configuration_is_explicit(monkeypatch):
    monkeypatch.delenv("CAREER_AI_DATA_DIR", raising=False)
    with pytest.raises(ValueError, match="CAREER_AI_DATA_DIR"):
        load_knowledge()
