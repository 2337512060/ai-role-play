 # 模块00｜项目骨架与统一契约（API/消息格式）

 ## 目标
 统一 API、消息格式、错误码与特征开关，保证后续模块可插拔、低耦合。

 ## 依赖
 无（其他模块依赖本模块约定）。

 ## 接口定义
 
 1) ASR 流式（WebSocket） `/asr/stream`
 - 客户端→服务端：
   ```json
   {"type":"init","sr":16000,"lang":"zh"}
   {"type":"chunk","pcm_base64":"..."}
   {"type":"end"}
   ```
 - 服务端→客户端：
   ```json
   {"type":"vad","event":"start|end"}
   {"type":"partial","text":"...","final":false}
   {"type":"final","text":"...","timestamps":[[0.12,0.45]]}
   ```

 2) 对话生成（HTTP） `/dialog/generate`
 - 请求：
   ```json
   {"text":"...","session_id":"s1","flags":{"kb":true}}
   ```
 - 响应：
   ```json
   {"reply":"...","emotion":"happy|curious|thinking","trace":{"policy":"chitchat|help|fact|story","kb_sources":[]}}
   ```

 3) TTS 流式（WebSocket） `/tts/stream`
 - 客户端→服务端：
   ```json
   {"text":"...","voice":"female_general","speed":1.0}
   ```
 - 服务端→客户端：
   ```json
   {"type":"audio","pcm_base64":"...","sr":24000}
   {"type":"marker","phoneme":"AA","t":0.123}
   {"type":"end","duration":1.82}
   ```

 4) 口型时间轴（HTTP） `/viseme/timeline`
 - 请求：`multipart/form-data` 或：
   ```json
   {"wav_url":"..."}
   ```
 - 响应：
   ```json
   {"visemes":[{"t":0.12,"id":"A","w":0.8}],"src":"rhubarb"}
   ```

 5) 知识库检索（HTTP） `/kb/search`
 - 请求：
   ```json
   {"query":"...","topk":5}
   ```
 - 响应：
   ```json
   {"hits":[{"text":"...","source":"public|custom","score":0.82}],"embedding_model":"bge-m3"}
   ```

 ## 错误码与通用结构
 ```json
 {"ok":false,"code":"BAD_REQUEST|INTERNAL|RATE_LIMIT|UNAUTHORIZED","msg":"...","trace_id":"..."}
 ```

 ## 特征开关（建议）
 - `feature.kb.enabled=false`
 - `feature.viseme.rhubarb=false`
 - `feature.viseme.ovr=false`
 - `feature.avatar.mode=live2d|vrm`

 ## 验收标准
 - OpenAPI/WS 文档可用；前端可接入并与假数据回环。
 - 各模块实现可独立启停，不破坏接口契约。

