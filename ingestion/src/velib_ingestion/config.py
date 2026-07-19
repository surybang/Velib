"""Configuration centralisée, chargée depuis l'environnement (12-factor)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres du service d'ingestion.

    Toutes les valeurs sont obligatoires et proviennent de l'environnement.
    Aucun défaut n'est fourni pour les secrets : une variable manquante doit
    faire échouer le démarrage.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    pghost: str
    pgport: int
    pgdatabase: str
    pguser: str
    pgpassword: str

    # APIs
    velib_api_base_url: str
    velib_api_page_size: int = 100
    meteo_api_base_url: str

    # Observabilité
    log_level: str = "INFO"
    json_logs: bool = False


settings = Settings()
