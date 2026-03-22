from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./local.db"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    local_only_mode: bool = False
    local_admin_email: str = "admin"
    local_admin_password: str = "admin"
    storage_dir: str = "/data/storage"
    s3_endpoint: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket: str | None = None
    s3_region: str | None = None
    transcription_backend: str = "server"
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    mlx_audio_model: str = "mlx-community/parakeet-tdt-0.6b-v3"
    ollama_base_url: str = "http://127.0.0.1:11434"
    lmstudio_base_url: str = "http://127.0.0.1:1234/v1"
    llama_cpp_base_url: str = "http://127.0.0.1:8080"
    local_engine_timeout_seconds: float = 0.75

    class Config:
        env_prefix = ""
        case_sensitive = False


settings = Settings()
