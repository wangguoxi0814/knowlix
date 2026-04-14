import os
from pathlib import Path

from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_name() -> str:
    """确定当前环境名：系统环境变量 ENV 优先，否则读 `.env` 里的 ENV，默认 dev。"""
    explicit = os.environ.get("ENV")
    if explicit is not None and str(explicit).strip():
        return str(explicit).strip()
    env_path = Path(".env")
    if env_path.is_file():
        values = dotenv_values(env_path)
        v = values.get("ENV")
        if v is not None and str(v).strip():
            return str(v).strip()
    return "dev"


def _env_file_paths() -> tuple[str, str]:
    """先加载公共 `.env`，再加载 `.env.<ENV>`；同名变量以后者为准。缺失文件会被忽略。"""
    name = _resolve_env_name()
    return (".env", f".env.{name}")


class Settings(BaseSettings):
    """
    Settings for the knowlix project.
    """

    PG_DATABASE_URL: str = ""
    LLM_API_KEY: str = ""
    ENV: str = "dev"
    DEBUG: bool = False
    RUN_DB_TESTS: int = 0

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="allow",
    )


# 全局单例：合并 `.env` 与 `.env.<ENV>`
settings = Settings(_env_file=_env_file_paths())
