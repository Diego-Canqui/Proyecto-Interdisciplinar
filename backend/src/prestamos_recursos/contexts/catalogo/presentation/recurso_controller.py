"""«Boundary» RecursoController."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from prestamos_recursos.contexts.catalogo.application.dto.recurso_dto import CrearRecursoDTO, RecursoDTO
from prestamos_recursos.contexts.catalogo.application.services import RecursoApplicationService
from prestamos_recursos.contexts.catalogo.infrastructure.repositories import SqlRecursoRepository
from prestamos_recursos.shared.database import get_session

router = APIRouter(prefix="/recursos", tags=["Recursos"])


@router.get("", response_model=list[RecursoDTO])
def buscar_recursos(filtro: str = "", session: Session = Depends(get_session)):
    repo = SqlRecursoRepository(session)
    service = RecursoApplicationService(repo)
    return service.buscar(filtro)


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def crear_recurso(dto: CrearRecursoDTO, session: Session = Depends(get_session)):
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
        )
        session.commit()
        return {"id": id_recurso, "mensaje": "Recurso creado exitosamente"}
    except ValueError as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{id_recurso}/disponibilidad")
def consultar_disponibilidad(id_recurso: UUID, session: Session = Depends(get_session)):
    repo = SqlRecursoRepository(session)
    service = RecursoApplicationService(repo)
    disponible = service.consultar_disponibilidad(id_recurso)
    return {"id_recurso": id_recurso, "disponible": disponible}


@router.get("/{id_recurso}/ficha-tecnica", response_model=RecursoDTO)
def obtener_ficha_tecnica(id_recurso: UUID, session: Session = Depends(get_session)):
    repo = SqlRecursoRepository(session)
    service = RecursoApplicationService(repo)
    recurso_dto = service.obtener_ficha_tecnica(id_recurso)
    if not recurso_dto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurso no encontrado")
    return recurso_dto
