"""Tests for UI request handling, lazy agent creation, and Gradio wiring."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from career_ai_core import ui


class TestAgentLifecycle:
    """Verify that the career agent is created only when needed."""

    def test_creates_agent_on_first_access(self, monkeypatch):
        """Instantiate and cache the agent when no instance exists."""
        constructor = Mock(return_value=object())
        monkeypatch.setattr(ui, "agent", None)
        monkeypatch.setattr(ui, "CareerAgent", constructor)

        result = ui.get_agent()

        assert result is ui.agent
        constructor.assert_called_once_with()

    def test_reuses_existing_agent(self, monkeypatch):
        """Return the cached agent without constructing another one."""
        existing = object()
        constructor = Mock()
        monkeypatch.setattr(ui, "agent", existing)
        monkeypatch.setattr(ui, "CareerAgent", constructor)

        assert ui.get_agent() is existing
        constructor.assert_not_called()


class TestRespond:
    """Verify visitor identification, rejection messages, and delegation."""

    @pytest.fixture
    def setup(self, monkeypatch):
        """Provide isolated limiter, agent, and translated UI messages."""
        limiter = SimpleNamespace(check=Mock(return_value=None))
        agent = SimpleNamespace(ask=Mock(return_value="Answer"))
        translations = {
            "global_daily_limit_message": "Global quota reached",
            "rate_limit_message": "Maximum {max_requests} in {period}",
        }
        monkeypatch.setattr(ui, "rate_limiter", limiter)
        monkeypatch.setattr(ui, "get_agent", Mock(return_value=agent))
        monkeypatch.setattr(ui, "configured_locale", Mock(return_value="en"))
        monkeypatch.setattr(ui, "get_translations", Mock(return_value=translations))
        return limiter, agent

    def test_delegates_allowed_request_to_agent(self, setup):
        """Pass the visitor's message and history unchanged to the agent."""
        limiter, agent = setup
        history = [{"role": "user", "content": "Earlier"}]
        request = SimpleNamespace(client=SimpleNamespace(host="visitor-1"))

        assert ui.respond("Question", history, request) == "Answer"

        limiter.check.assert_called_once_with("visitor-1")
        agent.ask.assert_called_once_with("Question", history)

    def test_uses_unknown_for_request_without_client(self, setup):
        """Assign a stable fallback identifier when client metadata is missing."""
        limiter, _ = setup

        assert ui.respond("Question", [], SimpleNamespace(client=None)) == "Answer"

        limiter.check.assert_called_once_with("unknown")

    def test_global_rejection_does_not_invoke_agent(self, setup):
        """Return the global quota message without calling the agent."""
        limiter, agent = setup
        limiter.check.return_value = "global"

        result = ui.respond("Question", [], SimpleNamespace(client=None))

        assert result == "Global quota reached"
        agent.ask.assert_not_called()
        ui.get_agent.assert_not_called()

    def test_visitor_rejection_includes_limit_and_period(self, setup, monkeypatch):
        """Format the visitor quota message with configured limit and period."""
        limiter, agent = setup
        limiter.check.return_value = "visitor"
        monkeypatch.setattr(ui, "MAX_REQUESTS", 7)
        monkeypatch.setattr(ui, "rate_limit_period_text", Mock(return_value="one hour"))

        result = ui.respond("Question", [], SimpleNamespace(client=None))

        assert result == "Maximum 7 in one hour"
        ui.rate_limit_period_text.assert_called_once_with()
        agent.ask.assert_not_called()
        ui.get_agent.assert_not_called()


class FakeComponent:
    """Record Gradio component construction and registered event handlers."""

    def __init__(self, kind, registry, *args, **kwargs):
        self.kind = kind
        self.args = args
        self.kwargs = kwargs
        self.events = []
        registry.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def click(self, **kwargs):
        self.events.append(("click", kwargs))

    def change(self, **kwargs):
        self.events.append(("change", kwargs))

    def launch(self, **kwargs):
        self.events.append(("launch", kwargs))


