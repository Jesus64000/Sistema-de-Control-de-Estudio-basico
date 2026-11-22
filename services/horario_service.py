from db import ejecutar_accion, ejecutar_consulta
from services.academico_service import verificar_periodo_editable

DIAS_SEMANA = {
    1: "Lunes",
    2: "Martes",
    3: "Miércoles",
    4: "Jueves",
    5: "Viernes",
}


def _validar_choques(
    id_periodo: int,
    id_seccion: int,
    id_docente: int,
    dia_semana: int,
    hora_inicio: str,
    hora_fin: str,
    aula: str = "",
    excluir_id: int = None,
):
    if dia_semana not in DIAS_SEMANA:
        raise ValueError("Día de la semana inválido (debe ser Lunes a Viernes).")
    if not hora_inicio or not hora_fin or hora_inicio >= hora_fin:
        raise ValueError("La hora de inicio debe ser menor a la hora de fin.")

    extra_sql = " AND h.id <> %s" if excluir_id else ""
    extra_param = (excluir_id,) if excluir_id else ()

    choque_seccion = ejecutar_consulta(
        "SELECT h.id, TIME_FORMAT(h.hora_inicio, '%%H:%%i') AS hi, TIME_FORMAT(h.hora_fin, '%%H:%%i') AS hf, "
        "COALESCE(m.nombre, h.descripcion_bloque, 'Bloque') AS bloque "
        "FROM horarios h "
        "LEFT JOIN materias m ON m.id = h.id_materia "
        "WHERE h.id_periodo = %s AND h.id_seccion = %s AND h.dia_semana = %s "
        f"AND h.hora_inicio < %s AND h.hora_fin > %s{extra_sql} LIMIT 1",
        (id_periodo, id_seccion, dia_semana, hora_fin, hora_inicio) + extra_param,
        uno=True,
    )
    if choque_seccion:
        raise ValueError(
            f"Choque de horario en la sección el día {DIAS_SEMANA[dia_semana]} "
            f"con '{choque_seccion['bloque']}' ({choque_seccion['hi']} - {choque_seccion['hf']})."
        )

    choque_docente = ejecutar_consulta(
        "SELECT h.id, TIME_FORMAT(h.hora_inicio, '%%H:%%i') AS hi, TIME_FORMAT(h.hora_fin, '%%H:%%i') AS hf, "
        "g.nombre AS grado, s.nombre AS seccion, COALESCE(m.nombre, h.descripcion_bloque, 'Bloque') AS bloque "
        "FROM horarios h "
        "JOIN secciones s ON s.id = h.id_seccion "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "LEFT JOIN materias m ON m.id = h.id_materia "
        "WHERE h.id_periodo = %s AND h.id_docente = %s AND h.dia_semana = %s "
        f"AND h.hora_inicio < %s AND h.hora_fin > %s{extra_sql} LIMIT 1",
        (id_periodo, id_docente, dia_semana, hora_fin, hora_inicio) + extra_param,
        uno=True,
    )
    if choque_docente:
        raise ValueError(
            f"El docente ya tiene clase el {DIAS_SEMANA[dia_semana]} en {choque_docente['grado']} "
            f"Sección \"{choque_docente['seccion']}\" ({choque_docente['bloque']}, {choque_docente['hi']} - {choque_docente['hf']})."
        )

    aula_limpia = (aula or "").strip()
    if aula_limpia:
        choque_aula = ejecutar_consulta(
            "SELECT h.id, TIME_FORMAT(h.hora_inicio, '%%H:%%i') AS hi, TIME_FORMAT(h.hora_fin, '%%H:%%i') AS hf, "
            "g.nombre AS grado, s.nombre AS seccion, COALESCE(m.nombre, h.descripcion_bloque, 'Bloque') AS bloque "
            "FROM horarios h "
            "JOIN secciones s ON s.id = h.id_seccion "
            "JOIN grados_anios g ON g.id = s.id_grado_anio "
            "LEFT JOIN materias m ON m.id = h.id_materia "
            "WHERE h.id_periodo = %s AND h.dia_semana = %s "
            "AND LOWER(TRIM(COALESCE(h.aula, ''))) = LOWER(%s) "
            f"AND h.hora_inicio < %s AND h.hora_fin > %s{extra_sql} LIMIT 1",
            (id_periodo, dia_semana, aula_limpia, hora_fin, hora_inicio) + extra_param,
            uno=True,
        )
        if choque_aula:
            raise ValueError(
                f"Choque de aula: '{aula_limpia}' ya está ocupada el {DIAS_SEMANA[dia_semana]} por "
                f"{choque_aula['grado']} Sección \"{choque_aula['seccion']}\" ({choque_aula['hi']} - {choque_aula['hf']})."
            )


