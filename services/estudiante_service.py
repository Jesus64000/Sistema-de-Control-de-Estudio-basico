from datetime import date
import re
from db import ejecutar_accion, ejecutar_consulta, obtener_conexion
from services.academico_service import obtener_grado_siguiente, verificar_periodo_editable
from services.calificacion_service import obtener_boletin_estudiante

CONDICIONES_VALIDAS = ("regular", "nuevo_ingreso", "repitiente", "materia_pendiente", "reingreso")

_RE_NOMBRE = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s'\-]+$")
_RE_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
_RE_TEL_VE = re.compile(r"^(0412|0414|0424|0416|0426|0422|02\d{2})\d{7}$")
_MARCADORES_SIN_CI = {"", "NOTIENE", "VNOTIENE", "SINCEDULA", "S/C", "SC", "N/T"}


def normalizar_y_validar_cedula(
    valor: str,
    etiqueta: str,
    max_digitos: int = 12,
    permitir_sin_cedula: bool = False,
) -> str:
    """Normaliza y valida una cedula venezolana o cedula escolar (V-/E-/CE-/SC-)."""
    crudo = re.sub(r"[\s\.]+", "", (valor or "").strip().upper())
    if permitir_sin_cedula and crudo in _MARCADORES_SIN_CI:
        return "__GENERAR__"
    if not crudo:
        raise ValueError(f"La {etiqueta} es obligatoria.")
    if re.match(r"^(SC|CE)-?\d{4,12}$", crudo):
        pref = crudo[:2]
        num = crudo[2:].lstrip("-")
        return f"{pref}-{num}"
    if crudo.isdigit():
        crudo = f"V-{crudo}"
    elif re.match(r"^[VE]\d+$", crudo):
        crudo = f"{crudo[0]}-{crudo[1:]}"
    if not re.match(rf"^[VE]-\d{{6,{max_digitos}}}$", crudo):
        raise ValueError(
            f"La {etiqueta} tiene formato inválido. Use V- o E- seguido de 6 a {max_digitos} dígitos."
        )
    return crudo


def generar_cedula_provisional(cur) -> str:
    """Genera un identificador unico SC-0001 para estudiantes que aun no poseen cedula."""
    cur.execute(
        "SELECT cedula FROM estudiantes WHERE cedula LIKE 'SC-%' "
        "ORDER BY CAST(SUBSTRING(cedula, 4) AS UNSIGNED) DESC, id DESC LIMIT 1"
    )
    row = cur.fetchone()
    siguiente = 1
    if row and row.get("cedula"):
        m = re.search(r"(\d+)$", row["cedula"])
        if m:
            siguiente = int(m.group(1)) + 1
    while True:
        cand = f"SC-{siguiente:04d}"
        cur.execute("SELECT 1 FROM estudiantes WHERE cedula = %s", (cand,))
        if not cur.fetchone():
            return cand
        siguiente += 1


def generar_cedula_escolar(cur, rep_cedula: str, fecha_nacimiento=None) -> str:
    """Genera una Cedula Escolar venezolana (CE-[orden][AA][CI_rep]) unica a partir del representante."""
    from datetime import date

    dig_rep = re.sub(r"\D", "", rep_cedula or "")
    if not dig_rep:
        return generar_cedula_provisional(cur)
    rep_8 = dig_rep.zfill(8)[-8:]

    yy = date.today().strftime("%y")
    if isinstance(fecha_nacimiento, date):
        yy = fecha_nacimiento.strftime("%y")
    elif isinstance(fecha_nacimiento, str) and len(fecha_nacimiento) >= 4 and fecha_nacimiento[:4].isdigit():
        yy = fecha_nacimiento[2:4]

    orden = 1
    while True:
        cand = f"CE-{orden}{yy}{rep_8}"
        cur.execute("SELECT 1 FROM estudiantes WHERE cedula = %s", (cand,))
        if not cur.fetchone():
            return cand
        orden += 1


