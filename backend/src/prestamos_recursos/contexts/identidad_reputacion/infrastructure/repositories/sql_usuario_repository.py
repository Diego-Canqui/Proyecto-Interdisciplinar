from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.usuario import Usuario
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.usuario_repository import (
    UsuarioRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.usuario_model import (
    UsuarioModel,
)


class SqlUsuarioRepository(UsuarioRepository):
    """Implementación SQL (SQLAlchemy) de UsuarioRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, usuario: Usuario) -> Usuario:
        modelo = self._session.get(UsuarioModel, usuario.id)
        if modelo is None:
            modelo = UsuarioModel.from_entity(usuario)
            self._session.add(modelo)
        else:
            # Actualizar campos existentes
            modelo.nombre = usuario.nombre
            modelo.correo = usuario.correo
            modelo.telefono = usuario.telefono
            modelo.password_hash = usuario.password_hash
            modelo.estado = usuario.estado
            modelo.roles = [rol.value for rol in usuario.roles]
        self._session.commit()
        # Retornar la entidad con ID (refrescar para obtener valores generados por BD)
        self._session.refresh(modelo)
        return modelo.to_entity()

    def obtener_por_id(self, id: UUID) -> Usuario | None:
        modelo = self._session.get(UsuarioModel, id)
        return modelo.to_entity() if modelo else None

    def obtener_por_correo(self, correo: str) -> Usuario | None:
        modelo = self._session.scalar(select(UsuarioModel).where(UsuarioModel.correo == correo))
        return modelo.to_entity() if modelo else None

    def listar(self) -> list[Usuario]:
        modelos = self._session.scalars(select(UsuarioModel)).all()
        return [m.to_entity() for m in modelos]
