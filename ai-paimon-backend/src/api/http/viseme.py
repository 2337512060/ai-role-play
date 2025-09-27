"""
口型时间轴HTTP接口
"""

from fastapi import APIRouter, Depends, HTTPException

from ...core.dependencies import get_trace_id
from ...core.errors import create_http_exception, PaimonException, ValidationException
from ...models import VisemeRequest, VisemeResponse
from ...services.mock_viseme import get_viseme_service


router = APIRouter(prefix="/viseme", tags=["Viseme"])


@router.post("/timeline", response_model=VisemeResponse)
async def generate_viseme_timeline(
    request: VisemeRequest,
    trace_id: str = Depends(get_trace_id)
) -> VisemeResponse:
    """
    生成口型时间轴

    根据文本或音频文件生成口型动画的时间轴数据。
    支持的口型类型：A, E, I, O, U, M, L, F, S, T, H, X(静音)

    可以通过以下方式之一提供输入：
    - text: 直接提供文本，系统会估算时长并生成口型
    - wav_url: 提供音频文件URL，系统会解析音频生成精确的口型时间轴
    """
    try:
        # 验证输入
        if not request.text and not request.wav_url:
            raise ValidationException(
                "Either 'text' or 'wav_url' must be provided",
                details={"request": request.model_dump()}
            )

        viseme_service = get_viseme_service()
        response = await viseme_service.generate_viseme_timeline(request, trace_id)
        return response

    except PaimonException as e:
        raise create_http_exception(e)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "ok": False,
                "code": "BAD_REQUEST",
                "msg": str(e),
                "trace_id": trace_id
            }
        )
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