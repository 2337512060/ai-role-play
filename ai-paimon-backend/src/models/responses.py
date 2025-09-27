"""
HTTP响应数据模型
定义各API端点的响应格式
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from .common import (
    BaseResponse,
    DialogTrace,
    EmotionType,
    KnowledgeSource,
    VisemeFrame
)


class DialogResponse(BaseResponse):
    """对话生成响应"""
    reply: str = Field(..., description="回复文本")
    emotion: EmotionType = Field(..., description="情绪状态")
    trace: DialogTrace = Field(..., description="对话追踪信息")

    class Config:
        json_schema_extra = {
            "example": {
                "ok": True,
                "reply": "欸！旅行者你好呀～派蒙刚才在想今天要吃什么好吃的呢！",
                "emotion": "happy",
                "trace": {
                    "policy": "chitchat",
                    "kb_sources": [],
                    "processing_time": 156.7
                },
                "trace_id": "abc123"
            }
        }


class VisemeResponse(BaseResponse):
    """口型时间轴响应"""
    visemes: List[VisemeFrame] = Field(..., description="口型时间轴")
    src: str = Field(..., description="生成源（rhubarb/ovr）")
    duration: float = Field(..., description="总时长（秒）")

    class Config:
        json_schema_extra = {
            "example": {
                "ok": True,
                "visemes": [
                    {"t": 0.12, "id": "A", "w": 0.8},
                    {"t": 0.24, "id": "I", "w": 0.6},
                    {"t": 0.36, "id": "M", "w": 0.9}
                ],
                "src": "rhubarb",
                "duration": 2.5,
                "trace_id": "xyz789"
            }
        }


class KnowledgeSearchResponse(BaseResponse):
    """知识库检索响应"""
    hits: List[KnowledgeSource] = Field(..., description="检索结果")
    embedding_model: str = Field(..., description="使用的嵌入模型")
    total_count: Optional[int] = Field(None, description="总结果数量")

    class Config:
        json_schema_extra = {
            "example": {
                "ok": True,
                "hits": [
                    {
                        "text": "提瓦特大陆是七神共同统治的世界...",
                        "source": "public",
                        "score": 0.92,
                        "metadata": {"category": "lore"}
                    }
                ],
                "embedding_model": "bge-m3",
                "total_count": 15,
                "trace_id": "def456"
            }
        }


class HealthResponse(BaseResponse):
    """健康检查响应"""
    status: str = Field(..., description="服务状态")
    service: str = Field(..., description="服务名称")
    version: str = Field(..., description="版本号")

    class Config:
        json_schema_extra = {
            "example": {
                "ok": True,
                "status": "healthy",
                "service": "ai-paimon-backend",
                "version": "0.1.0"
            }
        }