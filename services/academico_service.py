from db import ejecutar_accion, ejecutar_consulta, obtener_conexion


def listar_periodos():
    return ejecutar_consulta("SELECT * FROM periodos_escolares ORDER BY id DESC")


def obtener_periodo_activo():
    return ejecutar_consulta(
        "SELECT * FROM periodos_escolares WHERE activo = TRUE LIMIT 1", uno=True
    )


def obtener_periodo_por_id(pid: int):
    if not pid:
        return None
    return ejecutar_consulta(
        "SELECT * FROM periodos_escolares WHERE id = %s LIMIT 1", (pid,), uno=True
    )


def resolver_periodo_consulta(id_periodo_param: int = None, id_periodo_sesion: int = None) -> tuple:
    """Resuelve (periodo_consulta, periodo_activo, periodos, solo_lectura) usando URL > sesion > activo."""
    periodos = listar_periodos()
    periodo_activo = next((p for p in periodos if p.get("activo")), None)
    periodo_sel = None
    if id_periodo_param:
        periodo_sel = next((p for p in periodos if p["id"] == id_periodo_param), None)
    if not periodo_sel and id_periodo_sesion:
        periodo_sel = next((p for p in periodos if p["id"] == id_periodo_sesion), None)
    if not periodo_sel:
        periodo_sel = periodo_activo or (periodos[0] if periodos else None)
    solo_lectura = bool(
        not periodo_sel or not periodo_sel.get("activo") or periodo_sel.get("cerrado")
    )
    return periodo_sel, periodo_activo, periodos, solo_lectura


def obtener_grado_siguiente(id_grado: int):
    """Retorna el siguiente grado/anio en la progresion escolar (incluyendo 6.o Grado -> 1.er Anio), o None si es el ultimo."""
    grados = ejecutar_consulta(
        "SELECT g.*, n.nombre AS nivel_nombre, n.tipo_escala, n.orden AS nivel_orden "
        "FROM grados_anios g "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "WHERE g.activo = TRUE "
        "ORDER BY n.orden ASC, g.orden ASC, g.id ASC"
    )
    for idx, g in enumerate(grados):
        if g["id"] == id_grado:
            return grados[idx + 1] if idx + 1 < len(grados) else None
    return None


def verificar_periodo_editable(pid: int):
    """Valida que el periodo exista y no este cerrado formalmente."""
    periodo = obtener_periodo_por_id(pid)
    if not periodo:
        raise ValueError("Período escolar no encontrado.")
    if periodo.get("cerrado"):
        raise ValueError(
            f"El período escolar {periodo['nombre']} está cerrado y no admite modificaciones."
        )
    return periodo


def cambiar_cierre_periodo(pid: int, cerrar: bool):
    periodo = obtener_periodo_por_id(pid)
    if not periodo:
        raise ValueError("Período escolar no encontrado.")
    ejecutar_accion(
        "UPDATE periodos_escolares SET cerrado = %s WHERE id = %s",
        (bool(cerrar), pid),
    )


