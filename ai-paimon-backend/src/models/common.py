"""
通用数据模型
定义跨模块使用的通用数据结构
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """基础响应模型"""
    ok: bool = True
    trace_id: Optional[str] = None


class TimestampModel(BaseModel):
    """时间戳模型"""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


class EmotionType(str, Enum):
    """情绪类型枚举"""
    HAPPY = "happy"
    CURIOUS = "curious"
    THINKING = "thinking"
    EXCITED = "excited"
    CONFUSED = "confused"
    NEUTRAL = "neutral"


class PolicyType(str, Enum):
    """对话策略类型"""
    CHITCHAT = "chitchat"
    HELP = "help"
    FACT = "fact"
    STORY = "story"


class AudioFormat(str, Enum):
    """音频格式枚举"""
    PCM = "pcm"
    WAV = "wav"
    MP3 = "mp3"


class VisemeType(str, Enum):
    """口型类型枚举"""
    A = "A"
    E = "E"
    I = "I"
    O = "O"
    U = "U"
    M = "M"
    L = "L"
    F = "F"
    S = "S"
    T = "T"
    H = "H"
    X = "X"  # 静音


class SourceType(str, Enum):
    """来源类型"""
    PUBLIC = "public"
    CUSTOM = "custom"
    GENERATED = "generated"


class Timestamp(BaseModel):
    """时间戳范围"""
    start: float = Field(..., description="开始时间（秒）")
    end: float = Field(..., description="结束时间（秒）")


class AudioChunk(BaseModel):
    """音频数据块"""
    pcm_base64: str = Field(..., description="Base64编码的PCM音频数据")
    sample_rate: int = Field(default=16000, description="采样率")
    channels: int = Field(default=1, description="声道数")
    timestamp: Optional[float] = Field(None, description="时间戳")


class KnowledgeSource(BaseModel):
    """知识库来源"""
    text: str = Field(..., description="文本内容")
    source: SourceType = Field(..., description="来源类型")
    score: float = Field(..., ge=0.0, le=1.0, description="相关性分数")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class DialogTrace(BaseModel):
    """对话追踪信息"""
    policy: PolicyType = Field(..., description="使用的对话策略")
    kb_sources: List[KnowledgeSource] = Field(default_factory=list, description="知识库来源")
    processing_time: Optional[float] = Field(None, description="处理时间（毫秒）")
    metadata: Optional[Dict[str, Any]] = Field(None, description="其他元数据")


class VisemeFrame(BaseModel):
    """口型帧"""
    t: float = Field(..., description="时间戳（秒）")
    id: VisemeType = Field(..., description="口型ID")
    w: float = Field(..., ge=0.0, le=1.0, description="权重/强度")


class PhonemeMarker(BaseModel):
    """音素标记"""
    phoneme: str = Field(..., description="音素符号")
    t: float = Field(..., description="时间戳（秒）")
    duration: Optional[float] = Field(None, description="持续时间（秒）")