"""
数据模型测试
"""

import pytest
from pydantic import ValidationError

from src.models import (
    DialogRequest,
    DialogResponse,
    VisemeRequest,
    VisemeResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    EmotionType,
    PolicyType,
    VisemeType,
    SourceType,
    DialogTrace,
    VisemeFrame,
    KnowledgeSource
)


class TestRequestModels:
    """请求模型测试"""

    def test_dialog_request_valid(self):
        """测试有效的对话请求"""
        request = DialogRequest(
            text="你好",
            session_id="test_session",
            flags={"kb": True}
        )
        assert request.text == "你好"
        assert request.session_id == "test_session"
        assert request.flags["kb"] is True

    def test_dialog_request_empty_text(self):
        """测试空文本验证"""
        with pytest.raises(ValidationError):
            DialogRequest(
                text="",
                session_id="test_session"
            )

    def test_dialog_request_long_text(self):
        """测试超长文本验证"""
        long_text = "a" * 1001  # 超过1000字符限制
        with pytest.raises(ValidationError):
            DialogRequest(
                text=long_text,
                session_id="test_session"
            )

    def test_viseme_request_valid_text(self):
        """测试有效的口型请求（文本）"""
        request = VisemeRequest(text="派蒙想吃好吃的")
        assert request.text == "派蒙想吃好吃的"
        assert request.wav_url is None

    def test_viseme_request_valid_wav_url(self):
        """测试有效的口型请求（音频URL）"""
        request = VisemeRequest(wav_url="http://example.com/test.wav")
        assert request.wav_url == "http://example.com/test.wav"
        assert request.text is None

    def test_knowledge_search_request_valid(self):
        """测试有效的知识库搜索请求"""
        request = KnowledgeSearchRequest(
            query="派蒙是谁",
            topk=5,
            min_score=0.5
        )
        assert request.query == "派蒙是谁"
        assert request.topk == 5
        assert request.min_score == 0.5

    def test_knowledge_search_request_invalid_topk(self):
        """测试无效的topk参数"""
        with pytest.raises(ValidationError):
            KnowledgeSearchRequest(
                query="测试",
                topk=0  # 应该 >= 1
            )

        with pytest.raises(ValidationError):
            KnowledgeSearchRequest(
                query="测试",
                topk=25  # 应该 <= 20
            )


class TestResponseModels:
    """响应模型测试"""

    def test_dialog_response_valid(self):
        """测试有效的对话响应"""
        trace = DialogTrace(
            policy=PolicyType.CHITCHAT,
            kb_sources=[],
            processing_time=100.5
        )

        response = DialogResponse(
            reply="你好，旅行者！",
            emotion=EmotionType.HAPPY,
            trace=trace,
            trace_id="test_trace"
        )

        assert response.reply == "你好，旅行者！"
        assert response.emotion == EmotionType.HAPPY
        assert response.trace.policy == PolicyType.CHITCHAT
        assert response.ok is True

    def test_viseme_response_valid(self):
        """测试有效的口型响应"""
        visemes = [
            VisemeFrame(t=0.1, id=VisemeType.A, w=0.8),
            VisemeFrame(t=0.2, id=VisemeType.I, w=0.6),
            VisemeFrame(t=0.3, id=VisemeType.M, w=0.9)
        ]

        response = VisemeResponse(
            visemes=visemes,
            src="rhubarb",
            duration=2.5,
            trace_id="test_trace"
        )

        assert len(response.visemes) == 3
        assert response.src == "rhubarb"
        assert response.duration == 2.5

    def test_knowledge_search_response_valid(self):
        """测试有效的知识库搜索响应"""
        hits = [
            KnowledgeSource(
                text="派蒙是旅行者的向导",
                source=SourceType.CUSTOM,
                score=0.95,
                metadata={"category": "character"}
            )
        ]

        response = KnowledgeSearchResponse(
            hits=hits,
            embedding_model="bge-m3",
            total_count=10,
            trace_id="test_trace"
        )

        assert len(response.hits) == 1
        assert response.hits[0].score == 0.95
        assert response.embedding_model == "bge-m3"


class TestCommonModels:
    """通用模型测试"""

    def test_viseme_frame_valid(self):
        """测试口型帧模型"""
        frame = VisemeFrame(
            t=0.123,
            id=VisemeType.A,
            w=0.8
        )
        assert frame.t == 0.123
        assert frame.id == VisemeType.A
        assert frame.w == 0.8

    def test_viseme_frame_invalid_weight(self):
        """测试无效的权重值"""
        with pytest.raises(ValidationError):
            VisemeFrame(
                t=0.1,
                id=VisemeType.A,
                w=1.5  # 应该 <= 1.0
            )

        with pytest.raises(ValidationError):
            VisemeFrame(
                t=0.1,
                id=VisemeType.A,
                w=-0.1  # 应该 >= 0.0
            )

    def test_knowledge_source_valid(self):
        """测试知识库来源模型"""
        source = KnowledgeSource(
            text="测试知识内容",
            source=SourceType.PUBLIC,
            score=0.85,
            metadata={"category": "test"}
        )
        assert source.text == "测试知识内容"
        assert source.source == SourceType.PUBLIC
        assert source.score == 0.85

    def test_knowledge_source_invalid_score(self):
        """测试无效的分数值"""
        with pytest.raises(ValidationError):
            KnowledgeSource(
                text="测试",
                source=SourceType.PUBLIC,
                score=1.5  # 应该 <= 1.0
            )

    def test_dialog_trace_valid(self):
        """测试对话追踪模型"""
        kb_sources = [
            KnowledgeSource(
                text="测试来源",
                source=SourceType.PUBLIC,
                score=0.9
            )
        ]

        trace = DialogTrace(
            policy=PolicyType.FACT,
            kb_sources=kb_sources,
            processing_time=250.5,
            metadata={"test": "value"}
        )

        assert trace.policy == PolicyType.FACT
        assert len(trace.kb_sources) == 1
        assert trace.processing_time == 250.5
        assert trace.metadata["test"] == "value"


class TestEnumTypes:
    """枚举类型测试"""

    def test_emotion_type_values(self):
        """测试情绪类型枚举值"""
        assert EmotionType.HAPPY == "happy"
        assert EmotionType.CURIOUS == "curious"
        assert EmotionType.THINKING == "thinking"

    def test_policy_type_values(self):
        """测试策略类型枚举值"""
        assert PolicyType.CHITCHAT == "chitchat"
        assert PolicyType.HELP == "help"
        assert PolicyType.FACT == "fact"
        assert PolicyType.STORY == "story"

    def test_viseme_type_values(self):
        """测试口型类型枚举值"""
        assert VisemeType.A == "A"
        assert VisemeType.E == "E"
        assert VisemeType.X == "X"  # 静音

    def test_source_type_values(self):
        """测试来源类型枚举值"""
        assert SourceType.PUBLIC == "public"
        assert SourceType.CUSTOM == "custom"
        assert SourceType.GENERATED == "generated"