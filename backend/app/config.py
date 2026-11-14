from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Forecastly"
    DEBUG: bool = False
    PORT: int = 8080
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: list[str] = ["*"]

    # Storage paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    STORAGE_DIR: Path = BASE_DIR / "storage"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/storage/forecastly.db"

    # Free hosting constraints
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    MAX_UPLOAD_ROWS: int = 200_000
    N_JOBS: int = 2
    ENABLE_PROPHET: bool = False
    DEFAULT_METRIC: str = "wape"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
(settings.DATA_DIR / "sample").mkdir(parents=True, exist_ok=True)
(settings.STORAGE_DIR / "artifacts").mkdir(parents=True, exist_ok=True)
(settings.STORAGE_DIR / "datasets").mkdir(parents=True, exist_ok=True)
