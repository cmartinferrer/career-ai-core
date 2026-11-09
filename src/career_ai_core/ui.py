import json
import os
from html import escape

import gradio as gr

from career_ai_core.agent import CareerAgent
from career_ai_core.components import (
    render_compact_experience,
    render_compact_header,
)
from career_ai_core.config import (
    MAX_REQUESTS,
    rate_limit_period_text,
)
from career_ai_core.i18n import configured_locale, get_translations
from career_ai_core.rate_limiter import rate_limiter
from career_ai_core.styles import CUSTOM_CSS
from career_ai_core.voice import VOICE_JS

agent = None


def get_agent() -> CareerAgent:
    """Initialize on first request, after consumer configuration is available."""
    global agent
    if agent is None:
        agent = CareerAgent()
    return agent


def respond(
    message: str,
    history: list,
    request: gr.Request,
) -> str:
    visitor_id = request.client.host if request.client else "unknown"

    rejection = rate_limiter.check(visitor_id)
    if rejection == "global":
        return get_translations(configured_locale())["global_daily_limit_message"]
    if rejection == "visitor":
        messages = get_translations(configured_locale())
        return messages["rate_limit_message"].format(
            max_requests=MAX_REQUESTS, period=rate_limit_period_text()
        )

    return get_agent().ask(message, history)


def launch_app() -> None:
    locale = configured_locale()
    messages = get_translations(locale)
    current_agent = get_agent()
    experiences = current_agent.knowledge["experience"]["experiences"]
    profile = current_agent.knowledge["profile"]
    personal = profile.get("personal") or {}
    candidate_name = str(personal.get("name") or "Candidate")

    tooltip_css = "\n".join(
        f"#chat-panel {{ --{key}: {json.dumps(messages[value], ensure_ascii=False)}; }}"
        for key, value in (
            ("voice-disable", "voice_disable"),
            ("voice-enable", "voice_enable"),
            ("voice-replay", "voice_replay"),
            ("voice-stop", "voice_stop"),
        )
    )

    with gr.Blocks(
        title=f"{candidate_name} | Career AI",
        head=VOICE_JS,
    ) as demo:
        gr.HTML(render_compact_header(profile))

        with gr.Row(equal_height=False):
            # Professional experience sidebar
            with gr.Column(scale=1, min_width=240):
                gr.HTML(render_compact_experience(experiences, locale=locale))

            # Chat panel
            with gr.Column(
                scale=3,
                min_width=350,
                elem_id="chat-panel",
            ):
                # Chat header with compact voice controls
                with gr.Row(
                    elem_classes=["chat-toolbar"],
                ):
                    with gr.Column(
                        scale=1,
                        min_width=130,
                    ):
                        gr.HTML(
                            '<div class="chat-toolbar-title">'
                            '<div class="sidebar-heading">'
                            + escape(messages["assistant_heading"])
                            + "</div>"
                            + "</div>"
                        )

                    with gr.Row(
                        elem_classes=["voice-controls"],
                    ):
                        auto_button = gr.Button(
                            "🔊 Auto",
                            size="sm",
                            variant="secondary",
                            elem_id="auto-voice-button",
                            elem_classes=["voice-auto-on"],
                            scale=0,
                            min_width=74,
                        )

                        replay_button = gr.Button(
                            "↻",
                            size="sm",
                            variant="secondary",
                            elem_id="replay-voice-button",
                            scale=0,
                            min_width=34,
                        )

                        stop_button = gr.Button(
                            "□",
                            size="sm",
                            variant="secondary",
                            elem_id="stop-voice-button",
                            scale=0,
                            min_width=34,
                        )

                # Chat interface
                chatbot = gr.Chatbot(
                    height=565,
                    placeholder=messages["assistant_welcome"].format(candidate_name=candidate_name),
                )

                gr.ChatInterface(
                    fn=respond,
                    chatbot=chatbot,
                    examples=[
                        messages["example_experience"],
                        messages["example_projects"],
                        messages["example_skills"],
                        messages["example_education"],
                    ],
                )

                # Automatically read new assistant responses
                chatbot.change(
                    fn=None,
                    inputs=[chatbot],
                    outputs=[],
                    js="""(messages) => {
                        window.cmfVoice?.onMessagesChanged(messages);
                    }""",
                )

                # Enable / disable automatic playback
                voice_on = json.dumps(messages["voice_disable"], ensure_ascii=False)
                voice_off = json.dumps(messages["voice_enable"], ensure_ascii=False)
                auto_button.click(
                    fn=None,
                    inputs=[],
                    outputs=[],
                    js="""() => {
                        const enabled = window.cmfVoice?.toggleAuto();

                        if (typeof enabled !== "boolean") {
                            return;
                        }

                        const container = document.getElementById(
                            "auto-voice-button"
                        );

                        if (!container) {
                            return;
                        }

                        const button = container.querySelector("button");

                        if (button) {
                            button.textContent = enabled
                                ? "🔊 Auto"
                                : "🔇 Off";
                            button.setAttribute(
                                "title",
                                enabled
                                    ? __VOICE_ON__
                                    : __VOICE_OFF__
                            );
                        }

                        container.classList.toggle(
                            "voice-auto-on",
                            enabled
                        );

                        container.classList.toggle(
                            "voice-auto-off",
                            !enabled
                        );
                    }""".replace("__VOICE_ON__", voice_on).replace("__VOICE_OFF__", voice_off),
                )

                # Replay the latest assistant response
                replay_button.click(
                    fn=None,
                    inputs=[],
                    outputs=[],
                    js="() => window.cmfVoice?.replay()",
                )

                # Stop current playback
                stop_button.click(
                    fn=None,
                    inputs=[],
                    outputs=[],
                    js="() => window.cmfVoice?.stop()",
                )

    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", "7860")),
        css=CUSTOM_CSS + "\n" + tooltip_css,
    )


if __name__ == "__main__":
    launch_app()
