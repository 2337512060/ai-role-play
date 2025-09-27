"""
配置管理模块
使用Pydantic Settings进行类型安全的配置管理
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False


class FeatureFlags(BaseModel):
    """特征开关配置"""

    class ASRConfig(BaseModel):
        provider: str = "mock"  # mock|vendorA|vendorB

    class TTSProviderConfig(BaseModel):
        provider: str = "mock"  # mock|vendorA|vendorB
        voice_profile_id: Optional[str] = None  # 语音克隆档（需授权）

    class KBConfig(BaseModel):
        enabled: bool = False

    class VisemeConfig(BaseModel):
        rhubarb: bool = False
        ovr: bool = False

    class AvatarConfig(BaseModel):
        mode: str = "live2d"  # live2d|vrm

    asr: ASRConfig = Field(default_factory=ASRConfig)
    tts: TTSProviderConfig = Field(default_factory=TTSProviderConfig)
    kb: KBConfig = Field(default_factory=KBConfig)
    viseme: VisemeConfig = Field(default_factory=VisemeConfig)
    avatar: AvatarConfig = Field(default_factory=AvatarConfig)


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class ASRConfig(BaseModel):
    """ASR服务配置"""

    class SiliconFlowConfig(BaseModel):
        api_url: str = "https://api.siliconflow.cn/v1/audio/transcriptions"
        model: str = "TeleAI/TeleSpeechASR"
        timeout: float = 10.0
        max_retries: int = 3

    class VADConfig(BaseModel):
        frame_length_ms: int = 25
        energy_threshold: float = 500.0
        min_speech_duration_ms: int = 200
        silence_duration_ms: int = 400

    class AudioConfig(BaseModel):
        sample_rate: int = 16000
        max_buffer_duration: float = 10.0
        chunk_overlap_ms: int = 50

    # 服务模式：'mock' 或 'siliconflow'
    service_mode: str = "mock"
    siliconflow: SiliconFlowConfig = Field(default_factory=SiliconFlowConfig)
    vad: VADConfig = Field(default_factory=VADConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)


class DialogConfig(BaseModel):
    """对话服务配置"""

    class FSMConfig(BaseModel):
        max_transitions: int = 20  # 最大状态转换次数
        kb_search_timeout: float = 5.0  # KB搜索超时时间
        enable_style_fuse: bool = False  # 启用风格融合（Module 04）
        enable_safety: bool = False  # 启用安全检查（Module 05）

    class StyleFuseConfig(BaseModel):
        enabled: bool = True  # 启用风格融合
        target_avg_length: int = 19  # 目标平均句长
        question_ratio_min: float = 0.45  # 问句比例下限
        question_ratio_max: float = 0.55  # 问句比例上限
        exclamation_ratio_min: float = 0.25  # 感叹句比例下限
        exclamation_ratio_max: float = 0.35  # 感叹句比例上限
        ellipsis_ratio_min: float = 0.15  # 省略号比例下限
        ellipsis_ratio_max: float = 0.25  # 省略号比例上限
        mood_particle_density: float = 0.6  # 语气词密度
        max_sentence_length: int = 35  # 句子最大长度
        min_sentence_length: int = 8  # 句子最小长度
        max_total_length: int = 160  # 回复最大总长度
        min_total_length: int = 10  # 回复最小总长度
        address_term: str = "旅行者"  # 称呼用词
        max_rewrite_attempts: int = 2  # 最大重写尝试次数

    class NLUConfig(BaseModel):
        min_confidence_threshold: float = 0.3  # 最小置信度阈值
        fallback_policy: str = "chitchat"  # 回退策略

    # 服务模式：'mock' 或 'fsm'
    service_mode: str = "mock"
    fsm: FSMConfig = Field(default_factory=FSMConfig)
    style_fuse: StyleFuseConfig = Field(default_factory=StyleFuseConfig)
    nlu: NLUConfig = Field(default_factory=NLUConfig)


class StyleConfig(BaseModel):
    """StyleFuse 风格配置（默认值可被 YAML 覆盖）"""
    sentence_len_min: int = 14
    sentence_len_max: int = 20
    ask_ratio_target: float = 0.5
    exclaim_ratio_target: float = 0.3
    max_length: int = 160
    mood_words: List[str] = Field(default_factory=lambda: ["啊", "呢", "呀", "啦", "欸", "哇", "哦", "嘿", "嘛", "哎"])
    traveler_address: str = "旅行者"


class SafetyConfig(BaseModel):
    """安全检查配置"""
    enabled: bool = True  # 启用安全检查

    # 分类阈值配置 (0.0-1.0)
    illegal_threshold: float = 0.7       # 违法内容阈值
    explicit_threshold: float = 0.8      # 露骨内容阈值
    minor_unsafe_threshold: float = 0.6  # 未成年人不宜阈值
    violence_threshold: float = 0.75     # 暴力内容阈值
    harassment_threshold: float = 0.7    # 骚扰内容阈值
    privacy_threshold: float = 0.9       # 隐私泄露阈值
    spam_threshold: float = 0.8          # 垃圾信息阈值
    polarizing_threshold: float = 0.6    # 极化内容阈值

    # 检查组件开关
    keyword_filter_enabled: bool = True   # 启用关键词过滤
    regex_filter_enabled: bool = True     # 启用正则表达式过滤
    classifier_enabled: bool = True       # 启用分类器
    context_check_enabled: bool = True    # 启用上下文检查

    # 处理配置
    max_processing_time: float = 1000.0   # 最大处理时间(毫秒)
    whitelist_enabled: bool = True        # 启用白名单
    escalation_enabled: bool = True       # 启用升级提醒
    redirect_enabled: bool = True         # 启用话题转向

    # 自定义关键词 (可通过YAML配置覆盖)
    custom_keywords: Dict[str, List[str]] = Field(default_factory=dict)


class MockConfig(BaseModel):
    """Mock服务配置"""

    class ASRConfig(BaseModel):
        delay_ms: int = 100
        response_texts: List[str] = Field(default_factory=lambda: [
            "你好",
            "今天天气怎么样",
            "派蒙想吃好吃的"
        ])

    class DialogConfig(BaseModel):
        response_templates: List[str] = Field(default_factory=lambda: [
            "欸！旅行者说的话，派蒙听不太懂呢...",
            "哇～这个派蒙知道！",
            "唔...让派蒙想想看"
        ])

    class TTSConfig(BaseModel):
        # 基础音频参数
        sample_rate: int = 24000
        chunk_size: int = 1024

        # Provider配置
        primary_provider: str = "mock"  # mock | fishaudio
        fallback_providers: List[str] = Field(default_factory=lambda: ["mock"])

        # FishAudio配置
        fishaudio_api_key: str = Field(default="", env="FISHAUDIO_API_KEY")
        fishaudio_model_id: str = "304d6864fe86478c922e72a7b41973f7"

        # 合成参数
        default_voice: str = "female_general"
        default_speed: float = 1.0
        default_volume: float = 0.0
        default_temperature: float = 0.7
        default_top_p: float = 0.7

        # 流式参数
        chunk_length: int = 200
        audio_format: str = "pcm"
        enable_emotions: bool = True

        # 性能参数
        max_retries: int = 3
        retry_delay: float = 1.0
        timeout_seconds: float = 30.0

        # 音素标记
        enable_phoneme_markers: bool = True
        marker_confidence_threshold: float = 0.5

    asr: ASRConfig = Field(default_factory=ASRConfig)
    dialog: DialogConfig = Field(default_factory=DialogConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)


class Settings(BaseSettings):
    """主配置类"""

    # 环境配置
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    debug: bool = Field(default=False, env="DEBUG")
    siliconflow_api_key: str = Field(default="", env="SILICONFLOW_API_KEY")

    # 子配置
    server: ServerConfig = Field(default_factory=ServerConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    asr: ASRConfig = Field(default_factory=ASRConfig)
    dialog: DialogConfig = Field(default_factory=DialogConfig)
    style: StyleConfig = Field(default_factory=StyleConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    mock: MockConfig = Field(default_factory=MockConfig)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"


def load_config_from_yaml(file_path: Path) -> Dict[str, Any]:
    """从YAML文件加载配置"""
    if not file_path.exists():
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def get_config_file_path(environment: str) -> Path:
    """获取配置文件路径"""
    project_root = Path(__file__).parent.parent.parent
    config_dir = project_root / "config"

    config_file = config_dir / f"{environment}.yaml"
    if not config_file.exists():
        config_file = config_dir / "development.yaml"

    return config_file


def create_settings() -> Settings:
    """创建配置实例"""
    # 获取环境变量
    environment = os.getenv("ENVIRONMENT", "development")

    # 加载YAML配置
    config_file = get_config_file_path(environment)
    yaml_config = load_config_from_yaml(config_file)

    # 创建设置实例，YAML配置会被环境变量覆盖
    return Settings(**yaml_config)


# 全局配置实例
settings = create_settings()


def get_settings() -> Settings:
    """获取配置实例（依赖注入用）"""
    return settings
