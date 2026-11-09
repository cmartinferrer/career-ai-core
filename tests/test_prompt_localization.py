"""Tests for language-independent Gemini instructions and localized errors."""

import pytest

from career_ai_core.i18n import get_translations
from career_ai_core.prompts import build_system_instruction


@pytest.fixture
def candidate_knowledge():
    return {
        "profile": {
            "personal": {"name": "Alex Example", "professional_title": "Engineer"},
            "summary": "Builds reliable software",
        }
    }


def test_prompt_preserves_candidate_identity_and_professional_data(candidate_knowledge):
    prompt = build_system_instruction(candidate_knowledge)
    assert "Alex Example" in prompt
    assert "Engineer" in prompt
    assert "Builds reliable software" in prompt


def test_prompt_requires_visitor_language_and_prohibits_invented_claims(candidate_knowledge):
    prompt = build_system_instruction(candidate_knowledge)
    assert "Reply in the language used by the visitor" in prompt
    assert "Never invent experience" in prompt
    assert "Never impersonate" in prompt
    assert "Do not disclose unrelated personal information" in prompt


@pytest.mark.parametrize("locale", ["en", "es"])
def test_agent_error_translations_are_available(locale):
    messages = get_translations(locale)
    for key in (
        "assistant_empty_response",
        "assistant_quota_error",
        "assistant_unavailable",
        "assistant_request_error",
        "assistant_unexpected_error",
    ):
        assert isinstance(messages[key], str)
        assert messages[key].strip()
