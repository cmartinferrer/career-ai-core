import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from career_ai_core.config import (
    MAX_HISTORY_MESSAGES,
    MAX_OUTPUT_TOKENS,
)
from career_ai_core.i18n import configured_locale, get_translations
from career_ai_core.knowledge import load_knowledge
from career_ai_core.prompts import build_system_instruction

load_dotenv()

logger = logging.getLogger(__name__)


class CareerAgent:
    def __init__(self, data_dir: str | Path | None = None):
        api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError("No se ha configurado GOOGLE_API_KEY en .env")

        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

        self.knowledge = load_knowledge(data_dir=data_dir)

        self.system_instruction = build_system_instruction(self.knowledge)

    def ask(self, question: str, history: list | None = None) -> str:
        """Send a question to Gemini with the configured amount of chat history."""

        messages = get_translations(configured_locale())
        contents = []

        # A zero history limit disables conversational context.
        recent_history = (history or [])[-MAX_HISTORY_MESSAGES:] if MAX_HISTORY_MESSAGES > 0 else []

        for message in recent_history:
            role = message.get("role")
            content = message.get("content")

            if role not in ("user", "assistant"):
                continue

            # Gradio may return plain text or structured content blocks.
            if isinstance(content, str):
                text = content

            elif isinstance(content, list):
                text = "\n".join(
                    block["text"]
                    for block in content
                    if isinstance(block, dict)
                    and block.get("type") == "text"
                    and isinstance(block.get("text"), str)
                )

            else:
                continue

            if not text.strip():
                continue

            contents.append(
                types.Content(
                    role="user" if role == "user" else "model",
                    parts=[types.Part.from_text(text=text)],
                )
            )

        # Append the current question after the conversation history.
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=question)],
            )
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.2,
                    max_output_tokens=MAX_OUTPUT_TOKENS,
                ),
            )

            usage = response.usage_metadata
            finish_reason = response.candidates[0].finish_reason if response.candidates else None

            logger.debug(
                "Gemini usage: input=%s, output=%s, total=%s, finish_reason=%s",
                usage.prompt_token_count if usage else None,
                usage.candidates_token_count if usage else None,
                usage.total_token_count if usage else None,
                finish_reason,
            )

            return response.text or messages["assistant_empty_response"]

        except errors.APIError as exc:
            logger.warning(
                "Gemini API error: status=%s",
                exc.code,
            )

            if exc.code == 429:
                return messages["assistant_quota_error"]

            if exc.code in (500, 502, 503, 504):
                return messages["assistant_unavailable"]

            return messages["assistant_request_error"]

        except Exception:
            logger.exception("Unexpected error while requesting Gemini")

            return messages["assistant_unexpected_error"]
