from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 дней

    # Firebase — JSON-строка (на проде) или путь к файлу (локально)
    FIREBASE_CREDENTIALS_JSON: str = ""

    # Supabase Storage
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET: str = "lumio-media"

    class Config:
        env_file = ".env"


settings = Settings()
