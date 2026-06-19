# 加载环境变量（必须在其他导入之前）
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from datetime import datetime
from agent.react_agent import ReactAgent
from database.redis_cache import RedisCache
from memory.session_manager import SessionManager

st.set_page_config(page_title="智扫通 · 智能客服", page_icon="🤖")
st.title("🤖 智扫通机器人智能客服")
st.caption("基于 LangChain ReAct Agent + 四层记忆库")
st.divider()

# 使用单例模式，避免重复初始化
if "redis_cache" not in st.session_state:
    st.session_state["redis_cache"] = RedisCache()
    st.session_state["session_manager"] = SessionManager(st.session_state["redis_cache"])
    st.session_state["agent"] = ReactAgent()

if "user_id" not in st.session_state:
    st.session_state["user_id"] = "user_default"

if "current_session_id" not in st.session_state:
    st.session_state["current_session_id"] = st.session_state["session_manager"].create_session(st.session_state["user_id"])

if "messages" not in st.session_state:
    st.session_state["messages"] = []

redis_cache = st.session_state["redis_cache"]
session_manager = st.session_state["session_manager"]

with st.sidebar:
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

for message in st.session_state["messages"]:
    st.chat_message(message["role"]).write(message["content"])

prompt = st.chat_input()

# 检查是否有新的用户输入需要处理
if prompt:
    # 立即保存到会话状态
    st.session_state["messages"].append({"role": "user", "content": prompt})
    
    # 标记正在处理中
    st.session_state["processing"] = True
    
    # 立即显示用户消息（因为脚本会重新运行，所以需要在显示之前检查）
    st.chat_message("user").write(prompt)
    
    # 显示处理中的状态
    with st.spinner("智能客服思考中..."):
        response_messages: list[str] = []
        res_stream = st.session_state["agent"].execute_stream(
            prompt,
            user_id=st.session_state["user_id"],
            session_id=st.session_state["current_session_id"]
        )

        def stream_generator(generator, cache_list):
            for chunk in generator:
                cache_list.append(chunk)
                for char in chunk:
                    yield char

        answer_placeholder = st.chat_message("assistant")
        with answer_placeholder:
            st.write_stream(stream_generator(res_stream, response_messages))
        
        assistant_response = "".join(response_messages)
        st.session_state["messages"].append({"role": "assistant", "content": assistant_response})
        st.session_state["processing"] = False

        session_manager.save_session(st.session_state["current_session_id"], st.session_state["messages"])