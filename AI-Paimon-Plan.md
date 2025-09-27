 # AI派蒙（风格化模拟）模块化落地方案（可直接上线演示）

 > 仅用 LLM + ASR + TTS + 基础向量库；不依赖第三方 Agent 框架。角色为“粉丝向风格化模拟”，UI 明示“非官方”。不复刻原作台词/剧情/声线；仅索引公共百科/自写世界观。TTS 使用通用女声参数；默认不联网检索。

 ---

 ## 目录
 - 总体目标与合规前提
 - 架构总览（前端/后端/数据）
 - 接口契约（统一消息格式）
 - 模块化路线图（搭积木式推进）
 - 动画与口型（2D/3D 两路线）
 - 模型与组件选型
 - 部署与可观测
 - 性能指标与评测
 - 里程碑（2–6 周）
 - 风险与对策
 - 交付物模板
 - 参考链接

 ---

 ## 总体目标与合规前提
 - 目标：构建“派蒙（风格化）”双向语音互动与口型同步的可上线演示，强调粉丝向风格模拟与非官方属性。
 - 合规前提：
   - 不复刻原作台词/剧情/声线；UI 明示“非官方/风格化模拟”。
   - 仅索引公共百科或自写世界观；不引入受版权保护原文。
   - TTS 仅用通用女声；严禁声纹克隆。
   - 默认关闭联网检索，仅用本地向量库；可灰度开启。
   - 显示“非专业记录”提示以应对 ASR 偶发幻觉。

 ---

 ## 架构总览

 ### 前端（Next.js + TypeScript）
 - 录音：`MediaRecorder`/`AudioWorklet`/WebRTC，分片上送。
 - 播放：TTS 音频流解码播放；UI 状态机（录音/思考/说话）。
 - 动画：
   - 路线A（2D）：Live2D Cubism Web SDK 或 `pixi-live2d-display`。
   - 路线B（3D）：three.js + `@pixiv/three-vrm`；可选 Ready Player Me。
 - 低延迟口型先行：`AnalyserNode` 采能量驱动嘴型开合，后续用 viseme 覆盖。

 ### 后端/边缘（FastAPI + WebSocket）
 - `asr-gw`：faster-whisper（CTranslate2）+ VAD（WebRTC/Silero），流式转写。
 - `dialog-core`：自研 FSM 策略（闲聊/求助/事实/故事），显式工具调用（KB 检索、情绪/语义标签）。
 - `style-fuse`：按“句长≈19/问≈0.5/感叹≈0.3/语气词库”二次重写。
 - `safety`：提示约束 + 敏感分类 + 关键词/正则 + 拒答模板。
 - `tts-svc`：XTTS‑v2 流式合成，返回音频分片；可选携带对齐标记。
 - `viseme-svc`（可选）：Rhubarb（离线/准实时）或 OVR LipSync（实时）。

 ### 数据与模型
 - 向量库：pgvector（或 FAISS）。
 - 嵌入：BGE‑M3（多语、多粒度，适配中文）。
 - LLM：Qwen2.5‑Instruct 7B/14B 或 Yi‑1.5‑Chat（中文稳）。

 ---

 ## 接口契约（统一消息格式）

 ### 1) ASR 流式（WebSocket） `/asr/stream`
 - C→S：
   ```json
   {"type":"init","sr":16000,"lang":"zh"}
   {"type":"chunk","pcm_base64":"..."}
   {"type":"end"}
   ```
 - S→C：
   ```json
   {"type":"vad","event":"start|end"}
   {"type":"partial","text":"...","final":false}
   {"type":"final","text":"...","timestamps":[[0.12,0.45]]}
   ```

 ### 2) 对话生成（HTTP） `/dialog/generate`
 - Req：
   ```json
   {"text":"...","session_id":"s1","flags":{"kb":true}}
   ```
 - Resp：
   ```json
   {"reply":"...","emotion":"happy|curious|thinking","trace":{"policy":"chitchat|help|fact|story","kb_sources":[]}}
   ```

 ### 3) TTS 流式（WebSocket） `/tts/stream`
 - C→S：
   ```json
   {"text":"...","voice":"female_general","speed":1.0}
   ```
 - S→C：
   ```json
   {"type":"audio","pcm_base64":"...","sr":24000}
   {"type":"marker","phoneme":"AA","t":0.123}
   {"type":"end","duration":1.82}
   ```

 ### 4) 口型时间轴（HTTP） `/viseme/timeline`
 - Req：`multipart/form-data` 或：
   ```json
   {"wav_url":"..."}
   ```
 - Resp：
   ```json
   {"visemes":[{"t":0.12,"id":"A","w":0.8}],"src":"rhubarb"}
   ```

 ### 5) 知识库检索（HTTP） `/kb/search`
 - Req：
   ```json
   {"query":"...","topk":5}
   ```
 - Resp：
   ```json
   {"hits":[{"text":"...","source":"public|custom","score":0.82}],"embedding_model":"bge-m3"}
   ```

 ---

 ## 模块化路线图（搭积木推进）

 > 每个模块包含 目标/依赖/验收；均可独立开关，便于灰度与回退。

 ### 模块0｜项目骨架与契约
 - 目标：统一接口、错误码、特征开关；OpenAPI/WS 文档可用。
 - 依赖：无。
 - 验收：本地可跑 stub 回环；前端接入成功。

 ### 模块1｜前端音频采集与播放（MVP）
 - 目标：按住说话→上行音频；下行流式播放；UI 状态同步。
 - 依赖：模块0。
 - 验收：看到“说-想-说”的闭环（后端可用假数据）。

 ### 模块2｜ASR 网关（faster‑whisper + VAD）
 - 目标：低延迟、端点稳定、中文优先。
 - 依赖：模块1。
 - 验收：首包 < 500ms；嘈杂容错可调门限。

 ### 模块3｜对话核心 FSM（自研）
 - 目标：闲聊/求助/事实/故事四策略；工具调用显式。
 - 依赖：模块2。
 - 验收：trace 可视化；不同意图触发正确策略。

 ### 模块4｜StyleFuse 风格重写
 - 目标：稳定风格（句长≈19、问≈0.5、感叹≈0.3、语气词）。
 - 依赖：模块3。
 - 验收：风格指标达标；无侵权表达。

 ### 模块5｜安全与合规
 - 目标：提示约束 + 敏感分类 + 关键词/正则 + 拒答模板。
 - 依赖：模块3/4。
 - 验收：红线样例全拦截，低误伤。

 ### 模块6｜TTS 服务（XTTS‑v2，流式）
 - 目标：自然度稳定、首包快；可产对齐标记或配合 Rhubarb。
 - 依赖：模块3/4/5。
 - 验收：RTF < 1；卡顿 < 5%；音色一致。

 ### 模块7A｜Live2D（能量驱动口型，MVP）
 - 目标：RMS→`ParamMouthOpenY`，附眨眼/轻点头。
 - 依赖：模块1/6。
 - 验收：视觉响应 < 30ms；观感自然。

 ### 模块8｜知识库（BGE‑M3 + pgvector/FAISS）
 - 目标：本地检索；证据可视化与来源标注。
 - 依赖：模块3。
 - 验收：命中率/相关性稳定；默认关闭检索，可灰度开。

 ### 模块9A｜精确口型（Rhubarb 离线/准实时）
 - 目标：TTS→WAV→Rhubarb→A‑H/X 序列→映射 `MouthForm/Open`。
 - 依赖：模块6/7A。
 - 验收：嘴型对齐误差 < 80ms；移动端可降级。

 ### 模块7B｜3D VRM（基础表情）
 - 目标：three.js + `@pixiv/three-vrm` 加载与表情控制。
 - 依赖：模块1/6。
 - 验收：桌面 60fps；移动端可自动降级至 2D。

 ### 模块9B｜实时 viseme（OVR LipSync，Pro）
 - 目标：音频流→15 维 viseme→VRM blendshapes。
 - 依赖：模块7B。
 - 验收：延迟 < 120ms；细节明显提升。

 ### 模块10｜可观测与指标
 - 目标：端到端监控：延迟、WER、TTS 断续、口型误差、风格一致性。
 - 依赖：全链路。
 - 验收：仪表盘可定位问题；SLO 统计可导出。

 ### 模块11｜部署与灰度
 - 目标：容器化编排；蓝绿/灰度；回滚迅速。
 - 依赖：全链路。
 - 验收：回滚 < 5 分钟；资源隔离与限流生效。

 ### 模块12｜评测与优化
 - 目标：首包 300–800ms；风格一致性；口型对齐；移动端功耗。
 - 依赖：全链路。
 - 验收：报告留档与改进计划。

 ---

 ## 动画与口型（2D/3D）

 ### MVP：能量驱动（Live2D）
 - 计算：`RMS = sqrt(mean(frame^2))`；指数平滑 `y_t = α*y_{t-1} + (1-α)*RMS`（建议 α=0.6）。
 - 映射：`mouth = clamp((y_t - t0) * k, 0, 1)`（建议 t0≈噪声阈 0.02，k≈20）。
 - 参数：`ParamMouthOpenY = mouth`；`ParamMouthForm` 随情绪微调；眨眼 `EyeOpen`、头部 `AngleX/Y/Z` 轻摆。

 ### 精确口型：viseme/phoneme 驱动
 - Rhubarb（离线/准实时）：TTS→WAV→`rhubarb -f wav -o json`→A‑H/X 时间轴→插值驱动 Live2D `Open/Form`。
 - OVR LipSync（实时，3D 佳）：从音频流推 15 维 viseme（PP/FF/TH/.../SIL）→VRM/OVR 同名 blendshapes。

 ### 3D Avatar（two choices）
 - three.js + `@pixiv/three-vrm`：`GLTFLoader` 加载、`VRMExpressionManager` 控表情/嘴型。
 - Ready Player Me：原生支持 OVR viseme；快速打样。

 ---

 ## 模型与组件选型（建议）
 | 能力 | 组件 | 备注 |
 |---|---|---|
 | ASR | faster‑whisper small/int8 | CTranslate2，高效低显存 |
 | VAD | webrtcvad / Silero VAD | 帧级端点，降延迟 |
 | TTS | Coqui XTTS‑v2 | 多语/多说话人，流式 |
 | 嵌入 | BGE‑M3 | 多语/多粒度，中文稳 |
 | 向量库 | pgvector 或 FAISS | Postgres 直集成或独立库 |
 | LLM | Qwen2.5‑Instruct 7B/14B；Yi‑1.5‑Chat | 中文对话一致性好 |
 | 2D | Live2D Cubism Web SDK | Web 可控参数成熟 |
 | 3D | three‑vrm / Ready Player Me | VRM 表情/OVR viseme |

 > 注意：Whisper 系列在极端场景偶有补字幻觉；在 UI 显示“非专业记录”。

 ---

 ## 部署与可观测
 - 编排：各服务容器化（ASR/VAD、LLM、TTS、KB、FSM）。
 - 进阶：NVIDIA Triton 或 CTranslate2 服务化，争取稳定吞吐与批处理。
 - 传输：WebSocket（文本/事件/口型）、音频可 WebRTC。
 - 存储：Postgres（会话摘要/向量）、对象存储（音频临时缓存）。
 - 可观测：Prometheus + Grafana；Sentry 捕获前端异常；采样日志便于追踪。

 ---

 ## 性能指标与评测
 - 延迟：首包 300–800ms（ASR 端点 + 口型先行 + TTS 流）。
 - ASR：中文 WER；静音/重叠鲁棒性。
 - TTS：主观自然度、停连/重音合理性；断续率。
 - 对话：风格一致性（句长、问/感叹比、语气词密度）。
 - 动画：口型‑音频对齐误差（ms）、帧率、移动端耗电。

 ---

 ## 里程碑（2–6 周）
 - 第 1 周（MVP 骨架）：模块0/1/2/3/4/5/7A → 语音→对话→TTS→2D 口型闭环。
 - 第 2–3 周（体验提升）：模块8（KB）/6 强化、9A（Rhubarb）、指标接入与打磨。
 - 第 4–6 周（优化与演示）：模块7B/9B（3D 与实时嘴型）、10（可观测）、11（灰度）、12（评测）。

 ---

 ## 风险与对策
 - 版权/肖像：避免原作元素与台词；使用原创立绘/模型；不做声纹克隆。
 - ASR 幻觉/噪声：VAD 门限与静音补偿；关键位置二次确认；“非专业记录”提示。
 - 口型与延迟：先能量驱动（<30ms），稳定后覆盖 viseme；移动端降级仅开合不换形。

 ---

 ## 交付物模板
 1. 角色卡 YAML（风格参数：句长/问感叹比/语气词/称呼/拒答策略）。
 2. FSM 配置（四策略 + 触发条件 + 输出后处理）。
 3. StyleFuse 模板（三段式：信息→口癖→收尾反问）。
 4. Live2D/VRM 参数映射表（`RMS→MouthOpenY`、`viseme→MouthForm`、`emotion→Eye/Angle/Body`；附默认曲线与阈值）。
 5. 接口定义与伪实现：
    - `/asr/stream`（WS，返部分转写 + 端点事件）
    - `/dialog/generate`（文本→回复 JSON + `emotion`）
    - `/tts/stream`（文本→音频分片；header 附采样率/时长）
    - `/viseme/timeline`（wav→Rhubarb JSON）
    - `/kb/search`（query→片段+来源）

 ---

 ## 参考链接（可选）
 - Live2D Cubism Web SDK 手册：https://docs.live2d.com/en/cubism-sdk-manual/cubism-sdk-for-web/
 - three‑vrm 文档与示例：https://pixiv.github.io/three-vrm/
 - MDN Web Audio（AnalyserNode）：https://developer.mozilla.org/en-US/docs/Web/API/AnalyserNode
 - faster‑whisper（CTranslate2）：https://github.com/SYSTRAN/faster-whisper
 - Coqui XTTS‑v2：
   - HF 模型卡：https://huggingface.co/coqui/XTTS-v2
   - 文档：https://docs.coqui.ai/en/stable/models/xtts.html
 - Rhubarb Lip Sync（音频→嘴型）：https://github.com/DanielSWolf/rhubarb-lip-sync
 - pgvector：https://github.com/pgvector/pgvector
 - BGE‑M3：
   - HF 模型卡：https://huggingface.co/BAAI/bge-m3
 - NVIDIA Triton Quickstart：https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/getting_started/quickstart.html
 - OVR LipSync（Ready Player Me 指引）：https://docs.readyplayer.me/ready-player-me/api-reference/avatars/morph-targets/oculus-ovr-libsync

