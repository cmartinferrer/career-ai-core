"""Integration tests for localized interface copy."""

from career_ai_core.components import render_compact_experience, render_experience
from career_ai_core.config import rate_limit_period_text
from career_ai_core.i18n import configured_locale, get_translations


def test_english_is_default(monkeypatch):
    monkeypatch.delenv("CAREER_AI_LOCALE", raising=False)
    assert configured_locale() == "en"


def test_owner_can_select_spanish(monkeypatch):
    monkeypatch.setenv("CAREER_AI_LOCALE", "es")
    assert configured_locale() == "es"
    assert get_translations(configured_locale())["assistant_heading"] == "ASISTENTE IA"


def test_invalid_owner_locale_fails_fast(monkeypatch):
    import pytest

    monkeypatch.setenv("CAREER_AI_LOCALE", "fr")
    with pytest.raises(ValueError, match="Unsupported locale"):
        configured_locale()


def test_experience_headings_are_localized():
    assert "Professional experience" in render_experience([], locale="en")
    assert "Trayectoria profesional" in render_experience([], locale="es")


def test_compact_experience_is_localized():
    experiences = [{"company": "Example", "role": "Engineer", "period": {"start": "2020"}}]
    assert "Present" in render_compact_experience(experiences, locale="en")
    assert "Actualidad" in render_compact_experience(experiences, locale="es")


def test_rate_limit_period_is_localized(monkeypatch):
    monkeypatch.setattr("career_ai_core.config.RATE_LIMIT_WINDOW_SECONDS", 3600)
    assert rate_limit_period_text("en") == "1 hour"
    assert rate_limit_period_text("es") == "1 hora"
