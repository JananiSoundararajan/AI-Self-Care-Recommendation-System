from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    openai_api_key: str = ""
    database_url: str = "sqlite:///./selfcare.db"
    chroma_persist_dir: str = "./chroma_db"
    model_path: str = "./ml/mood_classifier.joblib"
    use_mock_llm: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
