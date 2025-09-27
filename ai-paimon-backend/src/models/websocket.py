"""
WebSocket消息数据模型
定义WebSocket通信的消息格式
"""

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field

from .common import AudioChunk, PhonemeMarker, Timestamp


# ASR WebSocket 消息模型

class ASRInitMessage(BaseModel):
    """ASR初始化消息"""
    type: Literal["init"] = "init"
    sr: int = Field(default=16000, description="采样率")
    lang: str = Field(default="zh", description="语言代码")
    options: Optional[dict] = Field(None, description="其他选项")


class ASRChunkMessage(BaseModel):
    """ASR音频块消息"""
    type: Literal["chunk"] = "chunk"
    pcm_base64: str = Field(..., description="Base64编码的PCM音频数据")
    timestamp: Optional[float] = Field(None, description="时间戳")


class ASREndMessage(BaseModel):
    """ASR结束消息"""
    type: Literal["end"] = "end"


class ASRVADMessage(BaseModel):
    """ASR VAD事件消息"""
    type: Literal["vad"] = "vad"
    event: Literal["start", "end"] = Field(..., description="VAD事件类型")
    timestamp: float = Field(..., description="事件时间戳")


class ASRPartialMessage(BaseModel):
    """ASR部分识别结果"""
    type: Literal["partial"] = "partial"
    text: str = Field(..., description="部分识别文本")
    final: Literal[False] = False
    confidence: Optional[float] = Field(None, description="置信度")


class ASRFinalMessage(BaseModel):
    """ASR最终识别结果"""
    type: Literal["final"] = "final"
    text: str = Field(..., description="最终识别文本")
    timestamps: Optional[List[Timestamp]] = Field(None, description="时间戳对齐")
    confidence: Optional[float] = Field(None, description="置信度")


# TTS WebSocket 消息模型

class TTSRequestMessage(BaseModel):
    """TTS请求消息"""
    text: str = Field(..., description="要合成的文本")
    voice: str = Field(default="female_general", description="语音类型")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="语速倍率")
    options: Optional[dict] = Field(None, description="其他选项")


class TTSAudioMessage(BaseModel):
    """TTS音频数据消息"""
    type: Literal["audio"] = "audio"
    pcm_base64: str = Field(..., description="Base64编码的PCM音频数据")
    sr: int = Field(default=24000, description="采样率")
    chunk_id: Optional[int] = Field(None, description="音频块ID")


class TTSMarkerMessage(BaseModel):
    """TTS音素标记消息"""
    type: Literal["marker"] = "marker"
    phoneme: str = Field(..., description="音素符号")
    t: float = Field(..., description="时间戳（秒）")
    duration: Optional[float] = Field(None, description="持续时间")


class TTSEndMessage(BaseModel):
    """TTS结束消息"""
    type: Literal["end"] = "end"
    duration: float = Field(..., description="总时长（秒）")
    total_chunks: Optional[int] = Field(None, description="总音频块数")


class TTSErrorMessage(BaseModel):
    """TTS错误消息"""
    type: Literal["error"] = "error"
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误信息")


# 联合类型定义

ASRClientMessage = Union[ASRInitMessage, ASRChunkMessage, ASREndMessage]
ASRServerMessage = Union[ASRVADMessage, ASRPartialMessage, ASRFinalMessage]

TTSServerMessage = Union[TTSAudioMessage, TTSMarkerMessage, TTSEndMessage, TTSErrorMessage]


# WebSocket连接状态

class ConnectionState(BaseModel):
    """WebSocket连接状态"""
    session_id: str = Field(..., description="会话ID")
    connected_at: float = Field(..., description="连接时间戳")
    last_activity: float = Field(..., description="最后活动时间")
    message_count: int = Field(default=0, description="消息计数")
    is_active: bool = Field(default=True, description="是否活跃")