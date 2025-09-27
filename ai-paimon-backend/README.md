# AI派蒙后端API服务

AI Paimon Backend API Server - 模块化的AI角色交互系统后端服务。

## 项目概述

本项目实现了AI派蒙角色的后端API服务，支持：
- 语音识别(ASR)流式处理
- 对话生成与风格化
- 语音合成(TTS)流式输出
- 口型同步与viseme生成
- 知识库检索与问答

## 技术栈

- **FastAPI** 0.104+ - 高性能异步Web框架
- **Pydantic** v2 - 数据验证与序列化
- **WebSocket** - 实时双向通信
- **Python** 3.9+ - 开发语言

## 项目结构

```
ai-paimon-backend/
├── src/
│   ├── api/              # API路由层
│   │   ├── websocket/    # WebSocket端点
│   │   └── http/         # HTTP REST端点
│   ├── core/             # 核心配置与错误处理
│   ├── models/           # Pydantic数据模型
│   ├── services/         # Mock业务逻辑服务
│   └── utils/            # 工具函数
├── tests/                # 测试用例
├── config/               # 配置文件
└── docs/                 # API文档
```

## API接口

### WebSocket接口
- `/asr/stream` - ASR语音识别流式处理
- `/tts/stream` - TTS语音合成流式输出

### HTTP接口
- `/dialog/generate` - 对话生成
- `/viseme/timeline` - 口型时间轴生成
- `/kb/search` - 知识库检索
- `/health` - 健康检查

## 快速开始

### 1. 环境准备
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\\Scripts\\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动服务
```bash
# 开发模式启动
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 访问API文档
open http://localhost:8000/docs
```

### 3. 测试接口
```bash
# 健康检查
curl http://localhost:8000/health

# 对话测试
curl -X POST http://localhost:8000/dialog/generate \\
  -H "Content-Type: application/json" \\
  -d '{"text":"你好", "session_id":"test"}'
```

## 开发指南

### 代码规范
```bash
# 代码格式化
black src/ tests/

# 代码检查
ruff check src/ tests/

# 类型检查
mypy src/
```

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_api/

# 测试覆盖率
pytest --cov=src tests/
```

## 配置说明

### 特征开关
- `feature.kb.enabled=false` - 知识库检索开关
- `feature.viseme.rhubarb=false` - Rhubarb口型开关
- `feature.avatar.mode=live2d` - 角色模式(live2d/vrm)

### 环境变量
- `ENVIRONMENT` - 运行环境(development/production)
- `LOG_LEVEL` - 日志级别(debug/info/warning/error)

## API文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## 合规说明

本项目为"风格化模拟"实现，严格遵循：
- 明示非官方性质
- 不复刻原作内容
- 不使用受版权保护素材
- 不进行声纹克隆

## 版本历史

- v0.1.0 - 基础API框架与Mock服务实现

## 许可证

本项目仅用于学习与研究目的。