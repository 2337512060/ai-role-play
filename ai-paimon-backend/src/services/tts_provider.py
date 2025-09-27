"""
TTS Provider Abstraction Layer
提供统一的TTS服务接口和provider管理
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import AsyncGenerator, Dict, List, Optional, Union
import time
import json

from ..models.websocket import TTSRequestMessage


class TTSProviderType(str, Enum):
    """TTS Provider类型"""
    MOCK = "mock"
    FISHAUDIO = "fishaudio"


class AudioFormat(str, Enum):
    """支持的音频格式"""
    MP3 = "mp3"
    WAV = "wav"
    OPUS = "opus"
    PCM = "pcm"


@dataclass
class TTSRequest:
    """TTS请求参数"""
    text: str
    voice: str = "female_general"
    speed: float = 1.0
    volume: float = 0.0  # -20 to 20
    format: AudioFormat = AudioFormat.PCM
    sample_rate: int = 24000
    chunk_length: int = 200
    temperature: float = 0.7
    top_p: float = 0.7
    reference_id: Optional[str] = None
    emotions: Optional[str] = None


@dataclass
class AudioChunk:
    """音频数据块"""
    pcm_base64: str
    chunk_id: int
    sample_rate: int
    duration_ms: float


@dataclass
class PhonemeMarker:
    """音素标记"""
    phoneme: str
    timestamp: float  # 秒
    duration: float  # 秒
    confidence: float = 1.0


@dataclass
class TTSResult:
    """TTS合成结果"""
    audio_chunks: List[AudioChunk]
    phoneme_markers: List[PhonemeMarker]
    total_duration: float
    total_chunks: int
    provider: str
    rtf: float  # Real-time factor


class TTSStreamMessage:
    """TTS流消息基类"""
    def __init__(self, msg_type: str, session_id: str, trace_id: str):
        self.type = msg_type
        self.session_id = session_id
        self.trace_id = trace_id
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp
        }


class TTSAudioStreamMessage(TTSStreamMessage):
    """音频流消息"""
    def __init__(self, chunk: AudioChunk, session_id: str, trace_id: str):
        super().__init__("audio", session_id, trace_id)
        self.chunk = chunk

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "pcm_base64": self.chunk.pcm_base64,
            "sr": self.chunk.sample_rate,
            "chunk_id": self.chunk.chunk_id,
            "duration_ms": self.chunk.duration_ms
        })
        return data


class TTSMarkerStreamMessage(TTSStreamMessage):
    """音素标记流消息"""
    def __init__(self, marker: PhonemeMarker, session_id: str, trace_id: str):
        super().__init__("marker", session_id, trace_id)
        self.marker = marker

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "phoneme": self.marker.phoneme,
            "t": self.marker.timestamp,
            "duration": self.marker.duration,
            "confidence": self.marker.confidence
        })
        return data


class TTSEndStreamMessage(TTSStreamMessage):
    """结束流消息"""
    def __init__(self, duration: float, total_chunks: int, rtf: float,
                 session_id: str, trace_id: str):
        super().__init__("end", session_id, trace_id)
        self.duration = duration
        self.total_chunks = total_chunks
        self.rtf = rtf

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "duration": self.duration,
            "total_chunks": self.total_chunks,
            "rtf": self.rtf
        })
        return data


class TTSErrorStreamMessage(TTSStreamMessage):
    """错误流消息"""
    def __init__(self, code: str, message: str, session_id: str, trace_id: str):
        super().__init__("error", session_id, trace_id)
        self.code = code
        self.message = message

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "code": self.code,
            "message": self.message
        })
        return data


class BaseTTSProvider(ABC):
    """TTS Provider基类"""

    def __init__(self, provider_type: TTSProviderType):
        self.provider_type = provider_type
        self.is_healthy = True
        self.last_error: Optional[str] = None
        self._start_time: Optional[float] = None

    @abstractmethod
    async def synthesize_stream(
        self,
        request: TTSRequest,
        session_id: str,
        trace_id: str
    ) -> AsyncGenerator[Union[TTSAudioStreamMessage, TTSMarkerStreamMessage,
                             TTSEndStreamMessage, TTSErrorStreamMessage], None]:
        """
        流式语音合成

        Args:
            request: TTS请求参数
            session_id: 会话ID
            trace_id: 追踪ID

        Yields:
            TTSStreamMessage: 音频、标记或错误消息
        """
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """检查provider健康状态"""
        pass

    def mark_unhealthy(self, error: str):
        """标记provider为不健康状态"""
        self.is_healthy = False
        self.last_error = error

    def mark_healthy(self):
        """标记provider为健康状态"""
        self.is_healthy = True
        self.last_error = None

    def start_timing(self):
        """开始计时"""
        self._start_time = time.time()

    def get_rtf(self, audio_duration: float) -> float:
        """计算实时系数 (Real-Time Factor)"""
        if self._start_time is None:
            return 0.0
        processing_time = time.time() - self._start_time
        return processing_time / audio_duration if audio_duration > 0 else 0.0


class TTSProviderFactory:
    """TTS Provider工厂"""

    _providers: Dict[TTSProviderType, BaseTTSProvider] = {}
    _primary_provider: TTSProviderType = TTSProviderType.MOCK
    _fallback_providers: List[TTSProviderType] = [TTSProviderType.MOCK]

    @classmethod
    def register_provider(cls, provider_type: TTSProviderType, provider: BaseTTSProvider):
        """注册TTS Provider"""
        cls._providers[provider_type] = provider

    @classmethod
    def set_primary_provider(cls, provider_type: TTSProviderType):
        """设置主要Provider"""
        if provider_type in cls._providers:
            cls._primary_provider = provider_type
        else:
            raise ValueError(f"Provider {provider_type} not registered")

    @classmethod
    def set_fallback_providers(cls, fallback_list: List[TTSProviderType]):
        """设置回退Provider列表"""
        cls._fallback_providers = fallback_list

    @classmethod
    async def get_provider(cls) -> BaseTTSProvider:
        """获取可用的TTS Provider"""
        # 首先尝试主要provider
        primary = cls._providers.get(cls._primary_provider)
        if primary and primary.is_healthy:
            return primary

        # 检查主要provider健康状态
        if primary:
            try:
                if await primary.check_health():
                    primary.mark_healthy()
                    return primary
            except Exception as e:
                primary.mark_unhealthy(str(e))

        # 尝试回退providers
        for fallback_type in cls._fallback_providers:
            if fallback_type == cls._primary_provider:
                continue  # 跳过已测试的主要provider

            fallback = cls._providers.get(fallback_type)
            if fallback and fallback.is_healthy:
                return fallback

            # 检查回退provider健康状态
            if fallback:
                try:
                    if await fallback.check_health():
                        fallback.mark_healthy()
                        return fallback
                except Exception as e:
                    fallback.mark_unhealthy(str(e))

        # 如果所有providers都不可用，返回Mock作为最后的回退
        mock_provider = cls._providers.get(TTSProviderType.MOCK)
        if mock_provider:
            return mock_provider

        raise RuntimeError("No healthy TTS providers available")

    @classmethod
    def get_provider_status(cls) -> Dict[str, dict]:
        """获取所有provider状态"""
        status = {}
        for provider_type, provider in cls._providers.items():
            status[provider_type.value] = {
                "healthy": provider.is_healthy,
                "last_error": provider.last_error,
                "is_primary": provider_type == cls._primary_provider
            }
        return status


class TTSService:
    """统一TTS服务入口"""

    def __init__(self):
        self.factory = TTSProviderFactory()

    async def synthesize_stream(
        self,
        request: TTSRequest,
        session_id: str,
        trace_id: str
    ) -> AsyncGenerator[Union[TTSAudioStreamMessage, TTSMarkerStreamMessage,
                             TTSEndStreamMessage, TTSErrorStreamMessage], None]:
        """
        流式语音合成

        Args:
            request: TTS请求参数
            session_id: 会话ID
            trace_id: 追踪ID

        Yields:
            TTSStreamMessage: 流消息
        """
        try:
            provider = await self.factory.get_provider()
            async for message in provider.synthesize_stream(request, session_id, trace_id):
                yield message
        except Exception as e:
            yield TTSErrorStreamMessage(
                code="PROVIDER_ERROR",
                message=f"TTS provider error: {str(e)}",
                session_id=session_id,
                trace_id=trace_id
            )

    async def process_websocket_requests(self, websocket, session_id: str, trace_id: str):
        """处理WebSocket TTS请求"""
        try:
            async for message in websocket.iter_text():
                try:
                    request_data = json.loads(message)

                    # 构建TTS请求
                    tts_request = TTSRequest(
                        text=request_data.get("text", ""),
                        voice=request_data.get("voice", "female_general"),
                        speed=request_data.get("speed", 1.0),
                        volume=request_data.get("volume", 0.0),
                        format=AudioFormat(request_data.get("format", "pcm")),
                        sample_rate=request_data.get("sample_rate", 24000),
                        chunk_length=request_data.get("chunk_length", 200),
                        temperature=request_data.get("temperature", 0.7),
                        top_p=request_data.get("top_p", 0.7),
                        reference_id=request_data.get("reference_id"),
                        emotions=request_data.get("emotions")
                    )

                    if not tts_request.text:
                        error_msg = TTSErrorStreamMessage(
                            code="EMPTY_TEXT",
                            message="Text cannot be empty",
                            session_id=session_id,
                            trace_id=trace_id
                        )
                        await websocket.send_text(json.dumps(error_msg.to_dict()))
                        continue

                    # 流式合成
                    async for stream_message in self.synthesize_stream(
                        tts_request, session_id, trace_id
                    ):
                        await websocket.send_text(json.dumps(stream_message.to_dict()))

                except json.JSONDecodeError:
                    error_msg = TTSErrorStreamMessage(
                        code="INVALID_JSON",
                        message="Invalid JSON format",
                        session_id=session_id,
                        trace_id=trace_id
                    )
                    await websocket.send_text(json.dumps(error_msg.to_dict()))
                except Exception as e:
                    error_msg = TTSErrorStreamMessage(
                        code="PROCESSING_ERROR",
                        message=str(e),
                        session_id=session_id,
                        trace_id=trace_id
                    )
                    await websocket.send_text(json.dumps(error_msg.to_dict()))

        except Exception as e:
            print(f"TTS WebSocket error for {session_id}: {e}")

    def get_provider_status(self) -> Dict[str, dict]:
        """获取provider状态"""
        return self.factory.get_provider_status()


# 全局TTS服务实例
_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """获取TTS服务实例"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service