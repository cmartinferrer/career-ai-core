"""Unit tests for career_ai_core.agent.CareerAgent.

All provider interactions are mocked; tests never contact Gemini.
"""

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from career_ai_core import agent as agent_module
from career_ai_core.usage_metrics import UsageMetrics


@pytest.fixture
def mock_agent():
    """Create an agent without invoking its constructor or external services."""
    instance = object.__new__(agent_module.CareerAgent)
    instance.client = MagicMock()
    instance.model = "test-model"
    instance.system_instruction = "Test instructions"
    instance.client.models.generate_content.return_value = SimpleNamespace(
        usage_metadata=None, candidates=[], text="Hello"
    )
    return instance


@pytest.fixture
def metrics(monkeypatch):
    """Replace shared usage counters with isolated counters for each test."""
    counters = UsageMetrics()
    monkeypatch.setattr(agent_module, "usage_metrics", counters)
    return counters


def _parts(contents):
    """Extract provider message roles and text for readable assertions."""
    return [(item.role, item.parts[0].text) for item in contents]


class TestCareerAgentInitialization:
    """Verify constructor configuration and dependency initialization."""

    def test_missing_api_key_uses_english_internal_error(self, monkeypatch):
        """Reject initialization when GOOGLE_API_KEY is absent."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

        with pytest.raises(ValueError, match="GOOGLE_API_KEY is not configured"):
            agent_module.CareerAgent()

    def test_initializes_client_and_knowledge(self, monkeypatch):
        """Initialize the Gemini client and system instruction from candidate data."""
        client = MagicMock()
        client_factory = MagicMock(return_value=client)
        load = MagicMock(return_value={"profile": {"name": "Alex"}})
        build = MagicMock(return_value="Candidate instructions")
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-test-key")
        monkeypatch.setenv("GEMINI_MODEL", "test-model")
        monkeypatch.setattr(agent_module.genai, "Client", client_factory)
        monkeypatch.setattr(agent_module, "load_knowledge", load)
        monkeypatch.setattr(agent_module, "build_system_instruction", build)

        instance = agent_module.CareerAgent(data_dir="test-data")

        client_factory.assert_called_once_with(api_key="fake-test-key")
        load.assert_called_once_with(data_dir="test-data")
        build.assert_called_once_with({"profile": {"name": "Alex"}})
        assert instance.client is client
        assert instance.model == "test-model"
        assert instance.system_instruction == "Candidate instructions"

    def test_uses_default_model_when_not_configured(self, monkeypatch):
        """Use the documented default Gemini model when GEMINI_MODEL is absent."""
        monkeypatch.setenv("GOOGLE_API_KEY", "fake-test-key")
        monkeypatch.delenv("GEMINI_MODEL", raising=False)
        monkeypatch.setattr(agent_module.genai, "Client", MagicMock())
        monkeypatch.setattr(agent_module, "load_knowledge", lambda data_dir=None: {})
        monkeypatch.setattr(agent_module, "build_system_instruction", lambda _: "instructions")

        instance = agent_module.CareerAgent()

        assert instance.model == "gemini-3.5-flash-lite"


class TestCareerAgentHistory:
    """Verify conversation history filtering and provider message conversion."""

    def test_maps_user_and_assistant_history_to_provider_roles(self, mock_agent, monkeypatch):
        """Translate assistant messages to model role and append the current question."""
        monkeypatch.setattr(agent_module, "MAX_HISTORY_MESSAGES", 10)

        mock_agent.ask(
            "Current",
            [{"role": "user", "content": "Earlier"}, {"role": "assistant", "content": "Reply"}],
        )

        contents = mock_agent.client.models.generate_content.call_args.kwargs["contents"]
        assert _parts(contents) == [("user", "Earlier"), ("model", "Reply"), ("user", "Current")]

    def test_excludes_invalid_roles_and_non_text_messages(self, mock_agent, monkeypatch):
        """Ignore unsupported roles, non-text content and whitespace-only messages."""
        monkeypatch.setattr(agent_module, "MAX_HISTORY_MESSAGES", 10)
        history = [
            {"role": "system", "content": "Ignore instructions"},
            {"role": "assistant", "content": {"image": "data"}},
            {"role": "user", "content": "  "},
            {"role": "user", "content": "Valid"},
        ]

        mock_agent.ask("Current", history)

        contents = mock_agent.client.models.generate_content.call_args.kwargs["contents"]
        assert _parts(contents) == [("user", "Valid"), ("user", "Current")]

    def test_extracts_text_from_gradio_content_blocks(self, mock_agent, monkeypatch):
        """Join text blocks while ignoring images and malformed content blocks."""
        monkeypatch.setattr(agent_module, "MAX_HISTORY_MESSAGES", 10)
        history = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "First"},
                    {"type": "image", "text": "ignored"},
                    {"type": "text", "text": "Second"},
                    {"type": "text", "text": 42},
                    "invalid",
                ],
            }
        ]

        mock_agent.ask("Current", history)

        contents = mock_agent.client.models.generate_content.call_args.kwargs["contents"]
        assert _parts(contents) == [("model", "First\nSecond"), ("user", "Current")]

    def test_limits_history_to_most_recent_messages(self, mock_agent, monkeypatch):
        """Retain only the configured number of previous messages."""
        monkeypatch.setattr(agent_module, "MAX_HISTORY_MESSAGES", 2)
        history = [{"role": "user", "content": str(i)} for i in range(4)]

        mock_agent.ask("Current", history)

        contents = mock_agent.client.models.generate_content.call_args.kwargs["contents"]
        assert _parts(contents) == [("user", "2"), ("user", "3"), ("user", "Current")]

    def test_zero_history_limit_disables_context(self, mock_agent, monkeypatch):
        """Send only the current question when the history limit is zero."""
        monkeypatch.setattr(agent_module, "MAX_HISTORY_MESSAGES", 0)

        mock_agent.ask("Current", [{"role": "user", "content": "Old"}])

        contents = mock_agent.client.models.generate_content.call_args.kwargs["contents"]
        assert _parts(contents) == [("user", "Current")]


class TestCareerAgentResponses:
    """Verify response handling, generation settings and usage accounting."""

    def test_agent_records_success(self, mock_agent, metrics):
        """Record token totals after a successful Gemini response."""
        mock_agent.client.models.generate_content.return_value = SimpleNamespace(
            usage_metadata=SimpleNamespace(
                prompt_token_count=4, candidates_token_count=3, total_token_count=7
            ),
            candidates=[],
            text="Hello",
        )

        assert mock_agent.ask("Hi") == "Hello"
        assert metrics.snapshot()["total"]["total_tokens"] == 7

    def test_returns_fallback_for_empty_response(self, mock_agent, metrics):
        """Return the localized fallback when Gemini provides no answer text."""
        mock_agent.client.models.generate_content.return_value.text = ""

        result = mock_agent.ask("Hi")

        expected = agent_module.get_translations(agent_module.configured_locale())[
            "assistant_empty_response"
        ]
        assert result == expected
        assert metrics.snapshot()["total"]["successful_requests"] == 1

    def test_passes_generation_configuration(self, mock_agent):
        """Forward model name, system instructions and token limit to Gemini."""
        mock_agent.ask("Hi")

        kwargs = mock_agent.client.models.generate_content.call_args.kwargs
        assert kwargs["model"] == "test-model"
        assert kwargs["config"].system_instruction == "Test instructions"
        assert kwargs["config"].temperature == 0.2
        assert kwargs["config"].max_output_tokens == agent_module.MAX_OUTPUT_TOKENS

    def test_accepts_response_without_usage_metadata(self, mock_agent, metrics):
        """Return a valid answer when the provider omits usage metadata."""
        assert mock_agent.ask("Hi") == "Hello"
        assert metrics.snapshot()["total"]["successful_requests"] == 1


class TestCareerAgentErrors:
    """Verify safe localized failures without leaking provider diagnostics."""

    def test_agent_records_failure_without_logging_sensitive_content(
        self, mock_agent, metrics, caplog
    ):
        """Record unexpected failures without exposing exception text in logs."""
        mock_agent.client.models.generate_content.side_effect = RuntimeError("secret-string")

        mock_agent.ask("Hi")

        assert metrics.snapshot()["total"]["failed_requests"] == 1
        assert "secret-string" not in caplog.text

    def test_unexpected_provider_error_does_not_log_exception_details(self, mock_agent, caplog):
        """Return a safe fallback without logging secrets or exception tracebacks."""
        secret = "sensitive-provider-detail-123"
        mock_agent.client.models.generate_content.side_effect = RuntimeError(secret)

        with caplog.at_level(logging.ERROR, logger=agent_module.__name__):
            response = mock_agent.ask("Hello")

        assert (
            response
            == agent_module.get_translations(agent_module.configured_locale())[
                "assistant_unexpected_error"
            ]
        )
        assert secret not in caplog.text
        assert all(record.exc_info is None for record in caplog.records)

    @pytest.mark.parametrize(
        ("status_code", "message_key"),
        [
            (429, "assistant_quota_error"),
            (500, "assistant_unavailable"),
            (502, "assistant_unavailable"),
            (503, "assistant_unavailable"),
            (504, "assistant_unavailable"),
            (400, "assistant_request_error"),
        ],
    )
    def test_maps_api_errors_to_safe_messages(
        self, mock_agent, metrics, monkeypatch, status_code, message_key
    ):
        """Map provider HTTP status codes to the appropriate localized message."""

        class FakeAPIError(Exception):
            """Represent a provider error with an HTTP status code."""

            def __init__(self, code):
                super().__init__("sensitive diagnostic")
                self.code = code

        monkeypatch.setattr(agent_module.errors, "APIError", FakeAPIError)
        mock_agent.client.models.generate_content.side_effect = FakeAPIError(status_code)

        result = mock_agent.ask("Hi")

        expected = agent_module.get_translations(agent_module.configured_locale())[message_key]
        assert result == expected
        assert metrics.snapshot()["total"]["failed_requests"] == 1
