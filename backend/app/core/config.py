from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # App
    app_name: str = "prism-lab-alan-vo"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    # Auth / OIDC
    oidc_enabled: bool = True
    oidc_issuer_url: str = "http://127.0.0.1:8080/realms/prism-lab"
    oidc_client_id: str = "prism-lab-backend"
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "http://127.0.0.1:8000/auth/callback"
    oidc_scopes: str = "openid profile email roles"
    session_secret_key: str = "dev-secret-change-in-production"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # Frontend URL for CORS
    frontend_url: str = "http://127.0.0.1:5173"

    # LLM (optional)
    llm_api_key: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_base_url: Optional[str] = None

    # Demo mode (explicitly enabled, never auto)
    demo_mode: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()