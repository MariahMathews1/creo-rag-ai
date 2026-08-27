from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Environment-backed application settings."""

    app_name: str = "Creo NC Post Assistant API"
    app_environment: str = "development"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./data/creo_assistant.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    ai_provider: str = "mock"
    embedding_provider: str = "mock"
    document_storage_path: str = "./data/documents"
    max_document_upload_mb: int = Field(default=50, gt=0)
    document_chunk_size: int = Field(default=900, ge=100)
    document_chunk_overlap: int = Field(default=150, ge=0)
    retrieval_top_k: int = Field(default=6, gt=0)
    retrieval_min_score: float = Field(default=0.30, ge=0, le=1)
    enable_retrieval_debug: bool = False
    max_program_source_upload_mb: int = Field(default=25, gt=0)
    alignment_high_confidence: float = Field(default=0.90, ge=0, le=1)
    alignment_medium_confidence: float = Field(default=0.70, ge=0, le=1)
    alignment_min_confidence: float = Field(default=0.45, ge=0, le=1)
    alignment_coordinate_tolerance: float = Field(default=0.001, gt=0)
    alignment_feed_tolerance_percent: float = Field(default=2.0, ge=0)
    alignment_spindle_tolerance_percent: float = Field(default=1.0, ge=0)
    alignment_candidate_window: int = Field(default=20, gt=0)
    enable_alignment_debug: bool = False
    profile_extraction_provider: str = "mock"
    profile_extraction_model: str = ""
    profile_extraction_top_k: int = Field(default=8, gt=0)
    profile_extraction_min_score: float = Field(default=0.25, ge=0, le=1)
    profile_extraction_high_confidence: float = Field(default=0.90, ge=0, le=1)
    profile_extraction_medium_confidence: float = Field(default=0.70, ge=0, le=1)
    profile_extraction_min_recommended_confidence: float = Field(default=0.45, ge=0, le=1)
    enable_profile_extraction_debug: bool = False
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_chat_model: str = ""
    openai_embedding_model: str = ""
    translation_ai_provider: str = "mock"
    post_builder_ai_provider: str = "mock"
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    azure_openai_model: str = ""
    azure_openai_auth_mode: str = "entra_id"
    azure_openai_api_key: str = ""
    translation_ai_timeout_seconds: float = Field(default=20, gt=0, le=120)
    translation_ai_max_retries: int = Field(default=2, ge=0, le=5)

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_document_chunking(self) -> "Settings":
        if self.document_chunk_overlap >= self.document_chunk_size:
            raise ValueError(
                "DOCUMENT_CHUNK_OVERLAP must be smaller than DOCUMENT_CHUNK_SIZE"
            )
        if not (
            self.alignment_high_confidence
            > self.alignment_medium_confidence
            > self.alignment_min_confidence
        ):
            raise ValueError(
                "Alignment confidence values must satisfy HIGH > MEDIUM > MIN"
            )
        if not (
            self.profile_extraction_high_confidence
            > self.profile_extraction_medium_confidence
            > self.profile_extraction_min_recommended_confidence
        ):
            raise ValueError(
                "Profile extraction confidence values must satisfy HIGH > MEDIUM > MIN"
            )
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def document_storage_dir(self) -> Path:
        path = Path(self.document_storage_path)
        return path if path.is_absolute() else BACKEND_ROOT / path

    @property
    def resolved_database_url(self) -> str:
        """Anchor relative SQLite files to the backend, independent of shell cwd."""
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            return self.database_url
        value = self.database_url.removeprefix(prefix)
        if value in {"", ":memory:"} or Path(value).is_absolute():
            return self.database_url
        return f"{prefix}{(BACKEND_ROOT / value).resolve()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
