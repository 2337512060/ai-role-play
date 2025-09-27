# 快速启动指南

## 模块0已完成！🎉

AI Paimon Backend API的基础框架已经搭建完成，包含：

- ✅ 完整的项目结构
- ✅ 配置管理系统
- ✅ HTTP API接口（对话/口型/知识库）
- ✅ WebSocket接口（ASR/TTS）
- ✅ Mock服务实现
- ✅ 数据模型定义
- ✅ 错误处理机制
- ✅ 测试用例
- ✅ Docker容器化
- ✅ API文档

## 快速启动

### 方式1：Python开发模式（推荐）

```bash
cd ai-paimon-backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
./start.sh dev
# 或
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 方式2：Docker模式

```bash
cd ai-paimon-backend

# 启动基础服务
./start.sh start

# 或启动完整环境（包含Nginx）
./start.sh start with-nginx

# 查看服务状态
./start.sh status

# 查看日志
./start.sh logs
```

## 验证安装

```bash
# 运行验证脚本
python verify.py

# 或手动检查
curl http://localhost:8000/health
```

## 访问文档

- **API文档**: http://localhost:8000/docs
- **ReDoc文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## 测试API

### 对话生成
```bash
curl -X POST "http://localhost:8000/dialog/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好派蒙",
    "session_id": "test_session",
    "flags": {"kb": false}
  }'
```

### 口型生成
```bash
curl -X POST "http://localhost:8000/viseme/timeline" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "派蒙想吃好吃的"
  }'
```

## 下一步

模块0完成后，可以继续实施其他模块：

1. **模块1**: 前端音频采集与播放
2. **模块2**: 真实ASR服务集成
3. **模块3**: 对话策略优化
4. **模块4**: 风格化处理增强
5. **模块5**: 安全与合规
6. **模块6**: 真实TTS服务集成
7. **模块7-9**: 动画与口型同步
8. **模块10-12**: 监控、部署、评测

## 故障排除

### 常见问题

1. **端口占用**: 修改配置或停止占用进程
2. **依赖安装失败**: 检查Python版本（需要3.9+）
3. **Docker启动失败**: 检查Docker服务状态

### 日志查看

```bash
# Docker日志
./start.sh logs

# 开发模式日志直接在控制台显示
```

### 重置环境

```bash
# 清理Docker环境
./start.sh clean

# 重新构建
./start.sh build
```

## 功能特色

- **模块化设计**: 每个功能独立，可插拔
- **类型安全**: 全面使用Pydantic进行数据验证
- **实时通信**: WebSocket支持流式音频处理
- **Mock完整**: 无需外部依赖即可完整测试
- **容器化**: 支持Docker部署
- **可观测性**: 统一的错误处理和追踪
- **扩展性**: 特征开关控制功能启用

恭喜！模块0的API骨架已经完成，可以开始下一个模块的开发了！