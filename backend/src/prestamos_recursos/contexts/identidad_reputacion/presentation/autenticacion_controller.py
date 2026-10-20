"""«Boundary» AutenticacionController."""

from fastapi import APIRouter, Depends, Request, status

from prestamos_recursos.contexts.identidad_reputacion.application.autenticacion_service import (
    AutenticacionService,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.autenticacion_dto import (
    CrearUsuarioDTO,
    LoginDTO,
    TokenDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.application.dto.usuario_dto import (
    UsuarioDTO,
)
from prestamos_recursos.contexts.identidad_reputacion.presentation.dependencies import (
    get_autenticacion_service,
    get_current_user,
)
from prestamos_recursos.shared.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/registro", response_model=TokenDTO, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def registrar_usuario(
    request: Request,
    datos: CrearUsuarioDTO,
    service: AutenticacionService = Depends(get_autenticacion_service),  # noqa: B008
) -> TokenDTO:
    """
    Registra un nuevo usuario y devuelve token JWT + datos del usuario.

    - **nombre**: obligatorio, máx 100 chars
    - **correo**: obligatorio, formato email válido, máx 255 chars, único
    - **telefono**: opcional, regex ^\\+?[0-9\\s-]{7,20}$, máx 20 chars
    - **password**: obligatorio, mín 8 chars, al menos 1 mayúscula, 1 minúscula, 1 dígito
    - **roles**: opcional, lista de roles (por defecto [ESTUDIANTE])

    Retorna 201 con TokenDTO (JWT + UsuarioDTO sin passwordHash).
    Lanza 400 si validaciones fallan, 409 si correo duplicado.
    """
    return service.registrar_usuario(datos)


@router.post("/login", response_model=TokenDTO)
@limiter.limit("5/minute")
def login(
    request: Request,
    credenciales: LoginDTO,
    service: AutenticacionService = Depends(get_autenticacion_service),  # noqa: B008
) -> TokenDTO:
    """
    Autentica un usuario y devuelve token JWT + datos del usuario.

    - **correo**: obligatorio, formato email válido
    - **password**: obligatorio

    Retorna 200 con TokenDTO (JWT + UsuarioDTO).
    Lanza 401 si credenciales inválidas (mensaje genérico).
    """
    return service.login(credenciales)


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout() -> dict[str, str]:
    """
    Cierra la sesión del usuario (stateless).

    El cliente debe descartar el token JWT. No hay revocación server-side.

    Retorna 200 con mensaje de confirmación.
    """
    return {"message": "Sesión cerrada"}


@router.get("/perfil", response_model=UsuarioDTO)
def obtener_perfil(
    usuario: UsuarioDTO = Depends(get_current_user),  # noqa: B008
) -> UsuarioDTO:
    """
    Obtiene el perfil del usuario autenticado.

    Requiere header: Authorization: Bearer <token>

    Retorna 200 con UsuarioDTO.
    Lanza 401 si token inválido, expirado o usuario no existe.
    """
    return usuario