"""Unit tests for environment configuration and localized rate-limit periods."""

import runpy

import pytest

from career_ai_core import config


class TestConfigurationDefaults:
    """Verify configuration constants loaded from environment variables."""

    @pytest.mark.parametrize(
        ("name", "default"),
        [
            ("MAX_OUTPUT_TOKENS", 1024),
            ("MAX_HISTORY_MESSAGES", 10),
            ("MAX_REQUESTS", 20),
            ("GLOBAL_DAILY_REQUEST_LIMIT", 200),
            ("RATE_LIMIT_WINDOW_SECONDS", 3600),
        ],
    )
    def test_uses_default_when_environment_variable_is_absent(self, monkeypatch, name, default):
        """Use the documented integer default when an environment setting is missing."""
        monkeypatch.delenv(name, raising=False)

        values = runpy.run_path(config.__file__)

        assert values[name] == default

    @pytest.mark.parametrize(
        "name",
        [
            "MAX_OUTPUT_TOKENS",
            "MAX_HISTORY_MESSAGES",
            "MAX_REQUESTS",
            "GLOBAL_DAILY_REQUEST_LIMIT",
            "RATE_LIMIT_WINDOW_SECONDS",
        ],
    )
    def test_reads_integer_from_environment(self, monkeypatch, name):
        """Convert a configured environment variable into an integer."""
        monkeypatch.setenv(name, "123")

        values = runpy.run_path(config.__file__)

        assert values[name] == 123

    def test_invalid_integer_configuration_raises_value_error(self, monkeypatch):
        """Reject nonnumeric configuration rather than silently using a default."""
        monkeypatch.setenv("MAX_REQUESTS", "not-an-integer")

        with pytest.raises(ValueError):
            runpy.run_path(config.__file__)


class TestRateLimitPeriodText:
    """Verify localized time units, pluralization and unit precedence."""

    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [
            (86400, "1 day"),
            (172800, "2 days"),
            (3600, "1 hour"),
            (7200, "2 hours"),
            (60, "1 minute"),
            (120, "2 minutes"),
            (1, "1 second"),
            (2, "2 seconds"),
        ],
    )
    def test_formats_singular_and_plural_units_in_english(self, monkeypatch, seconds, expected):
        """Choose the largest exact time unit and apply English pluralization."""
        monkeypatch.setattr(config, "RATE_LIMIT_WINDOW_SECONDS", seconds)

        assert config.rate_limit_period_text("en") == expected

    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [
            (86400, "1 día"),
            (172800, "2 días"),
            (3600, "1 hora"),
            (7200, "2 horas"),
            (60, "1 minuto"),
            (120, "2 minutos"),
            (1, "1 segundo"),
            (2, "2 segundos"),
        ],
    )
    def test_formats_singular_and_plural_units_in_spanish(self, monkeypatch, seconds, expected):
        """Use Spanish translations for all supported time units."""
        monkeypatch.setattr(config, "RATE_LIMIT_WINDOW_SECONDS", seconds)

        assert config.rate_limit_period_text("es") == expected

    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [
            (86400 + 3600, "25 hours"),
            (3600 + 60, "61 minutes"),
            (61, "61 seconds"),
            (0, "0 days"),
        ],
    )
    def test_uses_only_exactly_divisible_units(self, monkeypatch, seconds, expected):
        """Select the largest exactly divisible unit without rounding the duration."""
        monkeypatch.setattr(config, "RATE_LIMIT_WINDOW_SECONDS", seconds)

        assert config.rate_limit_period_text("en") == expected

    def test_uses_configured_locale_when_no_locale_is_supplied(self, monkeypatch):
        """Resolve the default locale when the caller does not specify one."""
        monkeypatch.setattr(config, "RATE_LIMIT_WINDOW_SECONDS", 3600)
        monkeypatch.setattr("career_ai_core.i18n.configured_locale", lambda: "es")

        assert config.rate_limit_period_text() == "1 hora"

    def test_explicit_locale_overrides_configured_locale(self, monkeypatch):
        """Honor an explicit locale even when the configured locale differs."""
        monkeypatch.setattr(config, "RATE_LIMIT_WINDOW_SECONDS", 3600)
        monkeypatch.setattr("career_ai_core.i18n.configured_locale", lambda: "es")

        assert config.rate_limit_period_text("en") == "1 hour"
