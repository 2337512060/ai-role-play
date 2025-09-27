"""
知识库检索HTTP接口
"""

from fastapi import APIRouter, Depends, HTTPException

from ...core.dependencies import get_trace_id, require_kb
from ...core.errors import create_http_exception, PaimonException
from ...models import KnowledgeSearchRequest, KnowledgeSearchResponse
from ...services.mock_kb import get_knowledge_service


router = APIRouter(prefix="/kb", tags=["Knowledge Base"])


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    request: KnowledgeSearchRequest,
    trace_id: str = Depends(get_trace_id),
    _: bool = Depends(require_kb)  # 检查知识库功能是否启用
) -> KnowledgeSearchResponse:
    """
    知识库检索

    在预设的知识库中检索与查询相关的内容。知识库包含以下类别：
    - 角色信息：派蒙、旅行者等角色的基本信息
    - 世界设定：提瓦特大陆、七神、各个国家的背景
    - 地点信息：蒙德城、璃月港等地点的详细介绍
    - 游戏机制：元素系统、料理系统等玩法介绍

    支持的过滤条件：
    - category：内容类别（character/lore/location/gameplay/organization）
    - region：地区（mondstadt/liyue/inazuma等）
    - topic：主题标签
    """
    try:
        knowledge_service = get_knowledge_service()
        response = await knowledge_service.search_knowledge(request, trace_id)
        return response

    except PaimonException as e:
        raise create_http_exception(e)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "code": "INTERNAL",
                "msg": f"Unexpected error: {str(e)}",
                "trace_id": trace_id
            }
        )