def validar_texto_persona(valor: str, etiqueta: str) -> str:
    limpio = re.sub(r"\s+", " ", (valor or "").strip())
    if not limpio:
        raise ValueError(f"{etiqueta} es obligatorio.")
    if len(limpio) < 2 or len(limpio) > 80:
        raise ValueError(f"{etiqueta} debe tener entre 2 y 80 caracteres.")
    if not _RE_NOMBRE.match(limpio) or len(re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", limpio)) < 2:
        raise ValueError(f"{etiqueta} solo debe contener letras y espacios.")
    return limpio


def validar_telefono_ve(valor: str, etiqueta: str, obligatorio: bool = False) -> str:
    crudo = (valor or "").strip()
    if not crudo:
        if obligatorio:
            raise ValueError(f"El {etiqueta} es obligatorio.")
        return ""
    digitos = re.sub(r"[\s\-\(\)]+", "", crudo)
    if not _RE_TEL_VE.match(digitos):
        raise ValueError(
            f"El {etiqueta} es inválido. Use 11 dígitos (ej. 0414-1234567 o 0264-1234567)."
        )
    return f"{digitos[:4]}-{digitos[4:]}" if "-" in crudo or " " in crudo else digitos


def validar_correo_opcional(valor: str) -> str:
    limpio = (valor or "").strip()
    if not limpio:
        return ""
    if len(limpio) > 120 or not _RE_EMAIL.match(limpio):
        raise ValueError("El correo electrónico del representante no tiene un formato válido.")
    return limpio


def validar_direccion_opcional(valor: str, etiqueta: str) -> str:
    limpio = re.sub(r"\s+", " ", (valor or "").strip())
    if not limpio:
        return ""
    if len(limpio) < 5 or len(limpio) > 200:
        raise ValueError(f"La {etiqueta} debe tener entre 5 y 200 caracteres.")
    return limpio


def validar_lugar_nacimiento_opcional(valor: str) -> str:
    limpio = re.sub(r"\s+", " ", (valor or "").strip())
    if not limpio:
        return ""
    if len(limpio) > 120:
        raise ValueError("El lugar de nacimiento no debe exceder 120 caracteres.")
    return limpio


def validar_observaciones_opcional(valor: str) -> str:
    limpio = re.sub(r"\s+", " ", (valor or "").strip())
    return limpio[:255] if limpio else ""


def validar_fecha_nacimiento_opcional(valor: str):
    limpio = (valor or "").strip()
    if not limpio:
        return None
    try:
        fnac = date.fromisoformat(limpio[:10])
    except ValueError as err:
        raise ValueError("La fecha de nacimiento no es válida.") from err
    hoy = date.today()
    if fnac > hoy:
        raise ValueError("La fecha de nacimiento no puede ser futura.")
    edad = hoy.year - fnac.year - ((hoy.month, hoy.day) < (fnac.month, fnac.day))
    if edad < 3 or edad > 30:
        raise ValueError("Verifique la fecha de nacimiento (edad esperada entre 3 y 30 años).")
    return fnac.isoformat()


def _adjuntar_promedios(filas: list):
    """Adjunta el promedio (Media) o literal (Primaria) a una lista de inscripciones."""
    if not filas:
        return filas
    ids_num = [f["id_inscripcion"] for f in filas if f.get("tipo_escala") == "numerica"]
    ids_lit = [f["id_inscripcion"] for f in filas if f.get("tipo_escala") == "literal"]

    proms_num = {}
    if ids_num:
        ph = ",".join(["%s"] * len(ids_num))
        notas_sec = ejecutar_consulta(
            f"SELECT id_inscripcion, lapso_1, lapso_2, lapso_3, definitiva "
            f"FROM calificaciones_secundaria WHERE id_inscripcion IN ({ph})",
            tuple(ids_num),
        )
        agrupado = {}
        for ns in notas_sec:
            iid = ns["id_inscripcion"]
            agrupado.setdefault(iid, []).append(ns)
        for iid, lista in agrupado.items():
            defs = [x["definitiva"] for x in lista if x["definitiva"] is not None]
            if defs:
                proms_num[iid] = f"{sum(defs) / len(defs):.1f}"
            else:
                laps = [v for x in lista for v in (x["lapso_1"], x["lapso_2"], x["lapso_3"]) if v is not None]
                if laps:
                    proms_num[iid] = f"{sum(laps) / len(laps):.1f}"

    proms_lit = {}
    if ids_lit:
        ph = ",".join(["%s"] * len(ids_lit))
        notas_prim = ejecutar_consulta(
            f"SELECT id_inscripcion, lapso_1, lapso_2, lapso_3, definitiva "
            f"FROM calificaciones_primaria WHERE id_inscripcion IN ({ph})",
            tuple(ids_lit),
        )
        for np in notas_prim:
            iid = np["id_inscripcion"]
            if np.get("definitiva"):
                proms_lit[iid] = np["definitiva"]
            elif np.get("lapso_3"):
                proms_lit[iid] = f"L3: {np['lapso_3']}"
            elif np.get("lapso_2"):
                proms_lit[iid] = f"L2: {np['lapso_2']}"
            elif np.get("lapso_1"):
                proms_lit[iid] = f"L1: {np['lapso_1']}"

    for f in filas:
        iid = f["id_inscripcion"]
        if f.get("tipo_escala") == "literal":
            f["promedio_display"] = proms_lit.get(iid, "-")
        else:
            f["promedio_display"] = proms_num.get(iid, "-")
    return filas


def listar_inscripciones(
    id_periodo: int,
    filtro: str = "",
    id_nivel: int = None,
    id_grado: int = None,
    id_seccion: int = None,
    incluir_retirados: bool = False,
    estado: str = None,
):
    sql = (
        "SELECT i.id AS id_inscripcion, i.estado, i.condicion, i.observaciones, i.id_seccion, i.fecha_inscripcion, "
        "e.*, g.id AS id_grado, g.nombre AS grado_nombre, "
        "n.id AS id_nivel, n.nombre AS nivel_nombre, n.tipo_escala, "
        "s.nombre AS seccion_nombre, "
        "r.id AS id_representante, r.cedula AS rep_cedula, r.nombres AS rep_nombres, "
        "r.apellidos AS rep_apellidos, r.parentesco AS rep_parentesco, "
        "r.telefono AS rep_telefono, r.telefono_trabajo AS rep_telefono_trabajo, "
        "r.correo AS rep_correo, r.direccion AS rep_direccion "
        "FROM inscripciones i "
        "JOIN estudiantes e ON e.id = i.id_estudiante "
        "JOIN secciones s ON s.id = i.id_seccion "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "LEFT JOIN estudiante_representantes er ON er.id_estudiante = e.id AND er.es_principal = TRUE "
        "LEFT JOIN representantes r ON r.id = er.id_representante "
        "WHERE i.id_periodo = %s "
    )
    params = [id_periodo]
    estado_eff = estado if estado in ("activo", "retirado", "todos") else ("todos" if incluir_retirados else "activo")
    if estado_eff == "activo":
        sql += "AND i.estado = 'activo' AND e.activo = TRUE "
    elif estado_eff == "retirado":
        sql += "AND i.estado = 'retirado' "
    if id_nivel:
        sql += "AND n.id = %s "
        params.append(id_nivel)
    if id_grado:
        sql += "AND g.id = %s "
        params.append(id_grado)
    if id_seccion:
        sql += "AND s.id = %s "
        params.append(id_seccion)
    if filtro.strip():
        like = f"%{filtro.strip()}%"
        sql += "AND (e.cedula LIKE %s OR e.nombres LIKE %s OR e.apellidos LIKE %s OR r.cedula LIKE %s) "
        params.extend([like, like, like, like])
    sql += "ORDER BY n.orden ASC, g.orden ASC, s.nombre ASC, e.apellidos ASC, e.nombres ASC"
    return _adjuntar_promedios(ejecutar_consulta(sql, tuple(params)))


def _adjuntar_ultimo_historial(filas: list):
    """Adjunta el ultimo periodo/grado/seccion cursado a estudiantes sin inscripcion en el periodo consultado."""
    sin_insc_ids = [f["id"] for f in filas if not f.get("id_inscripcion")]
    if not sin_insc_ids:
        return filas
    ph = ",".join(["%s"] * len(sin_insc_ids))
    ultimos = ejecutar_consulta(
        f"SELECT i.id AS ultima_inscripcion_id, i.id_estudiante, i.estado AS ultimo_estado, "
        f"p.nombre AS ultimo_periodo_nombre, g.nombre AS ultimo_grado_nombre, "
        f"s.nombre AS ultima_seccion_nombre, n.nombre AS ultimo_nivel_nombre "
        f"FROM inscripciones i "
        f"JOIN periodos_escolares p ON p.id = i.id_periodo "
        f"JOIN secciones s ON s.id = i.id_seccion "
        f"JOIN grados_anios g ON g.id = s.id_grado_anio "
        f"JOIN niveles_educativos n ON n.id = g.id_nivel "
        f"WHERE i.id_estudiante IN ({ph}) "
        f"ORDER BY i.id_periodo DESC, i.id DESC",
        tuple(sin_insc_ids),
    )
    mapa = {}
    for u in ultimos:
        mapa.setdefault(u["id_estudiante"], u)
    for f in filas:
        if not f.get("id_inscripcion"):
            u = mapa.get(f["id"])
            if u:
                f["ultima_inscripcion_id"] = u["ultima_inscripcion_id"]
                f["ultimo_periodo_nombre"] = u["ultimo_periodo_nombre"]
                f["ultimo_grado_nombre"] = u["ultimo_grado_nombre"]
                f["ultima_seccion_nombre"] = u["ultima_seccion_nombre"]
                f["ultimo_nivel_nombre"] = u["ultimo_nivel_nombre"]
                f["ultimo_estado"] = u["ultimo_estado"]
            else:
                f["ultima_inscripcion_id"] = None
                f["ultimo_periodo_nombre"] = None
                f["ultimo_grado_nombre"] = None
                f["ultima_seccion_nombre"] = None
                f["ultimo_nivel_nombre"] = None
                f["ultimo_estado"] = None
    return filas


def listar_directorio_estudiantes(
    id_periodo: int = None,
    filtro: str = "",
    id_nivel: int = None,
    id_grado: int = None,
    id_seccion: int = None,
    estado: str = "activo",
):
    """Lista estudiantes en un periodo (inscritos, sin inscribir, retirados, egresados o todos) o directorio general."""
    if estado not in ("activo", "retirado", "sin_inscribir", "egresado", "todos"):
        estado = "activo"

    # Si hay periodo especifico y solo se piden inscritos activos o retirados, reutilizar la consulta directa
    if id_periodo and estado in ("activo", "retirado"):
        return listar_inscripciones(
            id_periodo,
            filtro=filtro,
            id_nivel=id_nivel,
            id_grado=id_grado,
            id_seccion=id_seccion,
            estado=estado,
        )

    # Consulta sobre el registro maestro de estudiantes + LEFT JOIN a su inscripcion en id_periodo (si aplica)
    params = []
    if id_periodo:
        join_insc = "LEFT JOIN inscripciones i ON i.id_estudiante = e.id AND i.id_periodo = %s "
        params.append(id_periodo)
    else:
        join_insc = (
            "LEFT JOIN inscripciones i ON i.id = ("
            "  SELECT i2.id FROM inscripciones i2 WHERE i2.id_estudiante = e.id "
            "  ORDER BY i2.id_periodo DESC, i2.id DESC LIMIT 1"
            ") "
        )

    sql = (
        "SELECT i.id AS id_inscripcion, i.estado, i.condicion, i.observaciones, i.id_seccion, i.fecha_inscripcion, i.id_periodo AS id_periodo_insc, "
        "p_insc.nombre AS periodo_insc_nombre, "
        "e.*, g.id AS id_grado, g.nombre AS grado_nombre, "
        "n.id AS id_nivel, n.nombre AS nivel_nombre, n.tipo_escala, "
        "s.nombre AS seccion_nombre, "
        "r.id AS id_representante, r.cedula AS rep_cedula, r.nombres AS rep_nombres, "
        "r.apellidos AS rep_apellidos, r.parentesco AS rep_parentesco, "
        "r.telefono AS rep_telefono, r.telefono_trabajo AS rep_telefono_trabajo, "
        "r.correo AS rep_correo, r.direccion AS rep_direccion "
        "FROM estudiantes e "
        + join_insc
        + "LEFT JOIN periodos_escolares p_insc ON p_insc.id = i.id_periodo "
        "LEFT JOIN secciones s ON s.id = i.id_seccion "
        "LEFT JOIN grados_anios g ON g.id = s.id_grado_anio "
        "LEFT JOIN niveles_educativos n ON n.id = g.id_nivel "
        "LEFT JOIN estudiante_representantes er ON er.id_estudiante = e.id AND er.es_principal = TRUE "
        "LEFT JOIN representantes r ON r.id = er.id_representante "
        "WHERE e.activo = TRUE "
    )

    if estado == "sin_inscribir":
        sql += "AND i.id IS NULL AND e.egresado = FALSE "
    elif estado == "egresado":
        sql += "AND e.egresado = TRUE "
    elif estado == "activo" and not id_periodo:
        sql += "AND e.egresado = FALSE AND (i.estado IS NULL OR i.estado = 'activo') "
    elif estado == "retirado" and not id_periodo:
        sql += "AND i.estado = 'retirado' "

    if id_nivel:
        sql += "AND n.id = %s "
        params.append(id_nivel)
    if id_grado:
        sql += "AND g.id = %s "
        params.append(id_grado)
    if id_seccion:
        sql += "AND s.id = %s "
        params.append(id_seccion)
    if filtro.strip():
        like = f"%{filtro.strip()}%"
        sql += "AND (e.cedula LIKE %s OR e.nombres LIKE %s OR e.apellidos LIKE %s OR r.cedula LIKE %s) "
        params.extend([like, like, like, like])

    sql += (
        "ORDER BY (i.id IS NULL) ASC, COALESCE(n.orden, 999) ASC, "
        "COALESCE(g.orden, 999) ASC, COALESCE(s.nombre, 'ZZZ') ASC, e.apellidos ASC, e.nombres ASC"
    )
    filas = ejecutar_consulta(sql, tuple(params))
    inscritos = [f for f in filas if f.get("id_inscripcion")]
    if inscritos:
        _adjuntar_promedios(inscritos)
    for f in filas:
        if not f.get("id_inscripcion"):
            f["promedio_display"] = "-"
    return _adjuntar_ultimo_historial(filas)


def contar_resumen_estudiantes_periodo(id_periodo: int = None) -> dict:
    """Retorna conteos de inscritos, sin inscribir, retirados, egresados y total registrados."""
    total_reg = ejecutar_consulta(
        "SELECT COUNT(*) AS c FROM estudiantes WHERE activo = TRUE", uno=True
    )["c"]
    egresados = ejecutar_consulta(
        "SELECT COUNT(*) AS c FROM estudiantes WHERE activo = TRUE AND egresado = TRUE", uno=True
    )["c"]
    if not id_periodo:
        return {
            "total_registrados": total_reg,
            "inscritos": 0,
            "retirados": 0,
            "egresados": egresados,
            "sin_inscribir": max(total_reg - egresados, 0),
        }
    inscritos = ejecutar_consulta(
        "SELECT COUNT(*) AS c FROM inscripciones i JOIN estudiantes e ON e.id = i.id_estudiante "
        "WHERE i.id_periodo = %s AND i.estado = 'activo' AND e.activo = TRUE",
        (id_periodo,),
        uno=True,
    )["c"]
    retirados = ejecutar_consulta(
        "SELECT COUNT(*) AS c FROM inscripciones WHERE id_periodo = %s AND estado = 'retirado'",
        (id_periodo,),
        uno=True,
    )["c"]
    sin_inscribir = ejecutar_consulta(
        "SELECT COUNT(*) AS c FROM estudiantes e "
        "WHERE e.activo = TRUE AND e.egresado = FALSE "
        "AND NOT EXISTS (SELECT 1 FROM inscripciones i WHERE i.id_estudiante = e.id AND i.id_periodo = %s)",
        (id_periodo,),
        uno=True,
    )["c"]
    return {
        "total_registrados": total_reg,
        "inscritos": inscritos,
        "retirados": retirados,
        "egresados": egresados,
        "sin_inscribir": sin_inscribir,
    }


def listar_inscripciones_por_ids(ids_inscripcion: list):
    if not ids_inscripcion:
        return []
    ph = ",".join(["%s"] * len(ids_inscripcion))
    sql = (
        "SELECT i.id AS id_inscripcion, i.estado, i.condicion, i.observaciones, i.id_seccion, i.fecha_inscripcion, "
        "e.*, g.id AS id_grado, g.nombre AS grado_nombre, "
        "n.id AS id_nivel, n.nombre AS nivel_nombre, n.tipo_escala, "
        "s.nombre AS seccion_nombre, "
        "r.id AS id_representante, r.cedula AS rep_cedula, r.nombres AS rep_nombres, "
        "r.apellidos AS rep_apellidos, r.parentesco AS rep_parentesco, "
        "r.telefono AS rep_telefono, r.telefono_trabajo AS rep_telefono_trabajo, "
        "r.correo AS rep_correo, r.direccion AS rep_direccion "
        "FROM inscripciones i "
        "JOIN estudiantes e ON e.id = i.id_estudiante "
        "JOIN secciones s ON s.id = i.id_seccion "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "LEFT JOIN estudiante_representantes er ON er.id_estudiante = e.id AND er.es_principal = TRUE "
        "LEFT JOIN representantes r ON r.id = er.id_representante "
        f"WHERE i.id IN ({ph}) "
        "ORDER BY n.orden ASC, g.orden ASC, s.nombre ASC, e.apellidos ASC, e.nombres ASC"
    )
    return ejecutar_consulta(sql, tuple(ids_inscripcion))


def obtener_expediente_completo(id_estudiante: int):
    """Retorna ficha del estudiante, representante y su historial de notas en todos los periodos."""
    estudiante = ejecutar_consulta("SELECT * FROM estudiantes WHERE id = %s", (id_estudiante,), uno=True)
    if not estudiante:
        return None
    representante = ejecutar_consulta(
        "SELECT r.* FROM estudiante_representantes er "
        "JOIN representantes r ON r.id = er.id_representante "
        "WHERE er.id_estudiante = %s ORDER BY er.es_principal DESC LIMIT 1",
        (id_estudiante,),
        uno=True,
    )
    historial = ejecutar_consulta(
        "SELECT i.id AS id_inscripcion, i.estado, i.condicion, i.fecha_inscripcion, "
        "p.id AS id_periodo, p.nombre AS periodo_nombre, p.activo AS periodo_activo, "
        "g.id AS id_grado, g.nombre AS grado_nombre, g.orden AS grado_orden, "
        "s.nombre AS seccion_nombre, s.turno, "
        "n.id AS id_nivel, n.nombre AS nivel_nombre, n.orden AS nivel_orden, "
        "n.tipo_escala, n.titulo_otorga, "
        "CONCAT(d.apellidos, ' ', d.nombres) AS docente_guia_nombre "
        "FROM inscripciones i "
        "JOIN periodos_escolares p ON p.id = i.id_periodo "
        "JOIN secciones s ON s.id = i.id_seccion "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "LEFT JOIN docentes d ON d.id = s.id_docente_titular_guia "
        "WHERE i.id_estudiante = %s "
        "ORDER BY p.activo DESC, p.id DESC",
        (id_estudiante,),
    )
    for h in historial:
        h["orden_global"] = int(h["nivel_orden"]) * 100 + int(h["grado_orden"])
        if h.get("fecha_inscripcion"):
            h["fecha_inscripcion"] = h["fecha_inscripcion"].strftime("%d/%m/%Y")
        h["boletin"] = obtener_boletin_estudiante(h["id_inscripcion"])
        if h["tipo_escala"] == "numerica":
            defs = [m["definitiva"] for m in h["boletin"]["secundaria"] if m["definitiva"] is not None]
            h["promedio"] = f"{sum(defs) / len(defs):.1f}" if defs else "-"
        else:
            np = h["boletin"].get("primaria") or {}
            h["promedio"] = np.get("definitiva") or "-"
    if estudiante.get("fecha_nacimiento"):
        estudiante["fecha_nacimiento"] = estudiante["fecha_nacimiento"].strftime("%d/%m/%Y")
    return {"estudiante": estudiante, "representante": representante, "historial": historial}


def obtener_historial_certificable(
    id_estudiante: int,
    desde: int = None,
    hasta: int = None,
    tipo_escala: str = None,
):
    """Retorna expediente y su historial en orden cronologico ascendente filtrado por rango de grados."""
    exp = obtener_expediente_completo(id_estudiante)
    if not exp:
        return None
    todos = sorted(
        exp["historial"],
        key=lambda h: (h["orden_global"], h["id_periodo"], h["id_inscripcion"]),
    )
    if tipo_escala in ("literal", "numerica"):
        base = [h for h in todos if h["tipo_escala"] == tipo_escala]
    else:
        base = list(todos)

    if desde is not None and hasta is not None and desde > hasta:
        desde, hasta = hasta, desde

    filtrados = [
        h for h in base
        if (desde is None or h["orden_global"] >= desde)
        and (hasta is None or h["orden_global"] <= hasta)
    ]

    if filtrados:
        primero = filtrados[0]["grado_nombre"]
        ultimo = filtrados[-1]["grado_nombre"]
        rango_texto = primero if primero == ultimo else f"{primero} a {ultimo}"
    else:
        rango_texto = "Sin registros en el rango seleccionado"

    notas_todas = []
    for h in filtrados:
        if h["tipo_escala"] == "numerica":
            for m in h["boletin"].get("secundaria", []):
                if m.get("definitiva") is not None:
                    notas_todas.append(float(m["definitiva"]))
    promedio_acumulado = (
        f"{sum(notas_todas) / len(notas_todas):.2f}" if notas_todas else "-"
    )

    return {
        "estudiante": exp["estudiante"],
        "representante": exp["representante"],
        "historial_todos": todos,
        "historial": filtrados,
        "rango_texto": rango_texto,
        "promedio_acumulado": promedio_acumulado,
        "total_materias_evaluadas": len(notas_todas),
        "desde": desde if desde is not None else (base[0]["orden_global"] if base else None),
        "hasta": hasta if hasta is not None else (base[-1]["orden_global"] if base else None),
    }


def obtener_inscripcion_detalle(id_inscripcion: int):
    return ejecutar_consulta(
        "SELECT i.id AS id_inscripcion, i.id_periodo, i.id_seccion, i.estado, i.fecha_inscripcion, "
        "p.nombre AS periodo_nombre, e.*, "
        "s.nombre AS seccion_nombre, s.turno, "
        "g.id AS id_grado, g.nombre AS grado_nombre, "
        "n.id AS id_nivel, n.nombre AS nivel_nombre, n.tipo_escala, n.titulo_otorga, "
        "CONCAT(d.apellidos, ' ', d.nombres) AS docente_guia_nombre, d.cedula AS docente_guia_cedula, "
        "r.cedula AS rep_cedula, r.nombres AS rep_nombres, r.apellidos AS rep_apellidos, "
        "r.parentesco AS rep_parentesco, r.telefono AS rep_telefono, r.telefono_trabajo AS rep_telefono_trabajo, "
        "r.correo AS rep_correo, r.direccion AS rep_direccion "
        "FROM inscripciones i "
        "JOIN periodos_escolares p ON p.id = i.id_periodo "
        "JOIN estudiantes e ON e.id = i.id_estudiante "
        "JOIN secciones s ON s.id = i.id_seccion "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "LEFT JOIN docentes d ON d.id = s.id_docente_titular_guia "
        "LEFT JOIN estudiante_representantes er ON er.id_estudiante = e.id AND er.es_principal = TRUE "
        "LEFT JOIN representantes r ON r.id = er.id_representante "
        "WHERE i.id = %s",
        (id_inscripcion,),
        uno=True,
    )


def _upsert_representante(cur, datos: dict, cedula_estudiante: str = "") -> int:
    rep_cedula = normalizar_y_validar_cedula(
        datos.get("rep_cedula", ""), "cédula del representante", max_digitos=9
    )
    if cedula_estudiante and rep_cedula == cedula_estudiante:
        raise ValueError("La cédula del representante no puede ser igual a la del estudiante.")
    rep_nombres = validar_texto_persona(datos.get("rep_nombres", ""), "Los nombres del representante")
    rep_apellidos = validar_texto_persona(datos.get("rep_apellidos", ""), "Los apellidos del representante")
    rep_telefono = validar_telefono_ve(
        datos.get("rep_telefono", ""), "teléfono personal del representante", obligatorio=True
    )
    rep_telefono_trabajo = validar_telefono_ve(
        datos.get("rep_telefono_trabajo", ""), "teléfono de trabajo del representante", obligatorio=False
    )
    rep_correo = validar_correo_opcional(datos.get("rep_correo", ""))
    rep_direccion = validar_direccion_opcional(
        datos.get("rep_direccion", ""), "dirección del representante"
    )
    rep_parentesco = (datos.get("rep_parentesco", "Representante Legal") or "").strip() or "Representante Legal"

    cur.execute("SELECT id FROM representantes WHERE cedula = %s", (rep_cedula,))
    rep = cur.fetchone()
    if rep:
        cur.execute(
            "UPDATE representantes SET nombres=%s, apellidos=%s, parentesco=%s, telefono=%s, "
            "telefono_trabajo=%s, correo=%s, direccion=%s WHERE id=%s",
            (
                rep_nombres,
                rep_apellidos,
                rep_parentesco,
                rep_telefono,
                rep_telefono_trabajo,
                rep_correo,
                rep_direccion,
                rep["id"],
            ),
        )
        return rep["id"]

    cur.execute(
        "INSERT INTO representantes (cedula, nombres, apellidos, parentesco, telefono, telefono_trabajo, correo, direccion) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (
            rep_cedula,
            rep_nombres,
            rep_apellidos,
            rep_parentesco,
            rep_telefono,
            rep_telefono_trabajo,
            rep_correo,
            rep_direccion,
        ),
    )
    return cur.lastrowid


