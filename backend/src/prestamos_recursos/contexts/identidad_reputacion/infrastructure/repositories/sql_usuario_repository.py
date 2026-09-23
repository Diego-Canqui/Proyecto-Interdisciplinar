from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.usuario import Usuario
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import RolUsuario
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.usuario_repository import UsuarioRepository
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.usuario_model import UsuarioModel


class SqlUsuarioRepository(UsuarioRepository):
    """Implementación SQL (SQLAlchemy) de UsuarioRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, usuario: Usuario) -> None:
        modelo = self._session.get(UsuarioModel, usuario.id)
        if modelo is None:
            modelo = UsuarioModel(id=usuario.id)
            self._session.add(modelo)
        modelo.nombre = usuario.nombre
        modelo.correo = usuario.correo
        modelo.telefono = usuario.telefono
        modelo.estado = usuario.estado
        modelo.roles = [rol.value for rol in usuario.roles]
        self._session.commit()

    def obtener_por_id(self, id: UUID) -> Usuario | None:
        modelo = self._session.get(UsuarioModel, id)
        return self._a_entidad(modelo) if modelo else None

    def obtener_por_correo(self, correo: str) -> Usuario | None:
        modelo = self._session.scalar(select(UsuarioModel).where(UsuarioModel.correo == correo))
        return self._a_entidad(modelo) if modelo else None

    def listar(self) -> list[Usuario]:
        modelos = self._session.scalars(select(UsuarioModel)).all()
        return [self._a_entidad(m) for m in modelos]

    @staticmethod
    def _a_entidad(modelo: UsuarioModel) -> Usuario:
        return Usuario(
            id=modelo.id,
            nombre=modelo.nombre,
            correo=modelo.correo,
            telefono=modelo.telefono,
            estado=modelo.estado,
            roles={RolUsuario(r) for r in modelo.roles},
        )
