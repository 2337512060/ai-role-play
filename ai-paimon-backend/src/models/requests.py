"""
HTTP请求数据模型
定义各API端点的请求格式
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field

from .common import AudioFormat, PolicyType


class DialogRequest(BaseModel):
    """对话生成请求"""
    text: str = Field(..., min_length=1, max_length=1000, description="用户输入文本")
    session_id: str = Field(..., min_length=1, description="会话ID")
    flags: Optional[Dict[str, bool]] = Field(
        default_factory=dict,
        description="功能开关标志"
    )
    context: Optional[Dict[str, str]] = Field(
        None,
        description="对话上下文"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text": "你好，派蒙",
                "session_id": "user_123_session_1",
                "flags": {
                    "kb": True
                },
                "context": {
                    "last_topic": "greeting"
                }
            }
        }


class VisemeRequest(BaseModel):
    """口型时间轴请求"""
    wav_url: Optional[str] = Field(None, description="音频文件URL")
    text: Optional[str] = Field(None, description="文本内容（用于合成音频）")
    audio_format: AudioFormat = Field(default=AudioFormat.WAV, description="音频格式")

    class Config:
        json_schema_extra = {
            "example": {
                "text": "派蒙想吃好吃的东西",
                "audio_format": "wav"
            }
        }


class KnowledgeSearchRequest(BaseModel):
    """知识库检索请求"""
    query: str = Field(..., min_length=1, max_length=500, description="检索查询")
    topk: int = Field(default=5, ge=1, le=20, description="返回结果数量")
    min_score: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="最小相关性分数"
    )
    filters: Optional[Dict[str, str]] = Field(
        None,
        description="过滤条件"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "提瓦特大陆的七神",
                "topk": 5,
                "min_score": 0.5
            }
        }