def registrar_e_inscribir_estudiante(datos: dict, id_periodo: int, id_seccion: int) -> int:
    verificar_periodo_editable(id_periodo)
    sin_cedula = str(datos.get("sin_cedula") or "").strip() in ("1", "true", "on", "si")
    cedula_raw = "" if sin_cedula else datos.get("cedula", "")
    cedula = normalizar_y_validar_cedula(
        cedula_raw, "cédula del estudiante", max_digitos=12, permitir_sin_cedula=True
    )
    nombres = validar_texto_persona(datos.get("nombres", ""), "Los nombres del estudiante")
    apellidos = validar_texto_persona(datos.get("apellidos", ""), "Los apellidos del estudiante")
    fecha_nacimiento = validar_fecha_nacimiento_opcional(datos.get("fecha_nacimiento", ""))
    lugar_nacimiento = validar_lugar_nacimiento_opcional(datos.get("lugar_nacimiento", ""))
    direccion = validar_direccion_opcional(datos.get("direccion", ""), "dirección del estudiante")
    observaciones = validar_observaciones_opcional(datos.get("observaciones", ""))
    genero = (datos.get("genero") or "M").strip()
    if genero not in ("M", "F"):
        genero = "M"
    condicion = (datos.get("condicion") or "regular").strip()
    if condicion not in CONDICIONES_VALIDAS:
        condicion = "regular"

    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            if cedula == "__GENERAR__":
                rep_ci_val = normalizar_y_validar_cedula(
                    datos.get("rep_cedula", ""), "cédula del representante", max_digitos=9
                )
                cedula = generar_cedula_escolar(cur, rep_ci_val, fecha_nacimiento)
            id_rep = _upsert_representante(cur, datos, cedula_estudiante=cedula)

            cur.execute("SELECT id, nombres, apellidos FROM estudiantes WHERE cedula = %s", (cedula,))
            est = cur.fetchone()
            if est:
                id_est_form = str(datos.get("id_estudiante_existente") or "").strip()
                mismo_id = id_est_form.isdigit() and int(id_est_form) == est["id"]
                mismo_nombre = (
                    re.sub(r"\s+", " ", (est["apellidos"] or "").strip().upper()) == apellidos.upper()
                    and re.sub(r"\s+", " ", (est["nombres"] or "").strip().upper()) == nombres.upper()
                )
                if not (mismo_id or mismo_nombre):
                    raise ValueError(
                        f"La cédula {cedula} ya pertenece a otro estudiante ({est['apellidos']} {est['nombres']}). "
                        "No pueden existir dos estudiantes con la misma cédula."
                    )
                id_estudiante = est["id"]
                rec_prev = evaluar_recomendacion_reinscripcion(id_estudiante, id_periodo_destino=id_periodo)
                if rec_prev.get("tiene_historial") and rec_prev.get("solo_superiores"):
                    cur.execute(
                        "SELECT g.nombre AS grado_nombre, g.orden AS grado_orden, n.orden AS nivel_orden "
                        "FROM secciones s "
                        "JOIN grados_anios g ON g.id = s.id_grado_anio "
                        "JOIN niveles_educativos n ON n.id = g.id_nivel "
                        "WHERE s.id = %s",
                        (id_seccion,),
                    )
                    sec_dest = cur.fetchone()
                    if sec_dest:
                        orden_dest = (sec_dest["nivel_orden"], sec_dest["grado_orden"])
                        orden_prev = (rec_prev["ultimo_nivel_orden"], rec_prev["ultimo_grado_orden"])
                        if orden_dest <= orden_prev:
                            raise ValueError(
                                f"El estudiante ya aprobó {rec_prev['ultimo_grado_nombre']}; "
                                "debe inscribirse en un grado o año superior."
                            )
                cur.execute(
                    "UPDATE estudiantes SET nombres=%s, apellidos=%s, genero=%s, fecha_nacimiento=%s, "
                    "lugar_nacimiento=%s, direccion=%s, egresado=FALSE, activo=TRUE WHERE id=%s",
                    (
                        nombres,
                        apellidos,
                        genero,
                        fecha_nacimiento,
                        lugar_nacimiento,
                        direccion,
                        id_estudiante,
                    ),
                )
            else:
                cur.execute(
                    "INSERT INTO estudiantes (cedula, nombres, apellidos, genero, fecha_nacimiento, lugar_nacimiento, direccion, egresado, activo) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE, TRUE)",
                    (
                        cedula,
                        nombres,
                        apellidos,
                        genero,
                        fecha_nacimiento,
                        lugar_nacimiento,
                        direccion,
                    ),
                )
                id_estudiante = cur.lastrowid

            cur.execute("UPDATE estudiante_representantes SET es_principal = FALSE WHERE id_estudiante = %s", (id_estudiante,))
            cur.execute(
                "INSERT INTO estudiante_representantes (id_estudiante, id_representante, es_principal) "
                "VALUES (%s, %s, TRUE) ON DUPLICATE KEY UPDATE es_principal = TRUE",
                (id_estudiante, id_rep),
            )

            cur.execute(
                "INSERT INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion, observaciones) "
                "VALUES (%s, %s, %s, 'activo', %s, %s) "
                "ON DUPLICATE KEY UPDATE id_seccion = VALUES(id_seccion), estado = 'activo', condicion = VALUES(condicion), observaciones = VALUES(observaciones)",
                (id_periodo, id_estudiante, id_seccion, condicion, observaciones),
            )
            cur.execute(
                "SELECT id FROM inscripciones WHERE id_periodo = %s AND id_estudiante = %s",
                (id_periodo, id_estudiante),
            )
            id_inscripcion = cur.fetchone()["id"]
        conn.commit()
        return id_inscripcion
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def buscar_representante_por_cedula(cedula: str):
    c = (cedula or "").strip().upper()
    if not c:
        return None
    return ejecutar_consulta(
        "SELECT cedula, nombres, apellidos, parentesco, telefono, telefono_trabajo, correo, direccion "
        "FROM representantes WHERE cedula = %s LIMIT 1",
        (c,),
        uno=True,
    )


