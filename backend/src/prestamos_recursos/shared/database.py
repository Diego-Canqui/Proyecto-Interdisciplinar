from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from prestamos_recursos.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base declarativa de SQLAlchemy para todos los modelos."""


def get_session() -> Iterator[Session]:
    """Dependencia de FastAPI: una sesión por petición.

    Frontera de transacción (unit of work, D13): confirma al terminar la petición
    con normalidad y revierte si hubo excepción, de modo que una respuesta 4xx/5xx
    no deje escrituras parciales confirmadas. Los repositorios solo hacen `flush`
    y se apoyan en esta frontera: hay un único dueño de la transacción.
    """
    with SessionLocal() as session:
        try:
            yield session
            # La petición terminó con normalidad: confirmar la unidad de trabajo
            session.commit()
        except Exception:
            # Revertir lo parcial y re-lanzar: la excepción no se traga aquí
            session.rollback()
            raise
