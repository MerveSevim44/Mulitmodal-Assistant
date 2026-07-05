"""
Application configuration.
Loads environment variables with Pydantic Settings for type safety and validation.
"""
import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Application ---
    APP_NAME: str = "Akademik Bellek API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:3000"

    # --- Supabase ---
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # --- AI API Keys ---
    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    HUGGINGFACE_TOKEN: str = ""
    GEMINI_API_KEY: str = ""

    # --- ChromaDB ---
    CHROMA_DB_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ai_engine", "chroma_db"
    )

    # --- File Storage ---
    TEMP_UPLOAD_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ai_engine", "data"
    )

    # --- LLM Settings ---
    LLM_MODEL: str = "openai/gpt-oss-120b"
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 1000

    # --- Whisper Settings ---
    WHISPER_MODEL: str = "whisper-large-v3-turbo"
    WHISPER_LANGUAGE: str = "tr"

    # --- Vision Settings ---
    VISION_MODEL: str = "meta-llama/llama-4-maverick"

    # --- Embedding Settings ---
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    # --- Retrieval Settings ---
    RETRIEVAL_K: int = 8
    RETRIEVAL_FETCH_K: int = 25

    class Config:
        env_file = (
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                ".env"
            )
        )
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — created once, reused everywhere."""
    return Settings()
