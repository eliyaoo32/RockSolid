from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """The backend's configuration, read from BACKEND_* environment variables."""

    model_config = SettingsConfigDict(env_prefix="BACKEND_")

    # postgresql+asyncpg://<user>:<password>@<host>:5432/<database>
    database_url: str
    # The Firebase project whose ID tokens sign users in.
    firebase_project_id: str
    port: int = 8080
