# 加载环境变量（必须在其他导入之前）
from dotenv import load_dotenv
load_dotenv()

from datetime import datetime
from collections import defaultdict

import streamlit as st

from frontend.api_client import ApiClient, ApiClientError
from frontend.chat_upload_guard import render_chat_upload_guard_component


st.set_page_config(page_title="智扫通 · 智能客服", page_icon="🤖")
st.title("🤖 智扫通机器人智能客服")
st.caption("Streamlit 前端通过 FastAPI 调用 Agent、RAG、记忆和知识库管理能力")
st.divider()


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


def inject_chat_layout_css():
    css = """
        <style>
        section.main > div[data-testid="stMainBlockContainer"],
        .main .block-container,
        [data-testid="stAppViewContainer"] .block-container {
            padding-bottom: 5.5rem;
        }

        body[data-chat-upload-panel-open="true"] section.main > div[data-testid="stMainBlockContainer"],
        body[data-chat-upload-panel-open="true"] .main .block-container,
        body[data-chat-upload-panel-open="true"] [data-testid="stAppViewContainer"] .block-container {
            padding-bottom: 13rem;
        }

        .st-key-chat-upload-bar {
            position: fixed;
            bottom: 6.5rem;
            z-index: 999;
            width: inherit;
            min-width: min(33rem, calc(100vw - 2rem));
            max-width: 46rem;
            overflow-y: auto;
            padding: 0.45rem 0.75rem 0.35rem;
            border: 1px solid rgba(49, 51, 63, 0.16);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.98);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
            max-height: 0;
            opacity: 0;
            visibility: hidden;
            pointer-events: none;
        }

        body[data-chat-upload-panel-open="true"] .st-key-chat-upload-bar {
            max-height: 11rem;
            opacity: 1;
            visibility: visible;
            pointer-events: auto;
        }

        .st-key-chat-upload-toggle {
            position: fixed;
            bottom: 3.7rem;
            z-index: 1000;
            width: inherit;
            min-width: min(33rem, calc(100vw - 2rem));
            max-width: 46rem;
            pointer-events: none;
        }

        .st-key-chat-upload-toggle [data-testid="stVerticalBlock"] {
            gap: 0;
        }

        .st-key-chat-upload-toggle [data-testid="stElementContainer"] {
            width: 2rem;
            margin-left: 0.45rem;
            pointer-events: auto;
        }

        .st-key-chat-upload-toggle [data-testid="stHtml"] {
            width: 2rem !important;
            pointer-events: none;
        }

        .st-key-chat-upload-toggle [data-testid="stHtml"] > * {
            pointer-events: auto;
        }

        .st-key-chat-upload-toggle .chat-upload-toggle-button {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 2rem;
            min-width: 2rem;
            height: 2rem;
            min-height: 2rem;
            padding: 0;
            border-radius: 999px;
            border: 1px solid rgba(49, 51, 63, 0.18);
            background: rgba(255, 255, 255, 0.96);
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.12);
            color: rgb(49, 51, 63);
            line-height: 1;
            font-size: 1.2rem;
            font-weight: 600;
            cursor: pointer;
        }

        .st-key-chat-upload-toggle .chat-upload-toggle-button:focus {
            outline: none;
        }

        [data-testid="stChatInput"] [data-testid="stChatInputTextArea"] {
            padding-left: 2.65rem;
        }

        .st-key-chat-upload-bar [data-testid="stFileUploader"] {
            margin-bottom: 0;
        }

        .st-key-chat-upload-bar [data-testid="stFileUploaderDropzone"] {
            min-height: 2.35rem;
            padding: 0.25rem 0.5rem;
        }

        .st-key-chat-upload-bar [data-testid="stFileUploaderDropzone"] button {
            padding: 0.25rem 0.65rem;
        }

        .st-key-chat-upload-bar [data-testid="stFileUploaderDropzone"] small {
            display: none;
        }

        .st-key-chat-upload-bar [data-testid="stExpander"] {
            margin-top: 0.15rem;
        }

        @media (prefers-color-scheme: dark) {
            .st-key-chat-upload-bar {
                border-color: rgba(250, 250, 250, 0.16);
                background: rgba(14, 17, 23, 0.98);
                box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
            }

            .st-key-chat-upload-toggle .chat-upload-toggle-button {
                border-color: rgba(250, 250, 250, 0.16);
                background: rgba(14, 17, 23, 0.96);
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.28);
                color: rgba(250, 250, 250, 0.92);
            }
        }

        @media (max-width: 640px) {
            section.main > div[data-testid="stMainBlockContainer"],
            .main .block-container,
            [data-testid="stAppViewContainer"] .block-container {
                padding-bottom: 6.5rem;
            }

            body[data-chat-upload-panel-open="true"] section.main > div[data-testid="stMainBlockContainer"],
            body[data-chat-upload-panel-open="true"] .main .block-container,
            body[data-chat-upload-panel-open="true"] [data-testid="stAppViewContainer"] .block-container {
                padding-bottom: 14rem;
            }

            .st-key-chat-upload-bar {
                left: 0.75rem;
                right: 0.75rem;
                width: auto;
            }

            .st-key-chat-upload-toggle {
                left: 0.75rem;
                right: 0.75rem;
                width: auto;
            }

            body[data-chat-upload-panel-open="true"] .st-key-chat-upload-bar {
                max-height: 12rem;
            }
        }
        </style>
    """
    st.markdown(css, unsafe_allow_html=True)


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
    except ApiClientError as e:
        st.session_state["messages"] = []
        show_backend_error(e)


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


