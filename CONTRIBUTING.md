# Contributing to Career AI Core

Thanks for your interest in improving Career AI Core!

## Before you start

For substantial changes, open an issue to discuss the proposed behavior and scope before investing time in an implementation. Keep pull requests focused and explain why the change is needed.

This repository contains the reusable engine, not a real candidate's CV. Use fictional data in tests, examples, and screenshots. Never commit `.env` files, API keys, private CVs, personal contact details, or provider responses containing sensitive information.

## Development setup

You need Python 3.10 or newer and [uv](https://docs.astral.sh/uv/).

```bash
git clone <YOUR-FORK-URL>
cd career-ai-core
uv sync --dev
```

To run the sample application, copy `examples/sample-data/` to a local directory, provide `GOOGLE_API_KEY`, and set `CAREER_AI_DATA_DIR` to that directory. Do not commit your local configuration or secrets.

## Quality checks

Run these commands before opening a pull request:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv build
```

If formatting needs adjustment, run `uv run ruff format .` and repeat the checks. Changes to packaging should also be checked against the built wheel using `scripts/verify_distribution.py`.

## Coding and testing guidelines

- Use English for source-code comments, docstrings, internal error messages, and documentation.
- Keep visitor-facing strings in the internationalization catalogs; English is the default locale.
- Add or update tests for behavior changes, including error handling and security-sensitive paths.
- Do not weaken the safeguards against fabricated candidate information or prompt injection.
- Avoid introducing new dependencies without explaining the need.
- Keep changes compatible with the supported Python versions.

## Pull requests

Describe the problem, summarize your solution, and include the commands you ran and their results. Link related issues where applicable. Prefer small, reviewable commits and avoid unrelated formatting changes.

## Reporting security issues

Do not publish working exploits, credentials, or private candidate data in public issues. Contact the repository maintainer privately through an available GitHub contact channel before disclosing sensitive details. A dedicated security reporting process may be added later.
