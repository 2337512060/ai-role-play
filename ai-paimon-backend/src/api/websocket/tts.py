"""
TTS语音合成WebSocket接口
"""

import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from ...services.mock_tts import get_tts_service


router = APIRouter()


@router.websocket("/tts/stream")
async def tts_stream(websocket: WebSocket):
    """
    TTS语音合成流式接口

    支持实时语音合成，包括：
    - 流式音频数据返回
    - 音素时间标记
    - 多种语音参数控制

    消息格式：
    客户端 -> 服务端：
    - {"text": "要合成的文本", "voice": "female_general", "speed": 1.0}

    服务端 -> 客户端：
    - {"type": "audio", "pcm_base64": "...", "sr": 24000, "chunk_id": 0}
    - {"type": "marker", "phoneme": "P", "t": 0.123, "duration": 0.05}
    - {"type": "end", "duration": 2.5, "total_chunks": 25}
    - {"type": "error", "code": "ERROR_CODE", "message": "错误信息"}

    支持的语音类型：
    - female_general: 通用女声
    - 其他语音类型可在Mock服务中扩展

    支持的参数：
    - text: 要合成的文本（必需）
    - voice: 语音类型（可选，默认female_general）
    - speed: 语速倍率（可选，范围0.5-2.0，默认1.0）
    """
    # 生成会话ID
    session_id = str(uuid.uuid4())

    await websocket.accept()

    try:
        # 获取TTS服务实例
        tts_service = get_tts_service()

        # 处理TTS请求
        await tts_service.process_tts_requests(websocket, session_id)

    except WebSocketDisconnect:
        print(f"TTS WebSocket client {session_id} disconnected")
    except Exception as e:
        print(f"TTS WebSocket error for {session_id}: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=1011, reason=f"Server error: {str(e)}")