if not st.session_state["current_session_id"]:
    load_latest_session(st.session_state["user_id"])


def render_knowledge_page():
    st.header("知识库管理")

    upload_tab, search_tab, chunks_tab, rebuild_tab = st.tabs(["上传文档", "检索预览", "Chunk 管理", "重建索引"])

    with upload_tab:
        uploaded_file = st.file_uploader("上传 txt/pdf 文档", type=["txt", "pdf"])
        if uploaded_file and st.button("上传并写入知识库"):
            with st.spinner("正在通过 FastAPI 写入向量库..."):
                try:
                    result = api_client.upload_document(uploaded_file.name, uploaded_file.getvalue())
                    if result["skipped"]:
                        st.warning(f"已跳过：{result['reason']}")
                    else:
                        st.success(f"入库完成：{result['chunk_count']} 个 chunk")
                    st.json(result)
                except ApiClientError as e:
                    show_backend_error(e)

    with search_tab:
        query = st.text_input("检索问题或关键词", key="kb_search_query")
        k = st.slider("返回数量", min_value=1, max_value=20, value=5)
        if st.button("检索知识库") and query:
            with st.spinner("正在通过 FastAPI 检索..."):
                try:
                    results = api_client.search_chunks(query, k)
                    if not results:
                        st.info("没有检索到结果")
                    for item in results:
                        with st.expander(f"{item.get('doc_id') or 'unknown'}"):
                            st.write(item.get("content", ""))
                            st.json(item.get("metadata", {}))
                except ApiClientError as e:
                    show_backend_error(e)

    with chunks_tab:
        col1, col2 = st.columns(2)
        with col1:
            limit = st.number_input("每页数量", min_value=1, max_value=200, value=20)
        with col2:
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
        except ApiClientError as e:
            show_backend_error(e)

        delete_doc_id = st.text_input("要删除的 chunk doc_id")
        if st.button("删除 chunk", type="secondary") and delete_doc_id:
            try:
                result = api_client.delete_chunk(delete_doc_id)
                if result["deleted"]:
                    st.success(f"已删除 {delete_doc_id}")
                else:
                    st.warning(f"未找到或未删除 {delete_doc_id}")
                st.json(result)
            except ApiClientError as e:
                show_backend_error(e)

    with rebuild_tab:
        st.warning("重建会清空当前向量库，再从配置知识库目录和上传目录重新入库。")
        confirm = st.checkbox("确认重建知识库索引")
        if st.button("开始重建", type="primary", disabled=not confirm):
            with st.spinner("正在通过 FastAPI 重建知识库..."):
                try:
                    result = api_client.rebuild_knowledge()
                    st.success(f"重建完成：{result['file_count']} 个文件，{result['chunk_count']} 个 chunk")
                    st.json(result)
                except ApiClientError as e:
                    show_backend_error(e)


def render_chat_upload_toggle():
    with st.container(key="chat-upload-toggle"):
        st.html(
            '<button type="button" class="chat-upload-toggle-button" aria-label="上传私有知识文件" title="上传私有知识文件">+</button>'
        )


