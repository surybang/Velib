from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # PGSQL
    pghost: str
    pgport: int
    pgdatabase: str
    pguser: str
    pgpassword: str

    # API
    velib_api_base_url: str
    velib_api_page_size: int
    meteo_api_base_url: str
    fetch_interval_minutes: int


settings = Settings()
