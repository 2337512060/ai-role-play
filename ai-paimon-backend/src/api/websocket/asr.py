"""
ASR语音识别WebSocket接口
"""

import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from ...services.mock_asr import get_asr_service


router = APIRouter()


@router.websocket("/asr/stream")
async def asr_stream(websocket: WebSocket):
    """
    ASR语音识别流式接口

    支持实时语音识别，包括：
    - VAD (Voice Activity Detection) 语音活动检测
    - 流式识别结果返回
    - 部分识别和最终结果
    - 时间戳对齐

    消息格式：
    客户端 -> 服务端：
    - {"type": "init", "sr": 16000, "lang": "zh"}
    - {"type": "chunk", "pcm_base64": "...", "timestamp": 1234567890.123}
    - {"type": "end"}

    服务端 -> 客户端：
    - {"type": "vad", "event": "start|end", "timestamp": 1234567890.123}
    - {"type": "partial", "text": "...", "final": false, "confidence": 0.85}
    - {"type": "final", "text": "...", "timestamps": [...], "confidence": 0.92}
    """
    # 生成会话ID
    session_id = str(uuid.uuid4())

    await websocket.accept()

    try:
        # 获取ASR服务实例
        asr_service = get_asr_service()

        # 处理音频流
        await asr_service.process_audio_stream(websocket, session_id)

    except WebSocketDisconnect:
        print(f"ASR WebSocket client {session_id} disconnected")
    except Exception as e:
        print(f"ASR WebSocket error for {session_id}: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1011, reason=f"Server error: {str(e)}")