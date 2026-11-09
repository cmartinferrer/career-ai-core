"""Translations for candidate-facing interface copy."""

import os
from collections.abc import Mapping
from types import MappingProxyType

from career_ai_core.i18n.en import MESSAGES as EN_MESSAGES
from career_ai_core.i18n.es import MESSAGES as ES_MESSAGES

SUPPORTED_LOCALES = ("en", "es")
_CATALOGS: dict[str, Mapping[str, str]] = {
    "en": MappingProxyType(EN_MESSAGES),
    "es": MappingProxyType(ES_MESSAGES),
}


def get_translations(locale: str = "en") -> Mapping[str, str]:
    """Return immutable interface messages for a supported locale.

    Raise ValueError for unknown locales instead of silently changing language.
    """
    try:
        return _CATALOGS[locale]
    except KeyError as exc:
        raise ValueError(
            f"Unsupported locale: {locale!r}. Supported locales: {', '.join(SUPPORTED_LOCALES)}"
        ) from exc


def configured_locale() -> str:
    """Resolve the owner-selected locale at runtime."""
    locale = os.getenv("CAREER_AI_LOCALE", "en")
    get_translations(locale)
    return locale
