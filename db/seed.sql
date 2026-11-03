-- Script de datos semilla (seed) para desarrollo y demostración
-- Es idempotente (ON CONFLICT DO UPDATE): se puede ejecutar todas las veces que se quiera.
-- Incluye:
--   1. Usuario Admin/Gestor: admin@example.com (contraseña: admin123)
--   2. Usuario Estudiante:   estudiante@example.com (contraseña: estudiante123)
--   3. 8 Recursos en el catálogo (3 equipos tecnológicos/laboratorio + 5 libros clásicos)

BEGIN;

-- ============================================================================
-- 1. USUARIOS DE PRUEBA
-- ============================================================================

-- Usuario Administrador y Gestor de Almacén (password: admin123)
INSERT INTO identidad_reputacion.usuario (id, nombre, correo, telefono, password_hash, estado, roles)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'Administrador del Sistema',
    'admin@example.com',
    '999888777',
    '$2b$12$TaI2pgOiHokBQ5G2g4V7VuwYNwQ4zlzuigAAayDhBAze62LOMkixy',
    true,
    ARRAY['ADMINISTRADOR_SISTEMA', 'GESTOR_ALMACEN', 'DOCENTE', 'ESTUDIANTE']
) ON CONFLICT (correo) DO UPDATE 
SET password_hash = EXCLUDED.password_hash,
    roles = EXCLUDED.roles,
    estado = true;

-- Usuario Estudiante de prueba (password: estudiante123)
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
-- 2. PERFILES DE REPUTACIÓN
-- ============================================================================

INSERT INTO identidad_reputacion.perfiles_reputacion (id, usuario_id, puntos, nivel, fecha_actualizacion)
VALUES (
    'b0000000-0000-0000-0000-000000000001',
    'a0000000-0000-0000-0000-000000000001',
    1000,
    'EXCELENTE',
    NOW()
) ON CONFLICT (usuario_id) DO UPDATE
SET puntos = 1000, nivel = 'EXCELENTE', fecha_actualizacion = NOW();

INSERT INTO identidad_reputacion.perfiles_reputacion (id, usuario_id, puntos, nivel, fecha_actualizacion)
VALUES (
    'b0000000-0000-0000-0000-000000000002',
    'a0000000-0000-0000-0000-000000000002',
    500,
    'NORMAL',
    NOW()
) ON CONFLICT (usuario_id) DO UPDATE
SET puntos = 500, nivel = 'NORMAL', fecha_actualizacion = NOW();

-- ============================================================================
-- 3. RECURSOS DEL CATÁLOGO (EQUIPOS TECNOLÓGICOS + LIBROS)
-- ============================================================================