def render_chat_upload_bar():
    with st.container(key="chat-upload-bar"):
        current_user_id = st.session_state["user_id"]
        cached_chunks = st.session_state["user_chunks_cache"].get(current_user_id)
        user_chunks = cached_chunks if cached_chunks is not None else []
        if cached_chunks is None:
            try:
                user_chunks = get_user_chunks(current_user_id, force_refresh=True)
            except ApiClientError:
                user_chunks = []

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
                        uploaded_file.name, uploaded_file.getvalue(), user_id=current_user_id
                    )
                    if result["skipped"]:
                        st.warning(f"已跳过：{result.get('reason', '重复文件')}")
                    else:
                        st.session_state["user_chunks_cache"].pop(current_user_id, None)
                        st.success(f"已入库：{result['chunk_count']} 个 chunk")
                        st.rerun()
                except ApiClientError as e:
                    show_backend_error(e)

        with st.expander(f"我的知识文件 · {current_user_id}", expanded=False):
            if not user_chunks:
                st.info("还没有上传私有文件。上传后可在对话中检索到这些文件的内容。")
            else:
                group_files: dict[str, list[dict]] = defaultdict(list)
                for chunk in user_chunks:
                    source_file = chunk.get("metadata", {}).get("source_file", "unknown")
                    group_files[source_file].append(chunk)

                for source_file, chunks in sorted(group_files.items()):
                    cols = st.columns([8, 1])
                    cols[0].write(f"📄 {source_file}（{len(chunks)} chunks）")
                    with cols[1]:
                        if st.button("✕", key=f"del_{chunks[0].get('doc_id', '')}", help=f"删除 {source_file}"):
                            try:
                                for chunk in chunks:
                                    api_client.delete_chunk(chunk["doc_id"], user_id=current_user_id)
                                st.session_state["user_chunks_cache"].pop(current_user_id, None)
                                st.success(f"已删除 {source_file}")
                                st.rerun()
                            except ApiClientError as e:
                                show_backend_error(e)

with st.sidebar:
    page = st.radio("页面", ["聊天", "知识库管理"], horizontal=True)

    st.subheader("用户设置")
    user_id_input = st.text_input("用户ID", value=st.session_state["user_id"])
    if user_id_input != st.session_state["user_id"]:
        st.session_state["user_id"] = user_id_input
        st.session_state["current_session_id"] = None
        st.session_state["messages"] = []
        st.session_state["user_sessions_cache"].pop(user_id_input, None)
        st.session_state["user_chunks_cache"].pop(user_id_input, None)
        load_latest_session(user_id_input)
        st.rerun()

    st.subheader("会话管理")
    if st.button("📝 新建会话"):
        try:
            current_user_id = st.session_state["user_id"]
            st.session_state["user_sessions_cache"].pop(current_user_id, None)
            st.session_state["current_session_id"] = api_client.create_session(current_user_id)
            st.session_state["messages"] = []
            st.rerun()
        except ApiClientError as e:
            show_backend_error(e)

    st.subheader("历史会话")
    try:
        sessions = get_user_sessions(st.session_state["user_id"])
    except ApiClientError:
        sessions = []

    for session in sessions:
        session_date = datetime.fromisoformat(session["saved_at"]).strftime("%m-%d %H:%M") if session["saved_at"] else ""
        if st.button(f"📄 {session['preview'][:20]}...\n{session_date}", key=f"session_{session['session_id']}"):
            try:
                loaded_data = api_client.get_session(session["session_id"])
                if loaded_data:
                    st.session_state["messages"] = loaded_data["messages"]
                    st.session_state["current_session_id"] = session["session_id"]
                    st.rerun()
            except ApiClientError as e:
                show_backend_error(e)


if page == "知识库管理":
    render_knowledge_page()
    st.stop()


for message in st.session_state["messages"]:
    if message["role"] == "__thoughts__":
        with st.expander("🔍 思考过程", expanded=False):
            st.code(message["content"], language="text")
    else:
        st.chat_message(message["role"]).write(message["content"])

render_chat_upload_guard_component()
inject_chat_layout_css()
render_chat_upload_toggle()
render_chat_upload_bar()

prompt = st.chat_input()

if prompt:
    st.session_state["messages"].append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    response_messages: list[str] = []
    thoughts_chunks: list[str] = []

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
        except ApiClientError as e:
            yield f"\n\n{e}"

    stream_placeholder = st.empty()
    with stream_placeholder.container():
        st.write_stream(stream_generator())
    stream_placeholder.empty()

    # 思考过程（在用户问题和助手回答之间）
    if thoughts_chunks:
        cleaned = []
        for t in thoughts_chunks:
            t = t.strip()
            if t.startswith("[TOOL:") or t.startswith("[TOOL_RESULT:") or t.startswith("[TOOL_THINK]"):
                t = t.replace("[TOOL:", "🔧 调用: ").replace("[TOOL_RESULT:", "✅ 返回: ").replace("[TOOL_THINK]", "")
            cleaned.append(t)
        with st.expander("🔍 思考过程", expanded=False):
            st.code("\n".join(cleaned), language="text")

    # 助手回答
    assistant_response = "".join(response_messages)
    if assistant_response:
        st.chat_message("assistant").write(assistant_response)
        st.session_state["messages"].append({"role": "assistant", "content": assistant_response})
        st.session_state["user_sessions_cache"].pop(st.session_state["user_id"], None)
