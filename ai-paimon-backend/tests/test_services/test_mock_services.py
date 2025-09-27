"""
Mock服务测试
"""

import pytest

from src.services.mock_dialog import get_dialog_service
from src.services.mock_viseme import get_viseme_service
from src.services.mock_kb import get_knowledge_service
from src.models import (
    DialogRequest,
    VisemeRequest,
    KnowledgeSearchRequest,
    PolicyType,
    EmotionType
)


class TestMockDialogService:
    """Mock对话服务测试"""

    def test_service_singleton(self):
        """测试服务单例模式"""
        service1 = get_dialog_service()
        service2 = get_dialog_service()
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_generate_dialog_chitchat(self):
        """测试闲聊策略"""
        service = get_dialog_service()
        request = DialogRequest(
            text="你好",
            session_id="test_session",
            flags={}
        )

        response = await service.generate_dialog(request, "test_trace_id")

        assert response.reply
        assert response.emotion in list(EmotionType)
        assert response.trace.policy == PolicyType.CHITCHAT
        assert response.trace_id == "test_trace_id"

    @pytest.mark.asyncio
    async def test_generate_dialog_help(self):
        """测试求助策略"""
        service = get_dialog_service()
        request = DialogRequest(
            text="怎么做这个任务",
            session_id="test_session",
            flags={}
        )

        response = await service.generate_dialog(request, "test_trace_id")

        assert response.trace.policy == PolicyType.HELP
        assert "帮助" in response.reply or "方法" in response.reply

    @pytest.mark.asyncio
    async def test_session_context(self):
        """测试会话上下文管理"""
        service = get_dialog_service()
        session_id = "context_test_session"

        # 第一次对话
        request1 = DialogRequest(
            text="你好",
            session_id=session_id,
            flags={}
        )
        await service.generate_dialog(request1, "trace1")

        # 检查会话上下文是否创建
        assert session_id in service.session_context
        context = service.session_context[session_id]
        assert context["message_count"] == 1

        # 第二次对话
        request2 = DialogRequest(
            text="再见",
            session_id=session_id,
            flags={}
        )
        await service.generate_dialog(request2, "trace2")

        # 检查消息计数更新
        assert context["message_count"] == 2


class TestMockVisemeService:
    """Mock口型服务测试"""

    def test_service_singleton(self):
        """测试服务单例模式"""
        service1 = get_viseme_service()
        service2 = get_viseme_service()
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_generate_viseme_with_text(self):
        """测试基于文本生成口型"""
        service = get_viseme_service()
        request = VisemeRequest(text="派蒙想吃好吃的")

        response = await service.generate_viseme_timeline(request, "test_trace_id")

        assert response.visemes
        assert response.duration > 0
        assert response.src == "rhubarb"
        assert response.trace_id == "test_trace_id"

        # 检查口型数据格式
        for viseme in response.visemes:
            assert 0 <= viseme.w <= 1
            assert viseme.t >= 0

    @pytest.mark.asyncio
    async def test_generate_viseme_with_wav_url(self):
        """测试基于音频URL生成口型"""
        service = get_viseme_service()
        request = VisemeRequest(wav_url="http://example.com/test.wav")

        response = await service.generate_viseme_timeline(request, "test_trace_id")

        assert response.visemes
        assert response.duration > 0

    @pytest.mark.asyncio
    async def test_generate_viseme_no_input(self):
        """测试无输入的异常处理"""
        service = get_viseme_service()
        request = VisemeRequest()

        with pytest.raises(ValueError):
            await service.generate_viseme_timeline(request, "test_trace_id")


class TestMockKnowledgeService:
    """Mock知识库服务测试"""

    def test_service_singleton(self):
        """测试服务单例模式"""
        service1 = get_knowledge_service()
        service2 = get_knowledge_service()
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_search_knowledge_relevant(self):
        """测试相关性搜索"""
        service = get_knowledge_service()
        request = KnowledgeSearchRequest(
            query="派蒙",
            topk=5
        )

        response = await service.search_knowledge(request, "test_trace_id")

        assert response.hits
        assert response.embedding_model == "bge-m3"
        assert response.total_count == len(service.knowledge_base)
        assert response.trace_id == "test_trace_id"

        # 检查是否返回了相关结果
        paimon_results = [hit for hit in response.hits if "派蒙" in hit.text]
        assert len(paimon_results) > 0

    @pytest.mark.asyncio
    async def test_search_knowledge_with_filters(self):
        """测试带过滤条件的搜索"""
        service = get_knowledge_service()
        request = KnowledgeSearchRequest(
            query="角色",
            topk=10,
            filters={"category": "character"}
        )

        response = await service.search_knowledge(request, "test_trace_id")

        # 检查返回结果是否符合过滤条件
        for hit in response.hits:
            assert hit.metadata.get("category") == "character"

    @pytest.mark.asyncio
    async def test_search_knowledge_min_score(self):
        """测试最小分数过滤"""
        service = get_knowledge_service()
        request = KnowledgeSearchRequest(
            query="测试查询不匹配任何内容xyzabc",
            topk=10,
            min_score=0.5
        )

        response = await service.search_knowledge(request, "test_trace_id")

        # 由于查询不匹配，高分数阈值应该返回很少或没有结果
        for hit in response.hits:
            assert hit.score >= 0.5