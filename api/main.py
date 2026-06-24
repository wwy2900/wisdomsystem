"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager
import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.routes.admin import router as admin_router
from api.routes.admin_users import router as admin_users_router
from api.routes.auth import router as auth_router
from api.routes.chat import router as chat_router
from api.routes.knowledge import router as knowledge_router
from api.routes.me import router as me_router
from api.schemas import HealthResponse
from services.auth_service import AuthService
from utils.logger_handler import logger


load_dotenv()


def _frontend_origins() -> list[str]:
    raw_value = os.getenv("FRONTEND_ORIGINS", "http://localhost:5173")
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def build_chat_service():
    from services.chat_service import ChatService

    return ChatService()


def build_knowledge_service():
    from services.knowledge_service import KnowledgeService

    return KnowledgeService()


def build_auth_service():
    return AuthService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[FastAPI] initializing services")
    app.state.chat_service = build_chat_service()
    app.state.knowledge_service = build_knowledge_service()
    app.state.auth_service = build_auth_service()
    app.state.chat_service.warmup_async()
    logger.info("[FastAPI] services ready")
    yield
    logger.info("[FastAPI] shutdown")


app = FastAPI(
    title="WisdomSystem API",
    description="WisdomSystem FastAPI backend",
    version="1.7.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health(request: Request):
    chat_service = getattr(request.app.state, "chat_service", None)
    redis_cache = getattr(chat_service, "redis_cache", None)
    cache_backend = getattr(redis_cache, "backend", "unknown")
    return HealthResponse(status="ok", agent_ready=chat_service is not None, cache_backend=cache_backend)


app.include_router(auth_router)
app.include_router(me_router)
app.include_router(admin_router)
app.include_router(admin_users_router)
app.include_router(chat_router)
app.include_router(knowledge_router)
