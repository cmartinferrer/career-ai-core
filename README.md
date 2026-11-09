# Career AI Core

Reusable Python engine for conversational CV applications. Uses Gemini, Gradio, YAML/Markdown, and browser text-to-speech.

## Quick start

1. Copy `examples/sample-data/` to your own data directory and edit the YAML/Markdown files.
2. Set `GOOGLE_API_KEY` and `CAREER_AI_DATA_DIR` (absolute path).
3. Run `uv run career-ai` after installing dependencies.

The consuming project should keep its data and secrets separate. The package does not bundle any real candidate data.

**Important:** rate limits are currently in-memory and per process; do not rely on them as a billing cap. The API provider's quotas and billing settings must be configured separately.

This is an initial extraction for review, not yet a public release.
