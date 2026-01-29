"""
Application configuration using Pydantic Settings.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "IOSYS ItemBank AI"
    app_version: str = "1.0.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql://poc_user:poc_password@db:5432/poc_itembank"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Embeddings
    embeddings_path: str = "/app/data/qwen_embeddings_all_subjects_2b_multimodal.npz"
    embedding_dim: int = 2048

    # Search defaults
    default_top_k: int = 10
    default_threshold: float = 0.5
    max_top_k: int = 100

    # Performance
    search_timeout_ms: int = 5000

    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 1024
    openai_temperature: float = 0.7

    # RAG Configuration
    rag_context_limit: int = 5
    rag_system_prompt: str = """당신은 교육 문항 전문가입니다.
주어진 검색 결과를 바탕으로 사용자의 질문에 정확하게 답변해주세요.
검색된 문항 정보를 참고하여 답변하되, 없는 정보는 만들어내지 마세요."""

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
