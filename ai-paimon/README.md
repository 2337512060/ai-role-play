 # AI派蒙（风格化模拟）模块化方案文档索引

 本目录按“搭积木”方式拆分，每个文件对应一个功能模块，便于逐个审查与灰度上线。

 - 合规与底线：`ai-paimon/compliance.md`
 - 统一契约与接口：`ai-paimon/module-00-contracts.md`
 - 前端音频与播放（MVP）：`ai-paimon/module-01-frontend-audio.md`
 - ASR 网关：`ai-paimon/module-02-asr-gw.md`
 - 对话核心 FSM：`ai-paimon/module-03-dialog-fsm.md`
 - StyleFuse 风格重写：`ai-paimon/module-04-style-fuse.md`
 - 安全与合规层：`ai-paimon/module-05-safety.md`
 - TTS 服务：`ai-paimon/module-06-tts.md`
 - 2D 口型（Live2D，能量驱动）：`ai-paimon/module-07a-live2d-rms.md`
 - 3D 表情（VRM 基础）：`ai-paimon/module-07b-vrm-3d.md`
 - 知识库（BGE‑M3 + pgvector/FAISS）：`ai-paimon/module-08-kb.md`
 - 精确口型（Rhubarb）：`ai-paimon/module-09a-viseme-rhubarb.md`
 - 实时 viseme（OVR）：`ai-paimon/module-09b-viseme-ovr.md`
 - 可观测与指标：`ai-paimon/module-10-observability.md`
 - 部署与灰度：`ai-paimon/module-11-deploy-gray.md`
 - 评测与优化：`ai-paimon/module-12-eval.md`
 - 参考链接：`ai-paimon/references.md`

 审查建议：
 - 先看 `module-00-contracts.md`（接口契约），再逐个模块。
 - 每个模块均含：目标、依赖、接口/IO、技术方案、参数默认、风险回退、验收标准、落地清单。
 - 若要删改接口，请在 00 契约模块同时更新，避免漂移。

