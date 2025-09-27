"""
FishAudio TTS Provider Implementation
基于FishAudio API的TTS实现，支持流式合成和音素标记
"""

import asyncio
import base64
import json
import re
import time
from typing import AsyncGenerator, Dict, List, Optional, Union
import logging

import numpy as np
try:
    from fish_audio_sdk import Session, TTSRequest as FishTTSRequest, Prosody
    from fish_audio_sdk.exceptions import HttpCodeErr
    FISH_SDK_AVAILABLE = True
except ImportError:
    FISH_SDK_AVAILABLE = False
    Session = None
    FishTTSRequest = None
    Prosody = None
    HttpCodeErr = Exception

from .tts_provider import (
    BaseTTSProvider,
    TTSProviderType,
    TTSRequest,
    AudioChunk,
    PhonemeMarker,
    TTSAudioStreamMessage,
    TTSMarkerStreamMessage,
    TTSEndStreamMessage,
    TTSErrorStreamMessage,
    AudioFormat
)

logger = logging.getLogger(__name__)


class FishAudioTTSProvider(BaseTTSProvider):
    """FishAudio TTS Provider"""

    def __init__(self, api_key: str, default_model_id: str = "304d6864fe86478c922e72a7b41973f7"):
        super().__init__(TTSProviderType.FISHAUDIO)

        if not FISH_SDK_AVAILABLE:
            raise ImportError("fish-audio-sdk is not available. Please install it.")

        self.api_key = api_key
        self.default_model_id = default_model_id
        self.session: Optional[Session] = None
        self.max_retries = 3
        self.retry_delay = 1.0

        # 中文音素映射表（扩展版）
        self.phoneme_map = {
            # 基础汉字
            "派": ["P", "AI"], "蒙": ["M", "ENG"], "你": ["N", "I"], "好": ["H", "AO"],
            "旅": ["L", "YU"], "行": ["X", "ING"], "者": ["ZH", "E"], "今": ["J", "IN"],
            "天": ["T", "IAN"], "什": ["SH", "EN"], "么": ["M", "E"], "想": ["X", "IANG"],
            "吃": ["CH", "I"], "的": ["D", "E"], "东": ["D", "ONG"], "西": ["X", "I"],

            # 常用字扩展
            "我": ["W", "O"], "是": ["SH", "I"], "在": ["Z", "AI"], "有": ["Y", "OU"],
            "不": ["B", "U"], "了": ["L", "E"], "就": ["J", "IU"], "人": ["R", "EN"],
            "都": ["D", "OU"], "一": ["Y", "I"], "会": ["H", "UI"], "说": ["SH", "UO"],
            "他": ["T", "A"], "她": ["T", "A"], "它": ["T", "A"], "们": ["M", "EN"],
            "来": ["L", "AI"], "去": ["Q", "U"], "到": ["D", "AO"], "从": ["C", "ONG"],
            "这": ["ZH", "E"], "那": ["N", "A"], "里": ["L", "I"], "上": ["SH", "ANG"],
            "下": ["X", "IA"], "中": ["ZH", "ONG"], "内": ["N", "EI"], "外": ["W", "AI"],
            "前": ["Q", "IAN"], "后": ["H", "OU"], "左": ["Z", "UO"], "右": ["Y", "OU"],

            # 数字
            "零": ["L", "ING"], "一": ["Y", "I"], "二": ["E", "R"], "三": ["S", "AN"],
            "四": ["S", "I"], "五": ["W", "U"], "六": ["L", "IU"], "七": ["Q", "I"],
            "八": ["B", "A"], "九": ["J", "IU"], "十": ["SH", "I"],

            # 问候和常用词
            "请": ["Q", "ING"], "谢": ["X", "IE"], "对": ["D", "UI"], "起": ["Q", "I"],
            "再": ["Z", "AI"], "见": ["J", "IAN"], "早": ["Z", "AO"], "晚": ["W", "AN"],
            "安": ["A", "N"], "晚": ["W", "AN"], "午": ["W", "U"], "夜": ["Y", "E"],

            # 英文字母
            "A": ["EI"], "B": ["BI"], "C": ["SI"], "D": ["DI"], "E": ["I"],
            "F": ["EF"], "G": ["JI"], "H": ["EICH"], "I": ["AI"], "J": ["JEI"],
            "K": ["KEI"], "L": ["EL"], "M": ["EM"], "N": ["EN"], "O": ["OU"],
            "P": ["PI"], "Q": ["KYU"], "R": ["AR"], "S": ["ES"], "T": ["TI"],
            "U": ["YU"], "V": ["VI"], "W": ["DABLYU"], "X": ["EKS"], "Y": ["WAI"], "Z": ["ZI"]
        }

        self._init_session()

    def _init_session(self):
        """初始化FishAudio会话"""
        try:
            if not self.api_key:
                raise ValueError("FishAudio API key is required")
            self.session = Session(self.api_key)
            self.mark_healthy()
        except Exception as e:
            logger.error(f"Failed to initialize FishAudio session: {e}")
            self.mark_unhealthy(str(e))

    async def check_health(self) -> bool:
        """检查FishAudio API健康状态"""
        if not self.session:
            return False

        try:
            # 尝试一个简单的请求来测试API可用性
            test_request = FishTTSRequest(
                text="测试",
                reference_id=self.default_model_id,
                format="pcm",
                chunk_length=100
            )

            # 获取第一个chunk来验证API是否可用
            for chunk in self.session.tts(test_request):
                break  # 只需要第一个chunk来验证

            self.mark_healthy()
            return True
        except Exception as e:
            logger.error(f"FishAudio health check failed: {e}")
            self.mark_unhealthy(str(e))
            return False

    def _preprocess_text(self, text: str, emotions: Optional[str] = None) -> str:
        """预处理文本，添加情感标记和停顿"""
        processed_text = text.strip()

        # 添加情感标记
        if emotions:
            processed_text = f"({emotions}) {processed_text}"

        # 处理换行为轻停顿
        processed_text = re.sub(r'\n+', ' ', processed_text)

        # 在标点符号后添加适当停顿
        processed_text = re.sub(r'([。！？])', r'\1 ', processed_text)
        processed_text = re.sub(r'([，；：])', r'\1', processed_text)

        return processed_text

    def _generate_phoneme_markers(self, text: str, audio_duration: float) -> List[PhonemeMarker]:
        """根据文本生成音素标记"""
        markers = []
        char_count = len([c for c in text if c.strip() and c not in "，。！？；："])

        if char_count == 0:
            return markers

        # 估算每个字符的时长
        char_duration = audio_duration / char_count
        current_time = 0.0

        for char in text:
            if char.isspace():
                continue
            elif char in "，。！？；：":
                # 标点符号添加静音标记
                markers.append(PhonemeMarker(
                    phoneme="SIL",
                    timestamp=current_time,
                    duration=char_duration * 0.5,
                    confidence=1.0
                ))
                current_time += char_duration * 0.5
            elif char in self.phoneme_map:
                # 有映射的字符
                phonemes = self.phoneme_map[char]
                phoneme_duration = char_duration / len(phonemes)

                for phoneme in phonemes:
                    markers.append(PhonemeMarker(
                        phoneme=phoneme,
                        timestamp=current_time,
                        duration=phoneme_duration,
                        confidence=0.9
                    ))
                    current_time += phoneme_duration
            else:
                # 其他字符使用通用音素
                markers.append(PhonemeMarker(
                    phoneme="X",
                    timestamp=current_time,
                    duration=char_duration,
                    confidence=0.7
                ))
                current_time += char_duration

        return markers

    def _convert_audio_format(self, audio_data: bytes,
                             source_format: str, target_format: AudioFormat,
                             sample_rate: int) -> str:
        """转换音频格式并编码为base64"""
        if target_format == AudioFormat.PCM:
            # PCM格式直接返回base64编码
            return base64.b64encode(audio_data).decode('utf-8')
        elif target_format == AudioFormat.WAV:
            # 如果是WAV，可能需要添加WAV头
            return base64.b64encode(audio_data).decode('utf-8')
        else:
            # 其他格式暂时直接返回
            return base64.b64encode(audio_data).decode('utf-8')

    async def _synthesize_with_retry(self, fish_request: FishTTSRequest) -> bytes:
        """带重试的语音合成"""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                audio_data = b""
                for chunk in self.session.tts(fish_request):
                    audio_data += chunk
                return audio_data
            except HttpCodeErr as e:
                last_exception = e
                if e.status_code == 429:  # Rate limit
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited, retrying in {delay}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                elif e.status_code == 401:
                    raise Exception("Invalid FishAudio API key")
                else:
                    logger.error(f"HTTP error {e.status_code}: {e}")
                    if attempt == self.max_retries - 1:
                        raise e
                    await asyncio.sleep(self.retry_delay)
            except Exception as e:
                last_exception = e
                logger.error(f"Synthesis error (attempt {attempt + 1}): {e}")
                if attempt == self.max_retries - 1:
                    raise e
                await asyncio.sleep(self.retry_delay)

        if last_exception:
            raise last_exception

    async def synthesize_stream(
        self,
        request: TTSRequest,
        session_id: str,
        trace_id: str
    ) -> AsyncGenerator[Union[TTSAudioStreamMessage, TTSMarkerStreamMessage,
                             TTSEndStreamMessage, TTSErrorStreamMessage], None]:
        """流式语音合成"""

        if not self.session:
            yield TTSErrorStreamMessage(
                code="SESSION_NOT_INITIALIZED",
                message="FishAudio session not initialized",
                session_id=session_id,
                trace_id=trace_id
            )
            return

        self.start_timing()

        try:
            # 预处理文本
            processed_text = self._preprocess_text(request.text, request.emotions)

            # 构建FishAudio请求
            fish_format = "pcm" if request.format == AudioFormat.PCM else request.format.value
            prosody = None
            if request.speed != 1.0 or request.volume != 0.0:
                prosody = Prosody(speed=request.speed, volume=int(request.volume))

            fish_request = FishTTSRequest(
                text=processed_text,
                reference_id=request.reference_id or self.default_model_id,
                format=fish_format,
                sample_rate=request.sample_rate,
                chunk_length=request.chunk_length,
                normalize=True,
                latency="balanced",
                temperature=request.temperature,
                top_p=request.top_p,
                prosody=prosody
            )

            # 估算音频时长（用于音素标记）
            estimated_duration = len(processed_text) / 4.5 / request.speed
            estimated_duration = max(estimated_duration, 0.1)

            # 生成音素标记
            phoneme_markers = self._generate_phoneme_markers(
                processed_text, estimated_duration
            )

            # 流式合成
            chunk_id = 0
            total_audio_data = b""
            marker_index = 0
            current_time = 0.0

            # 分批处理音频流
            chunk_size = 1024 * 4  # 4KB per chunk for streaming

            async for audio_chunk in self._stream_synthesis(fish_request):
                total_audio_data += audio_chunk

                # 计算当前块的时长
                samples_in_chunk = len(audio_chunk) // 2  # 16-bit PCM
                chunk_duration = samples_in_chunk / request.sample_rate

                # 创建音频消息
                audio_base64 = self._convert_audio_format(
                    audio_chunk, fish_format, request.format, request.sample_rate
                )

                audio_msg = TTSAudioStreamMessage(
                    chunk=AudioChunk(
                        pcm_base64=audio_base64,
                        chunk_id=chunk_id,
                        sample_rate=request.sample_rate,
                        duration_ms=chunk_duration * 1000
                    ),
                    session_id=session_id,
                    trace_id=trace_id
                )
                yield audio_msg

                # 发送对应时间范围内的音素标记
                chunk_end_time = current_time + chunk_duration
                while (marker_index < len(phoneme_markers) and
                       phoneme_markers[marker_index].timestamp < chunk_end_time):
                    marker_msg = TTSMarkerStreamMessage(
                        marker=phoneme_markers[marker_index],
                        session_id=session_id,
                        trace_id=trace_id
                    )
                    yield marker_msg
                    marker_index += 1

                chunk_id += 1
                current_time = chunk_end_time

                # 模拟流式延迟
                await asyncio.sleep(0.01)

            # 发送剩余的音素标记
            while marker_index < len(phoneme_markers):
                marker_msg = TTSMarkerStreamMessage(
                    marker=phoneme_markers[marker_index],
                    session_id=session_id,
                    trace_id=trace_id
                )
                yield marker_msg
                marker_index += 1

            # 计算实际音频时长
            total_samples = len(total_audio_data) // 2  # 16-bit PCM
            actual_duration = total_samples / request.sample_rate
            rtf = self.get_rtf(actual_duration)

            # 发送结束消息
            end_msg = TTSEndStreamMessage(
                duration=actual_duration,
                total_chunks=chunk_id,
                rtf=rtf,
                session_id=session_id,
                trace_id=trace_id
            )
            yield end_msg

            # 记录性能指标
            logger.info(f"FishAudio synthesis completed: duration={actual_duration:.2f}s, "
                       f"chunks={chunk_id}, RTF={rtf:.3f}")

        except Exception as e:
            logger.error(f"FishAudio synthesis error: {e}")
            yield TTSErrorStreamMessage(
                code="SYNTHESIS_ERROR",
                message=str(e),
                session_id=session_id,
                trace_id=trace_id
            )

    async def _stream_synthesis(self, fish_request: FishTTSRequest) -> AsyncGenerator[bytes, None]:
        """异步流式合成音频"""
        try:
            # 在线程池中执行同步的FishAudio API调用
            loop = asyncio.get_event_loop()

            def sync_synthesis():
                audio_chunks = []
                for chunk in self.session.tts(fish_request):
                    audio_chunks.append(chunk)
                return audio_chunks

            # 执行合成
            audio_chunks = await loop.run_in_executor(None, sync_synthesis)

            # 逐块yield音频数据
            for chunk in audio_chunks:
                yield chunk
                await asyncio.sleep(0)  # 让出控制权

        except Exception as e:
            logger.error(f"Stream synthesis error: {e}")
            raise e