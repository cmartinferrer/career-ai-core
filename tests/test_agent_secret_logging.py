"""Regression tests for secret-safe Gemini error handling."""

import logging
from unittest.mock import MagicMock

import pytest

from career_ai_core import agent as agent_module


def test_missing_api_key_uses_english_internal_error(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_API_KEY is not configured"):
        agent_module.CareerAgent()


def test_unexpected_provider_error_does_not_log_exception_details(monkeypatch, caplog):
    secret = "sensitive-provider-detail-123"
    instance = object.__new__(agent_module.CareerAgent)
    instance.client = MagicMock()
    instance.client.models.generate_content.side_effect = RuntimeError(secret)
    instance.model = "test-model"
    instance.system_instruction = "Test instructions"

    with caplog.at_level(logging.ERROR, logger=agent_module.__name__):
        response = instance.ask("Hello")

    assert (
        response
        == agent_module.get_translations(agent_module.configured_locale())[
            "assistant_unexpected_error"
        ]
    )
    assert secret not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)
