from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/prestamos_recursos/config.py -> raíz del repositorio
ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://prestamos:cambiar_esto@localhost:5432/prestamos_recursos"
    )
    jwt_secret: str = "cambiar_esto"

    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")


settings = Settings()
