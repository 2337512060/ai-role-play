 # 模块09B｜实时 viseme（OVR LipSync）

 ## 目标
 实时从音频流推断 15 维 viseme（PP/FF/TH/.../SIL），直接驱动 VRM/RPM 的同名 blendshapes。

 ## 依赖
 - 模块07B VRM 3D

 ## 技术方案
 - OVR Runtime/库接入（WebGL/原生/Unity WebGL）；将 viseme 权重映射到表情系统。
 - 插值与平滑：过零抑制、最小保持时间、防抖动滤波。

 ## 风险与回退
 - 浏览器/平台限制：降级为 07A 能量驱动或 09A 离线覆盖。
 - 资源占用：动态降采样与帧率。

 ## 验收标准
 - 端到端延迟 < 120ms；嘴型细节与辅音闭合更自然。

 ## 落地清单
 - OVR 绑定器、权重映射表、插值器与降级策略。

