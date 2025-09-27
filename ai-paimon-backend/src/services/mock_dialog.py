"""
对话生成Mock服务
模拟对话生成的业务逻辑
"""

import random
import time
from typing import Dict, List

from ..core.config import get_settings
from ..models import (
    DialogRequest,
    DialogResponse,
    DialogTrace,
    EmotionType,
    PolicyType,
    KnowledgeSource
)


class MockDialogService:
    """Mock对话服务"""

    def __init__(self):
        self.settings = get_settings()
        self.session_context: Dict[str, Dict] = {}

    def _get_policy(self, text: str) -> PolicyType:
        """根据输入文本确定对话策略"""
        text_lower = text.lower()

        if any(word in text_lower for word in ["怎么", "如何", "帮助", "问题"]):
            return PolicyType.HELP
        elif any(word in text_lower for word in ["什么", "为什么", "是否", "介绍"]):
            return PolicyType.FACT
        elif any(word in text_lower for word in ["故事", "传说", "历史", "过去"]):
            return PolicyType.STORY
        else:
            return PolicyType.CHITCHAT

    def _get_emotion(self, policy: PolicyType, text: str) -> EmotionType:
        """根据策略和文本确定情绪"""
        emotion_map = {
            PolicyType.CHITCHAT: [EmotionType.HAPPY, EmotionType.EXCITED],
            PolicyType.HELP: [EmotionType.THINKING, EmotionType.CURIOUS],
            PolicyType.FACT: [EmotionType.THINKING, EmotionType.NEUTRAL],
            PolicyType.STORY: [EmotionType.EXCITED, EmotionType.HAPPY]
        }

        if "?" in text or "？" in text:
            return EmotionType.CURIOUS

        return random.choice(emotion_map[policy])

    def _generate_reply(self, request: DialogRequest, policy: PolicyType, emotion: EmotionType) -> str:
        """生成回复文本"""
        templates = self.settings.mock.dialog.response_templates

        if policy == PolicyType.CHITCHAT:
            replies = [
                f"欸！旅行者说的话，派蒙听不太懂呢...不过听起来很有趣！",
                f"哇～{request.text}，这个派蒙知道！让派蒙想想怎么说呢～",
                f"唔...派蒙觉得旅行者说得对呢！不过派蒙还是有点不明白...",
                f"嘿嘿，旅行者今天也很有精神呢！派蒙也很开心！"
            ]
        elif policy == PolicyType.HELP:
            replies = [
                f"派蒙来帮助旅行者！首先呢，要这样做...然后那样做...最后就好了！",
                f"欸？旅行者遇到困难了吗？派蒙虽然帮不上什么大忙，但会一直陪着旅行者的！",
                f"让派蒙想想看...嗯嗯，派蒙觉得可以试试这个方法哦！"
            ]
        elif policy == PolicyType.FACT:
            replies = [
                f"关于这个问题，派蒙记得...嗯...好像是这样的！不过派蒙也不太确定...",
                f"哇！旅行者问了个很有意思的问题呢！派蒙知道一点点！",
                f"这个啊...派蒙在某个地方听说过！让派蒙努力回忆一下..."
            ]
        elif policy == PolicyType.STORY:
            replies = [
                f"哦哦！派蒙最喜欢听故事了！这个故事是这样的...很久很久以前...",
                f"欸嘿！派蒙知道一个相关的有趣故事！要听吗要听吗？",
                f"说到这个，派蒙想起了一个传说...虽然不知道是不是真的..."
            ]

        base_reply = random.choice(replies)

        # 添加语气词
        mood_words = ["呢", "呀", "啦", "哦", "嘛", "欸"]
        if not any(word in base_reply for word in mood_words):
            base_reply += random.choice(["呢！", "呀～", "哦！"])

        return base_reply

    def _get_mock_kb_sources(self, text: str, use_kb: bool) -> List[KnowledgeSource]:
        """生成Mock知识库检索结果"""
        if not use_kb:
            return []

        # 模拟知识库检索
        mock_sources = [
            KnowledgeSource(
                text="提瓦特大陆是七神共同统治的世界，每个神都有自己的国家...",
                source="public",
                score=0.85,
                metadata={"category": "lore", "region": "teyvat"}
            ),
            KnowledgeSource(
                text="派蒙是旅行者的向导和伙伴，虽然有时候有点贪吃...",
                source="custom",
                score=0.76,
                metadata={"category": "character", "name": "paimon"}
            )
        ]

        # 根据文本相关性返回
        if any(word in text for word in ["派蒙", "paimon"]):
            return [mock_sources[1]]
        elif any(word in text for word in ["提瓦特", "七神", "世界"]):
            return [mock_sources[0]]
        else:
            return random.sample(mock_sources, k=random.randint(0, 1))

    async def generate_dialog(self, request: DialogRequest, trace_id: str) -> DialogResponse:
        """生成对话响应"""
        start_time = time.time()

        # 确定对话策略
        policy = self._get_policy(request.text)

        # 确定情绪
        emotion = self._get_emotion(policy, request.text)

        # 检查是否使用知识库
        use_kb = request.flags.get("kb", False) and self.settings.features.kb.enabled

        # 获取知识库来源
        kb_sources = self._get_mock_kb_sources(request.text, use_kb)

        # 生成回复
        reply = self._generate_reply(request, policy, emotion)

        # 更新会话上下文
        if request.session_id not in self.session_context:
            self.session_context[request.session_id] = {}

        self.session_context[request.session_id].update({
            "last_input": request.text,
            "last_policy": policy,
            "last_emotion": emotion,
            "message_count": self.session_context[request.session_id].get("message_count", 0) + 1
        })

        # 计算处理时间
        processing_time = (time.time() - start_time) * 1000

        # 构建追踪信息
        trace = DialogTrace(
            policy=policy,
            kb_sources=kb_sources,
            processing_time=processing_time,
            metadata={
                "session_context": self.session_context[request.session_id],
                "mock_version": "0.1.0"
            }
        )

        return DialogResponse(
            reply=reply,
            emotion=emotion,
            trace=trace,
            trace_id=trace_id
        )


# 单例实例
_dialog_service = None


def get_dialog_service() -> MockDialogService:
    """获取对话服务实例"""
    global _dialog_service
    if _dialog_service is None:
        _dialog_service = MockDialogService()
    return _dialog_service