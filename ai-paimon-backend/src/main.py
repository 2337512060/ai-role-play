"""
AI Paimon Backend API Server
主要入口文件
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import get_settings
from .core.errors import PaimonException
from .api.http import dialog, viseme, kb, health
from .api.websocket import asr, tts


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    settings = get_settings()

    app = FastAPI(
        title="AI Paimon Backend API",
        description="AI角色交互系统后端服务 - 支持语音对话、口型同步和知识库检索",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {
                "name": "Health",
                "description": "健康检查和服务状态"
            },
            {
                "name": "Dialog",
                "description": "对话生成接口"
            },
            {
                "name": "Viseme",
                "description": "口型时间轴生成"
            },
            {
                "name": "Knowledge Base",
                "description": "知识库检索"
            }
        ]
    )

    # CORS配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 开发环境允许所有源
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 全局异常处理
    @app.exception_handler(PaimonException)
    async def paimon_exception_handler(request: Request, exc: PaimonException):
        """处理业务异常"""
        return JSONResponse(
            status_code=500,
            content=exc.to_response().model_dump()
        )

    # 注册路由
    app.include_router(health.router)
    app.include_router(dialog.router)
    app.include_router(viseme.router)
    app.include_router(kb.router)

    # 注册WebSocket路由
    app.include_router(asr.router)
    app.include_router(tts.router)

    return app


# 创建应用实例
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)