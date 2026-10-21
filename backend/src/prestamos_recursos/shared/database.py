from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from prestamos_recursos.config import settings

engine_options: dict[str, object] = {"pool_pre_ping": True}
if settings.database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
    if settings.database_url.endswith(":memory:") or settings.database_url.endswith("sqlite://"):
        engine_options["poolclass"] = StaticPool

engine = create_engine(settings.database_url, **engine_options)
if engine.dialect.name == "sqlite":
    engine = engine.execution_options(schema_translate_map={"reservas": None})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base declarativa de SQLAlchemy para todos los modelos."""


def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición."""
    with SessionLocal() as session:
        yield session