class TestLaunchApp:
    """Verify Gradio layout, localization, voice controls, and launch options."""

    @pytest.fixture
    def app(self, monkeypatch):
        """Replace Gradio widgets with lightweight recording components."""
        registry = []
        for name in ("Blocks", "Row", "Column", "HTML", "Button", "Chatbot", "ChatInterface"):
            monkeypatch.setattr(
                ui.gr,
                name,
                lambda *args, _name=name, **kwargs: FakeComponent(_name, registry, *args, **kwargs),
            )

        messages = {
            "voice_disable": 'Disable "voice"',
            "voice_enable": "Enable voice",
            "voice_replay": "Replay voice",
            "voice_stop": "Stop voice",
            "assistant_heading": "<Assistant>",
            "assistant_welcome": "Ask about {candidate_name}",
            "example_experience": "Experience?",
            "example_projects": "Projects?",
            "example_skills": "Skills?",
            "example_education": "Education?",
        }
        candidate = SimpleNamespace(
            knowledge={
                "profile": {"personal": {"name": "Alex <Example>"}},
                "experience": {"experiences": [{"company": "Example"}]},
            }
        )
        monkeypatch.setattr(ui, "get_agent", Mock(return_value=candidate))
        monkeypatch.setattr(ui, "configured_locale", Mock(return_value="en"))
        monkeypatch.setattr(ui, "get_translations", Mock(return_value=messages))
        header = Mock(return_value="<header>Candidate</header>")
        experience = Mock(return_value="<aside>Experience</aside>")
        monkeypatch.setattr(ui, "render_compact_header", header)
        monkeypatch.setattr(ui, "render_compact_experience", experience)
        return registry, messages, header, experience

    @staticmethod
    def _one(registry, kind, **filters):
        """Find one recorded component by kind and selected properties."""
        matches = [
            component
            for component in registry
            if component.kind == kind
            and all(component.kwargs.get(key) == value for key, value in filters.items())
        ]
        assert len(matches) == 1, (kind, filters, matches)
        return matches[0]

    def test_builds_candidate_specific_layout(self, app, monkeypatch):
        """Render the profile, experience sidebar, chat, and localized examples."""
        registry, messages, header, experience = app
        monkeypatch.setenv("PORT", "8123")

        ui.launch_app()

        header.assert_called_once_with({"personal": {"name": "Alex <Example>"}})
        experience.assert_called_once_with([{"company": "Example"}], locale="en")
        blocks = self._one(registry, "Blocks")
        assert blocks.kwargs["title"] == "Alex <Example> | Career AI"
        assert blocks.kwargs["head"] == ui.VOICE_JS
        assert any(c.kind == "HTML" and c.args == ("<header>Candidate</header>",) for c in registry)
        assert any(c.kind == "HTML" and c.args == ("<aside>Experience</aside>",) for c in registry)
        assert any(c.kind == "HTML" and "&lt;Assistant&gt;" in c.args[0] for c in registry)
        chatbot = self._one(registry, "Chatbot")
        assert chatbot.kwargs["height"] == 565
        assert chatbot.kwargs["placeholder"] == "Ask about Alex <Example>"
        chat_interface = self._one(registry, "ChatInterface")
        assert chat_interface.kwargs["fn"] is ui.respond
        assert chat_interface.kwargs["chatbot"] is chatbot
        assert chat_interface.kwargs["examples"] == [
            messages["example_experience"],
            messages["example_projects"],
            messages["example_skills"],
            messages["example_education"],
        ]
        launch = blocks.events[0][1]
        assert launch["server_name"] == "0.0.0.0"
        assert launch["server_port"] == 8123
        assert launch["css"].startswith(ui.CUSTOM_CSS + "\n")
        assert '--voice-disable: "Disable \\"voice\\"";' in launch["css"]
        assert "--voice-enable:" in launch["css"]
        assert "--voice-replay:" in launch["css"]
        assert "--voice-stop:" in launch["css"]

    def test_default_port_and_missing_candidate_name(self, app, monkeypatch):
        """Use the default port and generic candidate name when unspecified."""
        registry, _, _, _ = app
        monkeypatch.delenv("PORT", raising=False)
        ui.get_agent.return_value.knowledge["profile"] = {}

        ui.launch_app()

        assert self._one(registry, "Blocks").kwargs["title"] == "Candidate | Career AI"
        assert self._one(registry, "Chatbot").kwargs["placeholder"] == "Ask about Candidate"
        assert self._one(registry, "Blocks").events[0][1]["server_port"] == 7860

    def test_registers_voice_control_handlers(self, app):
        """Wire chat changes, automatic speech, replay, and stop to JavaScript."""
        registry, _, _, _ = app

        ui.launch_app()

        chatbot = self._one(registry, "Chatbot")
        assert len(chatbot.events) == 1
        assert chatbot.events[0][0] == "change"
        assert "onMessagesChanged(messages)" in chatbot.events[0][1]["js"]
        assert chatbot.events[0][1]["fn"] is None

        buttons = {c.kwargs["elem_id"]: c for c in registry if c.kind == "Button"}
        assert set(buttons) == {"auto-voice-button", "replay-voice-button", "stop-voice-button"}
        for button in buttons.values():
            assert len(button.events) == 1
            assert button.events[0][0] == "click"
            assert button.events[0][1]["fn"] is None
        auto_js = buttons["auto-voice-button"].events[0][1]["js"]
        assert "toggleAuto()" in auto_js
        assert json.dumps('Disable "voice"', ensure_ascii=False) in auto_js
        assert "Enable voice" in auto_js
        assert "__VOICE_ON__" not in auto_js
        assert "__VOICE_OFF__" not in auto_js
        assert "replay()" in buttons["replay-voice-button"].events[0][1]["js"]
        assert "stop()" in buttons["stop-voice-button"].events[0][1]["js"]
