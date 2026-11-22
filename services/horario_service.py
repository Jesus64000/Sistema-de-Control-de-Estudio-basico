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
    excluir_id: int = None,
):
    if dia_semana not in DIAS_SEMANA:
        raise ValueError("Día de la semana inválido (debe ser Lunes a Viernes).")
    if not hora_inicio or not hora_fin or hora_inicio >= hora_fin:
        raise ValueError("La hora de inicio debe ser menor a la hora de fin.")

    extra_sql = " AND h.id <> %s" if excluir_id else ""
    extra_param = (excluir_id,) if excluir_id else ()

    choque_seccion = ejecutar_consulta(
        "SELECT h.id, h.hora_inicio, h.hora_fin, COALESCE(m.nombre, h.descripcion_bloque, 'Bloque') AS bloque "
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
            f"con '{choque_seccion['bloque']}' ({choque_seccion['hora_inicio']} - {choque_seccion['hora_fin']})."
        )

    choque_docente = ejecutar_consulta(
        "SELECT h.id, h.hora_inicio, h.hora_fin, g.nombre AS grado, s.nombre AS seccion "
        "FROM horarios h "
        "JOIN secciones s ON s.id = h.id_seccion "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "WHERE h.id_periodo = %s AND h.id_docente = %s AND h.dia_semana = %s "
        f"AND h.hora_inicio < %s AND h.hora_fin > %s{extra_sql} LIMIT 1",
        (id_periodo, id_docente, dia_semana, hora_fin, hora_inicio) + extra_param,
        uno=True,
    )
    if choque_docente:
        raise ValueError(
            f"El docente ya tiene clase el {DIAS_SEMANA[dia_semana]} en {choque_docente['grado']} "
            f"Sección {choque_docente['seccion']} ({choque_docente['hora_inicio']} - {choque_docente['hora_fin']})."
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
):
    """Registra un bloque horario validando que no exista choque de seccion ni de docente."""
    verificar_periodo_editable(id_periodo)
    _validar_choques(id_periodo, id_seccion, id_docente, dia_semana, hora_inicio, hora_fin)
    return ejecutar_accion(
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
):
    """Actualiza un bloque horario validando que no choque con otros bloques."""
    verificar_periodo_editable(id_periodo)
    _validar_choques(id_periodo, id_seccion, id_docente, dia_semana, hora_inicio, hora_fin, excluir_id=hid)
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
