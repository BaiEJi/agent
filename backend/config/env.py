"""
环境变量配置模块

使用 pydantic BaseSettings 管理所有环境变量。
- 自动读取 .env 文件
- 自动做类型校验
- 所有字段必须在 .env 中显式声明，缺少即报错
- 不设置默认值，确保配置透明可控

使用方式:
    from config.env import settings
    print(settings.OPENAI_API_KEY)
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    全局配置类

    所有环境变量在此定义，字段名即环境变量名（大写）。
    pydantic 会自动：
    1. 从 .env 文件读取
    2. 从系统环境变量读取（优先级更高）
    3. 做类型校验，缺少必填字段或类型不匹配时直接报错

    注意：所有字段不设置默认值，必须在 .env 中显式声明。
    """

    # --- OpenAI API 配置 ---
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    OPENAI_MODEL: str

    # --- PostgreSQL 数据库配置 ---
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    @property
    def DATABASE_URL(self) -> str:
        """
        拼接 PostgreSQL 异步连接串
        使用 asyncpg 驱动，格式: postgresql+asyncpg://user:pass@host:port/db
        """
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- Redis 配置 ---
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str
    REDIS_DB: int

    @property
    def REDIS_URL(self) -> str:
        """拼接 Redis 连接串，格式: redis://:password@host:port/db"""
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # --- 服务配置 ---
    APP_HOST: str
    APP_PORT: int
    APP_ENV: str

    @property
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return self.APP_ENV == "production"

    # --- 日志配置 ---
    LOG_LEVEL: str
    LOG_ROTATION: str
    LOG_RETENTION: str

    # --- pydantic Settings 配置 ---
    # env_file: 指定 .env 文件路径
    # env_file_encoding: 编码格式
    # case_sensitive: 环境变量名大小写敏感（大写）
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# ============================================================
# 全局单例
# 整个应用通过 from config.env import settings 使用同一份配置
# pydantic 会在实例化时自动读取 .env 并校验
# ============================================================
settings = Settings()
