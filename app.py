# 加载环境变量（必须在其他导入之前）
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from datetime import datetime
from agent.react_agent import ReactAgent
from database.redis_cache import RedisCache
from memory.session_manager import SessionManager
from services.knowledge_service import KnowledgeService

st.set_page_config(page_title="智扫通 · 智能客服", page_icon="🤖")
st.title("🤖 智扫通机器人智能客服")
st.caption("基于 LangChain ReAct Agent + 四层记忆库")
st.divider()

# 使用单例模式，避免重复初始化
if "redis_cache" not in st.session_state:
    st.session_state["redis_cache"] = RedisCache()
    st.session_state["session_manager"] = SessionManager(st.session_state["redis_cache"])
    st.session_state["agent"] = ReactAgent()
    st.session_state["knowledge_service"] = KnowledgeService()

if "knowledge_service" not in st.session_state:
    st.session_state["knowledge_service"] = KnowledgeService()

if "user_id" not in st.session_state:
    st.session_state["user_id"] = "user_default"

# 自动加载最近会话（断点续聊）
if "current_session_id" not in st.session_state:
    existing_sessions = st.session_state["session_manager"].list_user_sessions(st.session_state["user_id"])
    if existing_sessions:
        latest_session = existing_sessions[0]
        st.session_state["current_session_id"] = latest_session["session_id"]
        loaded_data = st.session_state["session_manager"].load_session(latest_session["session_id"])
        st.session_state["messages"] = loaded_data["messages"] if loaded_data else []
    else:
        st.session_state["current_session_id"] = st.session_state["session_manager"].create_session(st.session_state["user_id"])
        st.session_state["messages"] = []

if "messages" not in st.session_state:
    st.session_state["messages"] = []

redis_cache = st.session_state["redis_cache"]
session_manager = st.session_state["session_manager"]
knowledge_service = st.session_state["knowledge_service"]


def render_knowledge_page():
    st.header("知识库管理")

    upload_tab, search_tab, chunks_tab, rebuild_tab = st.tabs(["上传文档", "检索预览", "Chunk 管理", "重建索引"])

    with upload_tab:
        uploaded_file = st.file_uploader("上传 txt/pdf 文档", type=["txt", "pdf"])
        if uploaded_file and st.button("上传并写入知识库"):
            with st.spinner("正在写入向量库..."):
                try:
                    result = knowledge_service.add_uploaded_document(uploaded_file.name, uploaded_file.getvalue())
                    if result["skipped"]:
                        st.warning(f"已跳过：{result['reason']}")
                    else:
                        st.success(f"入库完成：{result['chunk_count']} 个 chunk")
                    st.json(result)
                except Exception as e:
                    st.error(f"上传失败：{e}")

    with search_tab:
        query = st.text_input("检索问题或关键词", key="kb_search_query")
        k = st.slider("返回数量", min_value=1, max_value=20, value=5)
        if st.button("检索知识库") and query:
            with st.spinner("正在检索..."):
                try:
                    results = knowledge_service.search_chunks(query, k)
                    if not results:
                        st.info("没有检索到结果")
                    for item in results:
                        with st.expander(f"{item.get('doc_id') or 'unknown'}"):
                            st.write(item.get("content", ""))
                            st.json(item.get("metadata", {}))
                except Exception as e:
                    st.error(f"检索失败：{e}")

    with chunks_tab:
        col1, col2 = st.columns(2)
        with col1:
            limit = st.number_input("每页数量", min_value=1, max_value=200, value=20)
        with col2:
            offset = st.number_input("偏移量", min_value=0, value=0)

        try:
            page = knowledge_service.list_chunks(limit=int(limit), offset=int(offset))
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
        except Exception as e:
            st.error(f"加载 chunk 失败：{e}")

        delete_doc_id = st.text_input("要删除的 chunk doc_id")
        if st.button("删除 chunk", type="secondary") and delete_doc_id:
            try:
                result = knowledge_service.delete_chunk(delete_doc_id)
                if result["deleted"]:
                    st.success(f"已删除 {delete_doc_id}")
                else:
                    st.warning(f"未找到或未删除 {delete_doc_id}")
                st.json(result)
            except Exception as e:
                st.error(f"删除失败：{e}")

    with rebuild_tab:
        st.warning("重建会清空当前向量库，再从配置知识库目录和上传目录重新入库。")
        confirm = st.checkbox("确认重建知识库索引")
        if st.button("开始重建", type="primary", disabled=not confirm):
            with st.spinner("正在重建知识库..."):
                try:
                    result = knowledge_service.rebuild()
                    st.success(f"重建完成：{result['file_count']} 个文件，{result['chunk_count']} 个 chunk")
                    st.json(result)
                except Exception as e:
                    st.error(f"重建失败：{e}")

