from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Mock HRMS API"
    environment: str = "dev"
    app_timezone: str = "Asia/Kolkata"
    database_url: str = "sqlite+aiosqlite:///./storage/hrms.db"

    jwt_secret_key: str = "change_me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    policy_upload_dir: str = "/app/storage/hr-policies"
    profile_photo_upload_dir: str = "/app/storage/profile-photos"
    employee_document_upload_dir: str = "/app/storage/employee-documents"


settings = Settings()
