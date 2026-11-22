import os
from werkzeug.security import generate_password_hash
from config import BASE_DIR, Config
from db import obtener_conexion

CONFIG_INICIAL = {
    "nombre_plantel": 'Escuela Básica Nacional "Los Laureles"',
    "nombre_corto": 'E. B. N. "Los Laureles"',
    "dependencia": "Pública / Nacional — Adscrita al Ministerio del Poder Popular para la Educación",
    "rif": "J-409263770",
    "codigo_dea": "S2355D2303",
    "codigo_estadistico": "230129",
    "direccion": "Urb. Los Laureles, sector 6, calle 14 con calle 25 (ref. calle 27 / C. 7), parroquia Germán Ríos Linares, municipio Cabimas, estado Zulia",
    "director": "Por definir en Configuración",
    "titulo_media": "Bachiller en Ciencias",
    "encabezado_pais": "REPÚBLICA BOLIVARIANA DE VENEZUELA",
    "encabezado_ministerio": "MINISTERIO DEL PODER POPULAR PARA LA EDUCACIÓN",
    "centro_calidad": "VIII. Centro de Desarrollo de la Calidad Educativa Estatal",
    "pie_fiscal": "VALOR FISCAL: Para su validez legal y de acuerdo al Ramo de Estampillas, al dorso de este documento se le debe colocar tres décimas de la Unidad Tributaria (0,3 U.T) | ESTE SERVICIO ES GRATUITO",
    "te_defecto": "F",
    "mes_defecto": "07",
    "anio_defecto": "2027",
}


