# API使用示例

本文档展示如何使用AI Paimon Backend API的各个接口。

## 前提条件

确保服务已启动：

```bash
cd ai-paimon-backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## HTTP API示例

### 1. 健康检查

```bash
# 健康检查
curl -X GET "http://localhost:8000/health"

# 响应示例
{
  "ok": true,
  "status": "healthy",
  "service": "ai-paimon-backend",
  "version": "0.1.0"
}
```

### 2. 对话生成

```bash
# 对话生成请求
curl -X POST "http://localhost:8000/dialog/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "你好派蒙",
    "session_id": "user_123_session_1",
    "flags": {
      "kb": false
    }
  }'

# 响应示例
{
  "ok": true,
  "reply": "欸！旅行者你好呀～派蒙刚才在想今天要吃什么好吃的呢！",
  "emotion": "happy",
  "trace": {
    "policy": "chitchat",
    "kb_sources": [],
    "processing_time": 156.7,
    "metadata": {
      "session_context": {
        "last_input": "你好派蒙",
        "last_policy": "chitchat",
        "last_emotion": "happy",
        "message_count": 1
      },
      "mock_version": "0.1.0"
    }
  },
  "trace_id": "abc123-def456"
}
```

### 3. 口型时间轴生成

```bash
# 基于文本生成口型
curl -X POST "http://localhost:8000/viseme/timeline" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "派蒙想吃好吃的东西",
    "audio_format": "wav"
  }'

# 响应示例
{
  "ok": true,
  "visemes": [
    {"t": 0.0, "id": "A", "w": 0.8},
    {"t": 0.2, "id": "I", "w": 0.6},
    {"t": 0.4, "id": "M", "w": 0.9},
    {"t": 0.6, "id": "A", "w": 0.7},
    {"t": 0.8, "id": "O", "w": 0.5},
    {"t": 1.0, "id": "X", "w": 0.0}
  ],
  "src": "rhubarb",
  "duration": 2.5,
  "trace_id": "xyz789"
}
```

### 4. 知识库检索（需启用特征开关）

```bash
# 知识库检索请求
curl -X POST "http://localhost:8000/kb/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "派蒙是谁",
    "topk": 3,
    "min_score": 0.5
  }'

# 当知识库功能禁用时的响应
{
  "ok": false,
  "code": "SERVICE_UNAVAILABLE",
  "msg": "Feature features.kb.enabled is disabled",
  "trace_id": "def456"
}
```

## WebSocket API示例

### 1. ASR语音识别流式接口

```javascript
// JavaScript WebSocket客户端示例
const asrSocket = new WebSocket('ws://localhost:8000/asr/stream');

asrSocket.onopen = function(event) {
    console.log('ASR WebSocket连接已建立');

    // 发送初始化消息
    asrSocket.send(JSON.stringify({
        type: 'init',
        sr: 16000,
        lang: 'zh'
    }));
};

asrSocket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('收到ASR消息:', data);

    switch(data.type) {
        case 'vad':
            console.log(`VAD事件: ${data.event} at ${data.timestamp}`);
            break;
        case 'partial':
            console.log(`部分识别: ${data.text}`);
            break;
        case 'final':
            console.log(`最终识别: ${data.text}`);
            console.log('时间戳:', data.timestamps);
            break;
    }
};

// 发送音频数据
function sendAudioChunk(pcmBase64Data) {
    asrSocket.send(JSON.stringify({
        type: 'chunk',
        pcm_base64: pcmBase64Data,
        timestamp: Date.now() / 1000
    }));
}

// 结束识别
function endRecognition() {
    asrSocket.send(JSON.stringify({
        type: 'end'
    }));
}
```

### 2. TTS语音合成流式接口

```javascript
// JavaScript WebSocket客户端示例
const ttsSocket = new WebSocket('ws://localhost:8000/tts/stream');

ttsSocket.onopen = function(event) {
    console.log('TTS WebSocket连接已建立');

    // 发送合成请求
    ttsSocket.send(JSON.stringify({
        text: '派蒙想吃好吃的东西呢！',
        voice: 'female_general',
        speed: 1.0
    }));
};

ttsSocket.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('收到TTS消息:', data);

    switch(data.type) {
        case 'audio':
            console.log(`收到音频块 ${data.chunk_id}, 采样率: ${data.sr}`);
            // 解码并播放音频数据
            playAudioChunk(data.pcm_base64, data.sr);
            break;
        case 'marker':
            console.log(`音素标记: ${data.phoneme} at ${data.t}s`);
            break;
        case 'end':
            console.log(`合成完成，总时长: ${data.duration}s`);
            console.log(`总音频块数: ${data.total_chunks}`);
            break;
        case 'error':
            console.error(`TTS错误: ${data.code} - ${data.message}`);
            break;
    }
};

