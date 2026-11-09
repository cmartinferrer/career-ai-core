import os

MAX_OUTPUT_TOKENS = int(os.getenv("MAX_OUTPUT_TOKENS", "1024"))

MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))

MAX_REQUESTS = int(os.getenv("MAX_REQUESTS", "20"))

RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "3600"))


def rate_limit_period_text() -> str:
    seconds = RATE_LIMIT_WINDOW_SECONDS

    if seconds % 86400 == 0:
        days = seconds // 86400
        return f"{days} día" if days == 1 else f"{days} días"

    if seconds % 3600 == 0:
        hours = seconds // 3600
        return f"{hours} hora" if hours == 1 else f"{hours} horas"

    if seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes} minuto" if minutes == 1 else f"{minutes} minutos"

    return f"{seconds} segundos"
