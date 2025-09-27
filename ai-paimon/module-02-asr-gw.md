 # 模块02｜ASR 网关（faster‑whisper + VAD）

 ## 目标
 低延迟中文流式转写，稳定端点检测，兼容嘈杂环境。

 ## 依赖
 - 模块00 契约（/asr/stream）

 ## 技术方案
import requests

url = "https://api.siliconflow.cn/v1/audio/transcriptions"

files = { "file": "open('example-file', 'rb')" }
payload = { "model": "FunAudioLLM/SenseVoiceSmall" }
headers = {"Authorization": "Bearer <token>"}

response = requests.post(url, data=payload, files=files, headers=headers)

print(response.json())
音系列
创建语音转文本请求
Creates an audio transcription.

POST
/
audio
/
transcriptions

Try it
Authorizations
​
Authorization
stringheaderrequired
Use the following format for authentication: Bearer <your api key>

Body
multipart/form-data
​
file
filerequired
The audio file object (not file name) to transcribe

​
model
enum<string>required
Corresponding Model Name. To better enhance service quality, we will make periodic changes to the models provided by this service, including but not limited to model on/offlining and adjustments to model service capabilities. We will notify you of such changes through appropriate means such as announcements or message pushes where feasible.

Available options: FunAudioLLM/SenseVoiceSmall, TeleAI/TeleSpeechASR 
Example:
"FunAudioLLM/SenseVoiceSmall"

Response

200

application/json
200

Represents a transcription response returned by model, based on the provided input.

​
text
stringrequired
The transcribed text.

 ## 参数建议
 - VAD 帧长 20–30ms；语音最小时长 200ms；尾静音 300–500ms 判终止。
 - Whisper beam_size=1、best_of=1；温度退火关闭；中文优先。

 ## 风险与回退
 - 噪声/重叠说话：提高门限 + 二次确认。
 - 幻觉补字：UI “非专业记录”；关键内容用户确认。

 ## 验收标准
 - 首包 < 500ms；端点误检/漏检可控；连续口述稳定。
 - WER 在标注集达标；日志可定位异常样例。

 ## 落地清单
 - WS 处理器、VAD 管线、转写缓冲、partial/final 事件、节流/限流。

