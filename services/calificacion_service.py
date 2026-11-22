from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from db import ejecutar_consulta, obtener_conexion
from services.academico_service import verificar_periodo_editable

LETRAS_NOTAS = [
    "", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE", "DIEZ",
    "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS", "DIECISIETE", "DIECIOCHO",
    "DIECINUEVE", "VEINTE",
]
ESCALA_LITERAL = ("A", "B", "C", "D", "E")
LITERAL_A_VALOR = {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}
VALOR_A_LITERAL = {5: "A", 4: "B", 3: "C", 2: "D", 1: "E"}
TIPOS_EVALUACION = ("F", "R", "A", "M", "***")


def numero_a_letras(nota) -> str:
    if nota is None or nota == "":
        return ""
    try:
        n = int(nota)
        if 1 <= n <= 20:
            return LETRAS_NOTAS[n]
    except (ValueError, TypeError):
        pass
    return ""


def calcular_definitiva_mppe(l1, l2, l3):
    """Calcula el promedio de 3 lapsos (acepta decimales) redondeado al entero mas cercano."""
    if l1 is None or l2 is None or l3 is None:
        return None
    promedio = (Decimal(str(l1)) + Decimal(str(l2)) + Decimal(str(l3))) / Decimal(3)
    return int(promedio.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calcular_definitiva_literal(l1, l2, l3):
    """Calcula la definitiva literal (A-E) promediando los 3 lapsos cuando todos existen."""
    if not l1 or not l2 or not l3:
        return None
    promedio = (
        Decimal(LITERAL_A_VALOR[l1]) + Decimal(LITERAL_A_VALOR[l2]) + Decimal(LITERAL_A_VALOR[l3])
    ) / Decimal(3)
    val = int(promedio.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return VALOR_A_LITERAL.get(val)


def _parse_nota_numerica(val):
    if val is None or str(val).strip() == "":
        return None
    txt = str(val).strip().replace(",", ".")
    try:
        n = Decimal(txt).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        raise ValueError("La calificación debe ser un número válido entre 01 y 20.")
    if not (Decimal("1") <= n <= Decimal("20")):
        raise ValueError("La calificación debe estar entre 01 y 20.")
    return n


def _parse_literal(val):
    if val is None or str(val).strip() == "":
        return None
    v = str(val).strip().upper()
    if v not in ESCALA_LITERAL:
        raise ValueError("La calificacion literal de Primaria debe ser A, B, C, D o E.")
    return v


def obtener_notas_primaria_seccion(id_seccion: int):
    return ejecutar_consulta(
        "SELECT i.id AS id_inscripcion, e.cedula, e.apellidos, e.nombres, "
        "cp.lapso_1, cp.lapso_2, cp.lapso_3, cp.definitiva, cp.observaciones "
        "FROM inscripciones i "
        "JOIN estudiantes e ON e.id = i.id_estudiante "
        "LEFT JOIN calificaciones_primaria cp ON cp.id_inscripcion = i.id "
        "WHERE i.id_seccion = %s AND i.estado = 'activo' AND e.activo = TRUE "
        "ORDER BY e.apellidos ASC, e.nombres ASC",
        (id_seccion,),
    )


def _validar_periodos_inscripciones(registros: list):
    ids = [r["id_inscripcion"] for r in registros if r.get("id_inscripcion")]
    if not ids:
        return
    ph = ",".join(["%s"] * len(ids))
    filas = ejecutar_consulta(
        f"SELECT DISTINCT id_periodo FROM inscripciones WHERE id IN ({ph})",
        tuple(ids),
    )
    for f in filas:
        verificar_periodo_editable(f["id_periodo"])


def guardar_notas_primaria(registros: list, usuario_id: int):
    _validar_periodos_inscripciones(registros)
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            for reg in registros:
                l1 = _parse_literal(reg.get("lapso_1"))
                l2 = _parse_literal(reg.get("lapso_2"))
                l3 = _parse_literal(reg.get("lapso_3"))
                def_lit = calcular_definitiva_literal(l1, l2, l3)
                obs = (reg.get("observaciones") or "").strip()
                cur.execute(
                    "INSERT INTO calificaciones_primaria "
                    "(id_inscripcion, lapso_1, lapso_2, lapso_3, definitiva, observaciones, actualizado_por) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE lapso_1=VALUES(lapso_1), lapso_2=VALUES(lapso_2), "
                    "lapso_3=VALUES(lapso_3), definitiva=VALUES(definitiva), "
                    "observaciones=VALUES(observaciones), actualizado_por=VALUES(actualizado_por)",
                    (reg["id_inscripcion"], l1, l2, l3, def_lit, obs, usuario_id),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_notas_secundaria_seccion_materia(id_seccion: int, id_materia: int):
    return ejecutar_consulta(
        "SELECT i.id AS id_inscripcion, e.cedula, e.apellidos, e.nombres, "
        "cs.lapso_1, cs.lapso_2, cs.lapso_3, cs.definitiva, cs.tipo_evaluacion, cs.mes, cs.anio "
        "FROM inscripciones i "
        "JOIN estudiantes e ON e.id = i.id_estudiante "
        "LEFT JOIN calificaciones_secundaria cs ON cs.id_inscripcion = i.id AND cs.id_materia = %s "
        "WHERE i.id_seccion = %s AND i.estado = 'activo' AND e.activo = TRUE "
        "ORDER BY e.apellidos ASC, e.nombres ASC",
        (id_materia, id_seccion),
    )


def guardar_notas_secundaria(id_materia: int, registros: list, usuario_id: int, mes_def: str = "07", anio_def: str = "2026"):
    _validar_periodos_inscripciones(registros)
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            for reg in registros:
                l1 = _parse_nota_numerica(reg.get("lapso_1"))
                l2 = _parse_nota_numerica(reg.get("lapso_2"))
                l3 = _parse_nota_numerica(reg.get("lapso_3"))
                definitiva = calcular_definitiva_mppe(l1, l2, l3)
                te = (reg.get("tipo_evaluacion") or "F").strip()
                if te not in TIPOS_EVALUACION:
                    te = "F"
                mes = (reg.get("mes") or mes_def).strip().zfill(2)[:2]
                anio = (reg.get("anio") or anio_def).strip()[:4]

                cur.execute(
                    "INSERT INTO calificaciones_secundaria "
                    "(id_inscripcion, id_materia, lapso_1, lapso_2, lapso_3, definitiva, tipo_evaluacion, mes, anio, actualizado_por) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE lapso_1=VALUES(lapso_1), lapso_2=VALUES(lapso_2), "
                    "lapso_3=VALUES(lapso_3), definitiva=VALUES(definitiva), "
                    "tipo_evaluacion=VALUES(tipo_evaluacion), mes=VALUES(mes), anio=VALUES(anio), "
                    "actualizado_por=VALUES(actualizado_por)",
                    (reg["id_inscripcion"], id_materia, l1, l2, l3, definitiva, te, mes, anio, usuario_id),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_boletin_estudiante(id_inscripcion: int):
    """Retorna la calificacion de Primaria o las materias agrupadas por bloque de Media General."""
    nota_primaria = ejecutar_consulta(
        "SELECT * FROM calificaciones_primaria WHERE id_inscripcion = %s",
        (id_inscripcion,),
        uno=True,
    )
    notas_secundaria = ejecutar_consulta(
        "SELECT m.id AS id_materia, m.nombre AS materia_nombre, b.nombre AS bloque_nombre, b.orden AS bloque_orden, "
        "cs.lapso_1, cs.lapso_2, cs.lapso_3, cs.definitiva, cs.tipo_evaluacion, cs.mes, cs.anio "
        "FROM inscripciones i "
        "JOIN secciones s ON s.id = i.id_seccion "
        "JOIN materias m ON m.id_grado_anio = s.id_grado_anio AND m.activo = TRUE "
        "JOIN bloques_formacion b ON b.id = m.id_bloque "
        "LEFT JOIN calificaciones_secundaria cs ON cs.id_inscripcion = i.id AND cs.id_materia = m.id "
        "WHERE i.id = %s "
        "ORDER BY b.orden ASC, m.nombre ASC",
        (id_inscripcion,),
    )
    return {"primaria": nota_primaria, "secundaria": notas_secundaria}


def obtener_sabana_secundaria_seccion(id_seccion: int):
    """Retorna por estudiante sus notas por materia y promedios por Lapso 1, 2, 3 y Final."""
    estudiantes = ejecutar_consulta(
        "SELECT i.id AS id_inscripcion, e.cedula, e.apellidos, e.nombres "
        "FROM inscripciones i "
        "JOIN estudiantes e ON e.id = i.id_estudiante "
        "WHERE i.id_seccion = %s AND i.estado = 'activo' AND e.activo = TRUE "
        "ORDER BY e.apellidos ASC, e.nombres ASC",
        (id_seccion,),
    )
    if not estudiantes:
        return []

    notas = ejecutar_consulta(
        "SELECT cs.id_inscripcion, cs.id_materia, cs.lapso_1, cs.lapso_2, cs.lapso_3, cs.definitiva "
        "FROM calificaciones_secundaria cs "
        "JOIN inscripciones i ON i.id = cs.id_inscripcion "
        "WHERE i.id_seccion = %s AND i.estado = 'activo'",
        (id_seccion,),
    )
    por_est = {}
    for n in notas:
        por_est.setdefault(n["id_inscripcion"], {})[n["id_materia"]] = n

    resultado = []
    for est in estudiantes:
        mapa = por_est.get(est["id_inscripcion"], {})
        l1s = [v["lapso_1"] for v in mapa.values() if v["lapso_1"] is not None]
        l2s = [v["lapso_2"] for v in mapa.values() if v["lapso_2"] is not None]
        l3s = [v["lapso_3"] for v in mapa.values() if v["lapso_3"] is not None]
        defs = [v["definitiva"] for v in mapa.values() if v["definitiva"] is not None]
        acum_mats = []
        for v in mapa.values():
            if v["definitiva"] is not None:
                acum_mats.append(float(v["definitiva"]))
            else:
                ls = [x for x in (v["lapso_1"], v["lapso_2"], v["lapso_3"]) if x is not None]
                if ls:
                    acum_mats.append(sum(ls) / len(ls))
        resultado.append({
            **est,
            "notas": mapa,
            "prom_l1": f"{sum(l1s) / len(l1s):.1f}" if l1s else "-",
            "prom_l2": f"{sum(l2s) / len(l2s):.1f}" if l2s else "-",
            "prom_l3": f"{sum(l3s) / len(l3s):.1f}" if l3s else "-",
            "prom_final": f"{sum(defs) / len(defs):.1f}" if defs else "-",
            "prom_acumulado": f"{sum(acum_mats) / len(acum_mats):.1f}" if acum_mats else "-",
        })
    return resultado
