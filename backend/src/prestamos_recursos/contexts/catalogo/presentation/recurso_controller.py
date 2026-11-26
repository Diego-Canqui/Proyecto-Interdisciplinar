"""«Boundary» RecursoController."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.catalogo.application.dto.recurso_dto import (
    ActualizarEstadoRecursoDTO,
    ActualizarRecursoDTO,
    CrearRecursoDTO,
    RecursoDTO,
)
from prestamos_recursos.contexts.catalogo.application.services import RecursoApplicationService
from prestamos_recursos.contexts.catalogo.domain.enums.estado_recurso import EstadoRecurso
from prestamos_recursos.contexts.catalogo.infrastructure.repositories import SqlRecursoRepository
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import (
    RolUsuario,
)
from prestamos_recursos.contexts.identidad_reputacion.presentation.dependencies import (
    require_roles,
)
from prestamos_recursos.contexts.prestamos.application.prestamo_service import PrestamoService
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_checklist_repository import (
    SqlChecklistRepository,
)
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_garantia_repository import (
    SqlGarantiaRepository,
)
from prestamos_recursos.contexts.prestamos.infrastructure.repositories.sql_prestamo_repository import (
    SqlPrestamoRepository,
)
from prestamos_recursos.shared.database import get_session

router = APIRouter(prefix="/recursos", tags=["Recursos"])
_solo_gestion = require_roles(RolUsuario.ADMINISTRADOR_SISTEMA, RolUsuario.GESTOR_ALMACEN)


def _enriquecer_disponible_desde(
    recursos: list[RecursoDTO],
    session: Session,
    catalogo_service: RecursoApplicationService,
) -> list[RecursoDTO]:
    """Completa disponible_desde con la fecha_fin del préstamo en curso para recursos EN_USO."""
    if not any(r.estado == EstadoRecurso.EN_USO for r in recursos):
        return recursos
    try:
        prestamo_service = PrestamoService(
            prestamo_repository=SqlPrestamoRepository(session),
            checklist_repository=SqlChecklistRepository(session),
            garantia_repository=SqlGarantiaRepository(session),
            catalogo_service=catalogo_service,
        )
        for recurso in recursos:
            if recurso.estado == EstadoRecurso.EN_USO:
                recurso.disponible_desde = prestamo_service.obtener_disponible_desde_recurso(
                    recurso.id
                )
    except Exception:  # noqa: BLE001
        return recursos
    return recursos


@router.get("", response_model=list[RecursoDTO])
def buscar_recursos(
    filtro: str = "",
    session: Session = Depends(get_session, scope="function"),  # noqa: B008
):
    repo = SqlRecursoRepository(session)
    service = RecursoApplicationService(repo)
    recursos = service.buscar(filtro)
    return _enriquecer_disponible_desde(recursos, session, service)


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def crear_recurso(
    dto: CrearRecursoDTO,
    session: Session = Depends(get_session, scope="function"),  # noqa: B008
    _usuario: UsuarioDTO = Depends(_solo_gestion),  # noqa: B008
):
    repo = SqlRecursoRepository(session)
    service = RecursoApplicationService(repo)
    try:
        id_recurso = service.crear_recurso(
            nombre=dto.nombre,
            descripcion=dto.descripcion,
            categoria=dto.categoria,
            marca=dto.marca,
            modelo=dto.modelo,
            numero_serie=dto.numero_serie,
            color=dto.color,
            estado_fisico=dto.estado_fisico,
            foto_url=dto.foto_url,
            especificaciones=dto.especificaciones,
        )
        return {"id": id_recurso, "mensaje": "Recurso creado exitosamente"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{id_recurso}/disponibilidad")
def consultar_disponibilidad(
    id_recurso: UUID,
    session: Session = Depends(get_session, scope="function"),  # noqa: B008
):
    repo = SqlRecursoRepository(session)
    service = RecursoApplicationService(repo)
    disponible = service.consultar_disponibilidad(id_recurso)
    return {"id_recurso": id_recurso, "disponible": disponible}


@router.get("/{id_recurso}/ficha-tecnica", response_model=RecursoDTO)
def obtener_ficha_tecnica(
    id_recurso: UUID,
    session: Session = Depends(get_session, scope="function"),  # noqa: B008
):
    repo = SqlRecursoRepository(session)
    service = RecursoApplicationService(repo)
    recurso_dto = service.obtener_ficha_tecnica(id_recurso)
    if not recurso_dto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")
    return _enriquecer_disponible_desde([recurso_dto], session, service)[0]


@router.put("/{id_recurso}", response_model=RecursoDTO)
def actualizar_recurso(
    id_recurso: UUID,
    dto: ActualizarRecursoDTO,
    session: Session = Depends(get_session, scope="function"),  # noqa: B008
    _usuario: UsuarioDTO = Depends(_solo_gestion),  # noqa: B008
):
    repo = SqlRecursoRepository(session)
    service = RecursoApplicationService(repo)
    try:
        return service.actualizar_recurso(
            id_recurso=id_recurso,
            nombre=dto.nombre,
            descripcion=dto.descripcion,
            categoria=dto.categoria,
            marca=dto.marca,
            modelo=dto.modelo,
            numero_serie=dto.numero_serie,
            color=dto.color,
            estado_fisico=dto.estado_fisico,
            foto_url=dto.foto_url,
            especificaciones=dto.especificaciones,
        )
    except ValueError as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "no encontrado" in str(e)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(e)) from e


@router.patch("/{id_recurso}/estado", response_model=dict)
def actualizar_estado(
    id_recurso: UUID,
    dto: ActualizarEstadoRecursoDTO,
    session: Session = Depends(get_session, scope="function"),  # noqa: B008
    _usuario: UsuarioDTO = Depends(_solo_gestion),  # noqa: B008
):
    repo = SqlRecursoRepository(session)
    service = RecursoApplicationService(repo)
    try:
        service.actualizar_estado(id_recurso, dto.estado)
        return {
            "id_recurso": id_recurso,
            "estado": dto.estado,
            "mensaje": "Estado actualizado exitosamente",
        }
    except ValueError as e:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "no encontrado" in str(e)
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=str(e)) from e
    except TypeError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
