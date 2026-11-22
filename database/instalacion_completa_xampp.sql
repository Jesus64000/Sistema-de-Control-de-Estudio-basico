-- ============================================================================
-- Instalacion Completa de Base de Datos (XAMPP / MySQL / MariaDB InnoDB)
-- Sistema de Control de Estudio - E. B. N. "Los Laureles"
-- ============================================================================
-- Uso directo en phpMyAdmin (Importar) o mediante instalar_w10.bat
-- Credenciales iniciales (requieren cambio de clave al primer ingreso):
--   Administrador : admin    / admin123
--   Operador      : operador / operador123
-- ============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE DATABASE IF NOT EXISTS `los_laureles_ce`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `los_laureles_ce`;

-- Esquema relacional para Control de Estudio - E. B. N. "Los Laureles"
-- Compatible con MySQL / MariaDB (XAMPP InnoDB)

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS docentes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cedula VARCHAR(25) NOT NULL UNIQUE,
    nombres VARCHAR(80) NOT NULL,
    apellidos VARCHAR(80) NOT NULL,
    telefono VARCHAR(30) NULL,
    correo VARCHAR(120) NULL,
    direccion VARCHAR(255) NULL,
    especialidad VARCHAR(100) NULL,
    categoria ENUM('Primaria', 'Media General', 'Especialista') NOT NULL DEFAULT 'Media General',
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    correo VARCHAR(120) NULL,
    password_hash VARCHAR(255) NOT NULL,
    rol ENUM('admin', 'operador', 'docente') NOT NULL DEFAULT 'operador',
    id_docente INT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    debe_cambiar_password BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_usuario_docente FOREIGN KEY (id_docente)
        REFERENCES docentes(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS solicitudes_recuperacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_usuario INT NOT NULL,
    correo_solicitado VARCHAR(120) NOT NULL,
    estado ENUM('pendiente', 'atendida', 'descartada') NOT NULL DEFAULT 'pendiente',
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atendido_en TIMESTAMP NULL,
    atendido_por INT NULL,
    CONSTRAINT fk_sol_rec_usuario FOREIGN KEY (id_usuario)
        REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_sol_rec_admin FOREIGN KEY (atendido_por)
        REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS configuracion_institucional (
    clave VARCHAR(60) PRIMARY KEY,
    valor TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS periodos_escolares (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(30) NOT NULL UNIQUE,
    activo BOOLEAN NOT NULL DEFAULT FALSE,
    cerrado BOOLEAN NOT NULL DEFAULT FALSE,
    fecha_inicio DATE NULL,
    fecha_fin DATE NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS niveles_educativos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(80) NOT NULL UNIQUE,
    tipo_escala ENUM('literal', 'numerica') NOT NULL,
    titulo_otorga VARCHAR(150) NULL,
    orden INT NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS grados_anios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_nivel INT NOT NULL,
    nombre VARCHAR(60) NOT NULL,
    orden INT NOT NULL DEFAULT 1,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE KEY uq_nivel_grado (id_nivel, nombre),
    CONSTRAINT fk_grado_nivel FOREIGN KEY (id_nivel)
        REFERENCES niveles_educativos(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS secciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_periodo INT NOT NULL,
    id_grado_anio INT NOT NULL,
    nombre VARCHAR(20) NOT NULL,
    turno ENUM('Mañana', 'Tarde', 'Integral') NOT NULL DEFAULT 'Mañana',
    id_docente_titular_guia INT NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE KEY uq_seccion_periodo_grado (id_periodo, id_grado_anio, nombre),
    CONSTRAINT fk_seccion_periodo FOREIGN KEY (id_periodo)
        REFERENCES periodos_escolares(id) ON DELETE RESTRICT,
    CONSTRAINT fk_seccion_grado FOREIGN KEY (id_grado_anio)
        REFERENCES grados_anios(id) ON DELETE RESTRICT,
    CONSTRAINT fk_seccion_docente FOREIGN KEY (id_docente_titular_guia)
        REFERENCES docentes(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bloques_formacion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL UNIQUE,
    orden INT NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS materias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_grado_anio INT NOT NULL,
    id_bloque INT NOT NULL,
    nombre VARCHAR(120) NOT NULL,
    codigo VARCHAR(20) NULL,
    es_especial BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE KEY uq_materia_grado (id_grado_anio, nombre),
    CONSTRAINT fk_materia_grado FOREIGN KEY (id_grado_anio)
        REFERENCES grados_anios(id) ON DELETE RESTRICT,
    CONSTRAINT fk_materia_bloque FOREIGN KEY (id_bloque)
        REFERENCES bloques_formacion(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS asignaciones_docentes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_periodo INT NOT NULL,
    id_seccion INT NOT NULL,
    id_materia INT NOT NULL,
    id_docente INT NOT NULL,
    UNIQUE KEY uq_asignacion (id_periodo, id_seccion, id_materia),
    CONSTRAINT fk_asig_periodo FOREIGN KEY (id_periodo)
        REFERENCES periodos_escolares(id) ON DELETE RESTRICT,
    CONSTRAINT fk_asig_seccion FOREIGN KEY (id_seccion)
        REFERENCES secciones(id) ON DELETE CASCADE,
    CONSTRAINT fk_asig_materia FOREIGN KEY (id_materia)
        REFERENCES materias(id) ON DELETE RESTRICT,
    CONSTRAINT fk_asig_docente FOREIGN KEY (id_docente)
        REFERENCES docentes(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS representantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cedula VARCHAR(25) NOT NULL UNIQUE,
    nombres VARCHAR(80) NOT NULL,
    apellidos VARCHAR(80) NOT NULL,
    parentesco VARCHAR(40) NOT NULL DEFAULT 'Representante Legal',
    telefono VARCHAR(30) NOT NULL,
    telefono_trabajo VARCHAR(30) NULL,
    correo VARCHAR(120) NULL,
    direccion VARCHAR(255) NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS estudiantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cedula VARCHAR(25) NOT NULL UNIQUE,
    nombres VARCHAR(80) NOT NULL,
    apellidos VARCHAR(80) NOT NULL,
    genero ENUM('M', 'F') NOT NULL DEFAULT 'M',
    fecha_nacimiento DATE NULL,
    direccion VARCHAR(255) NULL,
    egresado BOOLEAN NOT NULL DEFAULT FALSE,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS estudiante_representantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_estudiante INT NOT NULL,
    id_representante INT NOT NULL,
    es_principal BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE KEY uq_est_rep (id_estudiante, id_representante),
    CONSTRAINT fk_er_est FOREIGN KEY (id_estudiante)
        REFERENCES estudiantes(id) ON DELETE CASCADE,
    CONSTRAINT fk_er_rep FOREIGN KEY (id_representante)
        REFERENCES representantes(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS inscripciones (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_periodo INT NOT NULL,
    id_estudiante INT NOT NULL,
    id_seccion INT NOT NULL,
    estado ENUM('activo', 'retirado') NOT NULL DEFAULT 'activo',
    condicion ENUM('regular', 'repitiente', 'materia_pendiente', 'reingreso') NOT NULL DEFAULT 'regular',
    fecha_inscripcion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_inscripcion_periodo_est (id_periodo, id_estudiante),
    CONSTRAINT fk_insc_periodo FOREIGN KEY (id_periodo)
        REFERENCES periodos_escolares(id) ON DELETE RESTRICT,
    CONSTRAINT fk_insc_estudiante FOREIGN KEY (id_estudiante)
        REFERENCES estudiantes(id) ON DELETE RESTRICT,
    CONSTRAINT fk_insc_seccion FOREIGN KEY (id_seccion)
        REFERENCES secciones(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS calificaciones_primaria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_inscripcion INT NOT NULL UNIQUE,
    lapso_1 ENUM('A', 'B', 'C', 'D', 'E') NULL,
    lapso_2 ENUM('A', 'B', 'C', 'D', 'E') NULL,
    lapso_3 ENUM('A', 'B', 'C', 'D', 'E') NULL,
    definitiva ENUM('A', 'B', 'C', 'D', 'E') NULL,
    observaciones TEXT NULL,
    actualizado_por INT NULL,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_cal_prim_insc FOREIGN KEY (id_inscripcion)
        REFERENCES inscripciones(id) ON DELETE CASCADE,
    CONSTRAINT fk_cal_prim_usr FOREIGN KEY (actualizado_por)
        REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS calificaciones_secundaria (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_inscripcion INT NOT NULL,
    id_materia INT NOT NULL,
    lapso_1 DECIMAL(4,1) NULL,
    lapso_2 DECIMAL(4,1) NULL,
    lapso_3 DECIMAL(4,1) NULL,
    definitiva DECIMAL(4,1) NULL,
    tipo_evaluacion VARCHAR(10) NOT NULL DEFAULT 'F',
    mes VARCHAR(2) NOT NULL DEFAULT '07',
    anio VARCHAR(4) NOT NULL DEFAULT '2026',
    actualizado_por INT NULL,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_cal_sec_insc_mat (id_inscripcion, id_materia),
    CONSTRAINT fk_cal_sec_insc FOREIGN KEY (id_inscripcion)
        REFERENCES inscripciones(id) ON DELETE CASCADE,
    CONSTRAINT fk_cal_sec_mat FOREIGN KEY (id_materia)
        REFERENCES materias(id) ON DELETE RESTRICT,
    CONSTRAINT fk_cal_sec_usr FOREIGN KEY (actualizado_por)
        REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS horarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    id_periodo INT NOT NULL,
    id_seccion INT NOT NULL,
    id_materia INT NULL,
    id_docente INT NOT NULL,
    dia_semana TINYINT NOT NULL COMMENT '1=Lunes, 2=Martes, 3=Miercoles, 4=Jueves, 5=Viernes',
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    aula VARCHAR(40) NULL,
    descripcion_bloque VARCHAR(100) NULL,
    INDEX idx_horario_seccion (id_periodo, id_seccion, dia_semana),
    INDEX idx_horario_docente (id_periodo, id_docente, dia_semana),
    CONSTRAINT fk_hor_periodo FOREIGN KEY (id_periodo)
        REFERENCES periodos_escolares(id) ON DELETE RESTRICT,
    CONSTRAINT fk_hor_seccion FOREIGN KEY (id_seccion)
        REFERENCES secciones(id) ON DELETE CASCADE,
    CONSTRAINT fk_hor_materia FOREIGN KEY (id_materia)
        REFERENCES materias(id) ON DELETE SET NULL,
    CONSTRAINT fk_hor_docente FOREIGN KEY (id_docente)
        REFERENCES docentes(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 1. Configuracion institucional inicial
-- ============================================================================
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('nombre_plantel', 'Escuela Básica Nacional "Los Laureles"');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('nombre_corto', 'E. B. N. "Los Laureles"');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('dependencia', 'Pública / Nacional — Adscrita al Ministerio del Poder Popular para la Educación');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('rif', 'J-409263770');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('codigo_dea', 'S2355D2303');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('codigo_estadistico', '230129');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('direccion', 'Urb. Los Laureles, sector 6, calle 14 con calle 25 (ref. calle 27 / C. 7), parroquia Germán Ríos Linares, municipio Cabimas, estado Zulia');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('director', 'Por definir en Configuración');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('titulo_media', 'Bachiller en Ciencias');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('encabezado_pais', 'REPÚBLICA BOLIVARIANA DE VENEZUELA');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('encabezado_ministerio', 'MINISTERIO DEL PODER POPULAR PARA LA EDUCACIÓN');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('centro_calidad', 'VIII. Centro de Desarrollo de la Calidad Educativa Estatal');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('pie_fiscal', 'VALOR FISCAL: Para su validez legal y de acuerdo al Ramo de Estampillas, al dorso de este documento se le debe colocar tres décimas de la Unidad Tributaria (0,3 U.T) | ESTE SERVICIO ES GRATUITO');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('te_defecto', 'F');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('mes_defecto', '07');
INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES ('anio_defecto', '2027');

-- ============================================================================
-- 2. Usuarios semilla (contrasenas cifradas con scrypt)
-- ============================================================================
INSERT IGNORE INTO usuarios (nombre, username, password_hash, rol, activo, debe_cambiar_password) VALUES ('Administrador del Sistema', 'admin', 'scrypt:32768:8:1$pbyVw1h3E92A9yDT$d6cf556d6e3d0c2a43d1fab84c50031dfde7f6281d0f506774a8622519935dec38fcb6179305b2d45eacf3e3db24274ff7ad6699597f8df2a88dae182a220308', 'admin', TRUE, TRUE);
INSERT IGNORE INTO usuarios (nombre, username, password_hash, rol, activo, debe_cambiar_password) VALUES ('Operador Control de Estudio', 'operador', 'scrypt:32768:8:1$rpkNNke5qEpHDHlG$7f3c84f65e2af713330ee58a3ac7fb6a13365a28d77246dfb2cc2b94f4eb92ed185e0e2a84e760020cd44bf113f5ebcbfb9eedd7f9a78f49d0deadec57204547', 'operador', TRUE, TRUE);

-- ============================================================================
-- 3. Niveles educativos y bloques de formacion
-- ============================================================================
INSERT IGNORE INTO niveles_educativos (nombre, tipo_escala, titulo_otorga, orden) VALUES ('Educación Primaria', 'literal', 'Certificado de Educación Primaria', 1);
INSERT IGNORE INTO niveles_educativos (nombre, tipo_escala, titulo_otorga, orden) VALUES ('Educación Media General', 'numerica', 'Bachiller en Ciencias', 2);
INSERT IGNORE INTO bloques_formacion (nombre, orden) VALUES ('Formación General', 1);
INSERT IGNORE INTO bloques_formacion (nombre, orden) VALUES ('Formación Científica, Tecnológica y Productiva', 2);
INSERT IGNORE INTO bloques_formacion (nombre, orden) VALUES ('Práctica Vocacional y Profesional', 3);

-- ============================================================================
-- 4. Grados (1.o a 6.o Grado) y Anios (1.o a 5.o Anio)
-- ============================================================================
INSERT IGNORE INTO grados_anios (id_nivel, nombre, orden, activo) SELECT id, '1.º Grado', 1, TRUE FROM niveles_educativos WHERE nombre = 'Educación Primaria';
INSERT IGNORE INTO grados_anios (id_nivel, nombre, orden, activo) SELECT id, '2.º Grado', 2, TRUE FROM niveles_educativos WHERE nombre = 'Educación Primaria';
INSERT IGNORE INTO grados_anios (id_nivel, nombre, orden, activo) SELECT id, '3.º Grado', 3, TRUE FROM niveles_educativos WHERE nombre = 'Educación Primaria';
INSERT IGNORE INTO grados_anios (id_nivel, nombre, orden, activo) SELECT id, '4.º Grado', 4, TRUE FROM niveles_educativos WHERE nombre = 'Educación Primaria';
INSERT IGNORE INTO grados_anios (id_nivel, nombre, orden, activo) SELECT id, '5.º Grado', 5, TRUE FROM niveles_educativos WHERE nombre = 'Educación Primaria';
INSERT IGNORE INTO grados_anios (id_nivel, nombre, orden, activo) SELECT id, '6.º Grado', 6, TRUE FROM niveles_educativos WHERE nombre = 'Educación Primaria';
INSERT IGNORE INTO grados_anios (id_nivel, nombre, orden, activo) SELECT id, '1.º Año', 1, TRUE FROM niveles_educativos WHERE nombre = 'Educación Media General';
INSERT IGNORE INTO grados_anios (id_nivel, nombre, orden, activo) SELECT id, '2.º Año', 2, TRUE FROM niveles_educativos WHERE nombre = 'Educación Media General';
INSERT IGNORE INTO grados_anios (id_nivel, nombre, orden, activo) SELECT id, '3.º Año', 3, TRUE FROM niveles_educativos WHERE nombre = 'Educación Media General';
INSERT IGNORE INTO grados_anios (id_nivel, nombre, orden, activo) SELECT id, '4.º Año', 4, TRUE FROM niveles_educativos WHERE nombre = 'Educación Media General';
INSERT IGNORE INTO grados_anios (id_nivel, nombre, orden, activo) SELECT id, '5.º Año', 5, TRUE FROM niveles_educativos WHERE nombre = 'Educación Media General';

-- ============================================================================
-- 5. Periodos escolares (activo 2026-2027 e historicos cerrados 2022-2026)
-- ============================================================================
INSERT IGNORE INTO periodos_escolares (nombre, activo, cerrado, fecha_inicio, fecha_fin) VALUES ('2026-2027', TRUE, FALSE, '2026-09-15', '2027-07-31');
INSERT IGNORE INTO periodos_escolares (nombre, activo, cerrado, fecha_inicio, fecha_fin) VALUES ('2022-2023', FALSE, TRUE, '2022-09-15', '2023-07-31');
INSERT IGNORE INTO periodos_escolares (nombre, activo, cerrado, fecha_inicio, fecha_fin) VALUES ('2023-2024', FALSE, TRUE, '2023-09-15', '2024-07-31');
INSERT IGNORE INTO periodos_escolares (nombre, activo, cerrado, fecha_inicio, fecha_fin) VALUES ('2024-2025', FALSE, TRUE, '2024-09-15', '2025-07-31');
INSERT IGNORE INTO periodos_escolares (nombre, activo, cerrado, fecha_inicio, fecha_fin) VALUES ('2025-2026', FALSE, TRUE, '2025-09-15', '2026-07-31');

-- ============================================================================
-- 6. Secciones base (A y B en periodo activo 2026-2027)
-- ============================================================================
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '1.º Grado' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'B', 'Tarde', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '1.º Grado' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '2.º Grado' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'B', 'Tarde', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '2.º Grado' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '3.º Grado' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'B', 'Tarde', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '3.º Grado' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '4.º Grado' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'B', 'Tarde', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '4.º Grado' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '5.º Grado' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'B', 'Tarde', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '5.º Grado' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '6.º Grado' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'B', 'Tarde', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '6.º Grado' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '1.º Año' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'B', 'Tarde', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '1.º Año' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '2.º Año' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'B', 'Tarde', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '2.º Año' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '3.º Año' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'B', 'Tarde', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '3.º Año' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '4.º Año' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'B', 'Tarde', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '4.º Año' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '5.º Año' WHERE p.nombre = '2026-2027';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'B', 'Tarde', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '5.º Año' WHERE p.nombre = '2026-2027';

-- ============================================================================
-- 7. Materias basicas Media General (Fisica, Quimica y Biologia desde 3.o Anio)
-- ============================================================================
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Matemáticas', 'MAT', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '1.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Castellano', 'CAS', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '1.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Inglés', 'ING', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '1.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Educación Física', 'EDF', TRUE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '1.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Matemáticas', 'MAT', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '2.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Castellano', 'CAS', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '2.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Inglés', 'ING', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '2.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Educación Física', 'EDF', TRUE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '2.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Matemáticas', 'MAT', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '3.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Castellano', 'CAS', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '3.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Inglés', 'ING', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '3.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Educación Física', 'EDF', TRUE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '3.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Física', 'FIS', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '3.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Química', 'QUI', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '3.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Biología', 'BIO', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '3.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Matemáticas', 'MAT', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '4.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Castellano', 'CAS', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '4.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Inglés', 'ING', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '4.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Educación Física', 'EDF', TRUE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '4.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Física', 'FIS', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '4.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Química', 'QUI', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '4.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Biología', 'BIO', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '4.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Matemáticas', 'MAT', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '5.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Castellano', 'CAS', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '5.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Inglés', 'ING', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '5.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Educación Física', 'EDF', TRUE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación General' WHERE g.nombre = '5.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Física', 'FIS', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '5.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Química', 'QUI', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '5.º Año';
INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) SELECT g.id, b.id, 'Biología', 'BIO', FALSE, TRUE FROM grados_anios g JOIN bloques_formacion b ON b.nombre = 'Formación Científica, Tecnológica y Productiva' WHERE g.nombre = '5.º Año';

-- ============================================================================
-- 8. 8 Docentes semilla
-- ============================================================================
INSERT IGNORE INTO docentes (cedula, nombres, apellidos, telefono, correo, direccion, especialidad, categoria, activo) VALUES ('V-14250110', 'Carlos Alberto', 'Mendoza Ríos', '0414-6201101', 'cmendoza@loslaureles.edu.ve', 'Urb. Los Laureles, Cabimas', 'Matemáticas', 'Media General', TRUE);
INSERT IGNORE INTO docentes (cedula, nombres, apellidos, telefono, correo, direccion, especialidad, categoria, activo) VALUES ('V-15340221', 'Yelitza Carolina', 'Ramírez Ochoa', '0412-6202202', 'yramirez@loslaureles.edu.ve', 'Sector Las 40, Cabimas', 'Castellano', 'Media General', TRUE);
INSERT IGNORE INTO docentes (cedula, nombres, apellidos, telefono, correo, direccion, especialidad, categoria, activo) VALUES ('V-16480332', 'Luis Eduardo', 'Castillo Bracho', '0424-6203303', 'lcastillo@loslaureles.edu.ve', 'Urb. Concordia, Cabimas', 'Inglés', 'Especialista', TRUE);
INSERT IGNORE INTO docentes (cedula, nombres, apellidos, telefono, correo, direccion, especialidad, categoria, activo) VALUES ('V-13890443', 'Maritza Elena', 'Rojas Delgado', '0416-6204404', 'mrojas@loslaureles.edu.ve', 'Urb. Los Laureles, Cabimas', 'Física y Química', 'Media General', TRUE);
INSERT IGNORE INTO docentes (cedula, nombres, apellidos, telefono, correo, direccion, especialidad, categoria, activo) VALUES ('V-17120554', 'José Gregorio', 'Pirela Montero', '0414-6205505', 'jpirela@loslaureles.edu.ve', 'Sector Delicias Nuevas, Cabimas', 'Biología', 'Media General', TRUE);
INSERT IGNORE INTO docentes (cedula, nombres, apellidos, telefono, correo, direccion, especialidad, categoria, activo) VALUES ('V-18230665', 'Rafael Antonio', 'Briceño Soto', '0426-6206606', 'rbriceno@loslaureles.edu.ve', 'Urb. Buena Vista, Cabimas', 'Educación Física', 'Especialista', TRUE);
INSERT IGNORE INTO docentes (cedula, nombres, apellidos, telefono, correo, direccion, especialidad, categoria, activo) VALUES ('V-15910776', 'Carmen Rosa', 'González Medina', '0414-6207707', 'cgonzalez@loslaureles.edu.ve', 'Urb. Los Laureles, Cabimas', 'Educación Integral (Primaria)', 'Primaria', TRUE);
INSERT IGNORE INTO docentes (cedula, nombres, apellidos, telefono, correo, direccion, especialidad, categoria, activo) VALUES ('V-16750887', 'Norelys Josefina', 'Urdaneta Salas', '0412-6208808', 'nurdaneta@loslaureles.edu.ve', 'Sector Ambrosio, Cabimas', 'Educación Integral (Primaria)', 'Primaria', TRUE);

-- ============================================================================
-- 9. 10 Estudiantes y Representantes semilla (sin matricula en 2026-2027)
-- ============================================================================
INSERT IGNORE INTO estudiantes (cedula, nombres, apellidos, genero, fecha_nacimiento, direccion, egresado, activo) VALUES ('V-33101001', 'Sofía Valentina', 'Márquez León', 'F', '2018-04-12', 'Urb. Los Laureles, sector 6, calle 14', FALSE, TRUE);
INSERT IGNORE INTO representantes (cedula, nombres, apellidos, parentesco, telefono, telefono_trabajo, correo, direccion) VALUES ('V-17101001', 'Patricia Elena', 'León de Márquez', 'Madre', '0414-6310101', '0264-2410101', 'pleon@correo.com', 'Urb. Los Laureles, sector 6, calle 14');
INSERT IGNORE INTO estudiante_representantes (id_estudiante, id_representante, es_principal) SELECT e.id, r.id, TRUE FROM estudiantes e JOIN representantes r ON r.cedula = 'V-17101001' WHERE e.cedula = 'V-33101001';
INSERT IGNORE INTO estudiantes (cedula, nombres, apellidos, genero, fecha_nacimiento, direccion, egresado, activo) VALUES ('V-33101002', 'Mateo Alejandro', 'Quintero Paz', 'M', '2017-08-23', 'Urb. Los Laureles, sector 4, calle 8', FALSE, TRUE);
INSERT IGNORE INTO representantes (cedula, nombres, apellidos, parentesco, telefono, telefono_trabajo, correo, direccion) VALUES ('V-16202002', 'Ricardo José', 'Quintero Morales', 'Padre', '0412-6320202', '', 'rquintero@correo.com', 'Urb. Los Laureles, sector 4, calle 8');
INSERT IGNORE INTO estudiante_representantes (id_estudiante, id_representante, es_principal) SELECT e.id, r.id, TRUE FROM estudiantes e JOIN representantes r ON r.cedula = 'V-16202002' WHERE e.cedula = 'V-33101002';
INSERT IGNORE INTO estudiantes (cedula, nombres, apellidos, genero, fecha_nacimiento, direccion, egresado, activo) VALUES ('V-33101003', 'Camila Andrea', 'Finol Herrera', 'F', '2016-02-19', 'Sector Las 40, calle 10', FALSE, TRUE);
INSERT IGNORE INTO representantes (cedula, nombres, apellidos, parentesco, telefono, telefono_trabajo, correo, direccion) VALUES ('V-18303003', 'Mariana Isabel', 'Herrera Silva', 'Madre', '0424-6330303', '', 'mherrera@correo.com', 'Sector Las 40, calle 10');
INSERT IGNORE INTO estudiante_representantes (id_estudiante, id_representante, es_principal) SELECT e.id, r.id, TRUE FROM estudiantes e JOIN representantes r ON r.cedula = 'V-18303003' WHERE e.cedula = 'V-33101003';
INSERT IGNORE INTO estudiantes (cedula, nombres, apellidos, genero, fecha_nacimiento, direccion, egresado, activo) VALUES ('V-33101004', 'Diego Sebastián', 'Chacín Romero', 'M', '2015-11-05', 'Urb. Concordia, vereda 12', FALSE, TRUE);
INSERT IGNORE INTO representantes (cedula, nombres, apellidos, parentesco, telefono, telefono_trabajo, correo, direccion) VALUES ('V-15404004', 'Héctor Manuel', 'Chacín Nava', 'Padre', '0416-6340404', '0264-2410404', 'hchacin@correo.com', 'Urb. Concordia, vereda 12');
INSERT IGNORE INTO estudiante_representantes (id_estudiante, id_representante, es_principal) SELECT e.id, r.id, TRUE FROM estudiantes e JOIN representantes r ON r.cedula = 'V-15404004' WHERE e.cedula = 'V-33101004';
INSERT IGNORE INTO estudiantes (cedula, nombres, apellidos, genero, fecha_nacimiento, direccion, egresado, activo) VALUES ('V-33101005', 'Valeria Lucía', 'Perozo Díaz', 'F', '2014-06-30', 'Urb. Los Laureles, sector 6, calle 25', FALSE, TRUE);
INSERT IGNORE INTO representantes (cedula, nombres, apellidos, parentesco, telefono, telefono_trabajo, correo, direccion) VALUES ('V-17505005', 'Claudia Beatriz', 'Díaz de Perozo', 'Madre', '0414-6350505', '', 'cdiaz@correo.com', 'Urb. Los Laureles, sector 6, calle 25');
INSERT IGNORE INTO estudiante_representantes (id_estudiante, id_representante, es_principal) SELECT e.id, r.id, TRUE FROM estudiantes e JOIN representantes r ON r.cedula = 'V-17505005' WHERE e.cedula = 'V-33101005';
INSERT IGNORE INTO estudiantes (cedula, nombres, apellidos, genero, fecha_nacimiento, direccion, egresado, activo) VALUES ('V-32101006', 'Santiago David', 'Vílchez Morales', 'M', '2010-09-14', 'Sector Delicias Nuevas, av. 32', FALSE, TRUE);
INSERT IGNORE INTO representantes (cedula, nombres, apellidos, parentesco, telefono, telefono_trabajo, correo, direccion) VALUES ('V-14606006', 'Oscar Enrique', 'Vílchez Gómez', 'Padre', '0426-6360606', '', 'ovilchez@correo.com', 'Sector Delicias Nuevas, av. 32');
INSERT IGNORE INTO estudiante_representantes (id_estudiante, id_representante, es_principal) SELECT e.id, r.id, TRUE FROM estudiantes e JOIN representantes r ON r.cedula = 'V-14606006' WHERE e.cedula = 'V-32101006';
INSERT IGNORE INTO estudiantes (cedula, nombres, apellidos, genero, fecha_nacimiento, direccion, egresado, activo) VALUES ('V-32101007', 'Isabella Sofía', 'Nava Zambrano', 'F', '2011-03-27', 'Urb. Buena Vista, calle 5', FALSE, TRUE);
INSERT IGNORE INTO representantes (cedula, nombres, apellidos, parentesco, telefono, telefono_trabajo, correo, direccion) VALUES ('V-16707007', 'Verónica del Valle', 'Zambrano Cruz', 'Madre', '0412-6370707', '0264-2410707', 'vzambrano@correo.com', 'Urb. Buena Vista, calle 5');
INSERT IGNORE INTO estudiante_representantes (id_estudiante, id_representante, es_principal) SELECT e.id, r.id, TRUE FROM estudiantes e JOIN representantes r ON r.cedula = 'V-16707007' WHERE e.cedula = 'V-32101007';
INSERT IGNORE INTO estudiantes (cedula, nombres, apellidos, genero, fecha_nacimiento, direccion, egresado, activo) VALUES ('V-31101008', 'Gabriel Enrique', 'Colina Vargas', 'M', '2010-07-18', 'Sector Ambrosio, av. Principal', FALSE, TRUE);
INSERT IGNORE INTO representantes (cedula, nombres, apellidos, parentesco, telefono, telefono_trabajo, correo, direccion) VALUES ('V-15808008', 'Eduardo Luis', 'Colina Méndez', 'Padre', '0414-6380808', '', 'ecolina@correo.com', 'Sector Ambrosio, av. Principal');
INSERT IGNORE INTO estudiante_representantes (id_estudiante, id_representante, es_principal) SELECT e.id, r.id, TRUE FROM estudiantes e JOIN representantes r ON r.cedula = 'V-15808008' WHERE e.cedula = 'V-31101008';
INSERT IGNORE INTO estudiantes (cedula, nombres, apellidos, genero, fecha_nacimiento, direccion, egresado, activo) VALUES ('V-31101009', 'Antonella María', 'Palmar Chirinos', 'F', '2010-12-09', 'Urb. Los Laureles, sector 5, calle 19', FALSE, TRUE);
INSERT IGNORE INTO representantes (cedula, nombres, apellidos, parentesco, telefono, telefono_trabajo, correo, direccion) VALUES ('V-14909009', 'Lisbeth Carolina', 'Chirinos Reyes', 'Madre', '0424-6390909', '', 'lchirinos@correo.com', 'Urb. Los Laureles, sector 5, calle 19');
INSERT IGNORE INTO estudiante_representantes (id_estudiante, id_representante, es_principal) SELECT e.id, r.id, TRUE FROM estudiantes e JOIN representantes r ON r.cedula = 'V-14909009' WHERE e.cedula = 'V-31101009';
INSERT IGNORE INTO estudiantes (cedula, nombres, apellidos, genero, fecha_nacimiento, direccion, egresado, activo) VALUES ('V-30101010', 'Andrés Felipe', 'Salazar Rincón', 'M', '2010-01-22', 'Urb. Los Laureles, sector 6, calle 27', FALSE, TRUE);
INSERT IGNORE INTO representantes (cedula, nombres, apellidos, parentesco, telefono, telefono_trabajo, correo, direccion) VALUES ('V-13101010', 'Jorge Alberto', 'Salazar Peña', 'Padre', '0416-6401010', '0264-2411010', 'jsalazar@correo.com', 'Urb. Los Laureles, sector 6, calle 27');
INSERT IGNORE INTO estudiante_representantes (id_estudiante, id_representante, es_principal) SELECT e.id, r.id, TRUE FROM estudiantes e JOIN representantes r ON r.cedula = 'V-13101010' WHERE e.cedula = 'V-30101010';

-- ============================================================================
-- 10. Historial aprobado 1.o a 4.o Anio para 5 estudiantes (por iniciar 5.o Anio)
-- ============================================================================
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '1.º Año' WHERE p.nombre = '2022-2023';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '1.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-32101006' WHERE p.nombre = '2022-2023';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 15, 15, 16, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 14, 16, 16, 15, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 14, 17, 15, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 15, 15, 15, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '1.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-32101007' WHERE p.nombre = '2022-2023';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 17, 18, 17, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 18, 19, 18, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 16, 17, 17, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 19, 17, 18, 18, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '1.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-31101008' WHERE p.nombre = '2022-2023';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 14, 14, 16, 15, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 15, 14, 15, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 13, 15, 15, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 13, 14, 16, 14, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '1.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-31101009' WHERE p.nombre = '2022-2023';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 19, 18, 18, 18, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 20, 19, 19, 19, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 17, 20, 18, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 18, 18, 18, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '1.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-30101010' WHERE p.nombre = '2022-2023';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 16, 17, 17, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 17, 18, 17, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 15, 16, 16, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 16, 17, 17, 'F', '07', '2023' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2022-2023' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '1.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '2.º Año' WHERE p.nombre = '2023-2024';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '2.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-32101006' WHERE p.nombre = '2023-2024';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 14, 15, 15, 15, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 16, 16, 16, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 14, 17, 16, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 15, 15, 16, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '2.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-32101007' WHERE p.nombre = '2023-2024';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 17, 18, 17, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 18, 19, 18, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 19, 16, 17, 17, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 17, 18, 17, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '2.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-31101008' WHERE p.nombre = '2023-2024';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 14, 16, 15, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 15, 14, 15, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 13, 13, 15, 14, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 14, 14, 16, 15, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '2.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-31101009' WHERE p.nombre = '2023-2024';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 20, 18, 18, 19, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 19, 19, 18, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 17, 20, 18, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 19, 18, 18, 18, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '2.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-30101010' WHERE p.nombre = '2023-2024';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 16, 17, 16, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 17, 18, 17, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 15, 16, 16, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 16, 17, 17, 'F', '07', '2024' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2023-2024' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '2.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '3.º Año' WHERE p.nombre = '2024-2025';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '3.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-32101006' WHERE p.nombre = '2024-2025';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 15, 15, 15, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 16, 16, 16, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 14, 17, 16, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 14, 15, 15, 15, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 16, 16, 16, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 14, 17, 16, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Química';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 15, 15, 16, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Biología';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '3.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-32101007' WHERE p.nombre = '2024-2025';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 17, 18, 18, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 19, 18, 19, 19, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 16, 17, 16, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 17, 18, 17, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 18, 19, 18, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 19, 16, 17, 17, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Química';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 17, 18, 17, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Biología';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '3.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-31101008' WHERE p.nombre = '2024-2025';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 14, 16, 15, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 13, 15, 14, 14, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 14, 13, 15, 14, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 14, 16, 15, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 15, 14, 15, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 13, 13, 15, 14, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Química';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 14, 14, 16, 15, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Biología';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '3.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-31101009' WHERE p.nombre = '2024-2025';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 18, 18, 18, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 19, 19, 19, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 19, 17, 20, 19, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 20, 18, 18, 19, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 19, 19, 18, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 17, 20, 18, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Química';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 19, 18, 18, 18, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Biología';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '3.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-30101010' WHERE p.nombre = '2024-2025';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 16, 17, 16, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 17, 18, 17, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 15, 16, 16, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 16, 17, 16, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 17, 18, 17, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 15, 16, 16, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Química';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 16, 17, 17, 'F', '07', '2025' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2024-2025' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '3.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Biología';
INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) SELECT p.id, g.id, 'A', 'Mañana', TRUE FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '4.º Año' WHERE p.nombre = '2025-2026';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '4.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-32101006' WHERE p.nombre = '2025-2026';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 15, 15, 15, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 16, 16, 16, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 14, 14, 17, 15, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 15, 15, 15, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 16, 16, 16, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 14, 17, 16, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Química';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 14, 15, 15, 15, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101006' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Biología';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '4.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-32101007' WHERE p.nombre = '2025-2026';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 19, 17, 18, 18, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 18, 19, 18, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 16, 17, 17, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 17, 18, 18, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 19, 18, 19, 19, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 16, 17, 16, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Química';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 17, 18, 17, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-32101007' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Biología';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '4.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-31101008' WHERE p.nombre = '2025-2026';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 13, 14, 16, 14, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 14, 15, 14, 14, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 13, 15, 14, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 14, 16, 15, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 13, 15, 14, 14, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 14, 13, 15, 14, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Química';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 14, 16, 15, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101008' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Biología';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '4.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-31101009' WHERE p.nombre = '2025-2026';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 18, 18, 18, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 19, 19, 19, 19, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 20, 17, 20, 19, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 18, 18, 18, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 19, 19, 19, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 19, 17, 20, 19, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Química';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 20, 18, 18, 19, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-31101009' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Biología';
INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) SELECT p.id, e.id, s.id, 'activo', 'regular' FROM periodos_escolares p JOIN grados_anios g ON g.nombre = '4.º Año' JOIN secciones s ON s.id_periodo = p.id AND s.id_grado_anio = g.id AND s.nombre = 'A' JOIN estudiantes e ON e.cedula = 'V-30101010' WHERE p.nombre = '2025-2026';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 16, 17, 17, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Matemáticas';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 17, 18, 18, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Castellano';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 15, 16, 15, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Inglés';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 16, 16, 17, 16, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Educación Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 17, 17, 18, 17, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Física';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 18, 15, 16, 16, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Química';
INSERT IGNORE INTO calificaciones_secundaria (id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) SELECT i.id, m.id, 15, 16, 17, 16, 'F', '07', '2026' FROM inscripciones i JOIN periodos_escolares p ON p.id = i.id_periodo AND p.nombre = '2025-2026' JOIN estudiantes e ON e.id = i.id_estudiante AND e.cedula = 'V-30101010' JOIN grados_anios g ON g.nombre = '4.º Año' JOIN materias m ON m.id_grado_anio = g.id AND m.nombre = 'Biología';

-- ============================================================================
-- 11. Asignaciones iniciales de docentes por materia y titulares en 2026-2027
-- ============================================================================
UPDATE secciones s
JOIN periodos_escolares p ON p.id = s.id_periodo AND p.nombre = '2026-2027'
JOIN grados_anios g ON g.id = s.id_grado_anio
JOIN niveles_educativos n ON n.id = g.id_nivel AND n.tipo_escala = 'literal'
JOIN docentes d ON d.cedula = CASE WHEN s.nombre = 'A' THEN 'V-15910776' ELSE 'V-16750887' END
SET s.id_docente_titular_guia = d.id
WHERE s.activo = TRUE AND s.id_docente_titular_guia IS NULL;

INSERT IGNORE INTO asignaciones_docentes (id_periodo, id_seccion, id_materia, id_docente)
SELECT p.id, s.id, m.id, d.id
FROM secciones s
JOIN periodos_escolares p ON p.id = s.id_periodo AND p.nombre = '2026-2027'
JOIN grados_anios g ON g.id = s.id_grado_anio
JOIN niveles_educativos n ON n.id = g.id_nivel AND n.tipo_escala = 'numerica'
JOIN materias m ON m.id_grado_anio = g.id AND m.activo = TRUE
JOIN docentes d ON d.cedula = CASE m.nombre
    WHEN 'Matemáticas' THEN 'V-14250110'
    WHEN 'Castellano' THEN 'V-15340221'
    WHEN 'Inglés' THEN 'V-16480332'
    WHEN 'Física' THEN 'V-13890443'
    WHEN 'Química' THEN 'V-13890443'
    WHEN 'Biología' THEN 'V-17120554'
    WHEN 'Educación Física' THEN 'V-18230665'
    ELSE NULL
END
WHERE s.activo = TRUE;

SET FOREIGN_KEY_CHECKS = 1;