def registrar_bloque_horario(
    id_periodo: int,
    id_seccion: int,
    id_docente: int,
    dia_semana: int,
    hora_inicio: str,
    hora_fin: str,
    id_materia: int = None,
    aula: str = "",
    descripcion_bloque: str = "",
    guardar_asignacion: bool = False,
):
    """Registra un bloque horario validando que no exista choque de seccion, docente ni aula."""
    verificar_periodo_editable(id_periodo)
    _validar_choques(id_periodo, id_seccion, id_docente, dia_semana, hora_inicio, hora_fin, aula=aula)
    hid = ejecutar_accion(
        "INSERT INTO horarios (id_periodo, id_seccion, id_materia, id_docente, dia_semana, hora_inicio, hora_fin, aula, descripcion_bloque) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            id_periodo,
            id_seccion,
            id_materia or None,
            id_docente,
            dia_semana,
            hora_inicio,
            hora_fin,
            (aula or "").strip(),
            (descripcion_bloque or "").strip(),
        ),
    )
    if guardar_asignacion and id_materia:
        ejecutar_accion(
            "INSERT INTO asignaciones_docentes (id_periodo, id_seccion, id_materia, id_docente) "
            "VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE id_docente = VALUES(id_docente)",
            (id_periodo, id_seccion, id_materia, id_docente),
        )
    return hid


def actualizar_bloque_horario(
    hid: int,
    id_periodo: int,
    id_seccion: int,
    id_docente: int,
    dia_semana: int,
    hora_inicio: str,
    hora_fin: str,
    id_materia: int = None,
    aula: str = "",
    descripcion_bloque: str = "",
    guardar_asignacion: bool = False,
):
    """Actualiza un bloque horario validando que no choque con otros bloques (seccion, docente ni aula)."""
    verificar_periodo_editable(id_periodo)
    _validar_choques(
        id_periodo, id_seccion, id_docente, dia_semana, hora_inicio, hora_fin, aula=aula, excluir_id=hid
    )
    ejecutar_accion(
        "UPDATE horarios SET id_docente=%s, dia_semana=%s, hora_inicio=%s, hora_fin=%s, "
        "id_materia=%s, aula=%s, descripcion_bloque=%s WHERE id=%s AND id_periodo=%s AND id_seccion=%s",
        (
            id_docente,
            dia_semana,
            hora_inicio,
            hora_fin,
            id_materia or None,
            (aula or "").strip(),
            (descripcion_bloque or "").strip(),
            hid,
            id_periodo,
            id_seccion,
        ),
    )
    if guardar_asignacion and id_materia:
        ejecutar_accion(
            "INSERT INTO asignaciones_docentes (id_periodo, id_seccion, id_materia, id_docente) "
            "VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE id_docente = VALUES(id_docente)",
            (id_periodo, id_seccion, id_materia, id_docente),
        )


