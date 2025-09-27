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

    class KBConfig(BaseModel):
        enabled: bool = False

    class VisemeConfig(BaseModel):
        rhubarb: bool = False
        ovr: bool = False

    class AvatarConfig(BaseModel):
        mode: str = "live2d"  # live2d|vrm

    kb: KBConfig = Field(default_factory=KBConfig)
    viseme: VisemeConfig = Field(default_factory=VisemeConfig)
    avatar: AvatarConfig = Field(default_factory=AvatarConfig)


class LoggingConfig(BaseModel):
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


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
        sample_rate: int = 24000
        chunk_size: int = 1024

    asr: ASRConfig = Field(default_factory=ASRConfig)
    dialog: DialogConfig = Field(default_factory=DialogConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)


class Settings(BaseSettings):
    """主配置类"""

    # 环境配置
    environment: str = Field(default="development", env="ENVIRONMENT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # 子配置
    server: ServerConfig = Field(default_factory=ServerConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
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