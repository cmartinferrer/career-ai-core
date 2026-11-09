"""Browser speech synthesis integration."""

from importlib.resources import files


def load_voice_js() -> str:
    """Load the browser voice script from the packaged asset."""
    script = files("career_ai_core").joinpath("assets", "voice.js").read_text(encoding="utf-8")
    return f"<script>\n{script}</script>"


VOICE_JS = load_voice_js()