def evaluar_recomendacion_reinscripcion(id_estudiante: int, id_periodo_destino: int = None) -> dict:
    """Evalua la recomendacion academica de reinscripcion (promovido, mat. pendiente, repitiente, egreso o reingreso)."""
    params = [id_estudiante]
    extra_per = ""
    if id_periodo_destino:
        extra_per = "AND i.id_periodo <> %s "
        params.append(id_periodo_destino)

    ultima = ejecutar_consulta(
        "SELECT i.id AS id_inscripcion, i.id_periodo, i.estado, i.condicion, "
        "p.nombre AS periodo_nombre, s.id AS id_seccion, s.nombre AS seccion_nombre, "
        "g.id AS id_grado, g.nombre AS grado_nombre, g.orden AS grado_orden, "
        "n.nombre AS nivel_nombre, n.orden AS nivel_orden, n.tipo_escala "
        "FROM inscripciones i "
        "JOIN periodos_escolares p ON p.id = i.id_periodo "
        "JOIN secciones s ON s.id = i.id_seccion "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        f"WHERE i.id_estudiante = %s {extra_per}"
        "ORDER BY i.id_periodo DESC, i.id DESC LIMIT 1",
        tuple(params),
        uno=True,
    )
    if not ultima:
        return {
            "tiene_historial": False,
            "accion_sugerida": "inscribir",
            "condicion_sugerida": "regular",
            "tipo_badge": "neutral",
            "etiqueta": "Nuevo ingreso (sin historial previo)",
            "detalle": "",
            "evaluacion_incompleta": False,
            "solo_superiores": False,
            "ultimo_grado_id": None,
            "ultimo_grado_nombre": None,
            "ultimo_nivel_orden": None,
            "ultimo_grado_orden": None,
            "grado_sugerido_id": None,
            "grado_sugerido_nombre": None,
            "id_seccion_sugerida": None,
            "aplazadas": 0,
            "materias_aplazadas": [],
        }

    siguiente = obtener_grado_siguiente(ultima["id_grado"])
    accion = "inscribir"
    condicion = "regular"
    tipo_badge = "ok"
    incompleta = False
    aplazadas = 0
    materias_aplazadas = []
    grado_sug_id = siguiente["id"] if siguiente else ultima["id_grado"]
    grado_sug_nom = siguiente["nombre"] if siguiente else ultima["grado_nombre"]
    etiqueta = ""
    detalle = f'Último: {ultima["grado_nombre"]} "{ultima["seccion_nombre"]}" ({ultima["periodo_nombre"]})'

    if ultima["estado"] == "retirado":
        condicion = "reingreso"
        tipo_badge = "warn"
        grado_sug_id = ultima["id_grado"]
        grado_sug_nom = ultima["grado_nombre"]
        etiqueta = f"Reingreso → {grado_sug_nom}"
        detalle = f'Retirado en {ultima["grado_nombre"]} "{ultima["seccion_nombre"]}" ({ultima["periodo_nombre"]})'
    elif ultima["tipo_escala"] == "literal":
        np = ejecutar_consulta(
            "SELECT definitiva FROM calificaciones_primaria WHERE id_inscripcion = %s",
            (ultima["id_inscripcion"],),
            uno=True,
        )
        def_lit = np["definitiva"] if np else None
        if not def_lit:
            incompleta = True
            tipo_badge = "warn"
            etiqueta = "Evaluación incompleta (sin definitiva literal)"
        elif def_lit == "E":
            condicion = "repitiente"
            tipo_badge = "danger"
            grado_sug_id = ultima["id_grado"]
            grado_sug_nom = ultima["grado_nombre"]
            etiqueta = f"Repitiente (Def: E) → {grado_sug_nom}"
        else:
            if siguiente:
                etiqueta = f"Promovido (Def: {def_lit}) → {siguiente['nombre']}"
            else:
                accion = "egresar"
                etiqueta = f"Aprobado (Def: {def_lit}) · Apto para Egreso"
    else:
        mats = ejecutar_consulta(
            "SELECT m.id, m.nombre, cs.definitiva "
            "FROM materias m "
            "LEFT JOIN calificaciones_secundaria cs ON cs.id_materia = m.id AND cs.id_inscripcion = %s "
            "WHERE m.id_grado_anio = %s AND m.activo = TRUE "
            "ORDER BY m.nombre ASC",
            (ultima["id_inscripcion"], ultima["id_grado"]),
        )
        total_m = len(mats)
        con_def = [m for m in mats if m["definitiva"] is not None]
        aplaz_list = [m["nombre"] for m in con_def if m["definitiva"] < 10]
        aplazadas = len(aplaz_list)
        materias_aplazadas = aplaz_list

        if total_m == 0 or len(con_def) < total_m:
            incompleta = True
            tipo_badge = "warn"
            faltan = total_m - len(con_def)
            etiqueta = (
                "Sin definitivas registradas"
                if len(con_def) == 0
                else f"Evaluación incompleta (faltan {faltan} definitiva(s))"
            )
            if aplazadas > 0:
                detalle += f" · {aplazadas} aplazada(s) cargada(s)"
        elif aplazadas == 0:
            if siguiente:
                etiqueta = f"Promovido → {siguiente['nombre']}"
            else:
                accion = "egresar"
                grado_sug_id = None
                grado_sug_nom = "Egresado"
                etiqueta = "Aprobado · Apto para Egreso (Graduando)"
        elif aplazadas in (1, 2):
            if siguiente:
                condicion = "materia_pendiente"
                tipo_badge = "warn"
                etiqueta = f"Promovido con {aplazadas} Mat. Pendiente → {siguiente['nombre']}"
                detalle = "Pendiente: " + ", ".join(aplaz_list)
            else:
                condicion = "repitiente"
                tipo_badge = "danger"
                grado_sug_id = ultima["id_grado"]
                grado_sug_nom = ultima["grado_nombre"]
                etiqueta = f"Pendiente en {ultima['grado_nombre']} ({aplazadas} aplazada(s))"
                detalle = "Aplazada(s): " + ", ".join(aplaz_list)
        else:
            condicion = "repitiente"
            tipo_badge = "danger"
            grado_sug_id = ultima["id_grado"]
            grado_sug_nom = ultima["grado_nombre"]
            etiqueta = f"Repitiente ({aplazadas} aplazadas) → {grado_sug_nom}"
            detalle = "Aplazadas: " + ", ".join(aplaz_list[:4]) + ("..." if len(aplaz_list) > 4 else "")

    id_seccion_sug = None
    if id_periodo_destino and accion == "inscribir" and grado_sug_id:
        secs_dest = ejecutar_consulta(
            "SELECT id, nombre FROM secciones "
            "WHERE id_periodo = %s AND id_grado_anio = %s AND activo = TRUE "
            "ORDER BY nombre ASC",
            (id_periodo_destino, grado_sug_id),
        )
        if secs_dest:
            misma_letra = next((s for s in secs_dest if s["nombre"] == ultima["seccion_nombre"]), None)
            id_seccion_sug = (misma_letra or secs_dest[0])["id"]

    solo_superiores = (
        ultima["estado"] != "retirado"
        and not incompleta
        and condicion in ("regular", "materia_pendiente")
    )

    return {
        "tiene_historial": True,
        "accion_sugerida": accion,
        "condicion_sugerida": condicion,
        "tipo_badge": tipo_badge,
        "etiqueta": etiqueta,
        "detalle": detalle,
        "evaluacion_incompleta": incompleta,
        "solo_superiores": solo_superiores,
        "ultimo_grado_id": ultima["id_grado"],
        "ultimo_grado_nombre": ultima["grado_nombre"],
        "ultimo_nivel_orden": ultima["nivel_orden"],
        "ultimo_grado_orden": ultima["grado_orden"],
        "grado_sugerido_id": grado_sug_id,
        "grado_sugerido_nombre": grado_sug_nom,
        "id_seccion_sugerida": id_seccion_sug,
        "aplazadas": aplazadas,
        "materias_aplazadas": materias_aplazadas,
    }


