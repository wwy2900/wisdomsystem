"""FastAPI 应用入口"""
# 必须在所有项目模块导入前加载环境变量
from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routes.chat import router as chat_router
from api.routes.knowledge import router as knowledge_router
from api.schemas import HealthResponse
from services.chat_service import ChatService
from services.knowledge_service import KnowledgeService
from utils.logger_handler import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化重型组件"""
    logger.info("[FastAPI] 正在初始化服务...")
    app.state.chat_service = ChatService()
    app.state.knowledge_service = KnowledgeService()
    logger.info("[FastAPI] 服务初始化完成")
    yield
    logger.info("[FastAPI] 服务关闭")


app = FastAPI(title="智扫通 API", description="智扫通智能客服 FastAPI 后端", version="1.0.0", lifespan=lifespan)

# 健康检查（不鉴权）
@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        agent_ready=True,
        cache_backend="redis",
    )

# 业务路由（鉴权）
app.include_router(chat_router)
app.include_router(knowledge_router)
