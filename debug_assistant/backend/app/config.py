import os
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_FILE = os.path.join(_BACKEND_DIR, ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ENV_FILE, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


    # JWT
    secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_32_PLUS_RANDOM_BYTES"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8  # 8 hours

    # Database
    database_url: str = "sqlite:///./debug_assistant.db"

    # CORS — comma-separated origins, or * for dev
    allowed_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:8000"

    # Frontend base URL for OAuth redirects
    frontend_url: str = "http://localhost:8000"

    # Google OAuth 2.0 Credentials
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"

    # GitHub OAuth App Credentials
    github_client_id: str = ""
    github_client_secret: str = ""
    github_redirect_uri: str = "http://localhost:8000/auth/github/callback"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()

