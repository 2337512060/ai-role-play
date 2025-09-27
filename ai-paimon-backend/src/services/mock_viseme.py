"""
口型时间轴Mock服务
模拟口型生成的业务逻辑
"""

import random
import time
from typing import List

from ..models import (
    VisemeRequest,
    VisemeResponse,
    VisemeFrame,
    VisemeType
)


class MockVisemeService:
    """Mock口型服务"""

    def __init__(self):
        # 中文音素到口型的映射
        self.phoneme_to_viseme = {
            "a": VisemeType.A,
            "e": VisemeType.E,
            "i": VisemeType.I,
            "o": VisemeType.O,
            "u": VisemeType.U,
            "m": VisemeType.M,
            "p": VisemeType.M,
            "b": VisemeType.M,
            "f": VisemeType.F,
            "v": VisemeType.F,
            "t": VisemeType.T,
            "d": VisemeType.T,
            "s": VisemeType.S,
            "z": VisemeType.S,
            "l": VisemeType.L,
            "r": VisemeType.L,
            "h": VisemeType.H,
        }

    def _estimate_duration(self, text: str) -> float:
        """根据文本长度估算音频时长"""
        # 中文平均语速约 4-5 字/秒
        chars_per_second = 4.5
        duration = len(text) / chars_per_second
        # 添加一些随机变化
        return duration * random.uniform(0.8, 1.2)

    def _generate_viseme_sequence(self, text: str, duration: float) -> List[VisemeFrame]:
        """生成口型序列"""
        visemes = []
        char_count = len(text)

        if char_count == 0:
            return visemes

        # 计算每个字符的平均时长
        char_duration = duration / char_count

        current_time = 0.0

        for i, char in enumerate(text):
            # 根据字符生成口型
            if char.isspace() or char in "，。！？；：":
                # 标点和空格用静音
                viseme_type = VisemeType.X
                weight = 0.0
            elif char in "啊呀哎":
                viseme_type = VisemeType.A
                weight = random.uniform(0.7, 1.0)
            elif char in "欸嘿诶":
                viseme_type = VisemeType.E
                weight = random.uniform(0.6, 0.9)
            elif char in "咿呢嘻":
                viseme_type = VisemeType.I
                weight = random.uniform(0.5, 0.8)
            elif char in "哦噢喔":
                viseme_type = VisemeType.O
                weight = random.uniform(0.6, 0.9)
            elif char in "呜嗚唔":
                viseme_type = VisemeType.U
                weight = random.uniform(0.6, 0.9)
            elif char in "嘛吗妈":
                viseme_type = VisemeType.M
                weight = random.uniform(0.7, 1.0)
            else:
                # 其他字符随机选择口型
                viseme_type = random.choice([
                    VisemeType.A, VisemeType.E, VisemeType.I,
                    VisemeType.O, VisemeType.U, VisemeType.T
                ])
                weight = random.uniform(0.4, 0.8)

            # 添加口型帧
            visemes.append(VisemeFrame(
                t=round(current_time, 3),
                id=viseme_type,
                w=round(weight, 2)
            ))

            # 为某些字符添加过渡帧
            if i < char_count - 1 and random.random() < 0.3:
                transition_time = current_time + char_duration * 0.5
                transition_viseme = random.choice([VisemeType.X, VisemeType.T])
                visemes.append(VisemeFrame(
                    t=round(transition_time, 3),
                    id=transition_viseme,
                    w=round(random.uniform(0.2, 0.5), 2)
                ))

            current_time += char_duration

        # 添加结束帧
        visemes.append(VisemeFrame(
            t=round(duration, 3),
            id=VisemeType.X,
            w=0.0
        ))

        return visemes

    async def generate_viseme_timeline(self, request: VisemeRequest, trace_id: str) -> VisemeResponse:
        """生成口型时间轴"""
        # 模拟处理延迟
        await asyncio.sleep(0.1)

        if request.text:
            # 使用文本生成
            text = request.text
            duration = self._estimate_duration(text)
        elif request.wav_url:
            # 模拟音频文件解析
            # 在实际实现中，这里会解析音频文件获取时长
            text = "模拟音频内容"
            duration = random.uniform(1.0, 5.0)
        else:
            raise ValueError("Either text or wav_url must be provided")

        # 生成口型序列
        visemes = self._generate_viseme_sequence(text, duration)

        return VisemeResponse(
            visemes=visemes,
            src="rhubarb",  # 模拟使用Rhubarb生成
            duration=duration,
            trace_id=trace_id
        )


# 异步导入
import asyncio


# 单例实例
_viseme_service = None


def get_viseme_service() -> MockVisemeService:
    """获取口型服务实例"""
    global _viseme_service
    if _viseme_service is None:
        _viseme_service = MockVisemeService()
    return _viseme_service