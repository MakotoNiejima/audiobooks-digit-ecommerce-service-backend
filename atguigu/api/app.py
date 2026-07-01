from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from atguigu.api.router.chat_router import router as chat_router
from atguigu.infrastructure.db import init_db_engine, dispose_engine
from atguigu.infrastructure.http_client import init_http_client, dispose_http_client
from atguigu.api.dependencies import init_dialogue_engine

_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用启动时初始化资源，关闭时释放。
    数字人(avatar)本期跳过。
    """
    await init_db_engine()
    init_http_client()
    init_dialogue_engine()
    yield  # FASTAPI 正常处理请求

    # 清理资源（应用关闭）
    await dispose_engine()
    await dispose_http_client()


app = FastAPI(title="听书智能客服", description="听书平台智能客服V1.0", lifespan=lifespan)

# 允许前端调试页跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

# 静态调试页
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/static/index.html")