INSERT INTO catalogo.recursos (id, nombre, descripcion, categoria, estado, marca, modelo, numero_serie, color, estado_fisico, foto_url)
VALUES 
(
    'c0000000-0000-0000-0000-000000000001',
    'Laptop Dell Latitude 5420 (i7 / 16GB RAM)',
    'Equipo portátil de alto rendimiento para desarrollo de software y laboratorios. Incluye cargador USB-C original de 65W y maletín.',
    'Cómputo',
    'DISPONIBLE',
    'Dell',
    'Latitude 5420',
    'SN-DELL-LAT5420-01',
    'Gris Espacial',
    'Excelente',
    'https://i.dell.com/is/image/DellContent/content/dam/ss2/product-images/dell-client-products/notebooks/latitude-notebooks/14-5420/media-gallery/la5420nt_cnb_00055lf110_gy.psd?fmt=png-alpha&pscan=auto&scl=1&hei=402&wid=606'
),
(
    'c0000000-0000-0000-0000-000000000002',
    'Proyector Multimedia Epson PowerLite 4K',
    'Proyector láser de alta luminosidad para exposiciones y sustentaciones académicas. Incluye cable HDMI, cable de poder y control remoto.',
    'Multimedia',
    'DISPONIBLE',
    'Epson',
    'PowerLite L200W',
    'SN-EPSON-4K-0092',
    'Blanco',
    'Operativo',
    'https://mediaserver.goepson.com/ImConvServlet/imconv/7b18a2f79d9e89b10861b9d72b150e23f492820d/1200Wx1200H?use=banner&hybrisId=B2C&assetDescr=EB-L200W_01-1'
),
(
    'c0000000-0000-0000-0000-000000000003',
    'Kit Laboratorio Electrónica: Osciloscopio Digital + Arduino Mega',
    'Estación portátil de medición electrónica con osciloscopio digital de 2 canales (100MHz), puntas de prueba, protoboard y placa Arduino Mega 2560.',
    'Laboratorio',
    'DISPONIBLE',
    'Rigol / Arduino',
    'DS1102Z-E + Mega 2560',
    'SN-LAB-ELEC-044',
    'Negro y Azul',
    'Excelente',
    'https://store-usa.arduino.cc/cdn/shop/products/A000067_00.front_934x700.jpg'
),
(
    'c0000000-0000-0000-0000-000000000004',
    'Introduction to Algorithms (CLRS) 4ta Edición',
    'Texto canónico de algoritmos, estructuras de datos y análisis de complejidad por Cormen, Leiserson, Rivest y Stein.',
    'Libros',
    'DISPONIBLE',
    'MIT Press',
    '4ta Edición (Hardcover)',
    'ISBN-978-0262046305',
    'Azul',
    'Excelente',
    'https://images.mitpress.mit.edu/covers/9780262046305.jpg'
),
(
    'c0000000-0000-0000-0000-000000000005',
    'Compiladores: Principios, Técnicas y Herramientas (Libro del Dragón)',
    'Referencia fundamental en la teoría de diseño e implementación de compiladores y análisis léxico/sintáctico por Aho, Lam, Sethi y Ullman.',
    'Libros',
    'DISPONIBLE',
    'Pearson / Addison-Wesley',
    '2da Edición',
    'ISBN-978-0321486813',
    'Rojo / Ilustración Dragón',
    'Bueno',
    'https://m.media-amazon.com/images/I/71u9sJ-UjIL._SL1500_.jpg'
),
(
    'c0000000-0000-0000-0000-000000000006',
    'The C Programming Language 2nd Edition (K&R)',
    'Manual oficial y definitivo del lenguaje C estándar ANSI escrito por sus creadores Brian Kernighan y Dennis Ritchie.',
    'Libros',
    'DISPONIBLE',
    'Prentice Hall',
    '2da Edición ANSI C',
    'ISBN-978-0131103627',
    'Blanco y Azul',
    'Excelente',
    'https://m.media-amazon.com/images/I/61k1qVlWf8L._SL1200_.jpg'
),
(
    'c0000000-0000-0000-0000-000000000007',
    'Clean Code: A Handbook of Agile Software Craftsmanship',
    'Guía de buenas prácticas de programación, refactorización y diseño limpio de software por Robert C. Martin (Uncle Bob).',
    'Libros',
    'DISPONIBLE',
    'Prentice Hall',
    '1ra Edición',
    'ISBN-978-0132350884',
    'Verde',
    'Excelente',
    'https://m.media-amazon.com/images/I/51E2055ZGUL._SL1000_.jpg'
),
(
    'c0000000-0000-0000-0000-000000000008',
    'Design Patterns: Elements of Reusable Object-Oriented Software',
    'Catálogo clásico de 23 patrones de diseño de software por la "Gang of Four" (Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides).',
    'Libros',
    'DISPONIBLE',
    'Addison-Wesley',
    '1ra Edición',
    'ISBN-978-0201633610',
    'Blanco y Morado',
    'Excelente',
    'https://m.media-amazon.com/images/I/81gtKoapHFL._SL1500_.jpg'
)
ON CONFLICT (numero_serie) DO UPDATE 
SET nombre = EXCLUDED.nombre,
    descripcion = EXCLUDED.descripcion,
    categoria = EXCLUDED.categoria,
    marca = EXCLUDED.marca,
    modelo = EXCLUDED.modelo,
    color = EXCLUDED.color,
    estado_fisico = EXCLUDED.estado_fisico,
    foto_url = EXCLUDED.foto_url;

COMMIT;
