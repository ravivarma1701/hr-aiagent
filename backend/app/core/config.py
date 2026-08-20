from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Mock HRMS API"
    environment: str = "dev"
    app_timezone: str = "Asia/Kolkata"
    database_url: str = "sqlite+aiosqlite:///./storage/hrms.db"

    # Comma-separated list of allowed frontend origins for CORS. Must include
    # the deployed frontend's exact origin (scheme + host, no trailing
    # slash) in production -- e.g. "https://your-app.vercel.app".
    cors_allowed_origins: str = "http://localhost:3000"

    jwt_secret_key: str = "change_me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    policy_upload_dir: str = "/app/storage/hr-policies"
    profile_photo_upload_dir: str = "/app/storage/profile-photos"
    employee_document_upload_dir: str = "/app/storage/employee-documents"

    # --- AI layer (Phase 4) ---
    # LLM provider: "gemini" or "anthropic". llm_client.py dispatches on this
    # so the rest of the codebase (agents, endpoints) never touches a
    # provider SDK directly.
    ai_llm_provider: str = "gemini"
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    ai_model_name: str = "gemini-flash-latest"
    ai_max_output_tokens: int = 1024

    # Local embedding model for the Policy RAG vector store (sentence-transformers).
    ai_embedding_model_name: str = "all-MiniLM-L6-v2"
    ai_vector_store_dir: str = "/app/storage/vector-store"

    # SQL Agent guardrails
    ai_sql_max_rows: int = 200

    # Base URL the Action Agent's tool wrappers call back into for existing
    # backend APIs. Must always point at this same service.
    internal_api_base_url: str = "http://127.0.0.1:8000"


settings = Settings()
