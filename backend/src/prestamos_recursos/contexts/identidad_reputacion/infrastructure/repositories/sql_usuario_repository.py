from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.usuario import Usuario
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.usuario_repository import UsuarioRepository


class SqlUsuarioRepository(UsuarioRepository):
    """Implementación SQL (SQLAlchemy) de UsuarioRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, usuario: Usuario) -> None:
        raise NotImplementedError

    def obtener_por_id(self, id: UUID) -> Usuario | None:
        raise NotImplementedError

    def obtener_por_correo(self, correo: str) -> Usuario | None:
        raise NotImplementedError

    def listar(self) -> list[Usuario]:
        raise NotImplementedError
