 # 模块01｜前端音频采集与播放（MVP）

 ## 目标
 按住说话→分片上行（WS）→TTS 流下行→播放；UI 显示录音/思考/说话状态。

 ## 依赖
 - 模块00 契约（/asr/stream、/tts/stream）

 ## 技术方案
 - 采集：`MediaRecorder` 或 `AudioWorklet`（16k 单声道 PCM，20–40ms 分片）。
 - 上行：WebSocket 发送 `init`→连续 `chunk`→`end`；VAD 事件可驱动 UI。
 - 下行：TTS 音频流（PCM）边收边播；可用 `AudioWorklet`/`ScriptProcessor` 拼接播放。
 - 低延迟口型先行：Web Audio `AnalyserNode` 计算 RMS，驱动 Live2D 口型开合；后续由 viseme 覆盖。

 ## 参数建议
 - 分片大小：320–640 样本（20–40ms @16kHz）。
 - 抖动缓冲：60–120ms；音频首包预热 1–2 分片。

 ## 风险与回退
 - 浏览器兼容差异：降级到 `MediaRecorder`；移动端节能模式降低刷新率。
 - 丢包：重传/冗余片头；播放端淡入淡出防爆音。

 ## 验收标准
 - 首包可听 < 800ms（含 ASR 端点 + TTS 预热）。
 - UI 状态与实际流转同步；断网重连可恢复。

 ## 落地清单
 - 组件：录音按钮、波形/能量条、状态指示、错误 Toast。
 - 工具：WS 管理器、音频拼接播放器、Analyser 口型驱动器。

