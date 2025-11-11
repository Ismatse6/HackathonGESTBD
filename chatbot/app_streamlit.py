from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

import streamlit as st
from core.agent.agent import build_agent
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    UserPromptPart,
)
from pydantic_ai.usage import UsageLimits

# ========= Helpers UI =========


def _render_details(details: List[Dict[str, Any]]) -> None:
    for d in details:
        kind = d.get("kind")
        name = d.get("name", "tool")
        if kind == "tool-call":
            st.markdown(f"🛠️ **Tool call**: `{name}`")
            args = d.get("args")
            if args is not None:
                st.code(
                    json.dumps(args, ensure_ascii=False, indent=2)
                    if isinstance(args, (dict, list))
                    else str(args),
                    language="json",
                )
        elif kind == "tool-return":
            st.markdown(f"↩️ **Tool return**: `{name}`")
            content = d.get("content")
            if content is not None:
                st.code(
                    json.dumps(content, ensure_ascii=False, indent=2)
                    if isinstance(content, (dict, list))
                    else str(content),
                    language="json",
                )


def _extract_tool_details(new_msgs: List[Any]) -> List[Dict[str, Any]]:
    details: List[Dict[str, Any]] = []
    for m in new_msgs:
        parts = getattr(m, "parts", None)
        if not parts:
            continue
        for p in parts:
            kind = getattr(p, "part_kind", None)
            if kind == "tool-call":
                details.append(
                    {
                        "kind": "tool-call",
                        "name": getattr(p, "tool_name", "tool"),
                        "args": getattr(p, "args", None),
                    }
                )
            elif kind == "tool-return":
                details.append(
                    {
                        "kind": "tool-return",
                        "name": getattr(p, "tool_name", "tool"),
                        "content": getattr(p, "content", None),
                    }
                )
    return details


def _render_turns() -> None:
    """Pinta TODO el historial ya consolidado (ui_turns)."""
    for i, turn in enumerate(st.session_state.ui_turns):
        with st.chat_message("user", avatar="👤"):
            st.markdown(turn["user"])
        with st.chat_message("assistant"):
            st.markdown(turn["assistant"])
            if turn["details"]:
                with st.container():
                    with st.expander(
                        f"Ver detalles ({len(turn['details'])})", expanded=False
                    ):
                        _render_details(turn["details"])


# ========= Streaming =========


async def stream_agent_reply(user_input: str) -> None:
    # Para el modelo: añadimos el último prompt al historial técnico
    st.session_state.messages.append(
        ModelRequest(parts=[UserPromptPart(content=user_input)])
    )

    # Placeholder que contendrá TODA la respuesta en vivo
    live_block = st.empty()

    # Render en vivo dentro del placeholder
    with live_block.container():
        with st.chat_message("assistant"):
            with st.spinner("Procesando..."):
                text_placeholder = st.empty()
                details_placeholder = st.empty()
                partial = ""

                async with st.session_state.agent.run_stream(
                    user_input,
                    message_history=st.session_state.messages[:-1],
                    usage_limits=UsageLimits(request_limit=30),
                ) as result:
                    async for delta in result.stream_text(delta=True):
                        partial += delta
                        text_placeholder.markdown(partial)

                    # Nuevos mensajes (excluye el user-prompt)
                    new_msgs = [
                        msg
                        for msg in result.new_messages()
                        if not (
                            hasattr(msg, "parts")
                            and any(p.part_kind == "user-prompt" for p in msg.parts)
                        )
                    ]
                    st.session_state.messages.extend(new_msgs)

                    # Detalles de tools
                    details = _extract_tool_details(new_msgs)
                    if details:
                        with details_placeholder.container():
                            with st.expander(
                                f"Ver detalles ({len(details)})", expanded=False
                            ):
                                _render_details(details)

    # Al terminar: guardamos el turno en el historial de UI…
    st.session_state.ui_turns.append(
        {
            "user": user_input,
            "assistant": partial,
            "details": details if "details" in locals() else [],
        }
    )

    # …y limpiamos el bloque en vivo para que no quede duplicado
    live_block.empty()

    # Forzamos rerender: ahora solo se verá el histórico consolidado (sin el live)
    st.rerun()


# ========= Main =========


async def main():
    st.set_page_config(page_title="Chat Guías", page_icon="🎓", layout="wide")
    st.title("🎓 Chat de Guías de Aprendizaje")

    # Sidebar
    with st.sidebar:
        st.header("Descripción")
        st.caption("Chatbot para consultar las Guías de Aprendizaje de la universidad.")
        if st.button("Reiniciar conversación"):
            st.session_state.messages = []
            st.session_state.ui_turns = []
            st.rerun()

    # Estado inicial
    if "agent" not in st.session_state:
        st.session_state.agent = build_agent()
    if "messages" not in st.session_state:
        st.session_state.messages: List[ModelRequest | ModelResponse] = []
    if "ui_turns" not in st.session_state:
        st.session_state.ui_turns: List[Dict[str, Any]] = []

    # Pintar histórico consolidado
    _render_turns()

    # Input
    user_input = st.chat_input("Escribe tu consulta…")
    if user_input:
        # Pintar mensaje del usuario inmediatamente
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        # Lanzar streaming de la respuesta (en bloque “live” autocontenible)
        await stream_agent_reply(user_input)


if __name__ == "__main__":
    asyncio.run(main())
