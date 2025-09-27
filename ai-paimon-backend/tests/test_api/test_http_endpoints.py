"""
HTTP API端点测试
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthAPI:
    """健康检查API测试"""

    def test_health_check(self, client: TestClient):
        """测试健康检查接口"""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert data["ok"] is True
        assert data["status"] == "healthy"
        assert data["service"] == "ai-paimon-backend"
        assert data["version"] == "0.1.0"

    def test_root_endpoint(self, client: TestClient):
        """测试根路径"""
        response = client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "status" in data


class TestDialogAPI:
    """对话生成API测试"""

    def test_dialog_generate_success(self, client: TestClient, sample_dialog_request):
        """测试对话生成成功场景"""
        response = client.post("/dialog/generate", json=sample_dialog_request)
        assert response.status_code == 200

        data = response.json()
        assert data["ok"] is True
        assert "reply" in data
        assert "emotion" in data
        assert "trace" in data
        assert len(data["reply"]) > 0

        # 检查trace信息
        trace = data["trace"]
        assert "policy" in trace
        assert "kb_sources" in trace
        assert trace["policy"] in ["chitchat", "help", "fact", "story"]

    def test_dialog_generate_empty_text(self, client: TestClient):
        """测试空文本输入"""
        request_data = {
            "text": "",
            "session_id": "test_session",
            "flags": {}
        }
        response = client.post("/dialog/generate", json=request_data)
        assert response.status_code == 422  # 验证错误

    def test_dialog_generate_missing_session_id(self, client: TestClient):
        """测试缺少session_id"""
        request_data = {
            "text": "测试文本",
            "flags": {}
        }
        response = client.post("/dialog/generate", json=request_data)
        assert response.status_code == 422  # 验证错误


class TestVisemeAPI:
    """口型时间轴API测试"""

    def test_viseme_generate_with_text(self, client: TestClient, sample_viseme_request):
        """测试基于文本生成口型"""
        response = client.post("/viseme/timeline", json=sample_viseme_request)
        assert response.status_code == 200

        data = response.json()
        assert data["ok"] is True
        assert "visemes" in data
        assert "src" in data
        assert "duration" in data
        assert len(data["visemes"]) > 0

        # 检查口型数据格式
        for viseme in data["visemes"]:
            assert "t" in viseme
            assert "id" in viseme
            assert "w" in viseme
            assert 0 <= viseme["w"] <= 1

    def test_viseme_generate_with_wav_url(self, client: TestClient):
        """测试基于音频URL生成口型"""
        request_data = {
            "wav_url": "http://example.com/test.wav"
        }
        response = client.post("/viseme/timeline", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data["ok"] is True
        assert len(data["visemes"]) > 0

    def test_viseme_generate_no_input(self, client: TestClient):
        """测试无输入参数"""
        request_data = {}
        response = client.post("/viseme/timeline", json=request_data)
        assert response.status_code == 400  # 缺少必需参数


class TestKnowledgeAPI:
    """知识库API测试"""

    def test_kb_search_disabled_by_default(self, client: TestClient, sample_kb_request):
        """测试知识库默认禁用状态"""
        response = client.post("/kb/search", json=sample_kb_request)
        # 由于特征开关默认关闭，应该返回503
        assert response.status_code == 503

    def test_kb_search_empty_query(self, client: TestClient):
        """测试空查询"""
        request_data = {
            "query": "",
            "topk": 5
        }
        response = client.post("/kb/search", json=request_data)
        assert response.status_code == 422  # 验证错误

    def test_kb_search_invalid_topk(self, client: TestClient):
        """测试无效的topk参数"""
        request_data = {
            "query": "测试查询",
            "topk": 0  # 无效值
        }
        response = client.post("/kb/search", json=request_data)
        assert response.status_code == 422  # 验证错误