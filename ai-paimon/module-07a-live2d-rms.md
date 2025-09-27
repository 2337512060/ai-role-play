 # 模块07A｜Live2D 口型（能量驱动 MVP）

 ## 目标
 用音频能量（RMS）驱动 `ParamMouthOpenY`，附眨眼与轻点头；<30ms 响应。

 ## 依赖
 - 模块01 前端音频
 - 模块06 TTS（音频流）

 ## 技术方案
 - Web Audio `AnalyserNode` 采样帧数据，计算 `RMS = sqrt(mean(frame^2))`。
 - 指数平滑：`y_t = α*y_{t-1} + (1-α)*RMS`，建议 α=0.6。
 - 映射：`mouth = clamp((y_t - t0) * k, 0, 1)`（t0≈0.02，k≈20）。
 - 参数：`ParamMouthOpenY = mouth`；情绪驱动 `MouthForm/EyeOpen/AngleX/Y/Z` 小幅变化。

 ## 风险与回退
 - 背景噪声抖动：自适应门限；最小开合阈值；插值平滑。
 - 移动端性能：降帧到 30fps；仅开合不换形。

 ## 验收标准
 - 嘴型响应自然、无明显延迟/抽动；桌面 60fps、移动端稳定。

 ## 落地清单
 - Live2D 模型加载器、参数驱动器、能量到开合映射器、情绪到表情映射器。

