"""
依赖注入模块
定义FastAPI的依赖注入函数
"""

import uuid
from typing import Dict, Any

from fastapi import Request, Depends

from .config import Settings, get_settings


async def get_trace_id(request: Request) -> str:
    """获取或生成请求追踪ID"""
    # 从请求头获取追踪ID，如果没有则生成新的
    trace_id = request.headers.get("X-Trace-ID")
    if not trace_id:
        trace_id = str(uuid.uuid4())

    # 将追踪ID添加到请求状态中，供中间件使用
    request.state.trace_id = trace_id
    return trace_id


async def get_request_context(
    request: Request,
    trace_id: str = Depends(get_trace_id),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """获取请求上下文信息"""
    return {
        "trace_id": trace_id,
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("User-Agent"),
        "settings": settings
    }


class FeatureFlagChecker:
    """特征开关检查器"""

    def __init__(self, flag_path: str):
        self.flag_path = flag_path

    def __call__(self, settings: Settings = Depends(get_settings)) -> bool:
        """检查特征开关是否启用"""
        # 支持嵌套路径，如 "features.kb.enabled"
        path_parts = self.flag_path.split(".")
        obj = settings

        for part in path_parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return False

        return bool(obj) if not isinstance(obj, bool) else obj


# 预定义的特征开关检查器
check_kb_enabled = FeatureFlagChecker("features.kb.enabled")
check_viseme_rhubarb = FeatureFlagChecker("features.viseme.rhubarb")
check_viseme_ovr = FeatureFlagChecker("features.viseme.ovr")


def require_feature(flag_checker: FeatureFlagChecker):
    """特征开关装饰器，要求特征必须启用"""

    def dependency(is_enabled: bool = Depends(flag_checker)):
        if not is_enabled:
            from .errors import PaimonException, ErrorCode
            raise PaimonException(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message=f"Feature {flag_checker.flag_path} is disabled"
            )
        return True

    return dependency


# 常用的特征依赖
require_kb = require_feature(check_kb_enabled)
require_viseme_rhubarb = require_feature(check_viseme_rhubarb)
require_viseme_ovr = require_feature(check_viseme_ovr)