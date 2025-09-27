"""
TTS服务测试
测试FishAudio TTS服务、Mock TTS服务和provider管理
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
from typing import List

from src.services.tts_provider import (
    TTSProviderFactory,
    TTSProviderType,
    TTSRequest,
    TTSService,
    AudioFormat,
    get_tts_service
)
from src.services.mock_tts import MockTTSService
from src.services.fishaudio_tts import FishAudioTTSProvider


class TestTTSProvider:
    """TTS Provider基础测试"""

    def setup_method(self):
        """重置provider状态"""
        TTSProviderFactory._providers.clear()
        TTSProviderFactory._primary_provider = TTSProviderType.MOCK
        TTSProviderFactory._fallback_providers = [TTSProviderType.MOCK]

    @pytest.mark.asyncio
    async def test_mock_tts_provider(self):
        """测试Mock TTS Provider"""
        provider = MockTTSService()

        # 健康检查
        assert await provider.check_health() is True
        assert provider.is_healthy is True

        # 合成请求
        request = TTSRequest(
            text="派蒙很开心",
            voice="female_general",
            speed=1.0
        )

        messages = []
        async for message in provider.synthesize_stream(request, "test_session", "test_trace"):
            messages.append(message)

        # 验证消息类型
        audio_messages = [m for m in messages if m.type == "audio"]
        marker_messages = [m for m in messages if m.type == "marker"]
        end_messages = [m for m in messages if m.type == "end"]

        assert len(audio_messages) > 0
        assert len(marker_messages) > 0
        assert len(end_messages) == 1

        # 验证音素标记
        phonemes = [m.marker.phoneme for m in marker_messages]
        assert "P" in phonemes  # 派
        assert "M" in phonemes  # 蒙

        # 验证结束消息
        end_msg = end_messages[0]
        assert end_msg.duration > 0
        assert end_msg.total_chunks > 0
        assert end_msg.rtf >= 0

    @pytest.mark.asyncio
    async def test_fishaudio_provider_without_sdk(self):
        """测试没有SDK时的FishAudio Provider"""
        with patch('src.services.fishaudio_tts.FISH_SDK_AVAILABLE', False):
            with pytest.raises(ImportError, match="fish-audio-sdk is not available"):
                FishAudioTTSProvider("test_api_key")

    @pytest.mark.asyncio
    async def test_fishaudio_provider_with_mock_sdk(self):
        """测试模拟FishAudio SDK的Provider"""
        # 模拟FishAudio SDK
        mock_session = Mock()
        mock_tts_chunks = [b"chunk1", b"chunk2", b"chunk3"]
        mock_session.tts.return_value = mock_tts_chunks

        with patch('src.services.fishaudio_tts.FISH_SDK_AVAILABLE', True):
            with patch('src.services.fishaudio_tts.Session', return_value=mock_session):
                provider = FishAudioTTSProvider("test_api_key", "test_model_id")

                # 健康检查
                assert await provider.check_health() is True

                # 合成请求
                request = TTSRequest(
                    text="测试文本",
                    emotions="happy"
                )

                messages = []
                async for message in provider.synthesize_stream(request, "test_session", "test_trace"):
                    messages.append(message)

                # 验证调用
                assert len(messages) > 0
                audio_messages = [m for m in messages if m.type == "audio"]
                assert len(audio_messages) > 0

    def test_provider_factory_registration(self):
        """测试Provider工厂注册"""
        mock_provider = MockTTSService()

        # 注册provider
        TTSProviderFactory.register_provider(TTSProviderType.MOCK, mock_provider)

        # 设置主要provider
        TTSProviderFactory.set_primary_provider(TTSProviderType.MOCK)

        # 获取provider状态
        status = TTSProviderFactory.get_provider_status()
        assert TTSProviderType.MOCK.value in status
        assert status[TTSProviderType.MOCK.value]["is_primary"] is True

    @pytest.mark.asyncio
    async def test_provider_fallback(self):
        """测试Provider回退机制"""
        # 创建一个不健康的主provider
        unhealthy_provider = MockTTSService()
        unhealthy_provider.mark_unhealthy("Test error")

        # 创建健康的回退provider
        fallback_provider = MockTTSService()

        # 注册providers
        TTSProviderFactory.register_provider(TTSProviderType.FISHAUDIO, unhealthy_provider)
        TTSProviderFactory.register_provider(TTSProviderType.MOCK, fallback_provider)

        # 设置主要和回退
        TTSProviderFactory.set_primary_provider(TTSProviderType.FISHAUDIO)
        TTSProviderFactory.set_fallback_providers([TTSProviderType.MOCK])

        # 获取provider（应该返回回退的provider）
        provider = await TTSProviderFactory.get_provider()
        assert provider.provider_type == TTSProviderType.MOCK
        assert provider.is_healthy is True

    @pytest.mark.asyncio
    async def test_tts_service_integration(self):
        """测试TTS服务集成"""
        # 设置mock provider
        mock_provider = MockTTSService()
        TTSProviderFactory.register_provider(TTSProviderType.MOCK, mock_provider)
        TTSProviderFactory.set_primary_provider(TTSProviderType.MOCK)

        # 获取TTS服务
        tts_service = get_tts_service()

        # 测试合成请求
        request = TTSRequest(text="测试合成")
        messages = []

        async for message in tts_service.synthesize_stream(request, "test", "test"):
            messages.append(message)

        assert len(messages) > 0
        assert any(m.type == "audio" for m in messages)
        assert any(m.type == "end" for m in messages)

    def test_tts_request_parameters(self):
        """测试TTS请求参数"""
        request = TTSRequest(
            text="测试文本",
            voice="custom_voice",
            speed=1.2,
            volume=5.0,
            format=AudioFormat.WAV,
            sample_rate=44100,
            chunk_length=300,
            temperature=0.8,
            top_p=0.9,
            reference_id="model_123",
            emotions="excited"
        )

        assert request.text == "测试文本"
        assert request.voice == "custom_voice"
        assert request.speed == 1.2
        assert request.volume == 5.0
        assert request.format == AudioFormat.WAV
        assert request.sample_rate == 44100
        assert request.chunk_length == 300
        assert request.temperature == 0.8
        assert request.top_p == 0.9
        assert request.reference_id == "model_123"
        assert request.emotions == "excited"

    @pytest.mark.asyncio
    async def test_empty_text_handling(self):
        """测试空文本处理"""
        provider = MockTTSService()
        request = TTSRequest(text="")

        messages = []
        async for message in provider.synthesize_stream(request, "test", "test"):
            messages.append(message)

        # 应该返回错误消息
        assert len(messages) == 1
        assert messages[0].type == "error"
        assert messages[0].code == "EMPTY_TEXT"

    @pytest.mark.asyncio
    async def test_phoneme_marker_generation(self):
        """测试音素标记生成"""
        provider = MockTTSService()
        request = TTSRequest(text="派蒙", speed=1.0)

        marker_messages = []
        async for message in provider.synthesize_stream(request, "test", "test"):
            if message.type == "marker":
                marker_messages.append(message)

        # 验证音素标记
        phonemes = [m.marker.phoneme for m in marker_messages]

        # "派" 应该产生 ["P", "AI"]
        # "蒙" 应该产生 ["M", "ENG"]
        assert "P" in phonemes
        assert "AI" in phonemes
        assert "M" in phonemes
        assert "ENG" in phonemes

        # 验证时间戳递增
        timestamps = [m.marker.timestamp for m in marker_messages]
        assert timestamps == sorted(timestamps)

    @pytest.mark.asyncio
    async def test_rtf_calculation(self):
        """测试实时系数计算"""
        provider = MockTTSService()
        provider.start_timing()

        # 模拟处理时间
        await asyncio.sleep(0.1)

        # 假设音频时长为0.5秒
        rtf = provider.get_rtf(0.5)

        # RTF应该大于0且合理
        assert rtf > 0
        assert rtf < 10  # 不应该过大

    @pytest.mark.asyncio
    async def test_speed_adjustment(self):
        """测试语速调节"""
        provider = MockTTSService()

        # 正常语速
        request_normal = TTSRequest(text="测试文本", speed=1.0)
        # 快速语速
        request_fast = TTSRequest(text="测试文本", speed=2.0)

        # 获取结束消息中的时长
        async def get_duration(request):
            async for message in provider.synthesize_stream(request, "test", "test"):
                if message.type == "end":
                    return message.duration
            return 0

        duration_normal = await get_duration(request_normal)
        duration_fast = await get_duration(request_fast)

        # 快速语速应该产生更短的音频
        assert duration_fast < duration_normal

    def test_audio_format_enum(self):
        """测试音频格式枚举"""
        assert AudioFormat.PCM == "pcm"
        assert AudioFormat.MP3 == "mp3"
        assert AudioFormat.WAV == "wav"
        assert AudioFormat.OPUS == "opus"

    @pytest.mark.asyncio
    async def test_provider_error_handling(self):
        """测试Provider错误处理"""
        provider = MockTTSService()

        # 模拟provider错误
        with patch.object(provider, '_estimate_duration', side_effect=Exception("Test error")):
            request = TTSRequest(text="测试")

            messages = []
            async for message in provider.synthesize_stream(request, "test", "test"):
                messages.append(message)

            # 应该返回错误消息
            assert len(messages) == 1
            assert messages[0].type == "error"
            assert messages[0].code == "SYNTHESIS_ERROR"

    @pytest.mark.asyncio
    async def test_chunk_sequencing(self):
        """测试音频块序列"""
        provider = MockTTSService()
        request = TTSRequest(text="这是一个较长的测试文本，应该产生多个音频块")

        audio_messages = []
        async for message in provider.synthesize_stream(request, "test", "test"):
            if message.type == "audio":
                audio_messages.append(message)

        # 验证chunk_id递增
        chunk_ids = [m.chunk.chunk_id for m in audio_messages]
        assert chunk_ids == list(range(len(chunk_ids)))

        # 验证所有块都有音频数据
        for msg in audio_messages:
            assert len(msg.chunk.pcm_base64) > 0
            assert msg.chunk.sample_rate > 0
            assert msg.chunk.duration_ms > 0


class TestTTSWebSocketIntegration:
    """TTS WebSocket集成测试"""

    @pytest.mark.asyncio
    async def test_websocket_message_processing(self):
        """测试WebSocket消息处理"""
        # 模拟websocket
        mock_websocket = AsyncMock()
        mock_websocket.iter_text.return_value = [
            '{"text": "测试文本", "voice": "female_general"}'
        ]

        # 设置provider
        provider = MockTTSService()
        TTSProviderFactory.register_provider(TTSProviderType.MOCK, provider)
        TTSProviderFactory.set_primary_provider(TTSProviderType.MOCK)

        tts_service = get_tts_service()

        # 处理请求
        await tts_service.process_websocket_requests(mock_websocket, "test", "test")

        # 验证websocket被调用
        assert mock_websocket.send_text.called

    @pytest.mark.asyncio
    async def test_websocket_invalid_json(self):
        """测试WebSocket无效JSON处理"""
        mock_websocket = AsyncMock()
        mock_websocket.iter_text.return_value = ['invalid json']

        tts_service = get_tts_service()
        await tts_service.process_websocket_requests(mock_websocket, "test", "test")

        # 验证发送了错误消息
        sent_calls = mock_websocket.send_text.call_args_list
        assert len(sent_calls) > 0

        # 解析最后发送的消息
        last_message = json.loads(sent_calls[-1][0][0])
        assert last_message["type"] == "error"
        assert last_message["code"] == "INVALID_JSON"


@pytest.mark.integration
class TestTTSPerformance:
    """TTS性能测试"""

    @pytest.mark.asyncio
    async def test_synthesis_performance(self):
        """测试合成性能"""
        provider = MockTTSService()

        # 测试不同长度的文本
        test_texts = [
            "短",
            "这是中等长度的测试文本",
            "这是一个相当长的测试文本，用来测试TTS系统在处理较长文本时的性能表现，包括音频生成和音素标记的准确性"
        ]

        for text in test_texts:
            start_time = asyncio.get_event_loop().time()

            request = TTSRequest(text=text)
            messages = []

            async for message in provider.synthesize_stream(request, "test", "test"):
                messages.append(message)

            processing_time = asyncio.get_event_loop().time() - start_time

            # 获取音频时长
            end_messages = [m for m in messages if m.type == "end"]
            audio_duration = end_messages[0].duration if end_messages else 0

            # 计算RTF
            rtf = processing_time / audio_duration if audio_duration > 0 else float('inf')

            print(f"Text length: {len(text)}, Audio duration: {audio_duration:.2f}s, "
                  f"Processing time: {processing_time:.2f}s, RTF: {rtf:.3f}")

            # RTF应该小于某个阈值（比如5.0，考虑到这是mock服务）
            assert rtf < 5.0

    @pytest.mark.asyncio
    async def test_concurrent_synthesis(self):
        """测试并发合成"""
        provider = MockTTSService()

        async def single_synthesis(text_id):
            request = TTSRequest(text=f"并发测试文本{text_id}")
            messages = []
            async for message in provider.synthesize_stream(request, f"test_{text_id}", f"trace_{text_id}"):
                messages.append(message)
            return len(messages)

        # 并发执行多个合成任务
        tasks = [single_synthesis(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # 所有任务都应该成功完成
        assert all(count > 0 for count in results)


if __name__ == "__main__":
    # 运行性能测试
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "perf":
        asyncio.run(TestTTSPerformance().test_synthesis_performance())
        asyncio.run(TestTTSPerformance().test_concurrent_synthesis())
    else:
        pytest.main([__file__, "-v"])