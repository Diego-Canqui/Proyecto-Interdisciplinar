-- Un schema de PostgreSQL por bounded context.
-- Las tablas las crea Alembic (migraciones) a partir de los modelos SQLAlchemy.
-- Este script solo corre la primera vez que se crea el volumen de Docker.
CREATE SCHEMA IF NOT EXISTS identidad;
CREATE SCHEMA IF NOT EXISTS catalogo;
CREATE SCHEMA IF NOT EXISTS reservas;
CREATE SCHEMA IF NOT EXISTS prestamos;