with st.sidebar:
    page = st.radio("页面", ["聊天", "知识库管理"], horizontal=True)

    st.subheader("用户设置")
    user_id_input = st.text_input("用户ID", value=st.session_state["user_id"])
    if user_id_input != st.session_state["user_id"]:
        st.session_state["user_id"] = user_id_input
        st.session_state["current_session_id"] = session_manager.create_session(user_id_input)
        st.session_state["messages"] = []
        st.rerun()

    st.subheader("会话管理")
    if st.button("📝 新建会话"):
        st.session_state["current_session_id"] = session_manager.create_session(st.session_state["user_id"])
        st.session_state["messages"] = []
        st.rerun()

    st.subheader("历史会话")
    sessions = session_manager.list_user_sessions(st.session_state["user_id"])
    if sessions:
        for session in sessions:
            session_date = datetime.fromisoformat(session["saved_at"]).strftime("%m-%d %H:%M") if session["saved_at"] else ""
            if st.button(f"📄 {session['preview'][:20]}...\n{session_date}"):
                loaded_data = session_manager.load_session(session["session_id"])
                if loaded_data:
                    st.session_state["messages"] = loaded_data["messages"]
                    st.session_state["current_session_id"] = session["session_id"]
                    st.rerun()

if page == "知识库管理":
    render_knowledge_page()
    st.stop()

for message in st.session_state["messages"]:
    st.chat_message(message["role"]).write(message["content"])

prompt = st.chat_input()

# 检查是否有新的用户输入需要处理
if prompt:
    # 立即保存到会话状态
    st.session_state["messages"].append({"role": "user", "content": prompt})

    # 标记正在处理中
    st.session_state["processing"] = True

    # 立即显示用户消息
    st.chat_message("user").write(prompt)

    # 显示处理中的状态
    with st.spinner("智能客服思考中..."):
        response_messages: list[str] = []
        thoughts_chunks: list[str] = []
        res_stream = st.session_state["agent"].execute_stream(
            prompt,
            user_id=st.session_state["user_id"],
            session_id=st.session_state["current_session_id"]
        )

        def stream_generator(generator, answer_list, thoughts_list):
            """区分思考过程和最终回答的流式生成器"""
            for chunk in generator:
                stripped = chunk.lstrip()
                if stripped.startswith("🔧") or stripped.startswith("✅"):
                    thoughts_list.append(chunk)
                else:
                    answer_list.append(chunk)
                    yield chunk

        answer_placeholder = st.chat_message("assistant")
        with answer_placeholder:
            st.write_stream(stream_generator(res_stream, response_messages, thoughts_chunks))
            # 流式输出结束后，展示思考过程（可折叠）
            if thoughts_chunks:
                with st.expander("🔍 思考过程", expanded=False):
                    st.code("".join(thoughts_chunks), language="text")

        assistant_response = "".join(response_messages)
        st.session_state["messages"].append({"role": "assistant", "content": assistant_response})
        st.session_state["processing"] = False

        session_manager.save_session(st.session_state["current_session_id"], st.session_state["messages"])
