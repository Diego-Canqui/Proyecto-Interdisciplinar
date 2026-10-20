"""initial_schema

Revision ID: 20261020_000001
Revises: 
Create Date: 2026-10-20 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20261020_000001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crear schemas
    op.execute("CREATE SCHEMA IF NOT EXISTS identidad;")
    op.execute("CREATE SCHEMA IF NOT EXISTS catalogo;")
    op.execute("CREATE SCHEMA IF NOT EXISTS reservas;")
    op.execute("CREATE SCHEMA IF NOT EXISTS prestamos;")

    # Crear tabla recursos en schema catalogo
    op.create_table(
        'recursos',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('nombre', sa.String(length=255), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=False),
        sa.Column('categoria', sa.String(length=255), nullable=False),
        sa.Column('estado', sa.String(length=30), nullable=False),
        sa.Column('marca', sa.String(length=255), nullable=False),
        sa.Column('modelo', sa.String(length=255), nullable=False),
        sa.Column('numero_serie', sa.String(length=255), nullable=False),
        sa.Column('color', sa.String(length=255), nullable=False),
        sa.Column('estado_fisico', sa.String(length=255), nullable=False),
        sa.Column('foto_url', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('numero_serie'),
        schema='catalogo'
    )


def downgrade() -> None:
    op.drop_table('recursos', schema='catalogo')
    op.execute("DROP SCHEMA IF EXISTS prestamos;")
    op.execute("DROP SCHEMA IF EXISTS reservas;")
    op.execute("DROP SCHEMA IF EXISTS catalogo;")
    op.execute("DROP SCHEMA IF EXISTS identidad;")
