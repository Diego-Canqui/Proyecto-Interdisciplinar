from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.perfil_reputacion import (
    PerfilReputacion,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.entities.sancion import Sancion
from prestamos_recursos.contexts.identidad_reputacion.domain.repositories.perfil_reputacion_repository import (
    PerfilReputacionRepository,
)
from prestamos_recursos.contexts.identidad_reputacion.infrastructure.models.perfil_reputacion_model import (
    PerfilReputacionModel,
    SancionModel,
)


class SqlPerfilReputacionRepository(PerfilReputacionRepository):
    """Implementación SQL (SQLAlchemy) de PerfilReputacionRepository."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def guardar(self, perfil_reputacion: PerfilReputacion) -> None:
        """
        Upsert del perfil y sincronización atómica de sanciones.

        - Si el perfil existe (por ID o usuario_id), actualiza sus campos.
        - Sincroniza la lista completa de sanciones: borra las que no están en
          `perfil.sanciones` e inserta las nuevas, todo en una sola transacción.
        """
        # Buscar perfil existente por ID o por usuario_id
        stmt = select(PerfilReputacionModel).where(
            (PerfilReputacionModel.id == perfil_reputacion.id)
            | (PerfilReputacionModel.usuario_id == perfil_reputacion.usuario_id)
        )
        modelo = self._session.execute(stmt).scalar_one_or_none()

        if modelo is None:
            # Crear nuevo
            modelo = self._perfil_a_modelo(perfil_reputacion)
            self._session.add(modelo)
        else:
            # Actualizar campos del perfil
            modelo.puntos = perfil_reputacion.puntaje.puntos
            modelo.nivel = perfil_reputacion.nivel
            modelo.fecha_actualizacion = perfil_reputacion.fecha_actualizacion

        # Sincronizar sanciones: delete-orphan + insert nuevos
        # Obtener IDs de sanciones actuales en el dominio
        ids_dominio = {s.id for s in perfil_reputacion.sanciones}

        # Borrar sanciones que ya no están en el dominio
        if modelo.sanciones:
            ids_bd = {s.id for s in modelo.sanciones}
            ids_a_borrar = ids_bd - ids_dominio
            if ids_a_borrar:
                self._session.execute(
                    delete(SancionModel).where(SancionModel.id.in_(ids_a_borrar))
                )

        # Actualizar/insertar sanciones del dominio
        for sancion in perfil_reputacion.sanciones:
            sancion_modelo = next(
                (s for s in modelo.sanciones if s.id == sancion.id), None
            )
            if sancion_modelo is None:
                # Nueva sanción
                sancion_modelo = self._sancion_a_modelo(sancion, modelo.id)
                self._session.add(sancion_modelo)
            else:
                # Actualizar sanción existente
                self._actualizar_sancion_modelo(sancion_modelo, sancion)

        # Flush para persistir cambios en la misma transacción
        self._session.flush()

    def obtener_por_id(self, id: UUID) -> PerfilReputacion | None:
        """Obtiene un perfil por su ID, cargando sus sanciones (join)."""
        stmt = select(PerfilReputacionModel).where(PerfilReputacionModel.id == id)
        modelo = self._session.execute(stmt).scalar_one_or_none()
        if modelo is None:
            return None
        return self._modelo_a_perfil(modelo)

    def obtener_por_usuario(self, usuario_id: UUID) -> PerfilReputacion | None:
        """Obtiene un perfil por usuario_id, cargando sus sanciones (join)."""
        stmt = select(PerfilReputacionModel).where(
            PerfilReputacionModel.usuario_id == usuario_id
        )
        modelo = self._session.execute(stmt).scalar_one_or_none()
        if modelo is None:
            return None
        return self._modelo_a_perfil(modelo)

    def _perfil_a_modelo(self, perfil: PerfilReputacion) -> PerfilReputacionModel:
        """Convierte entidad de dominio a modelo ORM (nuevo)."""
        return PerfilReputacionModel(
            id=perfil.id,
            usuario_id=perfil.usuario_id,
            puntos=perfil.puntaje.puntos,
            nivel=perfil.nivel,
            fecha_actualizacion=perfil.fecha_actualizacion,
            sanciones=[
                self._sancion_a_modelo(s, perfil.id) for s in perfil.sanciones
            ],
        )

    def _sancion_a_modelo(self, sancion: Sancion, perfil_id: UUID) -> SancionModel:
        """Convierte entidad Sancion a modelo ORM."""
        return SancionModel(
            id=sancion.id,
            perfil_reputacion_id=perfil_id,
            tipo=sancion.tipo,
            puntos_descuento=sancion.puntos_descuento,
            monto_descuento=sancion.monto_descuento,
            motivo=sancion.motivo,
            fecha_aplicacion=sancion.fecha_aplicacion,
            activa=sancion.activa,
        )

    def _actualizar_sancion_modelo(
        self, modelo: SancionModel, sancion: Sancion
    ) -> None:
        """Actualiza un modelo SancionModel con los datos de la entidad."""
        modelo.tipo = sancion.tipo
        modelo.puntos_descuento = sancion.puntos_descuento
        modelo.monto_descuento = sancion.monto_descuento
        modelo.motivo = sancion.motivo
        modelo.fecha_aplicacion = sancion.fecha_aplicacion
        modelo.activa = sancion.activa

    def _modelo_a_perfil(self, modelo: PerfilReputacionModel) -> PerfilReputacion:
        """Convierte modelo ORM a entidad de dominio (con sanciones cargadas)."""
        from prestamos_recursos.contexts.identidad_reputacion.domain.value_objects.puntaje_reputacion import (
            PuntajeReputacion,
        )

        sanciones = [
            Sancion(
                id=s.id,
                tipo=s.tipo,
                puntos_descuento=s.puntos_descuento,
                monto_descuento=s.monto_descuento,
                motivo=s.motivo,
                fecha_aplicacion=s.fecha_aplicacion,
                activa=s.activa,
            )
            for s in modelo.sanciones
        ]

        return PerfilReputacion(
            id=modelo.id,
            usuario_id=modelo.usuario_id,
            puntaje=PuntajeReputacion(puntos=modelo.puntos),
            nivel=modelo.nivel,
            fecha_actualizacion=modelo.fecha_actualizacion,
            sanciones=sanciones,
        )