"""
TTS语音合成WebSocket接口
支持多provider切换和流式合成
"""

import uuid
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from ...core.config import get_settings
from ...services.tts_provider import get_tts_service, TTSProviderFactory, TTSProviderType
from ...services.mock_tts import MockTTSService
from ...services.fishaudio_tts import FishAudioTTSProvider

logger = logging.getLogger(__name__)
router = APIRouter()


async def initialize_tts_providers():
    """初始化TTS提供商"""
    settings = get_settings()
    tts_config = settings.mock.tts

    try:
        # 注册Mock Provider（总是可用）
        mock_provider = MockTTSService()
        TTSProviderFactory.register_provider(TTSProviderType.MOCK, mock_provider)

        # 注册FishAudio Provider（如果配置了API key）
        if tts_config.fishaudio_api_key:
            try:
                fish_provider = FishAudioTTSProvider(
                    api_key=tts_config.fishaudio_api_key,
                    default_model_id=tts_config.fishaudio_model_id
                )
                TTSProviderFactory.register_provider(TTSProviderType.FISHAUDIO, fish_provider)
                logger.info("FishAudio TTS provider registered successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize FishAudio provider: {e}")
        else:
            logger.info("FishAudio API key not configured, using Mock provider only")

        # 设置主要provider
        primary_provider = TTSProviderType(tts_config.primary_provider)
        TTSProviderFactory.set_primary_provider(primary_provider)

        # 设置回退providers
        fallback_providers = [TTSProviderType(p) for p in tts_config.fallback_providers]
        TTSProviderFactory.set_fallback_providers(fallback_providers)

        logger.info(f"TTS providers initialized: primary={primary_provider.value}, "
                   f"fallbacks={[p.value for p in fallback_providers]}")

    except Exception as e:
        logger.error(f"Failed to initialize TTS providers: {e}")
        # 至少确保Mock provider可用
        if TTSProviderType.MOCK not in TTSProviderFactory._providers:
            mock_provider = MockTTSService()
            TTSProviderFactory.register_provider(TTSProviderType.MOCK, mock_provider)
            TTSProviderFactory.set_primary_provider(TTSProviderType.MOCK)


# 在模块加载时初始化providers
_initialization_done = False


async def ensure_providers_initialized():
    """确保providers已初始化"""
    global _initialization_done
    if not _initialization_done:
        await initialize_tts_providers()
        _initialization_done = True


