 # 模块11｜部署与灰度

 ## 目标
 容器化编排，蓝绿/灰度发布，资源隔离与速回滚；特征开关可控。

 ## 依赖
 - 全链路服务容器化

 ## 技术方案
 - 编排：ASR/VAD、LLM、TTS、KB、FSM 拆分服务；WS 文本/事件；音频可 WebRTC。
 - 存储：Postgres(+pgvector)；对象存储用于音频临时缓存（TTL）。
 - 灰度：按用户/比例/地区；特征开关控制 KB/viseme/Avatar 路线。

 ## 验收标准
 - 回滚 < 5 分钟；灰度可精确控制，日志可对比。

 ## 落地清单
 - Dockerfile/Compose 或 K8s Manifests、特征开关管理、蓝绿/金丝雀策略与回滚脚本。

