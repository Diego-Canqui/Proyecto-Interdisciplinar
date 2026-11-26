-- Script de datos semilla (seed) para desarrollo y examen final
-- Es idempotente (ON CONFLICT DO UPDATE / DO NOTHING): se puede ejecutar todas las veces que se quiera.
-- Incluye:
--   1. 2 cuentas base de ./dev.sh (admin@example.com / estudiante@example.com)
--   2. 48 alumnos de la clase (@unsa.edu.pe, contraseña genérica: estudiante123)
--   3. 5 docentes (DOCENTE) y 2 administrativos (PERSONAL_ADMINISTRATIVO) (contraseña: estudiante123)
--   4. 20 recursos en el catálogo (Cómputo, Multimedia, Laboratorio y Libros)
--   5. 5 artículos prestados actualmente (estado EN_USO + reserva CONVERTIDA + préstamo ENTREGADO + garantía + checklist)

BEGIN;

-- ============================================================================
-- 1. USUARIOS BASE DE ./dev.sh
-- ============================================================================

-- Administrador y Gestor de Almacén (password: admin123)
INSERT INTO identidad_reputacion.usuario (id, nombre, correo, telefono, password_hash, estado, roles)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'Administrador del Sistema',
    'admin@example.com',
    '999888777',
    '$2b$12$TaI2pgOiHokBQ5G2g4V7VuwYNwQ4zlzuigAAayDhBAze62LOMkixy',
    true,
    ARRAY['ADMINISTRADOR_SISTEMA', 'GESTOR_ALMACEN']
) ON CONFLICT (correo) DO UPDATE
SET password_hash = EXCLUDED.password_hash,
    roles = EXCLUDED.roles,
    estado = true;

-- Estudiante de prueba (password: estudiante123)
INSERT INTO identidad_reputacion.usuario (id, nombre, correo, telefono, password_hash, estado, roles)
VALUES (
    'a0000000-0000-0000-0000-000000000002',
    'Estudiante de Prueba',
    'estudiante@example.com',
    '987654321',
    '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.',
    true,
    ARRAY['ESTUDIANTE']
) ON CONFLICT (correo) DO UPDATE
SET password_hash = EXCLUDED.password_hash,
    roles = EXCLUDED.roles,
    estado = true;

-- ============================================================================
-- 2. ALUMNOS DE LA CLASE (48 estudiantes — contraseña genérica: estudiante123)
-- ============================================================================

