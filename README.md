# Career AI Core

**Build a conversational, AI-powered résumé from structured candidate data.**

Career AI Core is a reusable Python application engine that combines Google Gemini, a Gradio web interface, and a YAML/Markdown knowledge base. Visitors can ask questions about a candidate's experience, projects, education, and skills instead of browsing a static résumé.

Candidate content and credentials live outside the package, so the same engine can power different personal CV applications.

> **Project status:** Pre-release (`0.1.0` in package metadata). The public repository and release workflow are being prepared; interfaces may change.

## Features

- Conversational CV assistant backed by Google Gemini
- Candidate profile and professional experience rendered in Gradio
- Structured YAML data with optional Markdown project details
- English and Spanish interface catalogs, selected by the application owner
- Answers in the visitor's language, subject to model behavior
- Optional browser text-to-speech controls (availability depends on browser support)
- Per-visitor hourly and process-wide daily request limits
- Process-local token usage counters and optional aggregate usage logs
- Tests for data validation, path handling, prompt behavior, and usage controls

## Requirements

- Python **3.10+**
- [uv](https://docs.astral.sh/uv/) for the development workflow below
- A Google Gemini API key

## Quick start

Clone the repository and install its dependencies:

```bash
uv sync
```

Copy the fictional example data into a separate working directory:

```bash
mkdir -p local-data
cp -R examples/sample-data/. local-data/
```

Create a local `.env` file (never commit your real credentials):

```dotenv
GOOGLE_API_KEY=your_gemini_api_key
CAREER_AI_DATA_DIR=/absolute/path/to/career-ai-core/local-data
CAREER_AI_LOCALE=en
```

Replace the example data path with its actual absolute path, then launch:

```bash
uv run career-ai
```

The Gradio application uses port `7860` by default (or the `PORT` environment variable). The sample data is fictional and intentionally minimal; customize it before using the application as a real CV.

## Candidate data

The engine reads three required YAML files from `CAREER_AI_DATA_DIR`:

```text
my-candidate-data/
├── profile.yaml
├── experience.yaml
├── skills.yaml
└── projects/
    └── example-project.md  # optional
```

The included [`examples/sample-data`](examples/sample-data) directory is the starting point for the supported structure.

### `profile.yaml`

```yaml
personal:
  name: "Alex Example"
  title: "Software Engineer"
  summary: "Engineer specializing in backend services."
presentation:
  tagline: "Software Engineer · Backend Systems"
  highlights: ["Python", "APIs"]
```

### `experience.yaml`

```yaml
experiences:
  - company: "Example Technologies"
    role: "Software Engineer"
    period:
      start: "2022-01"
      end: null
    skill_ids: []
    projects: []
```

### `skills.yaml`

```yaml
categories: []
```

Projects may reference a Markdown document using `details_file`. File references are resolved within the configured data directory; absolute paths and paths escaping that directory are rejected. Skill IDs are validated against the skills catalog.

**Privacy:** The candidate knowledge base is provided to Gemini as part of the request context. Only include information you are authorized and comfortable sending to the model provider and potentially disclosing through the assistant. Do not place passwords, tokens, or confidential documents in the knowledge directory.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `GOOGLE_API_KEY` | Required | Gemini API credential |
| `CAREER_AI_DATA_DIR` | Required for CLI | Directory containing candidate YAML/Markdown |
| `CAREER_AI_LOCALE` | `en` | Interface language: `en` or `es` |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Gemini model identifier; ensure your account has access |
| `MAX_OUTPUT_TOKENS` | `1024` | Maximum output tokens per generation |
| `MAX_HISTORY_MESSAGES` | `10` | Maximum recent conversation messages sent to Gemini |
| `MAX_REQUESTS` | `20` | Per-visitor request allowance |
| `RATE_LIMIT_WINDOW_SECONDS` | `3600` | Per-visitor limit window in seconds |
| `GLOBAL_DAILY_REQUEST_LIMIT` | `200` | Process-wide daily request allowance (UTC) |
| `GEMINI_USAGE_LOG_EVERY` | `0` | Log aggregate usage every N provider attempts; `0` disables it |
| `PORT` | `7860` | Gradio server port |

The interface language is configured by the application owner, not chosen through a visitor-facing language selector. Gemini is instructed to answer in the visitor's language, but generated-language behavior cannot be guaranteed.

## Usage limits and observability

Request limits are implemented in memory. They help reduce accidental overuse but are **not durable billing controls**: counters reset on restart, and multiple worker processes or instances maintain separate counters. Configure provider-side quotas, alerts, and billing safeguards independently.

Gemini usage is tracked in process-local, thread-safe counters. The following API returns aggregate totals and the current UTC day's counters:

```python
from career_ai_core.usage_metrics import usage_metrics

print(usage_metrics.snapshot())
```

To log aggregate token statistics after every 10 recorded Gemini attempts:

```dotenv
GEMINI_USAGE_LOG_EVERY=10
```

Logging requires the application's logging configuration to allow `INFO` messages. Usage metadata may be absent for some attempts; missing usage data does **not** prove zero token consumption. Counters and logs are not a persistent accounting system.

## Architecture

```text
src/career_ai_core/
├── agent.py          # Gemini integration
├── prompts.py        # System instructions and knowledge context
├── knowledge.py      # YAML/Markdown loading
├── models.py         # Data models
├── skills.py         # Skill resolution
├── validator.py      # Knowledge validation
├── ui.py             # Gradio application
├── components.py     # UI rendering helpers
├── i18n/             # English and Spanish UI messages
├── rate_limiter.py   # In-memory request limits
├── usage_metrics.py  # Aggregate token usage tracking
├── styles.py         # Bundled CSS loading
├── voice.py          # Bundled browser voice script
└── assets/           # CSS and JavaScript
```

The reusable engine is `career-ai-core`. A personal deployment should keep its own candidate data, configuration, and credentials in a separate consuming project rather than committing them to the engine repository.

## Development

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv build
```

The distribution verification script checks the expected bundled package resources in a built wheel:

```bash
python scripts/verify_distribution.py dist/career_ai_core-0.1.0-py3-none-any.whl
```

If the wheel filename changes, replace it with the generated filename in `dist/`.

## Deployment notes

The application starts a Gradio server and reads its port from `PORT`, which makes it suitable for deployment to a Python-capable hosting service. Set secrets in your host's environment configuration rather than committing a `.env` file. For production use, review provider quotas, logging settings, data privacy, and whether process-local limits meet your needs.

## Security considerations

- YAML is loaded using `yaml.safe_load`.
- Data file paths are constrained to the configured knowledge directory, including resolved symbolic links.
- Candidate documents are treated as reference data in the model instructions, but prompt-injection defenses are not foolproof.
- Application logs are intended to contain aggregate operational data rather than prompts or API keys.
- The assistant can still produce inaccurate or incomplete answers; verify important claims against the source CV.

## License and contributions

A license and contribution guidelines will be added before the public release. Until then, do not assume the project is licensed for unrestricted reuse.