def buscar_estudiante_por_cedula(cedula: str, id_periodo_destino: int = None):
    """Busca un estudiante registrado junto a su representante principal, historial y recomendacion."""
    c = (cedula or "").strip().upper()
    if not c:
        return None
    est = ejecutar_consulta(
        "SELECT id, cedula, nombres, apellidos, genero, fecha_nacimiento, direccion, egresado "
        "FROM estudiantes WHERE cedula = %s LIMIT 1",
        (c,),
        uno=True,
    )
    if not est:
        return None
    if est.get("fecha_nacimiento"):
        est["fecha_nacimiento"] = est["fecha_nacimiento"].strftime("%Y-%m-%d")
    rep = ejecutar_consulta(
        "SELECT r.cedula, r.nombres, r.apellidos, r.parentesco, r.telefono, r.telefono_trabajo, r.correo, r.direccion "
        "FROM estudiante_representantes er "
        "JOIN representantes r ON r.id = er.id_representante "
        "WHERE er.id_estudiante = %s ORDER BY er.es_principal DESC LIMIT 1",
        (est["id"],),
        uno=True,
    )
    ultima = ejecutar_consulta(
        "SELECT p.nombre AS periodo_nombre, g.nombre AS grado_nombre, s.nombre AS seccion_nombre "
        "FROM inscripciones i "
        "JOIN periodos_escolares p ON p.id = i.id_periodo "
        "JOIN secciones s ON s.id = i.id_seccion "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "WHERE i.id_estudiante = %s ORDER BY i.id_periodo DESC, i.id DESC LIMIT 1",
        (est["id"],),
        uno=True,
    )
    rec = evaluar_recomendacion_reinscripcion(est["id"], id_periodo_destino=id_periodo_destino)
    return {
        "estudiante": est,
        "representante": rep,
        "ultima_inscripcion": ultima,
        "recomendacion": rec,
    }


