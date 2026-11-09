"""Tests for the interface translation catalogs."""

import pytest

from career_ai_core.i18n import SUPPORTED_LOCALES, get_translations


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
