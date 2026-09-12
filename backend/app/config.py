"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: str = "development"
    app_name: str = "Ledger Lens"
    app_version: str = "1.0.0"
    debug: bool = True
    secret_key: str = "change_in_production"

    # Database
    database_url: str = "sqlite+aiosqlite:///./ledger_lens.db"

    # CORS
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    # Data paths (relative to backend/ directory)
    raw_data_dir: str = "../data/raw"
    processed_data_dir: str = "../data/processed"
    models_dir: str = "../models"

    @property
    def raw_data_path(self) -> Path:
        return Path(__file__).parent.parent.resolve() / Path(self.raw_data_dir)

    @property
    def processed_data_path(self) -> Path:
        return Path(__file__).parent.parent.resolve() / Path(self.processed_data_dir)

    @property
    def models_path(self) -> Path:
        return Path(__file__).parent.parent.resolve() / Path(self.models_dir)

    # ML Configuration
    anomaly_contamination: float = 0.05
    anomaly_random_state: int = 42
    similarity_threshold: float = 0.75

    # Risk Weights (must sum to 1.0)
    risk_weight_financial: float = 0.30
    risk_weight_progress: float = 0.20
    risk_weight_timeline: float = 0.20
    risk_weight_rules: float = 0.15
    risk_weight_similarity: float = 0.10
    risk_weight_data_quality: float = 0.05

    # Demo Mode
    demo_mode: bool = True
    demo_projects_count: int = 200


@lru_cache()
def get_settings() -> Settings:
    return Settings()
