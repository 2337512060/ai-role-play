 # 模块03｜对话核心 FSM（自研）

 ## 目标
 有限状态机实现四策略：闲聊/求助/事实问答/故事；工具显式调用（KB 检索、情绪标注）。

 ## 依赖
 - 模块00 契约（/dialog/generate）
 - 模块08 知识库（可选）

 ## 策略与流转
 - 状态：`idle → listen → asr → nlu → plan → (kb?) → draft → style_fuse → safety → tts → stream`
 - 策略：
   - 闲聊：共情 + 1 个推进问题。
   - 求助：3 步可执行建议 + 鼓励。
   - 事实问答：先结论 ≤2 句 + 来源；然后反问 1 句。
   - 故事：120 字内一幕式，收尾给行动钩子。

 ## 输出结构
 ```json
 {"reply":"...","emotion":"happy|curious|thinking","trace":{"policy":"chitchat|help|fact|story","kb_sources":[...]}}
 ```

 ## 验收标准
 - trace 可视化；不同意图样例触发正确策略。
 - 与 StyleFuse/Safety 串联无冲突；错误可回退。

 ## 落地清单
 - NLU 粗分类器、策略选择器、KB 调用器、模板填充器、trace 记录器。

