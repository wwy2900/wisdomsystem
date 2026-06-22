# 加载环境变量（必须在其他导入之前）
from dotenv import load_dotenv

load_dotenv()

from collections import defaultdict
from datetime import datetime
from html import escape

import streamlit as st

from frontend.api_client import ApiClient, ApiClientError
from frontend.chat_upload_guard import render_chat_upload_guard_component


CHAT_PAGE = "聊天"
KNOWLEDGE_PAGE = "知识库管理"


st.set_page_config(
    page_title="智扫通 · 智能客服",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)


if "api_client" not in st.session_state:
    st.session_state["api_client"] = ApiClient()

if "user_id" not in st.session_state:
    st.session_state["user_id"] = "user_default"

if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "current_session_id" not in st.session_state:
    st.session_state["current_session_id"] = None

if "user_sessions_cache" not in st.session_state:
    st.session_state["user_sessions_cache"] = {}

if "user_chunks_cache" not in st.session_state:
    st.session_state["user_chunks_cache"] = {}

api_client: ApiClient = st.session_state["api_client"]


def show_backend_error(error: Exception):
    st.error(f"{error}")
    st.info("请确认 FastAPI 后端已启动：uvicorn api.main:app --host 0.0.0.0 --port 8000")


def inject_app_theme_css():
    css = """
        <style>
        :root {
            --app-bg: #f5f7fb;
            --surface: #ffffff;
            --surface-muted: #f8fafc;
            --surface-strong: #eff4ff;
            --border: rgba(15, 23, 42, 0.08);
            --border-strong: rgba(37, 99, 235, 0.18);
            --text: #0f172a;
            --text-muted: #64748b;
            --primary: #2563eb;
            --primary-soft: #dbeafe;
            --danger-soft: #fee2e2;
            --danger: #dc2626;
            --shadow-sm: 0 6px 18px rgba(15, 23, 42, 0.06);
            --shadow-md: 0 16px 40px rgba(15, 23, 42, 0.08);
            --radius: 8px;
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.06), transparent 24rem),
                linear-gradient(180deg, #f8fbff 0%, var(--app-bg) 22rem);
        }

        section.main > div[data-testid="stMainBlockContainer"],
        .main .block-container,
        [data-testid="stAppViewContainer"] .block-container {
            max-width: 1180px;
            padding-top: 1.25rem;
            padding-bottom: 6.25rem;
        }

        body[data-chat-upload-panel-open="true"] section.main > div[data-testid="stMainBlockContainer"],
        body[data-chat-upload-panel-open="true"] .main .block-container,
        body[data-chat-upload-panel-open="true"] [data-testid="stAppViewContainer"] .block-container {
            padding-bottom: 14.25rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f8fbff 0%, #f3f6fb 100%);
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding-top: 1rem;
        }

        [data-testid="stSidebar"] .block-container {
            padding-top: 0.75rem;
            padding-bottom: 1rem;
        }

        [data-testid="stSidebar"] hr {
            margin: 0.75rem 0 1rem;
            border-color: var(--border);
        }

        .app-brand {
            display: flex;
            flex-direction: column;
            gap: 0.3rem;
            margin-bottom: 1rem;
        }

        .app-brand-kicker,
        .section-kicker,
        .page-header-kicker {
            color: var(--primary);
            font-size: 0.78rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0;
        }

        .app-brand-title {
            color: var(--text);
            font-size: 1.25rem;
            font-weight: 700;
            line-height: 1.25;
        }

        .app-brand-copy,
        .section-description,
        .page-header-copy p,
        .chat-empty-copy {
            color: var(--text-muted);
            font-size: 0.92rem;
            line-height: 1.5;
            margin: 0;
        }

        .page-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            padding: 0 0 1rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }

        .page-header-copy {
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
        }

        .page-header-copy h1 {
            margin: 0;
            color: var(--text);
            font-size: 1.8rem;
            line-height: 1.2;
            font-weight: 700;
        }

        .page-header-meta {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 0.5rem;
            min-width: 14rem;
        }

        .page-meta-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            padding: 0.45rem 0.7rem;
            border: 1px solid var(--border);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.76);
            color: var(--text);
            font-size: 0.85rem;
            white-space: nowrap;
        }

        .st-key-sidebar-nav,
        .st-key-sidebar-user-panel,
        .st-key-sidebar-session-panel,
        .st-key-knowledge-upload-panel,
        .st-key-knowledge-search-panel,
        .st-key-knowledge-chunks-panel,
        .st-key-knowledge-rebuild-panel,
        .st-key-chat-empty-state,
        .st-key-chat-upload-bar {
            border: 1px solid var(--border);
            border-radius: var(--radius);
            background: rgba(255, 255, 255, 0.95);
            box-shadow: var(--shadow-sm);
        }

        .st-key-sidebar-nav,
        .st-key-sidebar-user-panel,
        .st-key-sidebar-session-panel {
            padding: 0.9rem 0.9rem 0.95rem;
            margin-bottom: 0.9rem;
        }

        .st-key-knowledge-upload-panel,
        .st-key-knowledge-search-panel,
        .st-key-knowledge-chunks-panel,
        .st-key-knowledge-rebuild-panel {
            padding: 1rem 1rem 1.05rem;
            margin-bottom: 1rem;
        }

        .panel-heading {
            display: flex;
            flex-direction: column;
            gap: 0.3rem;
            margin-bottom: 0.8rem;
        }

        .section-title {
            color: var(--text);
            font-size: 1.05rem;
            line-height: 1.3;
            font-weight: 700;
        }

        .sidebar-section-title {
            color: var(--text);
            font-size: 0.98rem;
            font-weight: 700;
            line-height: 1.3;
            margin-bottom: 0.2rem;
        }

        .sidebar-section-copy {
            color: var(--text-muted);
            font-size: 0.84rem;
            line-height: 1.45;
            margin-bottom: 0.75rem;
        }

        .st-key-sidebar-nav [data-testid="stRadio"] label p {
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text);
        }

        .st-key-sidebar-nav [role="radiogroup"] {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.55rem;
        }

        .st-key-sidebar-nav [role="radiogroup"] > label {
            margin: 0;
            justify-content: center;
            min-height: 2.5rem;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            background: var(--surface-muted);
            transition: 0.18s ease;
        }

        .st-key-sidebar-nav [role="radiogroup"] > label:hover {
            border-color: rgba(37, 99, 235, 0.28);
            background: #f4f8ff;
        }

        .st-key-sidebar-nav [role="radiogroup"] > label:has(input:checked) {
            border-color: rgba(37, 99, 235, 0.36);
            background: var(--primary-soft);
            box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.06);
        }

        .st-key-sidebar-nav input[type="radio"] {
            display: none;
        }

        .st-key-sidebar-session-list {
            max-height: min(48vh, 34rem);
            overflow-y: auto;
            padding-right: 0.2rem;
        }

        .st-key-sidebar-session-list button {
            min-height: 3.35rem;
            margin-bottom: 0.45rem;
            padding: 0.65rem 0.8rem;
            border-radius: var(--radius);
            justify-content: flex-start;
            text-align: left;
            white-space: pre-wrap;
            line-height: 1.4;
        }

        .st-key-sidebar-session-list button[kind="secondary"] {
            border-color: var(--border);
            background: rgba(248, 250, 252, 0.96);
            color: var(--text);
        }

        .st-key-sidebar-session-list button[kind="secondary"]:hover {
            border-color: rgba(37, 99, 235, 0.3);
            background: #f6f9ff;
            color: var(--text);
        }

        .st-key-sidebar-session-list button[kind="primary"] {
            background: linear-gradient(180deg, #2f6ef5 0%, #2563eb 100%);
            border-color: rgba(37, 99, 235, 0.36);
        }

        .stButton > button,
        [data-testid="stFileUploaderDropzone"] button {
            border-radius: var(--radius);
            font-weight: 600;
        }

        [data-baseweb="input"] > div,
        [data-baseweb="base-input"] > div,
        [data-baseweb="textarea"] > div,
        [data-testid="stNumberInput"] [data-baseweb="input"] > div {
            border-radius: var(--radius);
            border-color: rgba(148, 163, 184, 0.38);
            background: rgba(255, 255, 255, 0.92);
        }

        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="base-input"] > div:focus-within,
        [data-baseweb="textarea"] > div:focus-within,
        [data-testid="stNumberInput"] [data-baseweb="input"] > div:focus-within {
            border-color: rgba(37, 99, 235, 0.5);
            box-shadow: 0 0 0 1px rgba(37, 99, 235, 0.16);
        }

        [data-testid="stSlider"] [role="slider"] {
            box-shadow: none;
        }

        .st-key-chat-empty-state {
            padding: 1rem 1rem 1.05rem;
            margin: 0.5rem 0 1rem;
        }

        .chat-empty-title {
            color: var(--text);
            font-size: 1.05rem;
            font-weight: 700;
            line-height: 1.35;
            margin-bottom: 0.35rem;
        }

        .chat-empty-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 0.85rem;
        }

        .chat-empty-tags span {
            display: inline-flex;
            align-items: center;
            padding: 0.42rem 0.7rem;
            border-radius: 999px;
            background: var(--surface-muted);
            border: 1px solid var(--border);
            color: var(--text);
            font-size: 0.84rem;
        }

        .st-key-chat-message-history [data-testid="stChatMessage"] {
            max-width: 58rem;
            margin: 0 auto 0.85rem;
            padding: 0;
        }

        .st-key-chat-message-history [data-testid="stChatMessageContent"] {
            border: 1px solid var(--border);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.97);
            padding: 0.95rem 1rem;
            box-shadow: var(--shadow-sm);
        }

        .st-key-chat-message-history [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
            background: #eef4ff;
            border-color: rgba(37, 99, 235, 0.16);
        }

        .st-key-chat-message-history [data-testid="stChatMessage"] p {
            color: var(--text);
            line-height: 1.7;
        }

        .st-key-chat-message-history [data-testid="stExpander"] {
            max-width: 58rem;
            margin: 0 auto 0.85rem;
            border: 1px solid var(--border);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.88);
        }

        .st-key-chat-message-history [data-testid="stExpander"] summary {
            font-size: 0.9rem;
            color: var(--text);
            font-weight: 600;
        }

        [data-testid="stChatInput"] {
            max-width: 58rem;
            margin: 0 auto;
        }

        [data-testid="stChatInput"] textarea,
        [data-testid="stChatInput"] [data-testid="stChatInputTextArea"] {
            padding-left: 2.8rem;
        }

        [data-testid="stChatInput"] [data-baseweb="textarea"] {
            border-radius: 14px;
            border-color: rgba(148, 163, 184, 0.38);
            background: rgba(255, 255, 255, 0.96);
            box-shadow: var(--shadow-sm);
        }

        .st-key-chat-upload-bar {
            position: fixed;
            bottom: 6.45rem;
            z-index: 999;
            width: inherit;
            min-width: min(34rem, calc(100vw - 2rem));
            max-width: 47rem;
            overflow-y: auto;
            padding: 0.75rem 0.85rem 0.65rem;
            box-shadow: var(--shadow-md);
            max-height: 0;
            opacity: 0;
            visibility: hidden;
            pointer-events: none;
        }

        body[data-chat-upload-panel-open="true"] .st-key-chat-upload-bar {
            max-height: 14rem;
            opacity: 1;
            visibility: visible;
            pointer-events: auto;
        }

        .upload-panel-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.75rem;
            margin-bottom: 0.7rem;
        }

        .upload-panel-title {
            color: var(--text);
            font-size: 0.96rem;
            font-weight: 700;
        }

        .upload-panel-copy {
            color: var(--text-muted);
            font-size: 0.82rem;
            line-height: 1.4;
        }

        .upload-panel-pill {
            display: inline-flex;
            align-items: center;
            padding: 0.3rem 0.55rem;
            border-radius: 999px;
            background: var(--surface-muted);
            border: 1px solid var(--border);
            color: var(--text);
            font-size: 0.78rem;
            white-space: nowrap;
        }

        .st-key-chat-upload-bar [data-testid="stFileUploader"] {
            margin-bottom: 0;
        }

        .st-key-chat-upload-bar [data-testid="stFileUploaderDropzone"] {
            min-height: 2.65rem;
            padding: 0.35rem 0.55rem;
            border-radius: var(--radius);
            background: var(--surface-muted);
            border-color: rgba(148, 163, 184, 0.26);
        }

        .st-key-chat-upload-bar [data-testid="stFileUploaderDropzone"] small {
            display: none;
        }

        .st-key-chat-upload-bar [data-testid="stExpander"] {
            margin-top: 0.35rem;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            background: rgba(248, 250, 252, 0.72);
        }

        .st-key-chat-upload-bar [data-testid="stExpander"] summary {
            font-size: 0.88rem;
            font-weight: 600;
            color: var(--text);
        }

        .st-key-chat-upload-bar button[kind="secondary"] {
            background: #fff7f7;
            border-color: rgba(220, 38, 38, 0.16);
            color: #b91c1c;
        }

        .st-key-chat-upload-toggle {
            position: fixed;
            bottom: 3.85rem;
            z-index: 1000;
            width: inherit;
            min-width: min(34rem, calc(100vw - 2rem));
            max-width: 47rem;
            pointer-events: none;
        }

        .st-key-chat-upload-toggle [data-testid="stVerticalBlock"] {
            gap: 0;
        }

        .st-key-chat-upload-toggle [data-testid="stElementContainer"] {
            width: 2.15rem;
            margin-left: 0.55rem;
            pointer-events: auto;
        }

        .st-key-chat-upload-toggle [data-testid="stHtml"] {
            width: 2.15rem !important;
            pointer-events: none;
        }

        .st-key-chat-upload-toggle [data-testid="stHtml"] > * {
            pointer-events: auto;
        }

        .st-key-chat-upload-toggle .chat-upload-toggle-button {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 2.15rem;
            min-width: 2.15rem;
            height: 2.15rem;
            min-height: 2.15rem;
            padding: 0;
            border-radius: 999px;
            border: 1px solid rgba(37, 99, 235, 0.18);
            background: rgba(255, 255, 255, 0.98);
            box-shadow: 0 8px 16px rgba(15, 23, 42, 0.12);
            color: var(--primary);
            line-height: 1;
            font-size: 1.2rem;
            font-weight: 700;
            cursor: pointer;
        }

        .st-key-chat-upload-toggle .chat-upload-toggle-button:focus {
            outline: none;
        }

        [data-testid="stDataFrame"] {
            border-radius: var(--radius);
            overflow: hidden;
            border: 1px solid var(--border);
        }

        @media (prefers-color-scheme: dark) {
            :root {
                --app-bg: #0f172a;
                --surface: #0f172a;
                --surface-muted: #111c31;
                --surface-strong: #10233f;
                --border: rgba(148, 163, 184, 0.16);
                --border-strong: rgba(96, 165, 250, 0.24);
                --text: #e2e8f0;
                --text-muted: #94a3b8;
                --primary-soft: rgba(37, 99, 235, 0.14);
                --danger-soft: rgba(127, 29, 29, 0.25);
                --shadow-sm: 0 10px 28px rgba(2, 6, 23, 0.22);
                --shadow-md: 0 20px 44px rgba(2, 6, 23, 0.3);
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
            }
        }

        @media (max-width: 960px) {
            .page-header {
                flex-direction: column;
            }

            .page-header-meta {
                justify-content: flex-start;
                min-width: 0;
            }
        }

        @media (max-width: 640px) {
            section.main > div[data-testid="stMainBlockContainer"],
            .main .block-container,
            [data-testid="stAppViewContainer"] .block-container {
                padding-top: 0.85rem;
                padding-bottom: 6.8rem;
            }

            body[data-chat-upload-panel-open="true"] section.main > div[data-testid="stMainBlockContainer"],
            body[data-chat-upload-panel-open="true"] .main .block-container,
            body[data-chat-upload-panel-open="true"] [data-testid="stAppViewContainer"] .block-container {
                padding-bottom: 14.8rem;
            }

            .page-header-copy h1 {
                font-size: 1.45rem;
            }

            .st-key-chat-upload-bar,
            .st-key-chat-upload-toggle {
                left: 0.75rem;
                right: 0.75rem;
                width: auto;
                min-width: 0;
            }

            .st-key-chat-upload-toggle [data-testid="stElementContainer"] {
                margin-left: 0.35rem;
            }

            body[data-chat-upload-panel-open="true"] .st-key-chat-upload-bar {
                max-height: 15rem;
            }
        }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_panel_heading(kicker: str, title: str, description: str):
    st.markdown(
        f"""
        <div class="panel-heading">
            <div class="section-kicker">{escape(kicker)}</div>
            <div class="section-title">{escape(title)}</div>
            <p class="section-description">{escape(description)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, description: str, meta_items: list[str]):
    meta_html = "".join(
        f'<span class="page-meta-pill">{escape(item)}</span>' for item in meta_items if item
    )
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-header-copy">
                <div class="page-header-kicker">智扫通</div>
                <h1>{escape(title)}</h1>
                <p>{escape(description)}</p>
            </div>
            <div class="page-header-meta">{meta_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_session_date(raw_value: str | None) -> str:
    if not raw_value:
        return ""
    try:
        return datetime.fromisoformat(raw_value).strftime("%m-%d %H:%M")
    except ValueError:
        return raw_value


def format_session_preview(session: dict) -> str:
    preview = (session.get("preview") or "新会话").replace("\n", " ").strip()
    if len(preview) > 26:
        preview = f"{preview[:26]}..."
    saved_at = format_session_date(session.get("saved_at"))
    return f"{preview}\n{saved_at}" if saved_at else preview


def get_user_sessions(user_id: str, force_refresh: bool = False) -> list[dict]:
    cache: dict[str, list[dict]] = st.session_state["user_sessions_cache"]
    if force_refresh or user_id not in cache:
        cache[user_id] = api_client.list_user_sessions(user_id)
    return cache.get(user_id, [])


def get_user_chunks(user_id: str, force_refresh: bool = False) -> list[dict]:
    cache: dict[str, list[dict]] = st.session_state["user_chunks_cache"]
    if force_refresh or user_id not in cache:
        data = api_client.list_user_chunks(user_id, limit=200)
        cache[user_id] = data.get("chunks", [])
    return cache.get(user_id, [])


def load_latest_session(user_id: str):
    try:
        sessions = get_user_sessions(user_id, force_refresh=True)
        if sessions:
            latest_session = sessions[0]
            st.session_state["current_session_id"] = latest_session["session_id"]
            loaded_data = api_client.get_session(latest_session["session_id"])
            st.session_state["messages"] = loaded_data["messages"] if loaded_data else []
        else:
            st.session_state["current_session_id"] = api_client.create_session(user_id)
            st.session_state["messages"] = []
    except ApiClientError as error:
        st.session_state["messages"] = []
        show_backend_error(error)


def ensure_current_session():
    if not st.session_state["current_session_id"]:
        load_latest_session(st.session_state["user_id"])


def group_user_files(user_chunks: list[dict]) -> list[tuple[str, list[dict]]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for chunk in user_chunks:
        source_file = chunk.get("metadata", {}).get("source_file", "unknown")
        grouped[source_file].append(chunk)
    return sorted(grouped.items())


def render_chat_upload_toggle():
    with st.container(key="chat-upload-toggle"):
        st.html(
            '<button type="button" class="chat-upload-toggle-button" aria-label="上传私有知识文件" title="上传私有知识文件">+</button>'
        )


def render_chat_upload_bar():
    current_user_id = st.session_state["user_id"]
    cached_chunks = st.session_state["user_chunks_cache"].get(current_user_id)
    user_chunks = cached_chunks if cached_chunks is not None else []
    if cached_chunks is None:
        try:
            user_chunks = get_user_chunks(current_user_id, force_refresh=True)
        except ApiClientError:
            user_chunks = []

    grouped_files = group_user_files(user_chunks)

    with st.container(key="chat-upload-bar"):
        st.markdown(
            f"""
            <div class="upload-panel-head">
                <div>
                    <div class="upload-panel-title">我的知识文件</div>
                    <div class="upload-panel-copy">上传后可直接参与当前用户的对话检索，不影响其他用户。</div>
                </div>
                <div class="upload-panel-pill">{escape(current_user_id)} · {len(grouped_files)} 个文件</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        upload_col, action_col = st.columns([5, 1])
        with upload_col:
            uploaded_file = st.file_uploader(
                "上传 txt/pdf 文档到我的知识库",
                type=["txt", "pdf"],
                key="chat_uploader",
                label_visibility="collapsed",
            )
        with action_col:
            upload_clicked = st.button("上传", key="chat_upload_btn", use_container_width=True)

        if upload_clicked and uploaded_file:
            with st.spinner("正在写入向量库..."):
                try:
                    result = api_client.upload_document(
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        user_id=current_user_id,
                    )
                    if result["skipped"]:
                        st.warning(f"已跳过：{result.get('reason', '重复文件')}")
                    else:
                        st.session_state["user_chunks_cache"].pop(current_user_id, None)
                        st.success(f"已入库：{result['chunk_count']} 个 chunk")
                        st.rerun()
                except ApiClientError as error:
                    show_backend_error(error)

        with st.expander(f"文件列表（{len(grouped_files)}）", expanded=False):
            if not grouped_files:
                st.info("还没有上传私有文件。上传后可在对话中检索到这些文件的内容。")
            else:
                for source_file, chunks in grouped_files:
                    file_col, count_col, action_col = st.columns([6, 2, 1])
                    file_col.write(source_file)
                    count_col.caption(f"{len(chunks)} chunks")
                    with action_col:
                        if st.button(
                            "删除",
                            key=f"del_{chunks[0].get('doc_id', '')}",
                            help=f"删除 {source_file}",
                            type="secondary",
                            use_container_width=True,
                        ):
                            try:
                                for chunk in chunks:
                                    api_client.delete_chunk(chunk["doc_id"], user_id=current_user_id)
                                st.session_state["user_chunks_cache"].pop(current_user_id, None)
                                st.success(f"已删除 {source_file}")
                                st.rerun()
                            except ApiClientError as error:
                                show_backend_error(error)


def render_thoughts_block(thoughts_chunks: list[str]):
    cleaned: list[str] = []
    for chunk in thoughts_chunks:
        text = chunk.strip()
        if text.startswith("[TOOL:") or text.startswith("[TOOL_RESULT:") or text.startswith("[TOOL_THINK]"):
            text = text.replace("[TOOL:", "🔧 调用: ").replace("[TOOL_RESULT:", "✅ 返回: ").replace(
                "[TOOL_THINK]",
                "",
            )
        cleaned.append(text)
    with st.expander("思考过程", expanded=False):
        st.code("\n".join(cleaned), language="text")


def render_existing_messages():
    with st.container(key="chat-message-history"):
        for message in st.session_state["messages"]:
            if message["role"] == "__thoughts__":
                with st.expander("思考过程", expanded=False):
                    st.code(message["content"], language="text")
            else:
                with st.chat_message(message["role"]):
                    st.write(message["content"])


def render_empty_chat_state():
    with st.container(key="chat-empty-state"):
        st.markdown(
            """
            <div class="chat-empty-title">开始当前用户的会话工作区</div>
            <p class="chat-empty-copy">支持流式回答、私有知识检索、多会话切换和知识文件即时上传。</p>
            <div class="chat-empty-tags">
                <span>售后答疑</span>
                <span>私有资料问答</span>
                <span>报告线索整理</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_sidebar() -> str:
    current_user_id = st.session_state["user_id"]

    with st.sidebar:
        st.markdown(
            """
            <div class="app-brand">
                <div class="app-brand-kicker">智扫通</div>
                <div class="app-brand-title">智能客服工作台</div>
                <p class="app-brand-copy">统一管理会话、用户私有知识和知识库运维操作。</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(key="sidebar-nav"):
            st.markdown(
                """
                <div class="sidebar-section-title">工作区</div>
                <div class="sidebar-section-copy">在聊天工作台和知识库管理之间切换。</div>
                """,
                unsafe_allow_html=True,
            )
            page = st.radio(
                "页面",
                [CHAT_PAGE, KNOWLEDGE_PAGE],
                horizontal=True,
                label_visibility="collapsed",
            )

        with st.container(key="sidebar-user-panel"):
            st.markdown(
                """
                <div class="sidebar-section-title">当前用户</div>
                <div class="sidebar-section-copy">用户切换后，会话和私有知识列表会按当前用户重新加载。</div>
                """,
                unsafe_allow_html=True,
            )
            user_id_input = st.text_input("用户 ID", value=current_user_id)
            if user_id_input != current_user_id:
                st.session_state["user_id"] = user_id_input
                st.session_state["current_session_id"] = None
                st.session_state["messages"] = []
                st.session_state["user_sessions_cache"].pop(current_user_id, None)
                st.session_state["user_chunks_cache"].pop(current_user_id, None)
                load_latest_session(user_id_input)
                st.rerun()

        with st.container(key="sidebar-session-panel"):
            st.markdown(
                """
                <div class="sidebar-section-title">会话管理</div>
                <div class="sidebar-section-copy">快速创建新会话，并切换到该用户的历史会话。</div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("新建会话", key="new_session_button", use_container_width=True):
                try:
                    current_user_id = st.session_state["user_id"]
                    st.session_state["user_sessions_cache"].pop(current_user_id, None)
                    st.session_state["current_session_id"] = api_client.create_session(current_user_id)
                    st.session_state["messages"] = []
                    st.rerun()
                except ApiClientError as error:
                    show_backend_error(error)

            try:
                sessions = get_user_sessions(st.session_state["user_id"])
            except ApiClientError:
                sessions = []

            st.caption(f"共 {len(sessions)} 个历史会话")
            with st.container(key="sidebar-session-list"):
                if not sessions:
                    st.info("当前用户还没有历史会话。")
                for session in sessions:
                    is_current = session["session_id"] == st.session_state["current_session_id"]
                    if st.button(
                        format_session_preview(session),
                        key=f"session_{session['session_id']}",
                        use_container_width=True,
                        type="primary" if is_current else "secondary",
                    ):
                        try:
                            loaded_data = api_client.get_session(session["session_id"])
                            if loaded_data:
                                st.session_state["messages"] = loaded_data["messages"]
                                st.session_state["current_session_id"] = session["session_id"]
                                st.rerun()
                        except ApiClientError as error:
                            show_backend_error(error)

    return page


def render_knowledge_page():
    render_page_header(
        "知识库管理",
        "统一处理共享知识和上传文档，支持检索预览、chunk 巡检与索引重建。",
        ["FastAPI 接口", "TXT / PDF", "共享与私有知识"],
    )

    top_left, top_right = st.columns(2)

    with top_left:
        with st.container(key="knowledge-upload-panel"):
            render_panel_heading(
                "Upload",
                "上传文档",
                "写入共享知识库，适合导入公共资料、FAQ 或运营文档。",
            )
            uploaded_file = st.file_uploader("上传 txt/pdf 文档", type=["txt", "pdf"], key="kb_upload_file")
            if uploaded_file and st.button("上传并写入知识库", key="kb_upload_button", use_container_width=True):
                with st.spinner("正在通过 FastAPI 写入向量库..."):
                    try:
                        result = api_client.upload_document(uploaded_file.name, uploaded_file.getvalue())
                        if result["skipped"]:
                            st.warning(f"已跳过：{result['reason']}")
                        else:
                            st.success(f"入库完成：{result['chunk_count']} 个 chunk")
                        with st.expander("响应详情", expanded=False):
                            st.json(result)
                    except ApiClientError as error:
                        show_backend_error(error)

    with top_right:
        with st.container(key="knowledge-search-panel"):
            render_panel_heading(
                "Search",
                "检索预览",
                "验证知识库召回效果，快速确认文档内容是否能被正常命中。",
            )
            query = st.text_input("检索问题或关键词", key="kb_search_query")
            k = st.slider("返回数量", min_value=1, max_value=20, value=5)
            if st.button("检索知识库", key="kb_search_button", use_container_width=True) and query:
                with st.spinner("正在通过 FastAPI 检索..."):
                    try:
                        results = api_client.search_chunks(query, k)
                        if not results:
                            st.info("没有检索到结果")
                        for item in results:
                            with st.expander(item.get("doc_id") or "unknown", expanded=False):
                                st.write(item.get("content", ""))
                                st.json(item.get("metadata", {}))
                    except ApiClientError as error:
                        show_backend_error(error)

    lower_left, lower_right = st.columns([1.65, 1])

    with lower_left:
        with st.container(key="knowledge-chunks-panel"):
            render_panel_heading(
                "Inspect",
                "Chunk 管理",
                "查看当前索引内容，并按 doc_id 删除指定 chunk。",
            )
            filter_col, offset_col = st.columns(2)
            with filter_col:
                limit = st.number_input("每页数量", min_value=1, max_value=200, value=20)
            with offset_col:
                offset = st.number_input("偏移量", min_value=0, value=0)

            try:
                page = api_client.list_chunks(limit=int(limit), offset=int(offset))
                st.caption(f"共 {page['total']} 个 chunk")
                table_rows = [
                    {
                        "doc_id": item["doc_id"],
                        "source_file": item.get("metadata", {}).get("source_file", ""),
                        "content": item["content"][:120],
                    }
                    for item in page["chunks"]
                ]
                st.dataframe(table_rows, use_container_width=True)
            except ApiClientError as error:
                show_backend_error(error)

            st.divider()
            delete_doc_id = st.text_input("要删除的 chunk doc_id", key="delete_chunk_doc_id")
            if st.button("删除 chunk", key="delete_chunk_button", type="secondary", use_container_width=True) and delete_doc_id:
                try:
                    result = api_client.delete_chunk(delete_doc_id)
                    if result["deleted"]:
                        st.success(f"已删除 {delete_doc_id}")
                    else:
                        st.warning(f"未找到或未删除 {delete_doc_id}")
                    with st.expander("响应详情", expanded=False):
                        st.json(result)
                except ApiClientError as error:
                    show_backend_error(error)

    with lower_right:
        with st.container(key="knowledge-rebuild-panel"):
            render_panel_heading(
                "Rebuild",
                "重建索引",
                "清空当前向量库后，从配置目录和上传目录重新入库。",
            )
            st.warning("这是高风险操作。执行前请确认当前索引允许被完全重建。")
            confirm = st.checkbox("确认重建知识库索引", key="confirm_rebuild_index")
            if st.button("开始重建", key="rebuild_knowledge_button", type="primary", disabled=not confirm, use_container_width=True):
                with st.spinner("正在通过 FastAPI 重建知识库..."):
                    try:
                        result = api_client.rebuild_knowledge()
                        st.success(f"重建完成：{result['file_count']} 个文件，{result['chunk_count']} 个 chunk")
                        with st.expander("响应详情", expanded=False):
                            st.json(result)
                    except ApiClientError as error:
                        show_backend_error(error)


def render_chat_page():
    current_user_id = st.session_state["user_id"]
    try:
        sessions = get_user_sessions(current_user_id)
    except ApiClientError:
        sessions = []

    try:
        user_chunks = get_user_chunks(current_user_id)
    except ApiClientError:
        user_chunks = []

    grouped_files = group_user_files(user_chunks)
    active_session = st.session_state["current_session_id"] or "未分配"

    render_page_header(
        "智能客服工作台",
        "面向当前用户的流式问答界面，可直接联动私有知识文件和历史会话。",
        [
            f"用户 {current_user_id}",
            f"历史会话 {len(sessions)}",
            f"私有文件 {len(grouped_files)}",
            f"会话 ID {active_session[:8]}",
        ],
    )

    render_existing_messages()
    render_chat_upload_guard_component()
    render_chat_upload_toggle()
    render_chat_upload_bar()

    prompt = st.chat_input("输入问题，或结合私有知识继续追问")

    if not st.session_state["messages"] and not prompt:
        render_empty_chat_state()

    if not prompt:
        return

    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    thoughts_chunks: list[str] = []
    response_messages: list[str] = []
    thoughts_placeholder = st.empty()
    assistant_placeholder = st.empty()

    def stream_generator():
        try:
            for event_type, payload in api_client.stream_chat(
                user_id=st.session_state["user_id"],
                session_id=st.session_state["current_session_id"],
                message=prompt,
            ):
                if event_type == "session":
                    st.session_state["current_session_id"] = payload.get("session_id")
                elif event_type == "answer_delta":
                    content = payload.get("content", "")
                    response_messages.append(content)
                    yield content
                elif event_type == "tool_event":
                    thoughts_chunks.append(payload.get("content", ""))
                elif event_type == "done":
                    st.session_state["current_session_id"] = payload.get(
                        "session_id",
                        st.session_state["current_session_id"],
                    )
                elif event_type == "error":
                    raise ApiClientError(payload.get("content", "后端返回错误"))
        except ApiClientError as error:
            yield f"\n\n{error}"

    with assistant_placeholder.container():
        with st.chat_message("assistant"):
            st.write_stream(stream_generator())

    if thoughts_chunks:
        with thoughts_placeholder.container():
            render_thoughts_block(thoughts_chunks)

    assistant_response = "".join(response_messages)
    if assistant_response:
        st.session_state["messages"].append({"role": "assistant", "content": assistant_response})
        st.session_state["user_sessions_cache"].pop(st.session_state["user_id"], None)


inject_app_theme_css()
try:
    ensure_current_session()
except ApiClientError as error:
    st.session_state["messages"] = []
    show_backend_error(error)

page = render_sidebar()

if page == KNOWLEDGE_PAGE:
    render_knowledge_page()
    st.stop()

render_chat_page()
