"""
对话有限状态机服务
实现四策略对话：闲聊/求助/事实问答/故事
状态流转：idle → listen → asr → nlu → plan → (kb?) → draft → style_fuse → safety → tts → stream
"""

import time
import asyncio
import uuid
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from ..core.config import get_settings
from ..models import (
    DialogRequest,
    DialogResponse,
    DialogTrace,
    EmotionType,
    PolicyType,
    KnowledgeSource,
    KnowledgeSearchRequest,
    SafetyCategory,
    SafetyLevel
)
from ..services.nlu_classifier import get_nlu_classifier, IntentMatch
from ..services.response_templates import get_response_template_service, ResponseContext
from ..services.mock_kb import get_knowledge_service
from ..services.style_fuse import get_style_fuse_service
from ..services.safety_service import get_safety_service
from ..services.tts_provider import TTSRequest, AudioFormat
from ..services.rejection_templates import get_rejection_template_service


class FSMState(str, Enum):
    """FSM状态枚举"""
    IDLE = "idle"
    LISTEN = "listen"
    ASR = "asr"
    NLU = "nlu"
    PLAN = "plan"
    KB_SEARCH = "kb_search"
    DRAFT = "draft"
    STYLE_FUSE = "style_fuse"
    SAFETY = "safety"
    TTS = "tts"
    STREAM = "stream"
    ERROR = "error"


@dataclass
class FSMTransition:
    """状态转换记录"""
    from_state: FSMState
    to_state: FSMState
    timestamp: float
    trigger: str
    metadata: Optional[Dict] = None


@dataclass
class FSMContext:
    """FSM上下文"""
    session_id: str
    trace_id: str
    current_state: FSMState
    request: DialogRequest
    intent_match: Optional[IntentMatch] = None
    policy: Optional[PolicyType] = None
    emotion: Optional[EmotionType] = None
    kb_sources: List[KnowledgeSource] = None
    draft_response: Optional[str] = None
    final_response: Optional[str] = None
    transitions: List[FSMTransition] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.kb_sources is None:
            self.kb_sources = []
        if self.transitions is None:
            self.transitions = []
        if self.metadata is None:
            self.metadata = {}