def buscar_estudiantes_para_inscripcion(q: str, id_periodo_destino: int = None, limite: int = 10):
    """Busca estudiantes registrados por CI, nombre/apellido, representante o ultima seccion/grado."""
    tokens = [t.strip() for t in (q or "").split() if t.strip()]
    if not tokens:
        return []

    params = []
    sel_actual = "NULL AS seccion_actual_nombre"
    join_actual = ""
    if id_periodo_destino:
        sel_actual = "CONCAT(ga.nombre, ' \"', sa.nombre, '\"') AS seccion_actual_nombre"
        join_actual = (
            "LEFT JOIN inscripciones ia ON ia.id_estudiante = e.id AND ia.id_periodo = %s "
            "LEFT JOIN secciones sa ON sa.id = ia.id_seccion "
            "LEFT JOIN grados_anios ga ON ga.id = sa.id_grado_anio "
        )
        params.append(id_periodo_destino)

    sql = (
        "SELECT e.id, e.cedula, e.nombres, e.apellidos, e.genero, e.fecha_nacimiento, e.direccion, e.egresado, "
        "r.cedula AS rep_cedula, r.nombres AS rep_nombres, r.apellidos AS rep_apellidos, "
        "r.parentesco AS rep_parentesco, r.telefono AS rep_telefono, r.telefono_trabajo AS rep_telefono_trabajo, "
        "r.correo AS rep_correo, r.direccion AS rep_direccion, "
        "p.nombre AS ultimo_periodo, g.nombre AS ultimo_grado, s.nombre AS ultima_seccion, "
        f"{sel_actual} "
        "FROM estudiantes e "
        "LEFT JOIN estudiante_representantes er ON er.id_estudiante = e.id AND er.es_principal = TRUE "
        "LEFT JOIN representantes r ON r.id = er.id_representante "
        "LEFT JOIN inscripciones iu ON iu.id = ("
        "  SELECT i2.id FROM inscripciones i2 WHERE i2.id_estudiante = e.id "
        "  ORDER BY i2.id_periodo DESC, i2.id DESC LIMIT 1"
        ") "
        "LEFT JOIN periodos_escolares p ON p.id = iu.id_periodo "
        "LEFT JOIN secciones s ON s.id = iu.id_seccion "
        "LEFT JOIN grados_anios g ON g.id = s.id_grado_anio "
        + join_actual
        + "WHERE e.activo = TRUE "
    )

    campo_busqueda = (
        "CONCAT_WS(' ', e.cedula, e.nombres, e.apellidos, "
        "COALESCE(r.cedula, ''), COALESCE(r.nombres, ''), COALESCE(r.apellidos, ''), "
        "COALESCE(g.nombre, ''), COALESCE(s.nombre, ''), COALESCE(p.nombre, ''))"
    )
    for tok in tokens[:5]:
        sql += f"AND {campo_busqueda} LIKE %s "
        params.append(f"%{tok}%")

    sql += "ORDER BY e.apellidos ASC, e.nombres ASC LIMIT %s"
    params.append(int(limite))

    filas = ejecutar_consulta(sql, tuple(params))
    for f in filas:
        if f.get("fecha_nacimiento"):
            f["fecha_nacimiento"] = f["fecha_nacimiento"].strftime("%Y-%m-%d")
        f["egresado"] = bool(f.get("egresado"))
    return filas


