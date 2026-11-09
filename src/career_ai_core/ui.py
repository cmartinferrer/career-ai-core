import os

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

    if not rate_limiter.allow(visitor_id):
        return (
            f"Has alcanzado el límite de {MAX_REQUESTS} "
            f"consultas cada {rate_limit_period_text()}. "
            "Por favor, vuelve a intentarlo más tarde."
        )

    return get_agent().ask(message, history)


def launch_app() -> None:
    current_agent = get_agent()
    experiences = current_agent.knowledge["experience"]["experiences"]
    profile = current_agent.knowledge["profile"]
    personal = profile.get("personal") or {}
    candidate_name = str(personal.get("name") or "Candidate")

    with gr.Blocks(
        title=f"{candidate_name} | Career AI",
        head=VOICE_JS,
    ) as demo:
        gr.HTML(render_compact_header(profile))

        with gr.Row(equal_height=False):
            # Professional experience sidebar
            with gr.Column(scale=1, min_width=240):
                gr.HTML(render_compact_experience(experiences))

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
                            "ASISTENTE IA"
                            "</div>"
                            "</div>"
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
                    placeholder=(
                        f"👋 ¡Hola! Soy el asistente profesional de {candidate_name}. "
                        "Pregúntame sobre sus proyectos, tecnologías o experiencia."
                    ),
                )

                gr.ChatInterface(
                    fn=respond,
                    chatbot=chatbot,
                    examples=[
                        "¿Cuál es su experiencia profesional?",
                        "¿Qué proyectos ha desarrollado?",
                        "¿Qué habilidades técnicas tiene?",
                        "¿Qué formación tiene?",
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
                                    ? "Desactivar la lectura automática"
                                    : "Activar la lectura automática"
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
                    }""",
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
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    launch_app()
