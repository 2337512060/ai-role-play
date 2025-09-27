"""
ASR语音识别Mock服务
模拟语音识别的业务逻辑
"""

import asyncio
import base64
import json
import random
import time
from typing import List, Optional

import numpy as np

from ..models.websocket import (
    ASRClientMessage,
    ASRVADMessage,
    ASRPartialMessage,
    ASRFinalMessage,
    Timestamp
)


class MockASRService:
    """Mock ASR服务"""

    def __init__(self):
        # 预设识别结果
        self.predefined_texts = [
            "你好派蒙",
            "今天天气怎么样",
            "派蒙想吃好吃的",
            "我们去冒险吧",
            "原神启动",
            "提瓦特大陆真美丽",
            "七神保佑我们",
            "愿风神指引你",
            "愿岩神庇护你",
            "派蒙是最好的向导"
        ]

        # 会话状态
        self.sessions = {}

    def _decode_audio_chunk(self, pcm_base64: str) -> np.ndarray:
        """解码音频数据"""
        try:
            pcm_bytes = base64.b64decode(pcm_base64)
            # 假设16位PCM音频
            audio_data = np.frombuffer(pcm_bytes, dtype=np.int16)
            return audio_data
        except Exception:
            # 如果解码失败，返回随机音频数据用于模拟
            return np.random.randint(-1000, 1000, size=1024, dtype=np.int16)

    def _calculate_energy(self, audio_data: np.ndarray) -> float:
        """计算音频能量（RMS）"""
        if len(audio_data) == 0:
            return 0.0
        return float(np.sqrt(np.mean(audio_data.astype(np.float32) ** 2)))

    def _detect_vad(self, energy: float, threshold: float = 500.0) -> bool:
        """简单的VAD检测"""
        return energy > threshold

    def _get_partial_text(self, full_text: str, progress: float) -> str:
        """生成部分识别结果"""
        if progress <= 0:
            return ""

        words = full_text.split()
        if len(words) <= 1:
            # 对于单个词，按字符进度返回
            char_count = int(len(full_text) * progress)
            return full_text[:char_count]

        # 对于多个词，按词进度返回
        word_count = int(len(words) * progress)
        return "".join(words[:word_count])

    def _generate_timestamps(self, text: str, duration: float) -> List[Timestamp]:
        """生成时间戳对齐"""
        timestamps = []
        if not text:
            return timestamps

        words = text.split() if " " in text else list(text)
        if not words:
            return timestamps

        word_duration = duration / len(words)
        current_time = 0.0

        for word in words:
            start_time = current_time
            end_time = current_time + word_duration
            timestamps.append(Timestamp(
                start=round(start_time, 3),
                end=round(end_time, 3)
            ))
            current_time = end_time

        return timestamps

    async def process_audio_stream(self, websocket, session_id: str):
        """处理音频流"""
        # 初始化会话状态
        session_state = {
            "is_speaking": False,
            "audio_buffer": [],
            "start_time": None,
            "current_text": "",
            "recognition_progress": 0.0,
            "vad_threshold": 500.0
        }
        self.sessions[session_id] = session_state

        try:
            async for message in websocket.iter_text():
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")

                    if msg_type == "init":
                        # 初始化确认
                        await websocket.send_text(json.dumps({
                            "type": "init_ack",
                            "session_id": session_id,
                            "config": {
                                "sr": data.get("sr", 16000),
                                "lang": data.get("lang", "zh")
                            }
                        }))

                    elif msg_type == "chunk":
                        await self._process_audio_chunk(websocket, data, session_state)

                    elif msg_type == "end":
                        await self._finalize_recognition(websocket, session_state)

                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "code": "INVALID_JSON",
                        "message": "Invalid JSON format"
                    }))
                except Exception as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "code": "PROCESSING_ERROR",
                        "message": str(e)
                    }))

        finally:
            # 清理会话状态
            if session_id in self.sessions:
                del self.sessions[session_id]

    async def _process_audio_chunk(self, websocket, data: dict, session_state: dict):
        """处理音频块"""
        pcm_base64 = data.get("pcm_base64", "")
        timestamp = data.get("timestamp", time.time())

        # 解码音频数据
        audio_data = self._decode_audio_chunk(pcm_base64)
        energy = self._calculate_energy(audio_data)

        # VAD检测
        is_speech = self._detect_vad(energy, session_state["vad_threshold"])

        # 检测语音开始
        if is_speech and not session_state["is_speaking"]:
            session_state["is_speaking"] = True
            session_state["start_time"] = timestamp
            session_state["current_text"] = random.choice(self.predefined_texts)
            session_state["recognition_progress"] = 0.0

            # 发送VAD开始事件
            await websocket.send_text(json.dumps({
                "type": "vad",
                "event": "start",
                "timestamp": timestamp
            }))

        # 语音进行中
        elif is_speech and session_state["is_speaking"]:
            # 更新识别进度
            session_state["recognition_progress"] = min(
                session_state["recognition_progress"] + random.uniform(0.1, 0.3),
                0.9
            )

            # 生成部分识别结果
            partial_text = self._get_partial_text(
                session_state["current_text"],
                session_state["recognition_progress"]
            )

            if partial_text:
                await websocket.send_text(json.dumps({
                    "type": "partial",
                    "text": partial_text,
                    "final": False,
                    "confidence": round(random.uniform(0.7, 0.9), 2)
                }))

        # 检测语音结束
        elif not is_speech and session_state["is_speaking"]:
            await self._end_speech_segment(websocket, session_state, timestamp)

    async def _end_speech_segment(self, websocket, session_state: dict, end_timestamp: float):
        """结束语音段"""
        session_state["is_speaking"] = False

        # 发送VAD结束事件
        await websocket.send_text(json.dumps({
            "type": "vad",
            "event": "end",
            "timestamp": end_timestamp
        }))

        # 模拟识别延迟
        await asyncio.sleep(random.uniform(0.1, 0.3))

        # 发送最终识别结果
        final_text = session_state["current_text"]
        duration = end_timestamp - session_state["start_time"] if session_state["start_time"] else 1.0
        timestamps = self._generate_timestamps(final_text, duration)

        await websocket.send_text(json.dumps({
            "type": "final",
            "text": final_text,
            "timestamps": [{"start": ts.start, "end": ts.end} for ts in timestamps],
            "confidence": round(random.uniform(0.8, 0.95), 2)
        }))

    async def _finalize_recognition(self, websocket, session_state: dict):
        """完成识别会话"""
        if session_state["is_speaking"]:
            # 如果还在说话状态，强制结束
            await self._end_speech_segment(websocket, session_state, time.time())

        # 发送会话结束确认
        await websocket.send_text(json.dumps({
            "type": "session_end",
            "message": "ASR session completed"
        }))


# 单例实例
_asr_service = None


def get_asr_service() -> MockASRService:
    """获取ASR服务实例"""
    global _asr_service
    if _asr_service is None:
        _asr_service = MockASRService()
    return _asr_service