def obtener_resumen_cierre_periodo(pid: int) -> dict:
    """Devuelve un checklist previo al cierre formal de un periodo escolar."""
    periodo = obtener_periodo_por_id(pid)
    if not periodo:
        raise ValueError("Período escolar no encontrado.")

    total_insc = ejecutar_consulta(
        "SELECT COUNT(*) AS c FROM inscripciones WHERE id_periodo = %s AND estado = 'activo'",
        (pid,),
        uno=True,
    )["c"]

    prim_sin_def = ejecutar_consulta(
        "SELECT COUNT(*) AS c FROM inscripciones i "
        "JOIN secciones s ON s.id = i.id_seccion "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "LEFT JOIN calificaciones_primaria cp ON cp.id_inscripcion = i.id "
        "WHERE i.id_periodo = %s AND i.estado = 'activo' AND n.tipo_escala = 'literal' "
        "AND (cp.definitiva IS NULL OR TRIM(cp.definitiva) = '')",
        (pid,),
        uno=True,
    )["c"]

    sec_sin_def = ejecutar_consulta(
        "SELECT COUNT(*) AS c FROM inscripciones i "
        "JOIN secciones s ON s.id = i.id_seccion "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "JOIN materias m ON m.id_grado_anio = s.id_grado_anio AND m.activo = TRUE "
        "LEFT JOIN calificaciones_secundaria cs ON cs.id_inscripcion = i.id AND cs.id_materia = m.id "
        "WHERE i.id_periodo = %s AND i.estado = 'activo' AND n.tipo_escala = 'numerica' "
        "AND cs.definitiva IS NULL",
        (pid,),
        uno=True,
    )["c"]

    sec_sin_guia = ejecutar_consulta(
        "SELECT COUNT(*) AS c FROM secciones "
        "WHERE id_periodo = %s AND activo = TRUE AND id_docente_titular_guia IS NULL",
        (pid,),
        uno=True,
    )["c"]

    mats_sin_doc = ejecutar_consulta(
        "SELECT COUNT(*) AS c FROM secciones s "
        "JOIN materias m ON m.id_grado_anio = s.id_grado_anio AND m.activo = TRUE "
        "LEFT JOIN asignaciones_docentes a ON a.id_periodo = s.id_periodo AND a.id_seccion = s.id AND a.id_materia = m.id "
        "WHERE s.id_periodo = %s AND s.activo = TRUE AND a.id IS NULL",
        (pid,),
        uno=True,
    )["c"]

    return {
        "periodo_nombre": periodo["nombre"],
        "total_inscripciones": int(total_insc or 0),
        "primaria_sin_definitiva": int(prim_sin_def or 0),
        "secundaria_sin_definitiva": int(sec_sin_def or 0),
        "secciones_sin_guia": int(sec_sin_guia or 0),
        "materias_sin_docente": int(mats_sin_doc or 0),
        "listo_para_cerrar": (int(prim_sin_def or 0) == 0 and int(sec_sin_def or 0) == 0),
    }


