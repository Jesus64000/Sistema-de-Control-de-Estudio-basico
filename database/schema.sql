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