function playAudioChunk(pcmBase64, sampleRate) {
    // 解码base64音频数据
    const binaryString = atob(pcmBase64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
    }

    // 转换为AudioBuffer并播放
    // 具体实现取决于音频播放库
    console.log(`解码音频数据: ${bytes.length} bytes`);
}
```

## Python客户端示例

### HTTP API客户端

```python
import requests
import json

class PaimonAPIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def health_check(self):
        """健康检查"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()

    def generate_dialog(self, text, session_id, use_kb=False):
        """生成对话"""
        data = {
            "text": text,
            "session_id": session_id,
            "flags": {"kb": use_kb}
        }
        response = requests.post(f"{self.base_url}/dialog/generate", json=data)
        return response.json()

    def generate_viseme(self, text=None, wav_url=None):
        """生成口型时间轴"""
        data = {}
        if text:
            data["text"] = text
        if wav_url:
            data["wav_url"] = wav_url

        response = requests.post(f"{self.base_url}/viseme/timeline", json=data)
        return response.json()

# 使用示例
client = PaimonAPIClient()

# 健康检查
health = client.health_check()
print(f"服务状态: {health['status']}")

# 对话生成
dialog_response = client.generate_dialog("你好派蒙", "test_session")
print(f"派蒙回复: {dialog_response['reply']}")
print(f"情绪: {dialog_response['emotion']}")

# 口型生成
viseme_response = client.generate_viseme(text="派蒙想吃美食")
print(f"口型时长: {viseme_response['duration']}秒")
print(f"口型数量: {len(viseme_response['visemes'])}")
```

### WebSocket客户端

```python
import asyncio
import websockets
import json
import base64

async def asr_client():
    """ASR WebSocket客户端"""
    uri = "ws://localhost:8000/asr/stream"

    async with websockets.connect(uri) as websocket:
        # 发送初始化消息
        init_msg = {
            "type": "init",
            "sr": 16000,
            "lang": "zh"
        }
        await websocket.send(json.dumps(init_msg))

        # 模拟发送音频数据
        for i in range(10):
            # 生成模拟音频数据
            dummy_audio = b'\x00' * 1024  # 1024字节的静音数据
            pcm_base64 = base64.b64encode(dummy_audio).decode('utf-8')

            chunk_msg = {
                "type": "chunk",
                "pcm_base64": pcm_base64,
                "timestamp": asyncio.get_event_loop().time()
            }
            await websocket.send(json.dumps(chunk_msg))
            await asyncio.sleep(0.1)  # 100ms间隔

        # 结束识别
        end_msg = {"type": "end"}
        await websocket.send(json.dumps(end_msg))

        # 接收响应
        async for message in websocket:
            data = json.loads(message)
            print(f"ASR响应: {data}")

            if data.get("type") == "final":
                print(f"最终识别结果: {data['text']}")
                break

async def tts_client():
    """TTS WebSocket客户端"""
    uri = "ws://localhost:8000/tts/stream"

    async with websockets.connect(uri) as websocket:
        # 发送合成请求
        request = {
            "text": "派蒙想吃好吃的东西",
            "voice": "female_general",
            "speed": 1.0
        }
        await websocket.send(json.dumps(request))

        # 接收音频流
        async for message in websocket:
            data = json.loads(message)
            print(f"TTS响应: {data.get('type', 'unknown')}")

            if data.get("type") == "audio":
                # 处理音频数据
                audio_data = base64.b64decode(data["pcm_base64"])
                print(f"收到音频块: {len(audio_data)} bytes")

            elif data.get("type") == "end":
                print(f"合成完成，总时长: {data['duration']}秒")
                break

# 运行示例
if __name__ == "__main__":
    print("运行ASR客户端...")
    asyncio.run(asr_client())

    print("\n运行TTS客户端...")
    asyncio.run(tts_client())
```

## 错误处理

### 常见错误码

- `BAD_REQUEST`: 请求参数错误
- `VALIDATION_ERROR`: 数据验证失败
- `SERVICE_UNAVAILABLE`: 功能未启用
- `INTERNAL`: 服务器内部错误

### 错误响应格式

```json
{
  "ok": false,
  "code": "VALIDATION_ERROR",
  "msg": "text field is required",
  "trace_id": "abc123-def456",
  "details": {
    "field": "text",
    "constraint": "min_length"
  }
}
```

## 特征开关配置

要启用知识库功能，需要修改配置文件：

```yaml
# config/development.yaml
features:
  kb:
    enabled: true  # 启用知识库
  viseme:
    rhubarb: false
    ovr: false
  avatar:
    mode: "live2d"
```

或通过环境变量：

```bash
export FEATURES__KB__ENABLED=true
```