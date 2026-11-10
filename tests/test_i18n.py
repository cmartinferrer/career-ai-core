"""Tests for the interface translation catalogs."""

import pytest

from career_ai_core.i18n import SUPPORTED_LOCALES, configured_locale, get_translations


def test_default_locale_is_english():
    assert get_translations()["assistant_heading"] == "AI ASSISTANT"


def test_spanish_catalog_preserves_existing_headings():
    messages = get_translations("es")
    assert messages["assistant_heading"] == "ASISTENTE IA"
    assert messages["career_heading"] == "TRAYECTORIA PROFESIONAL"


def test_all_locales_have_the_same_message_keys():
    english_keys = set(get_translations("en"))
    assert english_keys
    for locale in SUPPORTED_LOCALES:
        assert set(get_translations(locale)) == english_keys


def test_unsupported_locale_is_rejected():
    with pytest.raises(ValueError, match="Unsupported locale"):
        get_translations("fr")


def test_catalog_cannot_be_mutated():
    with pytest.raises(TypeError):
        get_translations("es")["assistant_heading"] = "Changed"


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
