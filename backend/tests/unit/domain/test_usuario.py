"""Tests unitarios para la entidad Usuario (domain)."""
import re
from uuid import UUID

from prestamos_recursos.contexts.identidad_reputacion.domain.entities.usuario import (
    Usuario,
)
from prestamos_recursos.contexts.identidad_reputacion.domain.enums.rol_usuario import (
    RolUsuario,
)


class TestUsuarioCrearConPassword:
    """Tests para el método de factoría crear_con_password."""

    def test_usuario_crear_con_password_hash_bcrypt(self) -> None:
        """El hash generado debe ser bcrypt válido con coste 12."""
        usuario = Usuario.crear_con_password(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password_plano="Password123",
        )

        # Verificar que password_hash es un hash bcrypt válido
        assert usuario.password_hash is not None
        assert isinstance(usuario.password_hash, str)
        assert len(usuario.password_hash) > 0

        # Verificar que es un hash bcrypt (formato $2b$12$...)
        assert usuario.password_hash.startswith("$2b$12$")

        # Verificar que el coste es 12 (los dos dígitos después de $2b$)
        match = re.match(r"^\$2b\$(\d{2})\$", usuario.password_hash)
        assert match is not None, "El hash no tiene formato bcrypt válido"
        coste = int(match.group(1))
        assert coste == 12, f"Coste bcrypt esperado 12, obtenido {coste}"

    def test_usuario_crear_con_password_id_uuid_roles_default(self) -> None:
        """Debe asignar UUID como id y roles por defecto [ESTUDIANTE]."""
        usuario = Usuario.crear_con_password(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password_plano="Password123",
        )

        # Verificar que id es UUID válido
        assert isinstance(usuario.id, UUID)

        # Verificar roles por defecto
        assert usuario.roles == [RolUsuario.ESTUDIANTE]

        # Verificar estado por defecto
        assert usuario.estado is True

        # Verificar que los demás atributos se asignan correctamente
        assert usuario.nombre == "Juan Pérez"
        assert usuario.correo == "juan@example.com"
        assert usuario.telefono == "+34 600 123 456"

    def test_usuario_crear_con_password_roles_personalizados(self) -> None:
        """Debe permitir pasar roles personalizados."""
        usuario = Usuario.crear_con_password(
            nombre="Admin User",
            correo="admin@example.com",
            telefono=None,
            password_plano="Password123",
            roles=[RolUsuario.ADMIN, RolUsuario.BIBLIOTECARIO],
        )

        assert usuario.roles == [RolUsuario.ADMIN, RolUsuario.BIBLIOTECARIO]

    def test_usuario_crear_con_password_telefono_opcional(self) -> None:
        """Teléfono es opcional y puede ser None."""
        usuario = Usuario.crear_con_password(
            nombre="Sin Teléfono",
            correo="sintel@example.com",
            telefono=None,
            password_plano="Password123",
        )

        assert usuario.telefono is None


class TestUsuarioVerificarPassword:
    """Tests para el método verificar_password."""

    def test_usuario_verificar_password_correcto(self) -> None:
        """Debe devolver True con el password correcto."""
        password_plano = "Password123"
        usuario = Usuario.crear_con_password(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password_plano=password_plano,
        )

        assert usuario.verificar_password(password_plano) is True

    def test_usuario_verificar_password_incorrecto(self) -> None:
        """Debe devolver False con password incorrecto."""
        usuario = Usuario.crear_con_password(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password_plano="Password123",
        )

        assert usuario.verificar_password("Password124") is False
        assert usuario.verificar_password("wrong") is False
        assert usuario.verificar_password("") is False

    def test_usuario_verificar_password_case_sensitive(self) -> None:
        """La verificación debe ser case-sensitive."""
        usuario = Usuario.crear_con_password(
            nombre="Juan Pérez",
            correo="juan@example.com",
            telefono="+34 600 123 456",
            password_plano="Password123",
        )

        assert usuario.verificar_password("password123") is False
        assert usuario.verificar_password("PASSWORD123") is False