class DialogFSMService:
    """对话有限状态机服务"""

    def __init__(self):
        self.settings = get_settings()
        self.nlu_classifier = get_nlu_classifier()
        self.response_service = get_response_template_service()
        self.knowledge_service = get_knowledge_service()
        self.safety_service = get_safety_service()
        self.rejection_service = get_rejection_template_service()

        # StyleFuse 服务按需使用（在状态中动态获取）

        self.session_contexts: Dict[str, Dict] = {}

    def _create_transition(self, context: FSMContext, to_state: FSMState, trigger: str, metadata: Optional[Dict] = None) -> FSMTransition:
        """创建状态转换记录"""
        transition = FSMTransition(
            from_state=context.current_state,
            to_state=to_state,
            timestamp=time.time(),
            trigger=trigger,
            metadata=metadata or {}
        )
        context.transitions.append(transition)
        context.current_state = to_state
        return transition

    def _should_use_kb(self, context: FSMContext) -> bool:
        """判断是否应该使用知识库"""
        # 检查配置是否启用KB
        if not self.settings.features.kb.enabled:
            return False

        # 检查请求标志
        if not context.request.flags.get("kb", False):
            return False

        # 只有事实问答策略使用KB
        return context.policy == PolicyType.FACT

    async def _execute_nlu_state(self, context: FSMContext) -> FSMState:
        """执行NLU状态"""
        intent_match = self.nlu_classifier.classify_intent(context.request.text)
        context.intent_match = intent_match
        context.policy = intent_match.policy

        # 获取策略对应的情绪
        context.emotion = self.response_service.get_policy_emotion(
            context.policy,
            context.request.text
        )

        self._create_transition(
            context,
            FSMState.PLAN,
            "nlu_completed",
            {
                "policy": context.policy.value,
                "confidence": intent_match.confidence,
                "matched_patterns": intent_match.matched_patterns
            }
        )
        return FSMState.PLAN

    async def _execute_plan_state(self, context: FSMContext) -> FSMState:
        """执行计划状态"""
        # 根据策略决定下一步
        if self._should_use_kb(context):
            self._create_transition(context, FSMState.KB_SEARCH, "kb_required")
            return FSMState.KB_SEARCH
        else:
            self._create_transition(context, FSMState.DRAFT, "direct_to_draft")
            return FSMState.DRAFT

    async def _execute_kb_search_state(self, context: FSMContext) -> FSMState:
        """执行知识库搜索状态"""
        try:
            # 构建知识库搜索请求
            kb_request = KnowledgeSearchRequest(
                query=context.request.text,
                topk=3,
                min_score=0.3
            )

            # 执行知识库搜索
            timeout = self.settings.dialog.fsm.kb_search_timeout
            if timeout and timeout > 0:
                kb_response = await asyncio.wait_for(
                    self.knowledge_service.search_knowledge(kb_request, context.trace_id),
                    timeout=timeout
                )
            else:
                kb_response = await self.knowledge_service.search_knowledge(kb_request, context.trace_id)

            context.kb_sources = kb_response.hits

            self._create_transition(
                context,
                FSMState.DRAFT,
                "kb_search_completed",
                {
                    "kb_hits": len(context.kb_sources),
                    "search_query": kb_request.query
                }
            )
            return FSMState.DRAFT

        except Exception as e:
            # KB搜索失败，继续执行但不使用KB结果
            context.metadata["kb_error"] = str(e)
            self._create_transition(
                context,
                FSMState.DRAFT,
                "kb_search_failed",
                {"error": str(e)}
            )
            return FSMState.DRAFT

    async def _execute_draft_state(self, context: FSMContext) -> FSMState:
        """执行草稿状态"""
        # 构建响应上下文
        response_context = ResponseContext(
            request=context.request,
            policy=context.policy,
            emotion=context.emotion,
            kb_sources=context.kb_sources,
            session_context=self.session_contexts.get(context.session_id),
            nlu_metadata=context.intent_match.metadata if context.intent_match else None
        )

        # 生成回复草稿
        context.draft_response = self.response_service.generate_response(response_context)

        self._create_transition(
            context,
            FSMState.STYLE_FUSE,
            "draft_completed",
            {"draft_length": len(context.draft_response) if context.draft_response else 0}
        )
        return FSMState.STYLE_FUSE

    async def _execute_style_fuse_state(self, context: FSMContext) -> FSMState:
        """执行风格融合状态（集成 Module 04 StyleFuse）"""
        enabled = self.settings.dialog.fsm.enable_style_fuse
        try:
            if enabled and context.draft_response:
                from .style_fuse import get_style_fuse_service
                sf = get_style_fuse_service()
                # 评估前后风格指标
                metrics_before = sf.evaluate(context.draft_response)
                fused = sf.apply(context.draft_response)
                metrics_after = sf.evaluate(fused)
                context.final_response = fused
                self._create_transition(
                    context,
                    FSMState.SAFETY,
                    "style_fuse_applied",
                    {
                        "before": {
                            "avg_length": metrics_before.avg_sentence_length,
                            "question_ratio": metrics_before.question_ratio,
                            "exclamation_ratio": metrics_before.exclamation_ratio,
                            "mood_particle_density": metrics_before.mood_particle_density,
                            "sentence_count": metrics_before.sentence_count,
                            "total_length": metrics_before.total_length,
                        },
                        "after": {
                            "avg_length": metrics_after.avg_sentence_length,
                            "question_ratio": metrics_after.question_ratio,
                            "exclamation_ratio": metrics_after.exclamation_ratio,
                            "mood_particle_density": metrics_after.mood_particle_density,
                            "sentence_count": metrics_after.sentence_count,
                            "total_length": metrics_after.total_length,
                        },
                    }
                )
            else:
                context.final_response = context.draft_response or "派蒙不知道该说什么呢..."
                self._create_transition(
                    context,
                    FSMState.SAFETY,
                    "style_fuse_bypassed",
                    {"reason": "disabled" if not enabled else "no_draft"}
                )
            return FSMState.SAFETY
        except Exception as e:
            context.final_response = context.draft_response or "派蒙不知道该说什么呢..."
            context.metadata["style_fuse_error"] = str(e)
            self._create_transition(
                context,
                FSMState.SAFETY,
                "style_fuse_failed",
                {"error": str(e)}
            )
            return FSMState.SAFETY

    async def _execute_safety_state(self, context: FSMContext) -> FSMState:
        """执行安全检查状态（Module 05 实现）"""
        enabled = self.settings.dialog.fsm.enable_safety
        safety_config = self.settings.safety

        if not enabled or not safety_config.enabled:
            # 安全检查未启用，直接通过
            self._create_transition(
                context,
                FSMState.TTS,
                "safety_disabled",
                {"safety_enabled": False}
            )
            return FSMState.TTS

        try:
            # 执行安全检查
            text_to_check = context.final_response or context.draft_response or ""
            if not text_to_check:
                # 没有内容需要检查，直接通过
                self._create_transition(
                    context,
                    FSMState.TTS,
                    "safety_no_content",
                    {"safety_enabled": True, "reason": "no_content"}
                )
                return FSMState.TTS

            # 调用安全服务检查
            safety_result = self.safety_service.check_safety(text_to_check)

            # 记录安全检查结果到上下文
            context.metadata["safety_result"] = {
                "level": safety_result.level.value,
                "blocked": safety_result.blocked,
                "category": safety_result.category.value if safety_result.category else None,
                "confidence": safety_result.confidence,
                "processing_time": safety_result.processing_time,
                "evidence_count": len(safety_result.evidence)
            }

            if safety_result.blocked:
                # 内容被阻断，生成拒绝回复
                session_ctx = self.session_contexts.get(context.session_id, {})
                conversation_count = session_ctx.get("message_count", 0)
                user_message_length = len(context.request.text)

                # 检查是否为连续触发（升级提醒）
                recent_blocks = session_ctx.get("recent_safety_blocks", [])
                current_time = time.time()
                # 清理5分钟前的记录
                recent_blocks = [t for t in recent_blocks if current_time - t < 300]

                if self.rejection_service.get_escalation_message and len(recent_blocks) >= 1:
                    # 使用升级提醒
                    rejection_message = self.rejection_service.get_escalation_message(len(recent_blocks) + 1)
                else:
                    # 使用常规拒绝模板
                    rejection_message = self.rejection_service.get_context_aware_message(
                        category=safety_result.category,
                        level=safety_result.level,
                        user_message_length=user_message_length,
                        conversation_count=conversation_count
                    )

                # 更新最终回复为拒绝消息
                context.final_response = rejection_message

                # 记录安全阻断历史
                recent_blocks.append(current_time)
                session_ctx["recent_safety_blocks"] = recent_blocks[-5:]  # 只保留最近5次

                # 设置对应的情绪
                if safety_result.category == SafetyCategory.HARASSMENT:
                    context.emotion = EmotionType.CONFUSED
                elif safety_result.category in [SafetyCategory.EXPLICIT, SafetyCategory.MINOR_UNSAFE]:
                    context.emotion = EmotionType.CONFUSED
                elif safety_result.category == SafetyCategory.VIOLENCE:
                    context.emotion = EmotionType.CONFUSED
                else:
                    context.emotion = EmotionType.NEUTRAL

                self._create_transition(
                    context,
                    FSMState.TTS,
                    "safety_blocked",
                    {
                        "safety_level": safety_result.level.value,
                        "safety_category": safety_result.category.value if safety_result.category else None,
                        "safety_confidence": safety_result.confidence,
                        "evidence_count": len(safety_result.evidence),
                        "rejection_type": "escalation" if len(recent_blocks) > 0 else "normal"
                    }
                )
            else:
                # 内容安全，继续正常流程
                if safety_result.level == SafetyLevel.WARNING:
                    # 警告级别，记录但不阻断
                    context.metadata["safety_warning"] = {
                        "category": safety_result.category.value if safety_result.category else None,
                        "confidence": safety_result.confidence
                    }

                self._create_transition(
                    context,
                    FSMState.TTS,
                    "safety_passed",
                    {
                        "safety_level": safety_result.level.value,
                        "safety_confidence": safety_result.confidence,
                        "processing_time": safety_result.processing_time
                    }
                )

            return FSMState.TTS

        except Exception as e:
            # 安全检查异常，记录错误但不阻断流程
            context.metadata["safety_error"] = str(e)
            self._create_transition(
                context,
                FSMState.TTS,
                "safety_error",
                {"error": str(e), "fallback": "passed"}
            )
            return FSMState.TTS

    async def _execute_tts_state(self, context: FSMContext) -> FSMState:
        """执行TTS状态，生成语音和音素标记"""
        try:
            # 获取最终回复文本
            response_text = context.final_response
            if not response_text:
                self._create_transition(
                    context,
                    FSMState.STREAM,
                    "tts_skip_empty",
                    {"error": "No response text for TTS", "tts_enabled": False}
                )
                return FSMState.STREAM

            # 获取TTS配置
            settings = get_settings()
            tts_config = settings.mock.tts

            # 构建TTS请求
            tts_request = TTSRequest(
                text=response_text,
                voice=tts_config.default_voice,
                speed=tts_config.default_speed,
                volume=tts_config.default_volume,
                format=AudioFormat.PCM,
                sample_rate=tts_config.sample_rate,
                chunk_length=tts_config.chunk_length,
                temperature=tts_config.default_temperature,
                top_p=tts_config.default_top_p,
                # 从上下文中获取情感信息
                emotions=context.metadata.get("emotion_hint")
            )

            # 检查是否启用TTS
            if not tts_config.enable_phoneme_markers:
                # 如果禁用TTS，直接转向流状态
                self._create_transition(
                    context,
                    FSMState.STREAM,
                    "tts_disabled",
                    {"tts_enabled": False, "text_only": True}
                )
                return FSMState.STREAM

            # 记录TTS阶段开始
            tts_start_time = time.time()

            # 在context中存储TTS请求信息，供WebSocket使用
            context.metadata["tts_request"] = {
                "text": response_text,
                "voice": tts_request.voice,
                "speed": tts_request.speed,
                "volume": tts_request.volume,
                "format": tts_request.format.value,
                "sample_rate": tts_request.sample_rate,
                "emotions": tts_request.emotions,
                "chunk_length": tts_request.chunk_length
            }

            # 记录TTS准备就绪
            tts_duration = time.time() - tts_start_time
            self._create_transition(
                context,
                FSMState.STREAM,
                "tts_ready",
                {
                    "tts_enabled": True,
                    "preparation_time": tts_duration,
                    "text_length": len(response_text),
                    "estimated_audio_duration": len(response_text) / 4.5 / tts_request.speed
                }
            )
            return FSMState.STREAM

        except Exception as e:
            # TTS错误，记录错误并转向流状态
            self._create_transition(
                context,
                FSMState.STREAM,
                "tts_error",
                {"error": str(e), "tts_enabled": False, "fallback": "text_only"}
            )
            return FSMState.STREAM

    async def _execute_stream_state(self, context: FSMContext) -> FSMState:
        """执行流式输出状态（完成）"""
        self._create_transition(
            context,
            FSMState.IDLE,
            "response_completed"
        )
        return FSMState.IDLE

    async def _execute_state(self, context: FSMContext) -> FSMState:
        """执行当前状态的逻辑"""
        if context.current_state == FSMState.NLU:
            return await self._execute_nlu_state(context)
        elif context.current_state == FSMState.PLAN:
            return await self._execute_plan_state(context)
        elif context.current_state == FSMState.KB_SEARCH:
            return await self._execute_kb_search_state(context)
        elif context.current_state == FSMState.DRAFT:
            return await self._execute_draft_state(context)
        elif context.current_state == FSMState.STYLE_FUSE:
            return await self._execute_style_fuse_state(context)
        elif context.current_state == FSMState.SAFETY:
            return await self._execute_safety_state(context)
        elif context.current_state == FSMState.TTS:
            return await self._execute_tts_state(context)
        elif context.current_state == FSMState.STREAM:
            return await self._execute_stream_state(context)
        else:
            # 未知状态，转到错误状态
            self._create_transition(context, FSMState.ERROR, "unknown_state")
            return FSMState.ERROR

    def _update_session_context(self, context: FSMContext):
        """更新会话上下文"""
        if context.session_id not in self.session_contexts:
            self.session_contexts[context.session_id] = {}

        session_ctx = self.session_contexts[context.session_id]
        session_ctx.update({
            "last_input": context.request.text,
            "last_policy": context.policy,
            "last_emotion": context.emotion,
            "message_count": session_ctx.get("message_count", 0) + 1,
            "last_intent_confidence": context.intent_match.confidence if context.intent_match else 0.0
        })

    async def generate_dialog(self, request: DialogRequest, trace_id: str) -> DialogResponse:
        """生成对话响应"""
        start_time = time.time()

        # 创建FSM上下文
        context = FSMContext(
            session_id=request.session_id,
            trace_id=trace_id,
            current_state=FSMState.LISTEN,
            request=request
        )

        try:
            # 初始转换到NLU状态
            self._create_transition(context, FSMState.NLU, "dialog_started")

            # 执行状态机直到完成或错误
            max_transitions = self.settings.dialog.fsm.max_transitions or 20  # 防止无限循环
            transition_count = 0

            while context.current_state not in [FSMState.IDLE, FSMState.ERROR] and transition_count < max_transitions:
                next_state = await self._execute_state(context)
                transition_count += 1

                # 防止死循环
                if next_state == context.current_state:
                    break

            # 检查是否成功完成
            if context.current_state == FSMState.ERROR:
                # 错误回退
                context.final_response = "派蒙遇到了一些小问题呢...让我们重新开始吧！"
                context.policy = PolicyType.CHITCHAT
                context.emotion = EmotionType.CONFUSED

            # 更新会话上下文
            self._update_session_context(context)

            # 计算处理时间
            processing_time = (time.time() - start_time) * 1000

            # 构建追踪信息
            safety_result = context.metadata.get("safety_result")
            trace = DialogTrace(
                policy=context.policy or PolicyType.CHITCHAT,
                kb_sources=context.kb_sources,
                processing_time=processing_time,

                # 安全检查信息
                safety_level=SafetyLevel(safety_result["level"]) if safety_result else None,
                safety_category=SafetyCategory(safety_result["category"]) if safety_result and safety_result["category"] else None,
                safety_confidence=safety_result["confidence"] if safety_result else None,
                safety_blocked=safety_result["blocked"] if safety_result else None,
                safety_processing_time=safety_result["processing_time"] if safety_result else None,

                metadata={
                    "fsm_version": "1.0.0",
                    "session_context": self.session_contexts.get(context.session_id, {}),
                    "state_transitions": [
                        {
                            "from": t.from_state.value,
                            "to": t.to_state.value,
                            "trigger": t.trigger,
                            "timestamp": t.timestamp,
                            "metadata": t.metadata
                        }
                        for t in context.transitions
                    ],
                    "intent_match": asdict(context.intent_match) if context.intent_match else None,
                    "total_transitions": len(context.transitions),
                    # 包含完整的安全检查结果
                    "safety_details": safety_result
                }
            )

            return DialogResponse(
                reply=context.final_response or "派蒙暂时想不出怎么回复呢...",
                emotion=context.emotion or EmotionType.NEUTRAL,
                trace=trace,
                trace_id=trace_id
            )

        except Exception as e:
            # 异常处理
            processing_time = (time.time() - start_time) * 1000

            trace = DialogTrace(
                policy=PolicyType.CHITCHAT,
                kb_sources=[],
                processing_time=processing_time,

                # 异常情况下安全信息为空
                safety_level=None,
                safety_category=None,
                safety_confidence=None,
                safety_blocked=None,
                safety_processing_time=None,

                metadata={
                    "error": str(e),
                    "fsm_version": "1.0.0",
                    "error_state": context.current_state.value if context.current_state else "unknown"
                }
            )

            return DialogResponse(
                reply="派蒙遇到了意想不到的问题呢...要不我们换个话题吧！",
                emotion=EmotionType.CONFUSED,
                trace=trace,
                trace_id=trace_id
            )


# 单例实例
_dialog_fsm_service = None


def get_dialog_fsm_service() -> DialogFSMService:
    """获取对话FSM服务实例"""
    global _dialog_fsm_service
    if _dialog_fsm_service is None:
        _dialog_fsm_service = DialogFSMService()
    return _dialog_fsm_service