def actualizar_estudiante(eid: int, datos: dict):
    cedula_cruda = (datos.get("cedula") or "").strip()
    cedula = normalizar_y_validar_cedula(cedula_cruda, "cédula del estudiante", max_digitos=12) if cedula_cruda else ""
    nombres = validar_texto_persona(datos.get("nombres", ""), "Los nombres del estudiante")
    apellidos = validar_texto_persona(datos.get("apellidos", ""), "Los apellidos del estudiante")
    fecha_nacimiento = validar_fecha_nacimiento_opcional(datos.get("fecha_nacimiento", ""))
    lugar_nacimiento = validar_lugar_nacimiento_opcional(datos.get("lugar_nacimiento", ""))
    direccion = validar_direccion_opcional(datos.get("direccion", ""), "dirección del estudiante")
    observaciones = validar_observaciones_opcional(datos.get("observaciones", ""))
    genero = (datos.get("genero") or "M").strip()
    if genero not in ("M", "F"):
        genero = "M"

    tiene_datos_rep = any(
        (datos.get(k) or "").strip()
        for k in ("rep_cedula", "rep_nombres", "rep_apellidos", "rep_telefono")
    )

    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            if cedula:
                cur.execute(
                    "SELECT id, nombres, apellidos FROM estudiantes WHERE cedula = %s AND id <> %s",
                    (cedula, eid),
                )
                dup = cur.fetchone()
                if dup:
                    raise ValueError(
                        f"La cédula {cedula} ya pertenece a otro estudiante ({dup['apellidos']} {dup['nombres']})."
                    )
            id_rep = _upsert_representante(cur, datos, cedula_estudiante=cedula) if tiene_datos_rep else None
            if cedula:
                cur.execute(
                    "UPDATE estudiantes SET cedula=%s, nombres=%s, apellidos=%s, genero=%s, fecha_nacimiento=%s, lugar_nacimiento=%s, direccion=%s WHERE id=%s",
                    (
                        cedula,
                        nombres,
                        apellidos,
                        genero,
                        fecha_nacimiento,
                        lugar_nacimiento,
                        direccion,
                        eid,
                    ),
                )
            else:
                cur.execute(
                    "UPDATE estudiantes SET nombres=%s, apellidos=%s, genero=%s, fecha_nacimiento=%s, lugar_nacimiento=%s, direccion=%s WHERE id=%s",
                    (
                        nombres,
                        apellidos,
                        genero,
                        fecha_nacimiento,
                        lugar_nacimiento,
                        direccion,
                        eid,
                    ),
                )
            id_inscripcion = datos.get("id_inscripcion")
            id_seccion = datos.get("id_seccion")
            condicion = (datos.get("condicion") or "").strip()
            if id_inscripcion:
                cur.execute(
                    "SELECT i.id_periodo, i.id_seccion, i.condicion, s.id_grado_anio "
                    "FROM inscripciones i JOIN secciones s ON s.id = i.id_seccion "
                    "WHERE i.id = %s AND i.id_estudiante = %s",
                    (int(id_inscripcion), eid),
                )
                insc_actual = cur.fetchone()
                if insc_actual:
                    if id_seccion and int(id_seccion) != insc_actual["id_seccion"]:
                        verificar_periodo_editable(insc_actual["id_periodo"])
                        cur.execute("SELECT id_grado_anio FROM secciones WHERE id = %s", (int(id_seccion),))
                        sec_nueva = cur.fetchone()
                        if sec_nueva and sec_nueva["id_grado_anio"] != insc_actual["id_grado_anio"]:
                            cur.execute(
                                "SELECT (SELECT COUNT(*) FROM calificaciones_primaria WHERE id_inscripcion = %s) "
                                "+ (SELECT COUNT(*) FROM calificaciones_secundaria WHERE id_inscripcion = %s) AS total_notas",
                                (int(id_inscripcion), int(id_inscripcion)),
                            )
                            if cur.fetchone()["total_notas"] > 0:
                                raise ValueError(
                                    "Este estudiante ya tiene calificaciones cargadas en su grado actual; "
                                    "solo puede cambiarlo a otra sección del mismo grado/año."
                                )
                        cur.execute(
                            "UPDATE inscripciones SET id_seccion = %s WHERE id = %s AND id_estudiante = %s",
                            (int(id_seccion), int(id_inscripcion), eid),
                        )
                    if condicion in CONDICIONES_VALIDAS and condicion != insc_actual.get("condicion"):
                        verificar_periodo_editable(insc_actual["id_periodo"])
                        cur.execute(
                            "UPDATE inscripciones SET condicion = %s WHERE id = %s AND id_estudiante = %s",
                            (condicion, int(id_inscripcion), eid),
                        )
                    if "observaciones" in datos:
                        verificar_periodo_editable(insc_actual["id_periodo"])
                        cur.execute(
                            "UPDATE inscripciones SET observaciones = %s WHERE id = %s AND id_estudiante = %s",
                            (observaciones, int(id_inscripcion), eid),
                        )
            if id_rep:
                cur.execute("UPDATE estudiante_representantes SET es_principal = FALSE WHERE id_estudiante = %s", (eid,))
                cur.execute(
                    "INSERT INTO estudiante_representantes (id_estudiante, id_representante, es_principal) "
                    "VALUES (%s, %s, TRUE) ON DUPLICATE KEY UPDATE es_principal = TRUE",
                    (eid, id_rep),
                )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def cambiar_estado_inscripcion(id_inscripcion: int, estado: str):
    if estado not in ("activo", "retirado"):
        raise ValueError("Estado inválido.")
    insc = ejecutar_consulta(
        "SELECT id_periodo FROM inscripciones WHERE id = %s", (id_inscripcion,), uno=True
    )
    if insc:
        verificar_periodo_editable(insc["id_periodo"])
    ejecutar_accion("UPDATE inscripciones SET estado = %s WHERE id = %s", (estado, id_inscripcion))