def copiar_secciones_periodo(
    id_periodo_origen: int,
    id_periodo_destino: int,
    copiar_guias: bool = True,
    copiar_asignaciones: bool = False,
) -> dict:
    """Copia las secciones activas de un periodo anterior al periodo destino (idempotente)."""
    if not id_periodo_origen or not id_periodo_destino:
        raise ValueError("Debe seleccionar el período de origen y el período destino.")
    if id_periodo_origen == id_periodo_destino:
        raise ValueError("El período de origen debe ser distinto al período destino.")

    verificar_periodo_editable(id_periodo_destino)

    secciones_origen = ejecutar_consulta(
        "SELECT s.*, d.activo AS guia_activo "
        "FROM secciones s "
        "LEFT JOIN docentes d ON d.id = s.id_docente_titular_guia "
        "WHERE s.id_periodo = %s AND s.activo = TRUE "
        "ORDER BY s.id ASC",
        (id_periodo_origen,),
    )
    if not secciones_origen:
        raise ValueError("El período de origen no tiene secciones activas para copiar.")

    conn = obtener_conexion()
    creadas = 0
    omitidas = 0
    asig_copiadas = 0
    try:
        with conn.cursor() as cur:
            for s in secciones_origen:
                cur.execute(
                    "SELECT id FROM secciones WHERE id_periodo = %s AND id_grado_anio = %s AND nombre = %s",
                    (id_periodo_destino, s["id_grado_anio"], s["nombre"]),
                )
                existente = cur.fetchone()
                if existente:
                    id_sec_dest = existente["id"]
                    omitidas += 1
                else:
                    id_guia = (
                        s["id_docente_titular_guia"]
                        if (copiar_guias and s.get("guia_activo"))
                        else None
                    )
                    cur.execute(
                        "INSERT INTO secciones (id_periodo, id_grado_anio, nombre, turno, id_docente_titular_guia, activo) "
                        "VALUES (%s, %s, %s, %s, %s, TRUE)",
                        (id_periodo_destino, s["id_grado_anio"], s["nombre"], s["turno"], id_guia),
                    )
                    id_sec_dest = cur.lastrowid
                    creadas += 1

                if copiar_asignaciones:
                    cur.execute(
                        "SELECT a.id_materia, a.id_docente "
                        "FROM asignaciones_docentes a "
                        "JOIN materias m ON m.id = a.id_materia AND m.activo = TRUE "
                        "JOIN docentes d ON d.id = a.id_docente AND d.activo = TRUE "
                        "WHERE a.id_periodo = %s AND a.id_seccion = %s",
                        (id_periodo_origen, s["id"]),
                    )
                    for a in cur.fetchall():
                        cur.execute(
                            "INSERT IGNORE INTO asignaciones_docentes (id_periodo, id_seccion, id_materia, id_docente) "
                            "VALUES (%s, %s, %s, %s)",
                            (id_periodo_destino, id_sec_dest, a["id_materia"], a["id_docente"]),
                        )
                        asig_copiadas += cur.rowcount
        conn.commit()
        return {
            "secciones_creadas": creadas,
            "secciones_omitidas": omitidas,
            "asignaciones_copiadas": asig_copiadas,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def crear_periodo(nombre: str, fecha_inicio=None, fecha_fin=None):
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre del periodo escolar es obligatorio.")
    return ejecutar_accion(
        "INSERT INTO periodos_escolares (nombre, activo, fecha_inicio, fecha_fin) "
        "VALUES (%s, FALSE, %s, %s)",
        (nombre, fecha_inicio or None, fecha_fin or None),
    )


def actualizar_periodo(pid: int, nombre: str, fecha_inicio=None, fecha_fin=None):
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre del periodo escolar es obligatorio.")
    return ejecutar_accion(
        "UPDATE periodos_escolares SET nombre = %s, fecha_inicio = %s, fecha_fin = %s WHERE id = %s",
        (nombre, fecha_inicio or None, fecha_fin or None, pid),
    )


def activar_periodo(pid: int):
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE periodos_escolares SET activo = FALSE")
            cur.execute("UPDATE periodos_escolares SET activo = TRUE WHERE id = %s", (pid,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def listar_niveles():
    return ejecutar_consulta("SELECT * FROM niveles_educativos ORDER BY orden ASC, id ASC")


def listar_grados(id_nivel: int = None):
    if id_nivel:
        return ejecutar_consulta(
            "SELECT g.*, n.nombre AS nivel_nombre, n.tipo_escala "
            "FROM grados_anios g JOIN niveles_educativos n ON n.id = g.id_nivel "
            "WHERE g.id_nivel = %s ORDER BY g.orden ASC, g.id ASC",
            (id_nivel,),
        )
    return ejecutar_consulta(
        "SELECT g.*, n.nombre AS nivel_nombre, n.tipo_escala "
        "FROM grados_anios g JOIN niveles_educativos n ON n.id = g.id_nivel "
        "ORDER BY n.orden ASC, g.orden ASC, g.id ASC"
    )


def crear_grado(id_nivel: int, nombre: str, orden: int = 1):
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre del grado o ano es obligatorio.")
    return ejecutar_accion(
        "INSERT INTO grados_anios (id_nivel, nombre, orden, activo) VALUES (%s, %s, %s, TRUE)",
        (id_nivel, nombre, orden),
    )


def actualizar_grado(gid: int, id_nivel: int, nombre: str, orden: int = 1):
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre del grado o ano es obligatorio.")
    return ejecutar_accion(
        "UPDATE grados_anios SET id_nivel = %s, nombre = %s, orden = %s WHERE id = %s",
        (id_nivel, nombre, orden, gid),
    )


def listar_grados_con_resumen(id_periodo: int):
    return ejecutar_consulta(
        "SELECT g.*, n.nombre AS nivel_nombre, n.tipo_escala, "
        "(SELECT COUNT(*) FROM materias m WHERE m.id_grado_anio = g.id AND m.activo = TRUE) AS total_materias, "
        "(SELECT COUNT(*) FROM secciones s WHERE s.id_grado_anio = g.id AND s.id_periodo = %s AND s.activo = TRUE) AS total_secciones "
        "FROM grados_anios g JOIN niveles_educativos n ON n.id = g.id_nivel "
        "ORDER BY n.orden ASC, g.orden ASC, g.id ASC",
        (id_periodo,),
    )


def listar_docentes(solo_activos: bool = True):
    sql = "SELECT * FROM docentes"
    if solo_activos:
        sql += " WHERE activo = TRUE"
    sql += " ORDER BY apellidos ASC, nombres ASC"
    return ejecutar_consulta(sql)


def listar_docentes_con_usuario(id_periodo: int = None):
    pid = id_periodo or 0
    return ejecutar_consulta(
        "SELECT d.*, "
        "EXISTS(SELECT 1 FROM usuarios u WHERE u.id_docente = d.id AND u.activo = TRUE) AS tiene_usuario, "
        "(SELECT COUNT(*) FROM asignaciones_docentes a WHERE a.id_docente = d.id AND a.id_periodo = %s) AS total_materias_asig, "
        "(SELECT COUNT(*) FROM horarios h WHERE h.id_docente = d.id AND h.id_periodo = %s) AS total_bloques_hor, "
        "(SELECT COUNT(*) FROM secciones s WHERE s.id_docente_titular_guia = d.id AND s.id_periodo = %s AND s.activo = TRUE) AS total_guias "
        "FROM docentes d "
        "ORDER BY d.apellidos ASC, d.nombres ASC",
        (pid, pid, pid),
    )


def _normalizar_datos_docente(
    cedula: str,
    nombres: str,
    apellidos: str,
    telefono: str = "",
    especialidad: str = "",
    correo: str = "",
    direccion: str = "",
    categoria: str = "Media General",
):
    if not cedula.strip() or not nombres.strip() or not apellidos.strip():
        raise ValueError("Cedula, nombres y apellidos del docente son obligatorios.")
    if categoria not in ("Primaria", "Media General", "Especialista"):
        categoria = "Media General"
    return (
        cedula.strip().upper(),
        nombres.strip(),
        apellidos.strip(),
        telefono.strip(),
        correo.strip(),
        direccion.strip(),
        especialidad.strip(),
        categoria,
    )


def crear_docente(
    cedula: str,
    nombres: str,
    apellidos: str,
    telefono: str = "",
    especialidad: str = "",
    correo: str = "",
    direccion: str = "",
    categoria: str = "Media General",
):
    datos = _normalizar_datos_docente(
        cedula, nombres, apellidos, telefono, especialidad, correo, direccion, categoria
    )
    return ejecutar_accion(
        "INSERT INTO docentes (cedula, nombres, apellidos, telefono, correo, direccion, especialidad, categoria, activo) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)",
        datos,
    )


def actualizar_docente(
    did: int,
    cedula: str,
    nombres: str,
    apellidos: str,
    telefono: str = "",
    especialidad: str = "",
    correo: str = "",
    direccion: str = "",
    categoria: str = "Media General",
):
    datos = _normalizar_datos_docente(
        cedula, nombres, apellidos, telefono, especialidad, correo, direccion, categoria
    )
    return ejecutar_accion(
        "UPDATE docentes SET cedula = %s, nombres = %s, apellidos = %s, telefono = %s, "
        "correo = %s, direccion = %s, especialidad = %s, categoria = %s WHERE id = %s",
        datos + (did,),
    )


def obtener_resumen_docente(id_periodo: int, id_docente: int):
    docente = ejecutar_consulta("SELECT * FROM docentes WHERE id = %s", (id_docente,), uno=True)
    if not docente:
        return None
    guias = ejecutar_consulta(
        "SELECT s.id, s.nombre AS seccion, s.turno, g.nombre AS grado, n.nombre AS nivel, n.tipo_escala "
        "FROM secciones s "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "WHERE s.id_periodo = %s AND s.id_docente_titular_guia = %s AND s.activo = TRUE",
        (id_periodo, id_docente),
    )
    asignaciones = ejecutar_consulta(
        "SELECT a.id_seccion, s.nombre AS seccion, g.nombre AS grado, m.id AS id_materia, m.nombre AS materia "
        "FROM asignaciones_docentes a "
        "JOIN secciones s ON s.id = a.id_seccion "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN materias m ON m.id = a.id_materia "
        "WHERE a.id_periodo = %s AND a.id_docente = %s "
        "ORDER BY g.orden ASC, s.nombre ASC, m.nombre ASC",
        (id_periodo, id_docente),
    )
    return {"docente": docente, "guias": guias, "asignaciones": asignaciones}


def listar_secciones_docente(id_periodo: int, id_docente: int):
    """Lista secciones donde el docente es titular/guia o tiene materias asignadas."""
    return ejecutar_consulta(
        "SELECT DISTINCT s.*, g.nombre AS grado_nombre, g.orden AS grado_orden, "
        "n.id AS id_nivel, n.nombre AS nivel_nombre, n.orden AS nivel_orden, n.tipo_escala, "
        "CONCAT(d.apellidos, ' ', d.nombres) AS docente_guia_nombre "
        "FROM secciones s "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "LEFT JOIN docentes d ON d.id = s.id_docente_titular_guia "
        "LEFT JOIN asignaciones_docentes a ON a.id_seccion = s.id AND a.id_periodo = s.id_periodo "
        "WHERE s.id_periodo = %s AND s.activo = TRUE "
        "AND (s.id_docente_titular_guia = %s OR a.id_docente = %s) "
        "ORDER BY n.orden ASC, g.orden ASC, s.nombre ASC",
        (id_periodo, id_docente, id_docente),
    )


def listar_materias_docente_seccion(id_periodo: int, id_docente: int, id_seccion: int):
    return ejecutar_consulta(
        "SELECT m.*, b.nombre AS bloque_nombre "
        "FROM asignaciones_docentes a "
        "JOIN materias m ON m.id = a.id_materia "
        "JOIN bloques_formacion b ON b.id = m.id_bloque "
        "WHERE a.id_periodo = %s AND a.id_docente = %s AND a.id_seccion = %s AND m.activo = TRUE "
        "ORDER BY b.orden ASC, m.nombre ASC",
        (id_periodo, id_docente, id_seccion),
    )


def toggle_docente(did: int):
    ejecutar_accion("UPDATE docentes SET activo = NOT activo WHERE id = %s", (did,))


def listar_secciones(id_periodo: int, id_nivel: int = None):
    sql = (
        "SELECT s.*, g.nombre AS grado_nombre, g.orden AS grado_orden, "
        "n.id AS id_nivel, n.nombre AS nivel_nombre, n.orden AS nivel_orden, n.tipo_escala, "
        "CONCAT(d.apellidos, ' ', d.nombres) AS docente_guia_nombre "
        "FROM secciones s "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "LEFT JOIN docentes d ON d.id = s.id_docente_titular_guia "
        "WHERE s.id_periodo = %s "
    )
    params = [id_periodo]
    if id_nivel:
        sql += "AND n.id = %s "
        params.append(id_nivel)
    sql += "ORDER BY n.orden ASC, g.orden ASC, s.nombre ASC"
    return ejecutar_consulta(sql, tuple(params))


def listar_secciones_con_resumen(id_periodo: int):
    return ejecutar_consulta(
        "SELECT s.*, g.nombre AS grado_nombre, g.orden AS grado_orden, "
        "n.id AS id_nivel, n.nombre AS nivel_nombre, n.orden AS nivel_orden, n.tipo_escala, "
        "CONCAT(d.apellidos, ' ', d.nombres) AS docente_guia_nombre, "
        "(SELECT COUNT(*) FROM inscripciones i WHERE i.id_seccion = s.id AND i.id_periodo = s.id_periodo AND i.estado = 'activo') AS total_alumnos, "
        "(SELECT COUNT(*) FROM materias m WHERE m.id_grado_anio = s.id_grado_anio AND m.activo = TRUE) AS total_materias, "
        "(SELECT COUNT(DISTINCT a.id_materia) FROM asignaciones_docentes a JOIN materias m ON m.id = a.id_materia "
        " WHERE a.id_seccion = s.id AND a.id_periodo = s.id_periodo AND m.activo = TRUE) AS materias_asignadas "
        "FROM secciones s "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "LEFT JOIN docentes d ON d.id = s.id_docente_titular_guia "
        "WHERE s.id_periodo = %s "
        "ORDER BY n.orden ASC, g.orden ASC, s.nombre ASC",
        (id_periodo,),
    )


def crear_seccion(id_periodo: int, id_grado_anio: int, nombre: str, turno: str = "Mañana", id_docente: int = None):
    verificar_periodo_editable(id_periodo)
    nombre = nombre.strip().upper()
    if not nombre:
        raise ValueError("El nombre de la sección es obligatorio (ej. A, B).")
    return ejecutar_accion(
        "INSERT INTO secciones (id_periodo, id_grado_anio, nombre, turno, id_docente_titular_guia, activo) "
        "VALUES (%s, %s, %s, %s, %s, TRUE)",
        (id_periodo, id_grado_anio, nombre, turno, id_docente or None),
    )


def actualizar_docente_seccion(id_seccion: int, id_docente: int = None):
    sec = ejecutar_consulta("SELECT id_periodo FROM secciones WHERE id = %s", (id_seccion,), uno=True)
    if sec:
        verificar_periodo_editable(sec["id_periodo"])
    ejecutar_accion(
        "UPDATE secciones SET id_docente_titular_guia = %s WHERE id = %s",
        (id_docente or None, id_seccion),
    )


def listar_bloques():
    return ejecutar_consulta("SELECT * FROM bloques_formacion ORDER BY orden ASC, id ASC")


def listar_materias(id_grado_anio: int = None, solo_activas: bool = False):
    sql = (
        "SELECT m.*, g.nombre AS grado_nombre, n.nombre AS nivel_nombre, n.tipo_escala, "
        "b.nombre AS bloque_nombre, b.orden AS bloque_orden "
        "FROM materias m "
        "JOIN grados_anios g ON g.id = m.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "JOIN bloques_formacion b ON b.id = m.id_bloque "
        "WHERE 1=1 "
    )
    params = []
    if id_grado_anio:
        sql += "AND m.id_grado_anio = %s "
        params.append(id_grado_anio)
    if solo_activas:
        sql += "AND m.activo = TRUE "
    sql += "ORDER BY n.orden ASC, g.orden ASC, b.orden ASC, m.nombre ASC"
    return ejecutar_consulta(sql, tuple(params))


def crear_materia(id_grado_anio: int, id_bloque: int, nombre: str, codigo: str = "", es_especial: bool = False):
    if not nombre.strip():
        raise ValueError("El nombre de la materia es obligatorio.")
    return ejecutar_accion(
        "INSERT INTO materias (id_grado_anio, id_bloque, nombre, codigo, es_especial, activo) "
        "VALUES (%s, %s, %s, %s, %s, TRUE)",
        (id_grado_anio, id_bloque, nombre.strip(), codigo.strip(), es_especial),
    )


def actualizar_materia(mid: int, id_grado_anio: int, id_bloque: int, nombre: str, codigo: str = "", es_especial: bool = False):
    if not nombre.strip():
        raise ValueError("El nombre de la materia es obligatorio.")
    return ejecutar_accion(
        "UPDATE materias SET id_grado_anio = %s, id_bloque = %s, nombre = %s, codigo = %s, es_especial = %s WHERE id = %s",
        (id_grado_anio, id_bloque, nombre.strip(), codigo.strip(), es_especial, mid),
    )


def toggle_materia(mid: int):
    ejecutar_accion("UPDATE materias SET activo = NOT activo WHERE id = %s", (mid,))


def listar_asignaciones_seccion(id_periodo: int, id_seccion: int):
    return ejecutar_consulta(
        "SELECT a.*, m.nombre AS materia_nombre, m.es_especial, "
        "CONCAT(d.apellidos, ' ', d.nombres) AS docente_nombre "
        "FROM asignaciones_docentes a "
        "JOIN materias m ON m.id = a.id_materia "
        "JOIN docentes d ON d.id = a.id_docente "
        "WHERE a.id_periodo = %s AND a.id_seccion = %s "
        "ORDER BY m.nombre ASC",
        (id_periodo, id_seccion),
    )


def asignar_docente_materia(id_periodo: int, id_seccion: int, id_materia: int, id_docente: int):
    verificar_periodo_editable(id_periodo)
    ejecutar_accion(
        "INSERT INTO asignaciones_docentes (id_periodo, id_seccion, id_materia, id_docente) "
        "VALUES (%s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE id_docente = VALUES(id_docente)",
        (id_periodo, id_seccion, id_materia, id_docente),
    )


def asignar_titular_a_materias_primaria(id_periodo: int, id_seccion: int, id_docente: int) -> int:
    """Asigna el docente titular a todas las materias no especiales del grado de la seccion."""
    verificar_periodo_editable(id_periodo)
    seccion = ejecutar_consulta(
        "SELECT id_grado_anio FROM secciones WHERE id = %s", (id_seccion,), uno=True
    )
    if not seccion:
        raise ValueError("Sección no encontrada.")
    materias = ejecutar_consulta(
        "SELECT id FROM materias WHERE id_grado_anio = %s AND activo = TRUE AND es_especial = FALSE",
        (seccion["id_grado_anio"],),
    )
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            for mat in materias:
                cur.execute(
                    "INSERT INTO asignaciones_docentes (id_periodo, id_seccion, id_materia, id_docente) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE id_docente = VALUES(id_docente)",
                    (id_periodo, id_seccion, mat["id"], id_docente),
                )
        conn.commit()
        return len(materias)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def guardar_asignaciones_seccion_lote(
    id_periodo: int,
    id_seccion: int,
    id_docente_guia: int = None,
    asignaciones: dict = None,
):
    """Actualiza el profesor guia y las asignaciones docente-materia de una seccion."""
    verificar_periodo_editable(id_periodo)
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE secciones SET id_docente_titular_guia = %s WHERE id = %s",
                (id_docente_guia or None, id_seccion),
            )
            for id_mat, id_doc in (asignaciones or {}).items():
                if id_doc:
                    cur.execute(
                        "INSERT INTO asignaciones_docentes (id_periodo, id_seccion, id_materia, id_docente) "
                        "VALUES (%s, %s, %s, %s) "
                        "ON DUPLICATE KEY UPDATE id_docente = VALUES(id_docente)",
                        (id_periodo, id_seccion, int(id_mat), int(id_doc)),
                    )
                else:
                    cur.execute(
                        "DELETE FROM asignaciones_docentes "
                        "WHERE id_periodo = %s AND id_seccion = %s AND id_materia = %s",
                        (id_periodo, id_seccion, int(id_mat)),
                    )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_carga_editable_docente(id_periodo: int, id_docente: int) -> dict:
    """Retorna todas las secciones/materias del periodo indicando cuales estan asignadas al docente."""
    docente = ejecutar_consulta(
        "SELECT id, cedula, nombres, apellidos, especialidad, categoria FROM docentes WHERE id = %s",
        (id_docente,),
        uno=True,
    )
    if not docente:
        return None
    filas = ejecutar_consulta(
        "SELECT s.id AS id_seccion, s.nombre AS seccion_nombre, s.turno, "
        "g.id AS id_grado, g.nombre AS grado_nombre, g.orden AS grado_orden, "
        "n.nombre AS nivel_nombre, n.orden AS nivel_orden, "
        "m.id AS id_materia, m.nombre AS materia_nombre, m.codigo AS materia_codigo, "
        "a.id_docente AS docente_asignado_id, "
        "CONCAT(d.apellidos, ' ', d.nombres) AS docente_asignado_nombre "
        "FROM secciones s "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "JOIN materias m ON m.id_grado_anio = g.id AND m.activo = TRUE "
        "LEFT JOIN asignaciones_docentes a ON a.id_periodo = s.id_periodo AND a.id_seccion = s.id AND a.id_materia = m.id "
        "LEFT JOIN docentes d ON d.id = a.id_docente "
        "WHERE s.id_periodo = %s AND s.activo = TRUE "
        "ORDER BY n.orden ASC, g.orden ASC, s.nombre ASC, m.nombre ASC",
        (id_periodo,),
    )
    agrupado = {}
    for f in filas:
        sid = f["id_seccion"]
        if sid not in agrupado:
            agrupado[sid] = {
                "id_seccion": sid,
                "label": f'{f["grado_nombre"]} "{f["seccion_nombre"]}" ({f["turno"]})',
                "nivel_nombre": f["nivel_nombre"],
                "materias": [],
            }
        agrupado[sid]["materias"].append({
            "id_materia": f["id_materia"],
            "nombre": f["materia_nombre"],
            "codigo": f["materia_codigo"] or "",
            "asignada_a_este": f["docente_asignado_id"] == id_docente,
            "otro_docente": (
                f["docente_asignado_nombre"]
                if f["docente_asignado_id"] and f["docente_asignado_id"] != id_docente
                else ""
            ),
        })
    return {"docente": docente, "secciones": list(agrupado.values())}


def guardar_asignaciones_docente_lote(id_periodo: int, id_docente: int, pares: list) -> dict:
    """Actualiza las materias/secciones asignadas a un docente en el periodo activo."""
    verificar_periodo_editable(id_periodo)
    limpios = set()
    for p in pares or []:
        if isinstance(p, str) and ":" in p:
            a, b = p.split(":", 1)
            if a.isdigit() and b.isdigit():
                limpios.add((int(a), int(b)))
        elif isinstance(p, (list, tuple)) and len(p) == 2:
            limpios.add((int(p[0]), int(p[1])))

    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id_seccion, id_materia FROM asignaciones_docentes "
                "WHERE id_periodo = %s AND id_docente = %s",
                (id_periodo, id_docente),
            )
            actuales = {(r["id_seccion"], r["id_materia"]) for r in cur.fetchall()}

            for sid, mid in actuales - limpios:
                cur.execute(
                    "DELETE FROM asignaciones_docentes "
                    "WHERE id_periodo = %s AND id_seccion = %s AND id_materia = %s AND id_docente = %s",
                    (id_periodo, sid, mid, id_docente),
                )
            for sid, mid in limpios:
                cur.execute(
                    "INSERT INTO asignaciones_docentes (id_periodo, id_seccion, id_materia, id_docente) "
                    "VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE id_docente = VALUES(id_docente)",
                    (id_periodo, sid, mid, id_docente),
                )
        conn.commit()
        return {"total": len(limpios)}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
