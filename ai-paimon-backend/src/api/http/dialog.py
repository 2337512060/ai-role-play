"""
对话生成HTTP接口
"""

from fastapi import APIRouter, Depends, HTTPException

from ...core.dependencies import get_trace_id
from ...core.errors import create_http_exception, PaimonException
from ...models import DialogRequest, DialogResponse
from ...services.mock_dialog import get_dialog_service


router = APIRouter(prefix="/dialog", tags=["Dialog"])


@router.post("/generate", response_model=DialogResponse)
async def generate_dialog(
    request: DialogRequest,
    trace_id: str = Depends(get_trace_id)
) -> DialogResponse:
    """
    生成对话回复

    根据用户输入生成派蒙风格的回复，支持多种对话策略：
    - 闲聊(chitchat)：日常对话，共情回应
    - 求助(help)：提供建议和帮助
    - 事实问答(fact)：基于知识的问答
    - 故事(story)：讲述相关故事
    """
    try:
        dialog_service = get_dialog_service()
        response = await dialog_service.generate_dialog(request, trace_id)
        return response

    except PaimonException as e:
        raise create_http_exception(e)
    except Exception as e:
        # 未预期的异常
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "code": "INTERNAL",
                "msg": f"Unexpected error: {str(e)}",
                "trace_id": trace_id
            }
        )