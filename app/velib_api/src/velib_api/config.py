"""Configuration chargée depuis l'environnement (12-factor)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    pghost: str
    pgport: int = 5432
    pgdatabase: str
    pguser: str
    pgpassword: str


settings = Settings()
