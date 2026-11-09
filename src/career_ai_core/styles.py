"""Shared Gradio application styles."""

from importlib.resources import files


def load_styles() -> str:
    """Read CSS from the packaged asset."""
    return files("career_ai_core").joinpath("assets", "styles.css").read_text(encoding="utf-8")


CUSTOM_CSS = load_styles()
