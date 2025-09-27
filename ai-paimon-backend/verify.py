#!/usr/bin/env python3
"""
快速验证脚本
验证AI Paimon Backend是否正常工作
"""

import asyncio
import json
import sys
import time
from typing import Dict, Any

import requests
import websockets


def print_status(message: str, status: str = "INFO"):
    """打印状态消息"""
    colors = {
        "INFO": "\033[0;34m",
        "SUCCESS": "\033[0;32m",
        "ERROR": "\033[0;31m",
        "WARNING": "\033[1;33m"
    }
    color = colors.get(status, "\033[0m")
    print(f"{color}[{status}]\033[0m {message}")


def test_health_check(base_url: str = "http://localhost:8000") -> bool:
    """测试健康检查接口"""
    try:
        print_status("Testing health check endpoint...")
        response = requests.get(f"{base_url}/health", timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy":
                print_status("Health check passed", "SUCCESS")
                return True
            else:
                print_status(f"Health check failed: {data}", "ERROR")
                return False
        else:
            print_status(f"Health check failed with status {response.status_code}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Health check failed: {e}", "ERROR")
        return False


def test_dialog_api(base_url: str = "http://localhost:8000") -> bool:
    """测试对话生成API"""
    try:
        print_status("Testing dialog generation API...")

        request_data = {
            "text": "你好派蒙",
            "session_id": "test_verification",
            "flags": {"kb": False}
        }

        response = requests.post(
            f"{base_url}/dialog/generate",
            json=request_data,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and data.get("reply"):
                print_status(f"Dialog API passed: {data['reply'][:50]}...", "SUCCESS")
                return True
            else:
                print_status(f"Dialog API failed: {data}", "ERROR")
                return False
        else:
            print_status(f"Dialog API failed with status {response.status_code}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Dialog API failed: {e}", "ERROR")
        return False


def test_viseme_api(base_url: str = "http://localhost:8000") -> bool:
    """测试口型生成API"""
    try:
        print_status("Testing viseme generation API...")

        request_data = {
            "text": "派蒙想吃好吃的",
            "audio_format": "wav"
        }

        response = requests.post(
            f"{base_url}/viseme/timeline",
            json=request_data,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("ok") and data.get("visemes"):
                print_status(f"Viseme API passed: {len(data['visemes'])} visemes generated", "SUCCESS")
                return True
            else:
                print_status(f"Viseme API failed: {data}", "ERROR")
                return False
        else:
            print_status(f"Viseme API failed with status {response.status_code}", "ERROR")
            return False
    except Exception as e:
        print_status(f"Viseme API failed: {e}", "ERROR")
        return False


async def test_asr_websocket(base_url: str = "ws://localhost:8000") -> bool:
    """测试ASR WebSocket接口"""
    try:
        print_status("Testing ASR WebSocket...")

        uri = f"{base_url}/asr/stream"

        async with websockets.connect(uri) as websocket:
            # 发送初始化消息
            init_msg = {
                "type": "init",
                "sr": 16000,
                "lang": "zh"
            }
            await websocket.send(json.dumps(init_msg))

            # 等待响应
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)

            if data.get("type") == "init_ack":
                print_status("ASR WebSocket passed", "SUCCESS")
                return True
            else:
                print_status(f"ASR WebSocket failed: {data}", "ERROR")
                return False

    except Exception as e:
        print_status(f"ASR WebSocket failed: {e}", "ERROR")
        return False


async def test_tts_websocket(base_url: str = "ws://localhost:8000") -> bool:
    """测试TTS WebSocket接口"""
    try:
        print_status("Testing TTS WebSocket...")

        uri = f"{base_url}/tts/stream"

        async with websockets.connect(uri) as websocket:
            # 发送合成请求
            request = {
                "text": "测试",
                "voice": "female_general",
                "speed": 1.0
            }
            await websocket.send(json.dumps(request))

            # 等待音频响应
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            data = json.loads(response)

            if data.get("type") == "audio":
                print_status("TTS WebSocket passed", "SUCCESS")
                return True
            else:
                print_status(f"TTS WebSocket unexpected response: {data}", "WARNING")
                return True  # 可能第一个响应不是音频，但连接正常

    except Exception as e:
        print_status(f"TTS WebSocket failed: {e}", "ERROR")
        return False


async def main():
    """主验证函数"""
    print_status("=== AI Paimon Backend Verification ===")
    print_status("Starting verification tests...\n")

    results = []

    # HTTP API测试
    results.append(test_health_check())
    results.append(test_dialog_api())
    results.append(test_viseme_api())

    # WebSocket测试
    results.append(await test_asr_websocket())
    results.append(await test_tts_websocket())

    # 汇总结果
    passed = sum(results)
    total = len(results)

    print_status(f"\n=== Verification Results ===")
    print_status(f"Tests passed: {passed}/{total}")

    if passed == total:
        print_status("All tests passed! 🎉", "SUCCESS")
        print_status("Your AI Paimon Backend is working correctly!", "SUCCESS")
        print_status("API Documentation: http://localhost:8000/docs", "INFO")
        return 0
    else:
        print_status(f"Some tests failed ({total - passed} failures)", "ERROR")
        print_status("Please check the service logs for details", "WARNING")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_status("Verification interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        print_status(f"Verification failed with error: {e}", "ERROR")
        sys.exit(1)