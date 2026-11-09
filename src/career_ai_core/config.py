import os

MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "1024"))

MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))

MAX_REQUESTS = int(os.getenv("MAX_REQUESTS", "20"))

RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600"))


def rate_limit_period_text(locale: str | None = None) -> str:
    from career_ai_core.i18n import configured_locale, get_translations

    messages = get_translations(locale or configured_locale())

    def plural(unit: str, count: int) -> str:
        word = messages[f"period_{unit}"]
        return f"{count} {word}" if count == 1 else f"{count} {word}s"

    seconds = RATE_LIMIT_WINDOW_SECONDS

    if seconds % 86400 == 0:
        days = seconds // 86400
        return plural("day", days)

    if seconds % 3600 == 0:
        hours = seconds // 3600
        return plural("hour", hours)

    if seconds % 60 == 0:
        minutes = seconds // 60
        return plural("minute", minutes)

    return plural("second", seconds)
