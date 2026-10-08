from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/prestamos_recursos/config.py -> raíz del repositorio
ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg://prestamos:cambiar_esto@localhost:5432/prestamos_recursos",
        validation_alias="DATABASE_URL",
    )
    jwt_secret: str = Field(..., validation_alias="JWT_SECRET")
    jwt_expiracion_horas: int = Field(default=24, validation_alias="JWT_EXPIRACION_HORAS")
    bcrypt_cost: int = Field(default=12, validation_alias="BCRYPT_COST")
    cors_origins_raw: str = Field(default="http://localhost:5173", validation_alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",")]

    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")


settings = Settings()