def trasladar_seccion_inscripcion(id_inscripcion: int, id_seccion_destino: int) -> dict:
    """Traslada una inscripcion activa a otra seccion del mismo periodo manteniendo sus notas."""
    insc = ejecutar_consulta(
        "SELECT i.id, i.id_periodo, i.id_seccion, i.estado, "
        "s.id_grado_anio, n.tipo_escala, g.nombre AS grado_origen, s.nombre AS seccion_origen "
        "FROM inscripciones i "
        "JOIN secciones s ON s.id = i.id_seccion "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "WHERE i.id = %s LIMIT 1",
        (id_inscripcion,),
        uno=True,
    )
    if not insc:
        raise ValueError("Inscripción no encontrada.")
    verificar_periodo_editable(insc["id_periodo"])
    if insc["id_seccion"] == id_seccion_destino:
        raise ValueError("El estudiante ya pertenece a esa sección.")

    dest = ejecutar_consulta(
        "SELECT s.id, s.id_periodo, s.id_grado_anio, s.activo, s.nombre AS seccion_destino, "
        "g.nombre AS grado_destino, n.tipo_escala "
        "FROM secciones s "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "WHERE s.id = %s LIMIT 1",
        (id_seccion_destino,),
        uno=True,
    )
    if not dest or not dest["activo"]:
        raise ValueError("La sección de destino no existe o está inactiva.")
    if dest["id_periodo"] != insc["id_periodo"]:
        raise ValueError("La sección de destino debe pertenecer al mismo período escolar.")
    if dest["tipo_escala"] != insc["tipo_escala"]:
        raise ValueError("No se puede trasladar entre Primaria y Media General en la misma matrícula.")

    if dest["tipo_escala"] == "numerica" and dest["id_grado_anio"] != insc["id_grado_anio"]:
        tiene_notas_sec = ejecutar_consulta(
            "SELECT 1 FROM calificaciones_secundaria WHERE id_inscripcion = %s LIMIT 1",
            (id_inscripcion,),
            uno=True,
        )
        if tiene_notas_sec:
            raise ValueError(
                "El estudiante ya posee calificaciones registradas en Media General; solo puede trasladarse a otra sección del mismo año."
            )

    ejecutar_accion(
        "UPDATE inscripciones SET id_seccion = %s WHERE id = %s",
        (id_seccion_destino, id_inscripcion),
    )
    return {
        "origen": f"{insc['grado_origen']} \"{insc['seccion_origen']}\"",
        "destino": f"{dest['grado_destino']} \"{dest['seccion_destino']}\"",
    }


def marcar_egresado(eid: int, egresado: bool):
    ejecutar_accion("UPDATE estudiantes SET egresado = %s WHERE id = %s", (bool(egresado), eid))


def listar_candidatos_prosecucion(
    id_periodo_origen: int,
    id_seccion_origen: int,
    id_periodo_destino: int,
):
    """Lista alumnos activos de una seccion de origen con su rendimiento y si ya estan inscritos en destino."""
    filas = listar_inscripciones(id_periodo_origen, id_seccion=id_seccion_origen, estado="activo")
    if not filas:
        return []
    est_ids = [f["id"] for f in filas]
    ph = ",".join(["%s"] * len(est_ids))

    dest_map = {}
    if id_periodo_destino:
        dest_rows = ejecutar_consulta(
            f"SELECT i.id_estudiante, g.nombre AS grado_nombre, s.nombre AS seccion_nombre "
            f"FROM inscripciones i "
            f"JOIN secciones s ON s.id = i.id_seccion "
            f"JOIN grados_anios g ON g.id = s.id_grado_anio "
            f"WHERE i.id_periodo = %s AND i.id_estudiante IN ({ph})",
            (id_periodo_destino,) + tuple(est_ids),
        )
        for dr in dest_rows:
            dest_map[dr["id_estudiante"]] = f'{dr["grado_nombre"]} "{dr["seccion_nombre"]}"'

    # Conteo de materias aplazadas (definitiva < 10) en Media General para orientar la promocion
    aplaz_map = {}
    insc_ids = [f["id_inscripcion"] for f in filas if f.get("tipo_escala") == "numerica"]
    if insc_ids:
        ph_i = ",".join(["%s"] * len(insc_ids))
        ap_rows = ejecutar_consulta(
            f"SELECT id_inscripcion, COUNT(*) AS aplazadas "
            f"FROM calificaciones_secundaria "
            f"WHERE id_inscripcion IN ({ph_i}) AND definitiva IS NOT NULL AND definitiva < 10 "
            f"GROUP BY id_inscripcion",
            tuple(insc_ids),
        )
        for ar in ap_rows:
            aplaz_map[ar["id_inscripcion"]] = ar["aplazadas"]

    resultado = []
    for f in filas:
        rec = evaluar_recomendacion_reinscripcion(f["id"], id_periodo_destino=id_periodo_destino)
        resultado.append({
            "id_estudiante": f["id"],
            "id_inscripcion_origen": f["id_inscripcion"],
            "cedula": f["cedula"],
            "apellidos": f["apellidos"],
            "nombres": f["nombres"],
            "egresado": bool(f.get("egresado")),
            "promedio": f.get("promedio_display", "-"),
            "aplazadas": aplaz_map.get(f["id_inscripcion"], rec.get("aplazadas", 0)),
            "ya_inscrito_destino": f["id"] in dest_map,
            "seccion_destino_actual": dest_map.get(f["id"]),
            "recomendacion": rec,
        })
    return resultado


def ejecutar_prosecucion_lote(
    id_periodo_destino: int,
    id_seccion_destino: int = None,
    ids_estudiantes: list = None,
    marcar_como_egresados: bool = False,
    decisiones: list = None,
) -> dict:
    """Ejecuta prosecucion/reinscripcion en lote (por decisiones individuales o lote uniforme)."""
    lista_decisiones = []
    if decisiones is not None:
        for d in decisiones:
            eid = d.get("id_estudiante")
            if not str(eid or "").isdigit():
                continue
            accion = (d.get("accion") or "inscribir").strip()
            cond = (d.get("condicion") or "regular").strip()
            if cond not in CONDICIONES_VALIDAS:
                cond = "regular"
            sec_id = d.get("id_seccion_destino")
            lista_decisiones.append({
                "id_estudiante": int(eid),
                "accion": "egresar" if accion == "egresar" else "inscribir",
                "id_seccion_destino": int(sec_id) if str(sec_id or "").isdigit() else None,
                "condicion": cond,
            })
    else:
        for x in (ids_estudiantes or []):
            if str(x).isdigit():
                lista_decisiones.append({
                    "id_estudiante": int(x),
                    "accion": "egresar" if marcar_como_egresados else "inscribir",
                    "id_seccion_destino": int(id_seccion_destino) if id_seccion_destino else None,
                    "condicion": "regular",
                })

    if not lista_decisiones:
        raise ValueError("Seleccione al menos un estudiante.")

    requiere_inscripcion = any(d["accion"] == "inscribir" for d in lista_decisiones)
    secciones_validas = set()
    if requiere_inscripcion:
        if not id_periodo_destino:
            raise ValueError("No hay período escolar activo para inscribir.")
        verificar_periodo_editable(id_periodo_destino)
        rows_sec = ejecutar_consulta(
            "SELECT id FROM secciones WHERE id_periodo = %s", (id_periodo_destino,)
        )
        secciones_validas = {r["id"] for r in rows_sec}
        for d in lista_decisiones:
            if d["accion"] == "inscribir":
                if not d["id_seccion_destino"] or d["id_seccion_destino"] not in secciones_validas:
                    raise ValueError(
                        "Todos los estudiantes marcados para reinscribir deben tener una sección destino válida en el período activo."
                    )

    conn = obtener_conexion()
    inscritos = 0
    omitidos = 0
    egresados = 0
    try:
        with conn.cursor() as cur:
            for d in lista_decisiones:
                eid = d["id_estudiante"]
                if d["accion"] == "egresar":
                    cur.execute("UPDATE estudiantes SET egresado = TRUE WHERE id = %s", (eid,))
                    egresados += 1
                    continue
                cur.execute(
                    "SELECT id FROM inscripciones WHERE id_periodo = %s AND id_estudiante = %s",
                    (id_periodo_destino, eid),
                )
                if cur.fetchone():
                    omitidos += 1
                    continue
                cur.execute(
                    "INSERT INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion) "
                    "VALUES (%s, %s, %s, 'activo', %s)",
                    (id_periodo_destino, eid, d["id_seccion_destino"], d["condicion"]),
                )
                cur.execute("UPDATE estudiantes SET egresado = FALSE, activo = TRUE WHERE id = %s", (eid,))
                inscritos += 1
        conn.commit()
        return {"inscritos": inscritos, "omitidos": omitidos, "egresados": egresados}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