@router.websocket("/tts/stream")
async def tts_stream(websocket: WebSocket):
    """
    TTS语音合成流式接口

    支持实时语音合成，包括：
    - 多provider支持（FishAudio/Mock）
    - 流式音频数据返回
    - 音素时间标记
    - 多种语音参数控制
    - 自动错误恢复和fallback

    消息格式：
    客户端 -> 服务端：
    - {"text": "要合成的文本", "voice": "female_general", "speed": 1.0, "volume": 0.0}
    - {"text": "派蒙很开心", "emotions": "happy", "reference_id": "custom_model_id"}

    服务端 -> 客户端：
    - {"type": "audio", "pcm_base64": "...", "sr": 24000, "chunk_id": 0}
    - {"type": "marker", "phoneme": "P", "t": 0.123, "duration": 0.05}
    - {"type": "end", "duration": 2.5, "total_chunks": 25, "rtf": 0.8}
    - {"type": "error", "code": "ERROR_CODE", "message": "错误信息"}
    - {"type": "provider_status", "providers": {...}}

    支持的语音类型：
    - female_general: 通用女声
    - 或使用reference_id指定FishAudio模型ID

    支持的参数：
    - text: 要合成的文本（必需）
    - voice: 语音类型（可选，默认female_general）
    - speed: 语速倍率（可选，范围0.5-2.0，默认1.0）
    - volume: 音量调节（可选，范围-20到20，默认0.0）
    - emotions: 情感标记（可选，如"happy", "sad", "excited"等）
    - reference_id: FishAudio模型ID（可选）
    - format: 音频格式（可选，支持pcm/mp3/wav/opus，默认pcm）
    - sample_rate: 采样率（可选，默认24000）
    - chunk_length: 文本分块长度（可选，默认200）
    - temperature: 随机性控制（可选，0.0-1.0，默认0.7）
    - top_p: Token选择控制（可选，0.0-1.0，默认0.7）

    高级功能：
    - {"action": "get_status"}: 获取provider状态
    - {"action": "switch_provider", "provider": "fishaudio"}: 切换provider
    """
    # 生成/获取会话与追踪ID
    session_id = websocket.query_params.get("session_id") or str(uuid.uuid4())
    trace_id = websocket.headers.get("x-trace-id") or websocket.query_params.get("trace_id") or str(uuid.uuid4())

    await websocket.accept()

    try:
        # 确保providers已初始化
        await ensure_providers_initialized()

        # 获取TTS服务实例
        tts_service = get_tts_service()

        logger.info(f"TTS WebSocket client {session_id} connected")

        # 发送初始状态信息
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "trace_id": trace_id,
            "providers": tts_service.get_provider_status(),
            "message": "TTS service ready"
        })

        # 处理客户端消息
        async for message in websocket.iter_text():
            try:
                import json
                request_data = json.loads(message)

                # 处理特殊命令
                action = request_data.get("action")
                if action == "get_status":
                    await websocket.send_json({
                        "type": "provider_status",
                        "providers": tts_service.get_provider_status(),
                        "session_id": session_id,
                        "trace_id": trace_id
                    })
                    continue
                elif action == "switch_provider":
                    provider_name = request_data.get("provider", "mock")
                    try:
                        provider_type = TTSProviderType(provider_name)
                        TTSProviderFactory.set_primary_provider(provider_type)
                        await websocket.send_json({
                            "type": "provider_switched",
                            "new_provider": provider_name,
                            "session_id": session_id,
                            "trace_id": trace_id
                        })
                    except ValueError:
                        await websocket.send_json({
                            "type": "error",
                            "code": "INVALID_PROVIDER",
                            "message": f"Unknown provider: {provider_name}",
                            "session_id": session_id,
                            "trace_id": trace_id
                        })
                    continue

                # 检查是否有文本合成请求
                if "text" not in request_data:
                    await websocket.send_json({
                        "type": "error",
                        "code": "MISSING_TEXT",
                        "message": "Text field is required for synthesis",
                        "session_id": session_id,
                        "trace_id": trace_id
                    })
                    continue

                # 处理TTS合成请求
                await tts_service.process_websocket_requests(
                    websocket, session_id, trace_id
                )

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "code": "INVALID_JSON",
                    "message": "Invalid JSON format",
                    "session_id": session_id,
                    "trace_id": trace_id
                })
            except Exception as e:
                logger.error(f"TTS message processing error for {session_id}: {e}")
                await websocket.send_json({
                    "type": "error",
                    "code": "PROCESSING_ERROR",
                    "message": str(e),
                    "session_id": session_id,
                    "trace_id": trace_id
                })

    except WebSocketDisconnect:
        logger.info(f"TTS WebSocket client {session_id} disconnected")
    except Exception as e:
        logger.error(f"TTS WebSocket error for {session_id}: {e}")
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_json({
                    "type": "error",
                    "code": "INTERNAL",
                    "message": f"Server error: {str(e)}",
                    "session_id": session_id,
                    "trace_id": trace_id
                })
            except Exception:
                pass
            try:
                await websocket.close(code=1011, reason=f"Server error: {str(e)}")
            except Exception:
                pass


@router.get("/tts/status")
async def get_tts_status():
    """
    获取TTS服务状态

    返回：
    - providers: 各provider的健康状态
    - configuration: 当前TTS配置
    """
    try:
        await ensure_providers_initialized()
        tts_service = get_tts_service()
        settings = get_settings()

        return {
            "status": "healthy",
            "providers": tts_service.get_provider_status(),
            "configuration": {
                "primary_provider": settings.mock.tts.primary_provider,
                "fallback_providers": settings.mock.tts.fallback_providers,
                "sample_rate": settings.mock.tts.sample_rate,
                "default_voice": settings.mock.tts.default_voice,
                "enable_emotions": settings.mock.tts.enable_emotions,
                "enable_phoneme_markers": settings.mock.tts.enable_phoneme_markers
            }
        }
    except Exception as e:
        logger.error(f"Failed to get TTS status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "providers": {},
            "configuration": {}
        }


@router.post("/tts/reinitialize")
async def reinitialize_tts():
    """
    重新初始化TTS providers

    用于配置更新后重新加载providers
    """
    global _initialization_done
    try:
        _initialization_done = False
        await ensure_providers_initialized()
        return {
            "status": "success",
            "message": "TTS providers reinitialized"
        }
    except Exception as e:
        logger.error(f"Failed to reinitialize TTS: {e}")
        return {
            "status": "error",
            "message": str(e)
        }