def consultar_disponibilidad_horario(
    id_periodo: int,
    id_seccion: int,
    id_docente: int,
    dia_semana: int,
    hora_inicio: str = "",
    hora_fin: str = "",
    aula: str = "",
    excluir_id: int = None,
) -> dict:
    """Retorna ficha del docente, bloques ocupados ese dia (docente y seccion) y choques en vivo."""
    doc = None
    if id_docente:
        doc = ejecutar_consulta(
            "SELECT id, cedula, nombres, apellidos, especialidad, categoria, telefono, correo "
            "FROM docentes WHERE id = %s LIMIT 1",
            (id_docente,),
            uno=True,
        )
        if doc:
            carga = ejecutar_consulta(
                "SELECT COUNT(*) AS bloques, "
                "COALESCE(SUM(TIMESTAMPDIFF(MINUTE, hora_inicio, hora_fin)), 0) AS minutos "
                "FROM horarios WHERE id_periodo = %s AND id_docente = %s",
                (id_periodo, id_docente),
                uno=True,
            )
            doc["bloques_semana"] = int(carga["bloques"] or 0)
            doc["horas_semana"] = round(float(carga["minutos"] or 0) / 60.0, 1)

    extra_sql = " AND h.id <> %s" if excluir_id else ""
    extra_param = (excluir_id,) if excluir_id else ()

    bloques_doc = []
    if id_docente and dia_semana in DIAS_SEMANA:
        bloques_doc = ejecutar_consulta(
            "SELECT h.id, h.id_seccion, TIME_FORMAT(h.hora_inicio, '%%H:%%i') AS hi, TIME_FORMAT(h.hora_fin, '%%H:%%i') AS hf, "
            "g.nombre AS grado_nombre, s.nombre AS seccion_nombre, "
            "COALESCE(m.nombre, h.descripcion_bloque, 'Bloque') AS materia_nombre, COALESCE(h.aula, '') AS aula "
            "FROM horarios h "
            "JOIN secciones s ON s.id = h.id_seccion "
            "JOIN grados_anios g ON g.id = s.id_grado_anio "
            "LEFT JOIN materias m ON m.id = h.id_materia "
            f"WHERE h.id_periodo = %s AND h.id_docente = %s AND h.dia_semana = %s{extra_sql} "
            "ORDER BY h.hora_inicio ASC",
            (id_periodo, id_docente, dia_semana) + extra_param,
        )
        for b in bloques_doc:
            b["es_misma_seccion"] = b["id_seccion"] == id_seccion

    bloques_sec = []
    if id_seccion and dia_semana in DIAS_SEMANA:
        bloques_sec = ejecutar_consulta(
            "SELECT h.id, TIME_FORMAT(h.hora_inicio, '%%H:%%i') AS hi, TIME_FORMAT(h.hora_fin, '%%H:%%i') AS hf, "
            "COALESCE(m.nombre, h.descripcion_bloque, 'Bloque') AS materia_nombre, "
            "CONCAT(d.apellidos, ' ', d.nombres) AS docente_nombre, COALESCE(h.aula, '') AS aula "
            "FROM horarios h "
            "LEFT JOIN materias m ON m.id = h.id_materia "
            "JOIN docentes d ON d.id = h.id_docente "
            f"WHERE h.id_periodo = %s AND h.id_seccion = %s AND h.dia_semana = %s{extra_sql} "
            "ORDER BY h.hora_inicio ASC",
            (id_periodo, id_seccion, dia_semana) + extra_param,
        )

    conflictos = []
    if dia_semana in DIAS_SEMANA and hora_inicio and hora_fin:
        if hora_inicio >= hora_fin:
            conflictos.append("La hora de inicio debe ser menor a la hora de fin.")
        else:
            for b in bloques_sec:
                if b["hi"] < hora_fin and b["hf"] > hora_inicio:
                    conflictos.append(
                        f"Choque en esta sección: '{b['materia_nombre']}' ({b['hi']} - {b['hf']})."
                    )
                    break
            for b in bloques_doc:
                if b["hi"] < hora_fin and b["hf"] > hora_inicio:
                    conflictos.append(
                        f"El docente ya dicta {b['materia_nombre']} en {b['grado_nombre']} \"{b['seccion_nombre']}\" ({b['hi']} - {b['hf']})."
                    )
                    break
            aula_limpia = (aula or "").strip()
            if aula_limpia:
                choque_aula = ejecutar_consulta(
                    "SELECT TIME_FORMAT(h.hora_inicio, '%%H:%%i') AS hi, TIME_FORMAT(h.hora_fin, '%%H:%%i') AS hf, "
                    "g.nombre AS grado, s.nombre AS seccion "
                    "FROM horarios h "
                    "JOIN secciones s ON s.id = h.id_seccion "
                    "JOIN grados_anios g ON g.id = s.id_grado_anio "
                    "WHERE h.id_periodo = %s AND h.dia_semana = %s "
                    "AND LOWER(TRIM(COALESCE(h.aula, ''))) = LOWER(%s) "
                    f"AND h.hora_inicio < %s AND h.hora_fin > %s{extra_sql} LIMIT 1",
                    (id_periodo, dia_semana, aula_limpia, hora_fin, hora_inicio) + extra_param,
                    uno=True,
                )
                if choque_aula:
                    conflictos.append(
                        f"Aula '{aula_limpia}' ocupada por {choque_aula['grado']} \"{choque_aula['seccion']}\" ({choque_aula['hi']} - {choque_aula['hf']})."
                    )

    return {
        "docente": doc,
        "dia_nombre": DIAS_SEMANA.get(dia_semana, ""),
        "bloques_docente_dia": bloques_doc,
        "bloques_seccion_dia": bloques_sec,
        "conflictos": conflictos,
        "disponible": len(conflictos) == 0,
    }


def eliminar_bloque_horario(hid: int):
    bloque = ejecutar_consulta("SELECT id_periodo FROM horarios WHERE id = %s", (hid,), uno=True)
    if bloque:
        verificar_periodo_editable(bloque["id_periodo"])
    ejecutar_accion("DELETE FROM horarios WHERE id = %s", (hid,))


def obtener_horario_seccion(id_periodo: int, id_seccion: int):
    return ejecutar_consulta(
        "SELECT h.*, TIME_FORMAT(h.hora_inicio, '%%H:%%i') AS hi, TIME_FORMAT(h.hora_fin, '%%H:%%i') AS hf, "
        "m.nombre AS materia_nombre, CONCAT(d.apellidos, ' ', d.nombres) AS docente_nombre "
        "FROM horarios h "
        "LEFT JOIN materias m ON m.id = h.id_materia "
        "JOIN docentes d ON d.id = h.id_docente "
        "WHERE h.id_periodo = %s AND h.id_seccion = %s "
        "ORDER BY h.dia_semana ASC, h.hora_inicio ASC",
        (id_periodo, id_seccion),
    )


def obtener_horario_docente(id_periodo: int, id_docente: int):
    return ejecutar_consulta(
        "SELECT h.*, TIME_FORMAT(h.hora_inicio, '%%H:%%i') AS hi, TIME_FORMAT(h.hora_fin, '%%H:%%i') AS hf, "
        "m.nombre AS materia_nombre, g.nombre AS grado_nombre, s.nombre AS seccion_nombre "
        "FROM horarios h "
        "LEFT JOIN materias m ON m.id = h.id_materia "
        "JOIN secciones s ON s.id = h.id_seccion "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "WHERE h.id_periodo = %s AND h.id_docente = %s "
        "ORDER BY h.dia_semana ASC, h.hora_inicio ASC",
        (id_periodo, id_docente),
    )