INSERT INTO identidad_reputacion.usuario (id, nombre, correo, telefono, password_hash, estado, roles)
VALUES
    ('a1000000-0000-0000-0000-000000000001', 'Jesus Alberto Alfaro Buiza', 'jalfaro@unsa.edu.pe', '951000001', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000002', 'Marco Antonio Armendariz Paredes', 'marmendariz@unsa.edu.pe', '951000002', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000003', 'Albert Gussepe Blanco Cana', 'ablanco@unsa.edu.pe', '951000003', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000004', 'Karina Paola Calcina Chuquipalla', 'kcalcina@unsa.edu.pe', '951000004', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000005', 'Diego Canqui Ecos', 'dcanqui@unsa.edu.pe', '951000005', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000006', 'Anderson Samuel Carpio Chura', 'acarpio@unsa.edu.pe', '951000006', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000007', 'Moises Robert Ccaso Idme', 'mccaso@unsa.edu.pe', '951000007', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000008', 'Elyud Edgar Chayña Calcina', 'echayna@unsa.edu.pe', '951000008', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000009', 'Luis Antonio Chipana Chura', 'lchipana@unsa.edu.pe', '951000009', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000010', 'Aldair Daniel Condori Ataucuri', 'acondori@unsa.edu.pe', '951000010', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000011', 'Emilio Alejandro Condori Pallardel', 'econdori@unsa.edu.pe', '951000011', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000012', 'Stephano Gian Pierre Delgado Chavez', 'sdelgado@unsa.edu.pe', '951000012', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000013', 'Mauricio Alejandro Farfan Huayta', 'mfarfan@unsa.edu.pe', '951000013', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000014', 'Fernando Antonio Gama Llicahua', 'fgama@unsa.edu.pe', '951000014', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000015', 'Carlos Enrique Gutierrez Castilla', 'cgutierrez@unsa.edu.pe', '951000015', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000016', 'Johan Diego Huamani Sabina', 'jhuamani@unsa.edu.pe', '951000016', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000017', 'Estrella de Jesús Emilia Fabiana Huarsaya Márquez', 'ehuarsaya@unsa.edu.pe', '951000017', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000018', 'Lizzy Arlette Huayhua Perez', 'lhuayhua@unsa.edu.pe', '951000018', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000019', 'Roid Niro Huaylla Guzman', 'rhuaylla@unsa.edu.pe', '951000019', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000020', 'Daysi Jara Arisaca', 'djara@unsa.edu.pe', '951000020', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000021', 'Hellen Grace Juan de Dios Delgado', 'hjuandedios@unsa.edu.pe', '951000021', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000022', 'Natalie Marleny Lazo Paxi', 'nlazo@unsa.edu.pe', '951000022', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000023', 'Fernando Enrique Llosa Manchego', 'fllosa@unsa.edu.pe', '951000023', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000024', 'Mariana Valery Luis Jimenez', 'mluis@unsa.edu.pe', '951000024', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000025', 'Diego de Alessandro Mamani Salazar', 'dmamani@unsa.edu.pe', '951000025', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000026', 'Luis Fernando Morales Tacca', 'lmorales@unsa.edu.pe', '951000026', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000027', 'Neill Elverth Olazabal Chavez', 'nolazabal@unsa.edu.pe', '951000027', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000028', 'Alvaro Johan Panibra Choctaya', 'apanibra@unsa.edu.pe', '951000028', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000029', 'Javier Alonzo Peñalva Humire', 'jpenalva@unsa.edu.pe', '951000029', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000030', 'Jesus Gustavo Perez Villasante', 'jperez@unsa.edu.pe', '951000030', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000031', 'Juan Carlos Postigo Cabana', 'jpostigo@unsa.edu.pe', '951000031', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000032', 'Claudia Roxana Quisocala Cruz', 'cquisocala@unsa.edu.pe', '951000032', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000033', 'Sharmely Yesenia Quispe Chavez', 'squispe@unsa.edu.pe', '951000033', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000034', 'David Augusto Quispe Lloccallasi', 'dquispe@unsa.edu.pe', '951000034', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000035', 'Angelo Josue Quispe Suarez', 'aquispe@unsa.edu.pe', '951000035', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000036', 'Job Lorenzo Quispe Torrez', 'jquispe@unsa.edu.pe', '951000036', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000037', 'Luis Enrique Ramos Chambi', 'lramos@unsa.edu.pe', '951000037', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000038', 'Rodrigo Abraham Ramos Mamani', 'rramos@unsa.edu.pe', '951000038', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000039', 'Omar Joaquin Rivera Olivera', 'orivera@unsa.edu.pe', '951000039', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000040', 'Edu Andre Sucari Ccansaya', 'esucari@unsa.edu.pe', '951000040', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000041', 'Cristhian Luis Taipe Huanca', 'ctaipe@unsa.edu.pe', '951000041', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000042', 'Lizeth Angelica Tito Vilca', 'ltito@unsa.edu.pe', '951000042', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000043', 'Jhair Alejandro Torres Chavez', 'jtorres@unsa.edu.pe', '951000043', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000044', 'Micaela Belen Uribe Zuñiga', 'muribe@unsa.edu.pe', '951000044', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000045', 'Ronald Reynaldo Valdez Agüero', 'rvaldez@unsa.edu.pe', '951000045', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000046', 'Diego Mauricio Villanueva Flores', 'dvillanueva@unsa.edu.pe', '951000046', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000048', 'Marving Alonzo Zamata Huaracha', 'mzamata@unsa.edu.pe', '951000048', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE']),
    ('a1000000-0000-0000-0000-000000000049', 'Eduardo Josue Zela Quispe', 'ezela@unsa.edu.pe', '951000049', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['ESTUDIANTE'])
ON CONFLICT (correo) DO UPDATE
SET nombre = EXCLUDED.nombre,
    password_hash = EXCLUDED.password_hash,
    roles = EXCLUDED.roles,
    estado = true;

-- ============================================================================
-- 3. DOCENTES (5) Y ADMINISTRATIVOS (2) — contraseña genérica: estudiante123
-- ============================================================================

INSERT INTO identidad_reputacion.usuario (id, nombre, correo, telefono, password_hash, estado, roles)
VALUES
    -- Docentes (5)
    ('a2000000-0000-0000-0000-000000000001', 'Dra. Yessenia Deysi Yari Ramos', 'yyarira@unsa.edu.pe', '952000001', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['DOCENTE']),
    ('a2000000-0000-0000-0000-000000000002', 'Alfredo Paz Valderrama', 'apazv@unsa.edu.pe', '952000002', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['DOCENTE']),
    ('a2000000-0000-0000-0000-000000000003', 'Dr. Alvaro Henry Mamani Aliaga', 'amamaniali@unsa.edu.pe', '952000003', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['DOCENTE']),
    ('a2000000-0000-0000-0000-000000000004', 'Dr. Yuber Elmer Velazco Paredes', 'yvelazco@unsa.edu.pe', '952000004', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['DOCENTE']),
    ('a2000000-0000-0000-0000-000000000005', 'Dr. Edgar Sarmiento Calisaya', 'esarmientoca@unsa.edu.pe', '952000005', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['DOCENTE']),
    -- Personal Administrativo (2)
    ('a3000000-0000-0000-0000-000000000001', 'Secretaría Académica EPCC', 'secretaria.epcc@unsa.edu.pe', '953000001', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['PERSONAL_ADMINISTRATIVO']),
    ('a3000000-0000-0000-0000-000000000002', 'Coordinación de Laboratorios EPCC', 'laboratorios.epcc@unsa.edu.pe', '953000002', '$2b$12$.dSz/IV1qYDbp6WlCOk61e9dLnhKnYonwL2mB3Rp8GT7aKchQDpQ.', true, ARRAY['PERSONAL_ADMINISTRATIVO'])
ON CONFLICT (correo) DO UPDATE
SET nombre = EXCLUDED.nombre,
    password_hash = EXCLUDED.password_hash,
    roles = EXCLUDED.roles,
    estado = true;

-- ============================================================================
-- 4. PERFILES DE REPUTACIÓN (automático para todos los usuarios sembrados)
-- ============================================================================

INSERT INTO identidad_reputacion.perfiles_reputacion (id, usuario_id, puntos, nivel, fecha_actualizacion)
VALUES (
    'b0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    1000,
    'EXCELENTE',
    NOW()
) ON CONFLICT (usuario_id) DO NOTHING;

INSERT INTO identidad_reputacion.perfiles_reputacion (id, usuario_id, puntos, nivel, fecha_actualizacion)
SELECT
    md5(u.id::text || '-perfil')::uuid,
    u.id,
    500,
    'NORMAL',
    NOW()
FROM identidad_reputacion.usuario u
WHERE u.id <> 'a0000000-0000-0000-0000-000000000001'
ON CONFLICT (usuario_id) DO NOTHING;

-- ============================================================================
-- 5. RECURSOS DEL CATÁLOGO (20 artículos: 5 en estado EN_USO + 15 DISPONIBLE)
-- ============================================================================

INSERT INTO catalogo.recursos (id, nombre, descripcion, categoria, estado, marca, modelo, numero_serie, color, estado_fisico, foto_url, especificaciones)
VALUES
(
    'c0000000-0000-0000-0000-000000000001',
    'Laptop Dell Latitude 5420 (i7 / 16GB RAM)',
    'Equipo portátil de alto rendimiento para desarrollo de software y laboratorios. Incluye cargador USB-C original de 65W y maletín.',
    'Cómputo',
    'EN_USO',
    'Dell',
    'Latitude 5420',
    'SN-DELL-LAT5420-01',
    'Gris Espacial',
    'Excelente',
    'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/latitude-notebooks/14-5420/media-gallery/la5420nt_cnb_00055lf110_gy.psd?fmt=png-alpha&pscan=auto&scl=1&hei=402&wid=606',
    '{"Procesador": "Intel Core i7-1185G7", "RAM": "16 GB DDR4", "Almacenamiento": "512 GB SSD NVMe"}'::json
),
(
    'c0000000-0000-0000-0000-000000000002',
    'Proyector Multimedia Epson PowerLite 4K',
    'Proyector láser de alta luminosidad para exposiciones y sustentaciones académicas. Incluye cable HDMI, cable de poder y control remoto.',
    'Multimedia',
    'EN_USO',
    'Epson',
    'PowerLite L200W',
    'SN-EPSON-4K-0092',
    'Blanco',
    'Operativo',
    'https://mediaserver.goepson.com/ImConvServlet/imconv/7b18a2f79d9e89b10861b9d72b150e23f492820d/1200Wx1200H?use=banner&hybrisId=B2C&assetDescr=EB-L200W_01-1',
    '{"Luminosidad": "4200 lúmenes", "Entradas": "HDMI x2, VGA, USB"}'::json
),
(
    'c0000000-0000-0000-0000-000000000003',
    'Kit Laboratorio Electrónica: Osciloscopio Digital + Arduino Mega',
    'Estación portátil de medición electrónica con osciloscopio digital de 2 canales (100MHz), puntas de prueba, protoboard y placa Arduino Mega 2560.',
    'Laboratorio',
    'EN_USO',
    'Rigol / Arduino',
    'DS1102Z-E + Mega 2560',
    'SN-LAB-ELEC-044',
    'Negro y Azul',
    'Excelente',
    'https://store-usa.arduino.cc/cdn/shop/products/A000067_00.front_934x700.jpg',
    '{"Canales": "2 canales 100MHz", "Microcontrolador": "ATmega2560"}'::json
),
(
    'c0000000-0000-0000-0000-000000000004',
    'Introduction to Algorithms (CLRS) 4ta Edición',
    'Texto canónico de algoritmos, estructuras de datos y análisis de complejidad por Cormen, Leiserson, Rivest y Stein.',
    'Libro',
    'EN_USO',
    NULL,
    NULL,
    NULL,
    NULL,
    'Excelente',
    'https://images.mitpress.mit.edu/covers/9780262046305.jpg',
    '{"Autor": "Cormen, Leiserson, Rivest y Stein", "Editorial": "MIT Press", "ISBN": "978-0262046305", "Edición": "4ta Edición"}'::json
),
(
    'c0000000-0000-0000-0000-000000000005',
    'Compiladores: Principios, Técnicas y Herramientas (Libro del Dragón)',
    'Referencia fundamental en la teoría de diseño e implementación de compiladores y análisis léxico/sintáctico por Aho, Lam, Sethi y Ullman.',
    'Libro',
    'DISPONIBLE',
    NULL,
    NULL,
    NULL,
    NULL,
    'Bueno',
    'https://m.media-amazon.com/images/I/71u9sJ-UjIL._SL1500_.jpg',
    '{"Autor": "Aho, Lam, Sethi y Ullman", "Editorial": "Pearson", "ISBN": "978-0321486813", "Edición": "2da Edición"}'::json
),
(
    'c0000000-0000-0000-0000-000000000006',
    'The C Programming Language 2nd Edition (K&R)',
    'Manual oficial y definitivo del lenguaje C estándar ANSI escrito por sus creadores Brian Kernighan y Dennis Ritchie.',
    'Libro',
    'DISPONIBLE',
    NULL,
    NULL,
    NULL,
    NULL,
    'Excelente',
    'https://m.media-amazon.com/images/I/61k1qVlWf8L._SL1200_.jpg',
    '{"Autor": "Brian Kernighan y Dennis Ritchie", "Editorial": "Prentice Hall", "ISBN": "978-0131103627", "Edición": "2da Edición"}'::json
),
(
    'c0000000-0000-0000-0000-000000000007',
    'Clean Code: A Handbook of Agile Software Craftsmanship',
    'Guía de buenas prácticas de programación, refactorización y diseño limpio de software por Robert C. Martin (Uncle Bob).',
    'Libro',
    'EN_USO',
    NULL,
    NULL,
    NULL,
    NULL,
    'Excelente',
    'https://m.media-amazon.com/images/I/51E2055ZGUL._SL1000_.jpg',
    '{"Autor": "Robert C. Martin", "Editorial": "Prentice Hall", "ISBN": "978-0132350884", "Edición": "1ra Edición"}'::json
),
(
    'c0000000-0000-0000-0000-000000000008',
    'Design Patterns: Elements of Reusable Object-Oriented Software',
    'Catálogo clásico de 23 patrones de diseño de software por la "Gang of Four" (Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides).',
    'Libro',
    'DISPONIBLE',
    NULL,
    NULL,
    NULL,
    NULL,
    'Excelente',
    'https://m.media-amazon.com/images/I/81gtKoapHFL._SL1500_.jpg',
    '{"Autor": "Gamma, Helm, Johnson y Vlissides", "Editorial": "Addison-Wesley", "ISBN": "978-0201633610", "Edición": "1ra Edición"}'::json
),
(
    'c0000000-0000-0000-0000-000000000009',
    'Laptop Lenovo ThinkPad T14 Gen 3 (Ryzen 7 / 16GB RAM)',
    'Laptop empresarial con teclado ergonómico ideal para compilación, Docker y pruebas de sistemas distribuidos. Incluye cargador USB-C.',
    'Cómputo',
    'DISPONIBLE',
    'Lenovo',
    'ThinkPad T14 Gen 3',
    'SN-LEN-T14G3-009',
    'Negro Mate',
    'Excelente',
    '',
    '{"Procesador": "AMD Ryzen 7 PRO 6850U", "RAM": "16 GB LPDDR5", "Almacenamiento": "512 GB SSD"}'::json
),
(
    'c0000000-0000-0000-0000-000000000010',
    'Tablet Gráfica Wacom Intuos Pro Medium',
    'Tableta digitalizadora profesional con lápiz Pro Pen 2 para diagramación UML, diseño UI/UX y clases virtuales.',
    'Cómputo',
    'DISPONIBLE',
    'Wacom',
    'Intuos Pro PTH-660',
    'SN-WAC-PTH660-010',
    'Negro',
    'Excelente',
    '',
    '{"Conectividad": "USB-C / Bluetooth", "Niveles de presión": "8192"}'::json
),
(
    'c0000000-0000-0000-0000-000000000011',
    'Monitor Portátil ASUS ZenScreen 15.6" Full HD',
    'Monitor secundario portátil USB-C con funda plegable para trabajo en equipo y revisiones de código en laboratorio.',
    'Cómputo',
    'DISPONIBLE',
    'ASUS',
    'ZenScreen MB16ACV',
    'SN-ASUS-ZEN16-011',
    'Gris Oscuro',
    'Bueno',
    '',
    '{"Resolución": "1920x1080 IPS", "Conexión": "USB-C"}'::json
),
(
    'c0000000-0000-0000-0000-000000000012',
    'Kit Raspberry Pi 5 (8GB RAM) con Carcasa y Fuente',
    'Computadora de placa única para proyectos de IoT, servidores ligeros y sistemas embebidos. Incluye tarjeta microSD de 64GB y cable micro-HDMI.',
    'Laboratorio',
    'DISPONIBLE',
    'Raspberry Pi',
    'Model 5 8GB',
    'SN-RPI5-8GB-012',
    'Rojo y Blanco',
    'Excelente',
    '',
    '{"RAM": "8 GB", "Almacenamiento": "microSD 64 GB", "Alimentación": "USB-C 27W"}'::json
),
(
    'c0000000-0000-0000-0000-000000000013',
    'Multímetro Digital Fluke 117 True-RMS',
    'Multímetro profesional para prácticas de circuitos eléctricos, mantenimiento de hardware y verificación de fuentes de poder.',
    'Laboratorio',
    'DISPONIBLE',
    'Fluke',
    '117 True-RMS',
    'SN-FLUKE-117-013',
    'Amarillo y Negro',
    'Excelente',
    '',
    '{"Categoría": "CAT III 600V", "Accesorios": "Puntas de prueba TL75"}'::json
),
(
    'c0000000-0000-0000-0000-000000000014',
    'Kit de Redes Cisco: Switch Administrable 8 Puertos + Cables Patch',
    'Kit portátil para laboratorios de redes de computadoras, VLANs y direccionamiento IP. Incluye 6 cables UTP Cat6 y cable de consola.',
    'Laboratorio',
    'DISPONIBLE',
    'Cisco',
    'CBS250-8T-D',
    'SN-CISCO-SW8-014',
    'Blanco',
    'Operativo',
    '',
    '{"Puertos": "8x Gigabit Ethernet", "Administrable": "Sí (L2/L3)"}'::json
),
(
    'c0000000-0000-0000-0000-000000000015',
    'Cámara Web Logitech Brio 4K Ultra HD',
    'Cámara de alta definición con enfoque automático y micrófono dual para grabaciones de sustentaciones y videoconferencias.',
    'Multimedia',
    'DISPONIBLE',
    'Logitech',
    'Brio 4K Pro',
    'SN-LOGI-BRIO-015',
    'Negro',
    'Excelente',
    '',
    '{"Resolución": "4K Ultra HD 30fps / 1080p 60fps", "Conexión": "USB-C"}'::json
),
(
    'c0000000-0000-0000-0000-000000000016',
    'Micrófono Condensador USB HyperX QuadCast',
    'Micrófono de escritorio con filtro antipop integrado y soporte antivibración para grabación de demos y podcasts académicos.',
    'Multimedia',
    'DISPONIBLE',
    'HyperX',
    'QuadCast S',
    'SN-HYPX-QC-016',
    'Negro',
    'Excelente',
    '',
    '{"Patrones polares": "Estéreo, Omnidireccional, Cardioide, Bidireccional", "Conexión": "USB"}'::json
),
(
    'c0000000-0000-0000-0000-000000000017',
    'Trípode Profesional Manfrotto Compact Action + Adaptador Móvil',
    'Trípode ligero de aluminio con cabezal joystick para grabación estable de exposiciones y prototipos en laboratorio.',
    'Multimedia',
    'DISPONIBLE',
    'Manfrotto',
    'MKCOMPACTACN-BK',
    'SN-MANF-TRI-017',
    'Negro',
    'Bueno',
    '',
    '{"Altura máxima": "155 cm", "Carga máxima": "1.5 kg"}'::json
),
(
    'c0000000-0000-0000-0000-000000000018',
    'Domain-Driven Design: Tackling Complexity in the Heart of Software',
    'Obra fundamental de Eric Evans sobre diseño guiado por el dominio, bounded contexts, agregados y lenguaje ubicuo.',
    'Libro',
    'DISPONIBLE',
    NULL,
    NULL,
    NULL,
    NULL,
    'Excelente',
    '',
    '{"Autor": "Eric Evans", "Editorial": "Addison-Wesley", "ISBN": "978-0321125217", "Edición": "1ra Edición"}'::json
),
(
    'c0000000-0000-0000-0000-000000000019',
    'Designing Data-Intensive Applications',
    'Referencia moderna de Martin Kleppmann sobre arquitectura de sistemas distribuidos, replicación, particionamiento y consistencia.',
    'Libro',
    'DISPONIBLE',
    NULL,
    NULL,
    NULL,
    NULL,
    'Excelente',
    '',
    '{"Autor": "Martin Kleppmann", "Editorial": "O''Reilly Media", "ISBN": "978-1449373320", "Edición": "1ra Edición"}'::json
),
(
    'c0000000-0000-0000-0000-000000000020',
    'Clean Architecture: A Craftsman''s Guide to Software Structure and Design',
    'Guía práctica de Robert C. Martin sobre arquitectura limpia, inversión de dependencias y separación por capas.',
    'Libro',
    'DISPONIBLE',
    NULL,
    NULL,
    NULL,
    NULL,
    'Excelente',
    '',
    '{"Autor": "Robert C. Martin", "Editorial": "Prentice Hall", "ISBN": "978-0134494166", "Edición": "1ra Edición"}'::json
)
ON CONFLICT (id) DO UPDATE
SET nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    categoria = EXCLUDED.categoria,
    marca = EXCLUDED.marca,
    modelo = EXCLUDED.modelo,
    numero_serie = EXCLUDED.numero_serie,
    color = EXCLUDED.color,
    estado_fisico = EXCLUDED.estado_fisico,
    foto_url = EXCLUDED.foto_url,
    especificaciones = EXCLUDED.especificaciones;

-- ============================================================================
-- 6. 5 ARTÍCULOS PRESTADOS ACTUALMENTE (Reserva CONVERTIDA + Préstamo ENTREGADO + Garantía + Checklist)
-- ============================================================================

INSERT INTO reservas.reservas (id, usuario_id, recurso_id, fecha_inicio, fecha_fin, estado)
VALUES
    ('d0000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000005', 'c0000000-0000-0000-0000-000000000001', NOW() - INTERVAL '1 day', NOW() + INTERVAL '4 days', 'CONVERTIDA'),
    ('d0000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000016', 'c0000000-0000-0000-0000-000000000002', NOW() - INTERVAL '1 day', NOW() + INTERVAL '3 days', 'CONVERTIDA'),
    ('d0000000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000038', 'c0000000-0000-0000-0000-000000000003', NOW() - INTERVAL '2 days', NOW() + INTERVAL '3 days', 'CONVERTIDA'),
    ('d0000000-0000-0000-0000-000000000004', 'a1000000-0000-0000-0000-000000000046', 'c0000000-0000-0000-0000-000000000004', NOW() - INTERVAL '1 day', NOW() + INTERVAL '5 days', 'CONVERTIDA'),
    ('d0000000-0000-0000-0000-000000000005', 'a1000000-0000-0000-0000-000000000007', 'c0000000-0000-0000-0000-000000000007', NOW() - INTERVAL '1 day', NOW() + INTERVAL '5 days', 'CONVERTIDA')
ON CONFLICT (id) DO NOTHING;

INSERT INTO prestamos.prestamos (id, reserva_id, recurso_id, usuario_id, fecha_inicio, fecha_fin, estado, fecha_entrega_real, fecha_devolucion_real)
VALUES
    ('e0000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001', 'c0000000-0000-0000-0000-000000000001', 'a1000000-0000-0000-0000-000000000005', NOW() - INTERVAL '1 day', NOW() + INTERVAL '4 days', 'ENTREGADO', NOW() - INTERVAL '1 day', NULL),
    ('e0000000-0000-0000-0000-000000000002', 'd0000000-0000-0000-0000-000000000002', 'c0000000-0000-0000-0000-000000000002', 'a1000000-0000-0000-0000-000000000016', NOW() - INTERVAL '1 day', NOW() + INTERVAL '3 days', 'ENTREGADO', NOW() - INTERVAL '1 day', NULL),
    ('e0000000-0000-0000-0000-000000000003', 'd0000000-0000-0000-0000-000000000003', 'c0000000-0000-0000-0000-000000000003', 'a1000000-0000-0000-0000-000000000038', NOW() - INTERVAL '2 days', NOW() + INTERVAL '3 days', 'ENTREGADO', NOW() - INTERVAL '2 days', NULL),
    ('e0000000-0000-0000-0000-000000000004', 'd0000000-0000-0000-0000-000000000004', 'c0000000-0000-0000-0000-000000000004', 'a1000000-0000-0000-0000-000000000046', NOW() - INTERVAL '1 day', NOW() + INTERVAL '5 days', 'ENTREGADO', NOW() - INTERVAL '1 day', NULL),
    ('e0000000-0000-0000-0000-000000000005', 'd0000000-0000-0000-0000-000000000005', 'c0000000-0000-0000-0000-000000000007', 'a1000000-0000-0000-0000-000000000007', NOW() - INTERVAL '1 day', NOW() + INTERVAL '5 days', 'ENTREGADO', NOW() - INTERVAL '1 day', NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO prestamos.garantias (id, prestamo_id, tipo, estado, fecha_registro, fecha_liberacion, compromiso_contenido, compromiso_fecha_firma, compromiso_firma_url, compromiso_testigo)
VALUES
    ('f0000000-0000-0000-0000-000000000001', 'e0000000-0000-0000-0000-000000000001', 'CARNET_UNIVERSITARIO', 'REGISTRADA', NOW() - INTERVAL '1 day', NULL, 'Me comprometo a devolver el equipo en las mismas condiciones recibidas.', NOW() - INTERVAL '1 day', 'https://firma.unsa.edu.pe/dcanqui', 'Administrador del Sistema'),
    ('f0000000-0000-0000-0000-000000000002', 'e0000000-0000-0000-0000-000000000002', 'CARNET_UNIVERSITARIO', 'REGISTRADA', NOW() - INTERVAL '1 day', NULL, 'Me comprometo a devolver el proyector con todos sus accesorios.', NOW() - INTERVAL '1 day', 'https://firma.unsa.edu.pe/jhuamani', 'Administrador del Sistema'),
    ('f0000000-0000-0000-0000-000000000003', 'e0000000-0000-0000-0000-000000000003', 'DOCUMENTO_IDENTIDAD', 'REGISTRADA', NOW() - INTERVAL '2 days', NULL, 'Me comprometo a devolver el kit de laboratorio completo y operativo.', NOW() - INTERVAL '2 days', 'https://firma.unsa.edu.pe/rramos', 'Administrador del Sistema'),
    ('f0000000-0000-0000-0000-000000000004', 'e0000000-0000-0000-0000-000000000004', 'CARNET_UNIVERSITARIO', 'REGISTRADA', NOW() - INTERVAL '1 day', NULL, 'Me comprometo a devolver el libro sin daños ni subrayados.', NOW() - INTERVAL '1 day', 'https://firma.unsa.edu.pe/dvillanueva', 'Administrador del Sistema'),
    ('f0000000-0000-0000-0000-000000000005', 'e0000000-0000-0000-0000-000000000005', 'CARNET_UNIVERSITARIO', 'REGISTRADA', NOW() - INTERVAL '1 day', NULL, 'Me comprometo a devolver el libro Clean Code en óptimas condiciones.', NOW() - INTERVAL '1 day', 'https://firma.unsa.edu.pe/mccaso', 'Administrador del Sistema')
ON CONFLICT (id) DO NOTHING;

INSERT INTO prestamos.checklists (id, prestamo_id, tipo, fecha_inspeccion, observaciones, fotos_urls, completo)
VALUES
    ('f1000000-0000-0000-0000-000000000001', 'e0000000-0000-0000-0000-000000000001', 'ESTADO_INICIAL', NOW() - INTERVAL '1 day', 'Equipo entregado con cargador USB-C y maletín sin rayones.', ARRAY['https://evidencia.unsa.edu.pe/laptop-01.jpg'], true),
    ('f1000000-0000-0000-0000-000000000002', 'e0000000-0000-0000-0000-000000000002', 'ESTADO_INICIAL', NOW() - INTERVAL '1 day', 'Proyector probado en ventanilla con cable HDMI y control remoto.', ARRAY['https://evidencia.unsa.edu.pe/proyector-02.jpg'], true),
    ('f1000000-0000-0000-0000-000000000003', 'e0000000-0000-0000-0000-000000000003', 'ESTADO_INICIAL', NOW() - INTERVAL '2 days', 'Osciloscopio, puntas de prueba y Arduino Mega verificados.', ARRAY['https://evidencia.unsa.edu.pe/kit-03.jpg'], true),
    ('f1000000-0000-0000-0000-000000000004', 'e0000000-0000-0000-0000-000000000004', 'ESTADO_INICIAL', NOW() - INTERVAL '1 day', 'Libro en tapa dura sin páginas dobladas ni anotaciones.', ARRAY['https://evidencia.unsa.edu.pe/clrs-04.jpg'], true),
    ('f1000000-0000-0000-0000-000000000005', 'e0000000-0000-0000-0000-000000000005', 'ESTADO_INICIAL', NOW() - INTERVAL '1 day', 'Ejemplar Clean Code completo y en excelente estado físico.', ARRAY['https://evidencia.unsa.edu.pe/cleancode-05.jpg'], true)
ON CONFLICT (id) DO NOTHING;

COMMIT;
