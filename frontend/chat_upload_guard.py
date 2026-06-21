from pathlib import Path

import streamlit.components.v1 as components


_COMPONENT_DIR = Path(__file__).resolve().parent / "chat_upload_guard_component"

_chat_upload_guard = components.declare_component(
    "chat_upload_guard",
    path=str(_COMPONENT_DIR),
)


def render_chat_upload_guard_component(key: str = "chat_upload_guard"):
    return _chat_upload_guard(key=key)
