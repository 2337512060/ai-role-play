"""
TTS语音合成Mock服务
模拟语音合成的业务逻辑
"""

import asyncio
import base64
import json
import random
import time
from typing import List, Optional

import numpy as np

from ..models.websocket import (
    TTSRequestMessage,
    TTSAudioMessage,
    TTSMarkerMessage,
    TTSEndMessage
)


class MockTTSService:
    """Mock TTS服务"""

    def __init__(self):
        self.sample_rate = 24000
        self.chunk_size = 1024

        # 中文音素映射
        self.phoneme_map = {
            "派": ["P", "AI"],
            "蒙": ["M", "ENG"],
            "你": ["N", "I"],
            "好": ["H", "AO"],
            "旅": ["L", "YU"],
            "行": ["X", "ING"],
            "者": ["ZH", "E"],
            "今": ["J", "IN"],
            "天": ["T", "IAN"],
            "什": ["SH", "EN"],
            "么": ["M", "E"],
            "想": ["X", "IANG"],
            "吃": ["CH", "I"],
            "的": ["D", "E"],
            "东": ["D", "ONG"],
            "西": ["X", "I"],
        }

    def _estimate_duration(self, text: str, speed: float = 1.0) -> float:
        """估算合成音频时长"""
        # 中文平均语速约 4-5 字/秒
        base_duration = len(text) / 4.5
        adjusted_duration = base_duration / speed
        return max(adjusted_duration, 0.5)  # 最少0.5秒

    def _generate_phoneme_markers(self, text: str, duration: float) -> List[dict]:
        """生成音素标记"""
        markers = []
        char_count = len(text)

        if char_count == 0:
            return markers

        char_duration = duration / char_count
        current_time = 0.0

        for char in text:
            if char.isspace() or char in "，。！？；：":
                # 标点符号添加静音
                markers.append({
                    "type": "marker",
                    "phoneme": "SIL",
                    "t": round(current_time, 3),
                    "duration": round(char_duration, 3)
                })
            elif char in self.phoneme_map:
                # 有映射的字符
                phonemes = self.phoneme_map[char]
                phoneme_duration = char_duration / len(phonemes)

                for i, phoneme in enumerate(phonemes):
                    markers.append({
                        "type": "marker",
                        "phoneme": phoneme,
                        "t": round(current_time + i * phoneme_duration, 3),
                        "duration": round(phoneme_duration, 3)
                    })
            else:
                # 其他字符使用通用音素
                markers.append({
                    "type": "marker",
                    "phoneme": "X",
                    "t": round(current_time, 3),
                    "duration": round(char_duration, 3)
                })

            current_time += char_duration

        return markers

    def _generate_audio_chunk(self, chunk_id: int, frequency: float = 440.0) -> str:
        """生成音频数据块"""
        # 生成正弦波音频数据（模拟语音）
        t = np.linspace(0, self.chunk_size / self.sample_rate, self.chunk_size)

        # 添加一些随机性来模拟真实语音
        base_freq = frequency * (0.8 + 0.4 * random.random())
        noise_level = 0.1

        # 生成复合波形
        wave1 = np.sin(2 * np.pi * base_freq * t)
        wave2 = 0.3 * np.sin(2 * np.pi * base_freq * 2 * t)
        wave3 = 0.1 * np.sin(2 * np.pi * base_freq * 3 * t)
        noise = noise_level * np.random.normal(0, 1, len(t))

        # 合成最终波形
        audio = wave1 + wave2 + wave3 + noise

        # 添加包络来模拟语音的动态特性
        envelope = 0.5 * (1 + np.sin(2 * np.pi * 2 * t - np.pi/2))
        audio *= envelope

        # 转换为16位PCM
        audio_int16 = (audio * 32767 * 0.5).astype(np.int16)

        # 编码为base64
        audio_bytes = audio_int16.tobytes()
        return base64.b64encode(audio_bytes).decode('utf-8')

    async def synthesize_text(self, websocket, request_data: dict):
        """合成文本为语音"""
        text = request_data.get("text", "")
        voice = request_data.get("voice", "female_general")
        speed = request_data.get("speed", 1.0)

        if not text:
            await websocket.send_text(json.dumps({
                "type": "error",
                "code": "EMPTY_TEXT",
                "message": "Text cannot be empty"
            }))
            return

        try:
            # 估算总时长
            total_duration = self._estimate_duration(text, speed)

            # 生成音素标记
            phoneme_markers = self._generate_phoneme_markers(text, total_duration)

            # 计算需要的音频块数
            samples_needed = int(total_duration * self.sample_rate)
            chunk_count = (samples_needed + self.chunk_size - 1) // self.chunk_size

            # 模拟合成延迟
            await asyncio.sleep(0.1)

            # 发送音频块和音素标记
            chunk_id = 0
            marker_index = 0
            current_time = 0.0

            for i in range(chunk_count):
                # 生成音频块
                audio_base64 = self._generate_audio_chunk(
                    chunk_id,
                    frequency=200 + random.uniform(0, 200)  # 模拟女声频率范围
                )

                # 发送音频数据
                await websocket.send_text(json.dumps({
                    "type": "audio",
                    "pcm_base64": audio_base64,
                    "sr": self.sample_rate,
                    "chunk_id": chunk_id
                }))

                # 发送对应时间的音素标记
                chunk_duration = self.chunk_size / self.sample_rate
                chunk_end_time = current_time + chunk_duration

                while (marker_index < len(phoneme_markers) and
                       phoneme_markers[marker_index]["t"] < chunk_end_time):
                    await websocket.send_text(json.dumps(phoneme_markers[marker_index]))
                    marker_index += 1

                # 模拟流式传输延迟
                await asyncio.sleep(chunk_duration * 0.8)  # 略快于实时

                chunk_id += 1
                current_time = chunk_end_time

            # 发送剩余的音素标记
            while marker_index < len(phoneme_markers):
                await websocket.send_text(json.dumps(phoneme_markers[marker_index]))
                marker_index += 1

            # 发送结束消息
            await websocket.send_text(json.dumps({
                "type": "end",
                "duration": round(total_duration, 3),
                "total_chunks": chunk_count
            }))

        except Exception as e:
            await websocket.send_text(json.dumps({
                "type": "error",
                "code": "SYNTHESIS_ERROR",
                "message": str(e)
            }))

    async def process_tts_requests(self, websocket, session_id: str):
        """处理TTS请求"""
        try:
            async for message in websocket.iter_text():
                try:
                    request_data = json.loads(message)

                    # 检查是否有必需的字段
                    if "text" in request_data:
                        await self.synthesize_text(websocket, request_data)
                    else:
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "code": "INVALID_REQUEST",
                            "message": "Missing required field: text"
                        }))

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

        except Exception as e:
            print(f"TTS WebSocket error for {session_id}: {e}")


# 单例实例
_tts_service = None


def get_tts_service() -> MockTTSService:
    """获取TTS服务实例"""
    global _tts_service
    if _tts_service is None:
        _tts_service = MockTTSService()
    return _tts_service