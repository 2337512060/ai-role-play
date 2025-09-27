"""
pytest配置文件
"""

import pytest
from fastapi.testclient import TestClient

from src.main import create_app


@pytest.fixture(scope="session")
def app():
    """创建测试应用实例"""
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_dialog_request():
    """示例对话请求"""
    return {
        "text": "你好派蒙",
        "session_id": "test_session_123",
        "flags": {"kb": False}
    }


@pytest.fixture
def sample_viseme_request():
    """示例口型请求"""
    return {
        "text": "派蒙想吃好吃的",
        "audio_format": "wav"
    }


@pytest.fixture
def sample_kb_request():
    """示例知识库请求"""
    return {
        "query": "派蒙是谁",
        "topk": 3,
        "min_score": 0.0
    }