def inicializar():
    """Crea la base de datos, tablas y datos iniciales de E. B. N. Los Laureles."""
    conn = obtener_conexion(usar_bd=False)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cur.execute(f"USE `{Config.DB_NAME}`")

            schema_path = os.path.join(BASE_DIR, "database", "schema.sql")
            with open(schema_path, "r", encoding="utf-8") as f:
                raw_sql = f.read()

            for stmt in raw_sql.split(";"):
                stmt = stmt.strip()
                if stmt and not stmt.startswith("--"):
                    cur.execute(stmt)

            # Migracion segura: asegurar columna correo en usuarios si la tabla ya existia
            cur.execute(
                "SELECT COUNT(*) AS c FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'usuarios' AND COLUMN_NAME = 'correo'",
                (Config.DB_NAME,),
            )
            if cur.fetchone()["c"] == 0:
                cur.execute("ALTER TABLE usuarios ADD COLUMN correo VARCHAR(120) NULL AFTER username")

            # Migracion segura: cierre formal en periodos_escolares
            cur.execute(
                "SELECT COUNT(*) AS c FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'periodos_escolares' AND COLUMN_NAME = 'cerrado'",
                (Config.DB_NAME,),
            )
            if cur.fetchone()["c"] == 0:
                cur.execute(
                    "ALTER TABLE periodos_escolares ADD COLUMN cerrado BOOLEAN NOT NULL DEFAULT FALSE AFTER activo"
                )

            # Migracion segura: bandera egresado en estudiantes
            cur.execute(
                "SELECT COUNT(*) AS c FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'estudiantes' AND COLUMN_NAME = 'egresado'",
                (Config.DB_NAME,),
            )
            if cur.fetchone()["c"] == 0:
                cur.execute(
                    "ALTER TABLE estudiantes ADD COLUMN egresado BOOLEAN NOT NULL DEFAULT FALSE AFTER direccion"
                )

            # Migracion segura: condicion academica en inscripciones
            cur.execute(
                "SELECT COUNT(*) AS c FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'inscripciones' AND COLUMN_NAME = 'condicion'",
                (Config.DB_NAME,),
            )
            if cur.fetchone()["c"] == 0:
                cur.execute(
                    "ALTER TABLE inscripciones "
                    "ADD COLUMN condicion ENUM('regular', 'repitiente', 'materia_pendiente', 'reingreso') "
                    "NOT NULL DEFAULT 'regular' AFTER estado"
                )

            # Migracion segura: permitir notas decimales (ej. 11.5, 18.4) en calificaciones_secundaria
            cur.execute(
                "SELECT DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'calificaciones_secundaria' AND COLUMN_NAME = 'lapso_1'",
                (Config.DB_NAME,),
            )
            col_info = cur.fetchone()
            if col_info and col_info["DATA_TYPE"] != "decimal":
                cur.execute(
                    "ALTER TABLE calificaciones_secundaria "
                    "MODIFY COLUMN lapso_1 DECIMAL(4,1) NULL, "
                    "MODIFY COLUMN lapso_2 DECIMAL(4,1) NULL, "
                    "MODIFY COLUMN lapso_3 DECIMAL(4,1) NULL, "
                    "MODIFY COLUMN definitiva DECIMAL(4,1) NULL"
                )

            # Configuracion institucional
            for clave, valor in CONFIG_INICIAL.items():
                cur.execute(
                    "INSERT IGNORE INTO configuracion_institucional (clave, valor) VALUES (%s, %s)",
                    (clave, valor),
                )

            # Usuarios semilla
            usuarios_semilla = [
                ("Administrador del Sistema", "admin", "admin123", "admin"),
                ("Operador Control de Estudio", "operador", "operador123", "operador"),
            ]
            for nombre, username, pwd, rol in usuarios_semilla:
                cur.execute(
                    "INSERT IGNORE INTO usuarios (nombre, username, password_hash, rol, activo, debe_cambiar_password) "
                    "VALUES (%s, %s, %s, %s, TRUE, TRUE)",
                    (nombre, username, generate_password_hash(pwd, method="scrypt"), rol),
                )

            # Niveles educativos base
            cur.execute(
                "INSERT IGNORE INTO niveles_educativos (nombre, tipo_escala, titulo_otorga, orden) "
                "VALUES (%s, %s, %s, %s)",
                ("Educación Primaria", "literal", "Certificado de Educación Primaria", 1),
            )
            cur.execute(
                "INSERT IGNORE INTO niveles_educativos (nombre, tipo_escala, titulo_otorga, orden) "
                "VALUES (%s, %s, %s, %s)",
                ("Educación Media General", "numerica", "Bachiller en Ciencias", 2),
            )

            # Bloques de formacion base
            bloques = [
                ("Formación General", 1),
                ("Formación Científica, Tecnológica y Productiva", 2),
                ("Práctica Vocacional y Profesional", 3),
            ]
            for nombre_b, orden in bloques:
                cur.execute(
                    "INSERT IGNORE INTO bloques_formacion (nombre, orden) VALUES (%s, %s)",
                    (nombre_b, orden),
                )

            # Periodo escolar inicial si no existe ninguno
            cur.execute("SELECT COUNT(*) AS total FROM periodos_escolares")
            if cur.fetchone()["total"] == 0:
                cur.execute(
                    "INSERT INTO periodos_escolares (nombre, activo, fecha_inicio, fecha_fin) "
                    "VALUES ('2026-2027', TRUE, '2026-09-15', '2027-07-31')"
                )

            # Obtener IDs de niveles, bloques y periodo activo para la estructura base
            cur.execute("SELECT id, nombre FROM niveles_educativos")
            niveles_map = {r["nombre"]: r["id"] for r in cur.fetchall()}
            id_primaria = niveles_map.get("Educación Primaria")
            id_media = niveles_map.get("Educación Media General")

            cur.execute("SELECT id, nombre FROM bloques_formacion")
            bloques_map = {r["nombre"]: r["id"] for r in cur.fetchall()}
            id_bloque_general = bloques_map.get("Formación General")
            id_bloque_cientifica = bloques_map.get("Formación Científica, Tecnológica y Productiva")

            # Grados y Anios estandar (1.o a 6.o Grado de Primaria y 1.o a 5.o Anio de Media General)
            grados_primaria = [
                ("1.º Grado", 1),
                ("2.º Grado", 2),
                ("3.º Grado", 3),
                ("4.º Grado", 4),
                ("5.º Grado", 5),
                ("6.º Grado", 6),
            ]
            grados_media = [
                ("1.º Año", 1),
                ("2.º Año", 2),
                ("3.º Año", 3),
                ("4.º Año", 4),
                ("5.º Año", 5),
            ]
            if id_primaria:
                for nombre_g, orden_g in grados_primaria:
                    cur.execute(
                        "INSERT IGNORE INTO grados_anios (id_nivel, nombre, orden, activo) "
                        "VALUES (%s, %s, %s, TRUE)",
                        (id_primaria, nombre_g, orden_g),
                    )
            if id_media:
                for nombre_g, orden_g in grados_media:
                    cur.execute(
                        "INSERT IGNORE INTO grados_anios (id_nivel, nombre, orden, activo) "
                        "VALUES (%s, %s, %s, TRUE)",
                        (id_media, nombre_g, orden_g),
                    )

            cur.execute("SELECT id, id_nivel, nombre, orden FROM grados_anios")
            grados_rows = cur.fetchall()
            grados_base_nombres = {g[0] for g in grados_primaria + grados_media}

            # Secciones base minimas (A y B) en el periodo activo para cada grado y anio
            cur.execute("SELECT id FROM periodos_escolares WHERE activo = TRUE LIMIT 1")
            per_activo = cur.fetchone()
            if per_activo:
                pid_activo = per_activo["id"]
                for g in grados_rows:
                    if g["nombre"] not in grados_base_nombres:
                        continue
                    for sec_nom, sec_turno in (("A", "Mañana"), ("B", "Tarde")):
                        cur.execute(
                            "INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) "
                            "VALUES (%s, %s, %s, %s, TRUE)",
                            (pid_activo, g["id"], sec_nom, sec_turno),
                        )

            # Materias basicas para Media General (Fisica, Quimica y Biologia a partir de 3.o Anio)
            if id_media and id_bloque_general and id_bloque_cientifica:
                materias_comunes = [
                    ("Matemáticas", "MAT", id_bloque_cientifica, False),
                    ("Castellano", "CAS", id_bloque_general, False),
                    ("Inglés", "ING", id_bloque_general, False),
                    ("Educación Física", "EDF", id_bloque_general, True),
                ]
                materias_desde_tercero = [
                    ("Física", "FIS", id_bloque_cientifica, False),
                    ("Química", "QUI", id_bloque_cientifica, False),
                    ("Biología", "BIO", id_bloque_cientifica, False),
                ]
                for g in grados_rows:
                    if g["id_nivel"] != id_media or g["nombre"] not in {x[0] for x in grados_media}:
                        continue
                    lista_mat = list(materias_comunes)
                    if g["orden"] >= 3:
                        lista_mat.extend(materias_desde_tercero)
                    for nom_m, cod_m, id_blq, esp in lista_mat:
                        cur.execute(
                            "INSERT IGNORE INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) "
                            "VALUES (%s, %s, %s, %s, %s, TRUE)",
                            (g["id"], id_blq, nom_m, cod_m, esp),
                        )

            # 8 docentes semilla realistas (Primaria, Media General y Especialistas)
            docentes_semilla = [
                ("V-14250110", "Carlos Alberto", "Mendoza Ríos", "0414-6201101", "cmendoza@loslaureles.edu.ve", "Urb. Los Laureles, Cabimas", "Matemáticas", "Media General"),
                ("V-15340221", "Yelitza Carolina", "Ramírez Ochoa", "0412-6202202", "yramirez@loslaureles.edu.ve", "Sector Las 40, Cabimas", "Castellano", "Media General"),
                ("V-16480332", "Luis Eduardo", "Castillo Bracho", "0424-6203303", "lcastillo@loslaureles.edu.ve", "Urb. Concordia, Cabimas", "Inglés", "Especialista"),
                ("V-13890443", "Maritza Elena", "Rojas Delgado", "0416-6204404", "mrojas@loslaureles.edu.ve", "Urb. Los Laureles, Cabimas", "Física y Química", "Media General"),
                ("V-17120554", "José Gregorio", "Pirela Montero", "0414-6205505", "jpirela@loslaureles.edu.ve", "Sector Delicias Nuevas, Cabimas", "Biología", "Media General"),
                ("V-18230665", "Rafael Antonio", "Briceño Soto", "0426-6206606", "rbriceno@loslaureles.edu.ve", "Urb. Buena Vista, Cabimas", "Educación Física", "Especialista"),
                ("V-15910776", "Carmen Rosa", "González Medina", "0414-6207707", "cgonzalez@loslaureles.edu.ve", "Urb. Los Laureles, Cabimas", "Educación Integral (Primaria)", "Primaria"),
                ("V-16750887", "Norelys Josefina", "Urdaneta Salas", "0412-6208808", "nurdaneta@loslaureles.edu.ve", "Sector Ambrosio, Cabimas", "Educación Integral (Primaria)", "Primaria"),
            ]
            for doc in docentes_semilla:
                cur.execute(
                    "INSERT IGNORE INTO docentes (cedula, nombres, apellidos, telefono, correo, direccion, especialidad, categoria, activo) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)",
                    doc,
                )

            # Asignaciones iniciales en el periodo activo (cada docente semilla a sus materias correspondientes)
            if per_activo:
                cur.execute("SELECT id, cedula FROM docentes")
                docs_por_ci = {r["cedula"]: r["id"] for r in cur.fetchall()}
                mapa_materia_docente = {
                    "Matemáticas": docs_por_ci.get("V-14250110"),
                    "Castellano": docs_por_ci.get("V-15340221"),
                    "Inglés": docs_por_ci.get("V-16480332"),
                    "Física": docs_por_ci.get("V-13890443"),
                    "Química": docs_por_ci.get("V-13890443"),
                    "Biología": docs_por_ci.get("V-17120554"),
                    "Educación Física": docs_por_ci.get("V-18230665"),
                }
                cur.execute(
                    "SELECT s.id AS id_seccion, s.nombre AS sec_nombre, g.id AS id_grado, n.tipo_escala "
                    "FROM secciones s "
                    "JOIN grados_anios g ON g.id = s.id_grado_anio "
                    "JOIN niveles_educativos n ON n.id = g.id_nivel "
                    "WHERE s.id_periodo = %s AND s.activo = TRUE",
                    (pid_activo,),
                )
                for sec_row in cur.fetchall():
                    if sec_row["tipo_escala"] == "literal":
                        titular = (
                            docs_por_ci.get("V-15910776")
                            if sec_row["sec_nombre"] == "A"
                            else docs_por_ci.get("V-16750887")
                        )
                        if titular:
                            cur.execute(
                                "UPDATE secciones SET id_docente_titular_guia = %s "
                                "WHERE id = %s AND id_docente_titular_guia IS NULL",
                                (titular, sec_row["id_seccion"]),
                            )
                    else:
                        cur.execute(
                            "SELECT id, nombre FROM materias WHERE id_grado_anio = %s AND activo = TRUE",
                            (sec_row["id_grado"],),
                        )
                        for m_row in cur.fetchall():
                            id_d = mapa_materia_docente.get(m_row["nombre"])
                            if id_d:
                                cur.execute(
                                    "INSERT IGNORE INTO asignaciones_docentes (id_periodo, id_seccion, id_materia, id_docente) "
                                    "VALUES (%s, %s, %s, %s)",
                                    (pid_activo, sec_row["id_seccion"], m_row["id"], id_d),
                                )

            # 10 estudiantes semilla con representantes, SIN grado ni seccion asignada (para probar inscripcion/flujo)
            estudiantes_semilla = [
                (
                    ("V-33101001", "Sofía Valentina", "Márquez León", "F", "2018-04-12", "Urb. Los Laureles, sector 6, calle 14"),
                    ("V-17101001", "Patricia Elena", "León de Márquez", "Madre", "0414-6310101", "0264-2410101", "pleon@correo.com", "Urb. Los Laureles, sector 6, calle 14"),
                ),
                (
                    ("V-33101002", "Mateo Alejandro", "Quintero Paz", "M", "2017-08-23", "Urb. Los Laureles, sector 4, calle 8"),
                    ("V-16202002", "Ricardo José", "Quintero Morales", "Padre", "0412-6320202", "", "rquintero@correo.com", "Urb. Los Laureles, sector 4, calle 8"),
                ),
                (
                    ("V-33101003", "Camila Andrea", "Finol Herrera", "F", "2016-02-19", "Sector Las 40, calle 10"),
                    ("V-18303003", "Mariana Isabel", "Herrera Silva", "Madre", "0424-6330303", "", "mherrera@correo.com", "Sector Las 40, calle 10"),
                ),
                (
                    ("V-33101004", "Diego Sebastián", "Chacín Romero", "M", "2015-11-05", "Urb. Concordia, vereda 12"),
                    ("V-15404004", "Héctor Manuel", "Chacín Nava", "Padre", "0416-6340404", "0264-2410404", "hchacin@correo.com", "Urb. Concordia, vereda 12"),
                ),
                (
                    ("V-33101005", "Valeria Lucía", "Perozo Díaz", "F", "2014-06-30", "Urb. Los Laureles, sector 6, calle 25"),
                    ("V-17505005", "Claudia Beatriz", "Díaz de Perozo", "Madre", "0414-6350505", "", "cdiaz@correo.com", "Urb. Los Laureles, sector 6, calle 25"),
                ),
                (
                    ("V-32101006", "Santiago David", "Vílchez Morales", "M", "2010-09-14", "Sector Delicias Nuevas, av. 32"),
                    ("V-14606006", "Oscar Enrique", "Vílchez Gómez", "Padre", "0426-6360606", "", "ovilchez@correo.com", "Sector Delicias Nuevas, av. 32"),
                ),
                (
                    ("V-32101007", "Isabella Sofía", "Nava Zambrano", "F", "2011-03-27", "Urb. Buena Vista, calle 5"),
                    ("V-16707007", "Verónica del Valle", "Zambrano Cruz", "Madre", "0412-6370707", "0264-2410707", "vzambrano@correo.com", "Urb. Buena Vista, calle 5"),
                ),
                (
                    ("V-31101008", "Gabriel Enrique", "Colina Vargas", "M", "2010-07-18", "Sector Ambrosio, av. Principal"),
                    ("V-15808008", "Eduardo Luis", "Colina Méndez", "Padre", "0414-6380808", "", "ecolina@correo.com", "Sector Ambrosio, av. Principal"),
                ),
                (
                    ("V-31101009", "Antonella María", "Palmar Chirinos", "F", "2010-12-09", "Urb. Los Laureles, sector 5, calle 19"),
                    ("V-14909009", "Lisbeth Carolina", "Chirinos Reyes", "Madre", "0424-6390909", "", "lchirinos@correo.com", "Urb. Los Laureles, sector 5, calle 19"),
                ),
                (
                    ("V-30101010", "Andrés Felipe", "Salazar Rincón", "M", "2010-01-22", "Urb. Los Laureles, sector 6, calle 27"),
                    ("V-13101010", "Jorge Alberto", "Salazar Peña", "Padre", "0416-6401010", "0264-2411010", "jsalazar@correo.com", "Urb. Los Laureles, sector 6, calle 27"),
                ),
            ]
            for est_data, rep_data in estudiantes_semilla:
                cur.execute(
                    "INSERT IGNORE INTO estudiantes (cedula, nombres, apellidos, genero, fecha_nacimiento, direccion, egresado, activo) "
                    "VALUES (%s, %s, %s, %s, %s, %s, FALSE, TRUE)",
                    est_data,
                )
                cur.execute(
                    "INSERT IGNORE INTO representantes (cedula, nombres, apellidos, parentesco, telefono, telefono_trabajo, correo, direccion) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    rep_data,
                )
                cur.execute("SELECT id FROM estudiantes WHERE cedula = %s", (est_data[0],))
                row_e = cur.fetchone()
                cur.execute("SELECT id FROM representantes WHERE cedula = %s", (rep_data[0],))
                row_r = cur.fetchone()
                if row_e and row_r:
                    cur.execute(
                        "INSERT IGNORE INTO estudiante_representantes (id_estudiante, id_representante, es_principal) "
                        "VALUES (%s, %s, TRUE)",
                        (row_e["id"], row_r["id"]),
                    )

            # Historial academico aprobado (1.o a 4.o Anio) para 5 de los 10 estudiantes,
            # dejandolos sin matricula en el periodo activo (listos para comenzar 5.o Anio y probar PDFs multi-anio)
            periodos_hist = [
                ("2022-2023", "2022-09-15", "2023-07-31", "1.º Año", "2023"),
                ("2023-2024", "2023-09-15", "2024-07-31", "2.º Año", "2024"),
                ("2024-2025", "2024-09-15", "2025-07-31", "3.º Año", "2025"),
                ("2025-2026", "2025-09-15", "2026-07-31", "4.º Año", "2026"),
            ]
            grados_por_nombre = {g["nombre"]: g["id"] for g in grados_rows}
            cedulas_pre_quinto = [
                ("V-32101006", 15),
                ("V-32101007", 17),
                ("V-31101008", 14),
                ("V-31101009", 18),
                ("V-30101010", 16),
            ]
            for p_nom, p_ini, p_fin, g_nom, anio_cierre in periodos_hist:
                gid_h = grados_por_nombre.get(g_nom)
                if not gid_h:
                    continue
                cur.execute(
                    "INSERT IGNORE INTO periodos_escolares (nombre, activo, cerrado, fecha_inicio, fecha_fin) "
                    "VALUES (%s, FALSE, TRUE, %s, %s)",
                    (p_nom, p_ini, p_fin),
                )
                cur.execute("SELECT id FROM periodos_escolares WHERE nombre = %s", (p_nom,))
                pid_h = cur.fetchone()["id"]
                cur.execute(
                    "INSERT IGNORE INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) "
                    "VALUES (%s, %s, 'A', 'Mañana', TRUE)",
                    (pid_h, gid_h),
                )
                cur.execute(
                    "SELECT id FROM secciones WHERE id_periodo = %s AND id_grado_anio = %s AND nombre = 'A'",
                    (pid_h, gid_h),
                )
                sid_h = cur.fetchone()["id"]
                cur.execute(
                    "SELECT id FROM materias WHERE id_grado_anio = %s AND activo = TRUE ORDER BY id ASC",
                    (gid_h,),
                )
                mats_h = [m["id"] for m in cur.fetchall()]

                for idx_e, (ced_e, base_nota) in enumerate(cedulas_pre_quinto):
                    cur.execute("SELECT id FROM estudiantes WHERE cedula = %s", (ced_e,))
                    row_e = cur.fetchone()
                    if not row_e:
                        continue
                    cur.execute(
                        "INSERT IGNORE INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) "
                        "VALUES (%s, %s, %s, 'activo', 'regular')",
                        (pid_h, row_e["id"], sid_h),
                    )
                    cur.execute(
                        "SELECT id FROM inscripciones WHERE id_periodo = %s AND id_estudiante = %s",
                        (pid_h, row_e["id"]),
                    )
                    iid_h = cur.fetchone()["id"]
                    for idx_m, mid_h in enumerate(mats_h):
                        variacion = ((idx_e + idx_m + int(anio_cierre)) % 4) - 1
                        l1 = min(20, max(12, base_nota + variacion))
                        l2 = min(20, max(12, base_nota + ((idx_m + 1) % 3) - 1))
                        l3 = min(20, max(12, base_nota + ((idx_e + idx_m) % 3)))
                        def_val = int((l1 + l2 + l3) / 3 + 0.5)
                        cur.execute(
                            "INSERT IGNORE INTO calificaciones_secundaria "
                            "(id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio) "
                            "VALUES (%s, %s, %s, %s, %s, %s, 'F', '07', %s)",
                            (iid_h, mid_h, l1, l2, l3, def_val, anio_cierre),
                        )

        conn.commit()
        print(f"Base de datos '{Config.DB_NAME}' inicializada correctamente.")
    except Exception as exc:
        conn.rollback()
        print(f"Error al inicializar la base de datos: {exc}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    inicializar()
