"""
健康检查HTTP接口
"""

from fastapi import APIRouter

from ...models import HealthResponse


router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    健康检查接口

    返回服务的基本状态信息，用于：
    - 负载均衡器健康检查
    - 监控系统状态探测
    - 服务发现和注册
    """
    return HealthResponse(
        status="healthy",
        service="ai-paimon-backend",
        version="0.1.0"
    )


@router.get("/")
async def root():
    """根路径，返回服务基本信息"""
    return {
        "service": "AI Paimon Backend API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "description": "AI角色交互系统后端服务"
    }