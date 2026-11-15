"""Project Brain - configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Agent"
    database_url: str = f"sqlite:///{(BASE_DIR / 'project_brain.db').as_posix()}"
    storage_dir: str = str(BASE_DIR / "storage")
    memory_engine: str = "eg2"

    model_config = SettingsConfigDict(env_prefix="PB_")


settings = Settings()
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = Path(settings.storage_dir)
RAW_DIR = STORAGE_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
