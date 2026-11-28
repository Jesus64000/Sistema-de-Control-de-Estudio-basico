from datetime import date, datetime
import re
from openpyxl import load_workbook
from db import obtener_conexion
from services.academico_service import verificar_periodo_editable
from services.estudiante_service import (
    generar_cedula_provisional,
    normalizar_y_validar_cedula,
    validar_lugar_nacimiento_opcional,
    validar_observaciones_opcional,
)


def _limpiar_str(val) -> str:
    if val is None:
        return ""
    return re.sub(r"\s+", " ", str(val).strip())


def _parsear_fecha_celdas(dia_v, mes_v, anio_v, fecha_unica=None):
    if isinstance(fecha_unica, datetime):
        return fecha_unica.date().isoformat()
    if isinstance(fecha_unica, date):
        return fecha_unica.isoformat()
    if isinstance(fecha_unica, str) and fecha_unica.strip():
        txt = fecha_unica.strip()[:10]
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(txt, fmt).date().isoformat()
            except ValueError:
                pass
    try:
        d = int(float(str(dia_v).strip()))
        m = int(float(str(mes_v).strip()))
        a = int(float(str(anio_v).strip()))
        if a < 100:
            a += 2000 if a <= 30 else 1900
        return date(a, m, d).isoformat()
    except (TypeError, ValueError):
        return None


def _mapear_sexo(val) -> str:
    s = _limpiar_str(val).upper()
    if s in ("F", "H", "FEMENINO", "HEMBRA"):
        return "F"
    return "M"


def _mapear_condicion_y_obs(obs_raw: str) -> tuple[str, str]:
    obs = validar_observaciones_opcional(obs_raw)
    u = obs.upper()
    if u == "R" or any(k in u for k in ("REP", "REPITE", "REPITIENTE")):
        return "repitiente", obs
    if u in ("MP", "PEN", "P") or "PENDIENTE" in u:
        return "materia_pendiente", obs
    if "NUEV" in u:
        return "nuevo_ingreso", obs
    if "REINGRESO" in u:
        return "reingreso", obs
    return "regular", obs


def _detectar_grado_y_seccion(ws, sheet_title: str) -> tuple[int | None, str | None, str]:
    """Intenta extraer (orden_grado 1..6, letra_seccion A..Z, tipo_escala) desde cabecera o nombre de hoja."""
    grado_num = None
    sec_letra = None
    tipo_escala = "numerica"

    for r in range(1, min(12, ws.max_row + 1)):
        for c in range(1, min(6, ws.max_column + 1)):
            txt = _limpiar_str(ws.cell(r, c).value).upper()
            if not txt:
                continue
            if "AÑO" in txt or "GRADO" in txt or "SECCIÓN" in txt or "SECCION" in txt:
                if "GRADO" in txt and "AÑO" not in txt:
                    tipo_escala = "literal"
                mg = re.search(r"([1-6])\s*(?:ER|ERO|DO|DA|RO|TO|VO|MO|º|°)?", txt)
                if mg:
                    grado_num = int(mg.group(1))
                ms = re.search(r"SECCI[OÓ]N\s*[:\-]?\s*[\"']?([A-Z])[\"']?", txt)
                if ms:
                    sec_letra = ms.group(1)
                if grado_num and sec_letra:
                    return grado_num, sec_letra, tipo_escala

    t = sheet_title.strip().upper()
    if "GRADO" in t:
        tipo_escala = "literal"
    mt = re.match(r"^([1-6])\s*(?:ER|ERO|DO|RO|TO|AMG|BMG|CMT|DMT)?\s*([A-Z])", t)
    if mt:
        return int(mt.group(1)), mt.group(2), tipo_escala
    return grado_num, sec_letra, tipo_escala


def _resolver_o_crear_seccion(
    cur, id_periodo: int, orden_grado: int, letra_sec: str, tipo_escala: str = "numerica"
) -> int | None:
    cur.execute(
        "SELECT s.id FROM secciones s "
        "JOIN grados_anios g ON g.id = s.id_grado_anio "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "WHERE s.id_periodo = %s AND n.tipo_escala = %s AND g.orden = %s AND UPPER(s.nombre) = %s "
        "LIMIT 1",
        (id_periodo, tipo_escala, orden_grado, letra_sec.upper()),
    )
    row = cur.fetchone()
    if row:
        return row["id"]

    cur.execute(
        "SELECT g.id FROM grados_anios g "
        "JOIN niveles_educativos n ON n.id = g.id_nivel "
        "WHERE n.tipo_escala = %s AND g.orden = %s LIMIT 1",
        (tipo_escala, orden_grado),
    )
    g_row = cur.fetchone()
    if not g_row:
        return None
    cur.execute(
        "INSERT INTO secciones (id_periodo, id_grado_anio, nombre, turno, activo) "
        "VALUES (%s, %s, %s, 'Mañana', TRUE)",
        (id_periodo, g_row["id"], letra_sec.upper()),
    )
    return cur.lastrowid


def _encontrar_columnas_hoja(ws) -> dict | None:
    """Localiza la fila de cabecera y los indices de columnas (1-based) de una hoja de nomina."""
    for r in range(1, min(25, ws.max_row + 1)):
        mapa = {}
        for c in range(1, min(30, ws.max_column + 1)):
            val = _limpiar_str(ws.cell(r, c).value).upper()
            if not val:
                continue
            if "CEDULA" in val or "CÉDULA" in val:
                mapa["cedula"] = c
            elif "APELLIDO" in val:
                mapa["apellidos"] = c
            elif "NOMBRE" in val:
                mapa["nombres"] = c
            elif "LUGAR" in val and "NAC" in val:
                mapa["lugar_nacimiento"] = c
            elif val in ("SEXO", "GENERO", "GÉNERO"):
                mapa["sexo"] = c
            elif "FECHA" in val and "NAC" in val:
                mapa["fecha_nac"] = c
            elif "OBSERV" in val:
                mapa["observaciones"] = c
        if "apellidos" in mapa and "nombres" in mapa:
            # Buscar subfila DIA / MES / AÑO y OBSERVACIONES en las siguientes 3 filas
            inicio_datos = r + 1
            for r_sub in range(r + 1, min(r + 5, ws.max_row + 1)):
                for c in range(1, min(30, ws.max_column + 1)):
                    v_sub = _limpiar_str(ws.cell(r_sub, c).value).upper()
                    if v_sub in ("DIA", "DÍA"):
                        mapa["dia"] = c
                        inicio_datos = max(inicio_datos, r_sub + 1)
                    elif v_sub == "MES":
                        mapa["mes"] = c
                        inicio_datos = max(inicio_datos, r_sub + 1)
                    elif v_sub in ("AÑO", "ANO"):
                        mapa["anio"] = c
                        inicio_datos = max(inicio_datos, r_sub + 1)
                    elif "OBSERV" in v_sub and "observaciones" not in mapa:
                        mapa["observaciones"] = c
                        inicio_datos = max(inicio_datos, r_sub + 1)
            mapa["inicio_datos"] = inicio_datos
            return mapa
    return None


def importar_nomina_excel(archivo_stream, id_periodo: int, id_seccion_fija: int = None) -> dict:
    """Importa estudiantes desde un archivo .xlsx (una o varias hojas de seccion)."""
    verificar_periodo_editable(id_periodo)
    wb = load_workbook(archivo_stream, data_only=True)

    procesados = 0
    sin_cedula_gen = 0
    omitidos = 0
    secciones_usadas = []
    advertencias = []
    cedulas_archivo = {}

    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                cols = _encontrar_columnas_hoja(ws)
                if not cols:
                    if ws.max_row and ws.max_row > 5:
                        advertencias.append(f"Hoja '{sheet_name}' omitida: sin cabecera de nómina.")
                    continue

                id_sec = id_seccion_fija
                if not id_sec:
                    orden_g, letra_s, tipo_escala = _detectar_grado_y_seccion(ws, sheet_name)
                    if orden_g and letra_s:
                        id_sec = _resolver_o_crear_seccion(cur, id_periodo, orden_g, letra_s, tipo_escala)
                if not id_sec:
                    advertencias.append(f"Hoja '{sheet_name}' omitida: no se detectó grado/sección.")
                    continue
                if sheet_name not in secciones_usadas:
                    secciones_usadas.append(sheet_name)

                for r in range(cols["inicio_datos"], ws.max_row + 1):
                    apellidos = _limpiar_str(ws.cell(r, cols["apellidos"]).value)
                    nombres = _limpiar_str(ws.cell(r, cols["nombres"]).value)
                    if not apellidos or not nombres:
                        continue
                    if apellidos.upper() in ("APELLIDOS", "TOTAL") or nombres.upper() == "NOMBRES":
                        continue

                    ci_raw = _limpiar_str(ws.cell(r, cols["cedula"]).value) if "cedula" in cols else ""
                    ci_clean = ci_raw.replace(",", "")
                    try:
                        cedula = normalizar_y_validar_cedula(
                            ci_clean, "cédula", max_digitos=12, permitir_sin_cedula=True
                        )
                    except ValueError:
                        omitidos += 1
                        advertencias.append(f"Hoja '{sheet_name}' fila {r}: cédula inválida ('{ci_raw}').")
                        continue

                    lugar_nac = (
                        validar_lugar_nacimiento_opcional(ws.cell(r, cols["lugar_nacimiento"]).value)
                        if "lugar_nacimiento" in cols
                        else ""
                    )
                    sexo = _mapear_sexo(ws.cell(r, cols["sexo"]).value) if "sexo" in cols else "M"

                    if "dia" in cols and "mes" in cols and "anio" in cols:
                        fnac = _parsear_fecha_celdas(
                            ws.cell(r, cols["dia"]).value,
                            ws.cell(r, cols["mes"]).value,
                            ws.cell(r, cols["anio"]).value,
                        )
                    elif "fecha_nac" in cols:
                        fnac = _parsear_fecha_celdas(None, None, None, ws.cell(r, cols["fecha_nac"]).value)
                    else:
                        fnac = None

                    obs_raw = _limpiar_str(ws.cell(r, cols["observaciones"]).value) if "observaciones" in cols else ""
                    if not obs_raw:
                        # Algunas hojas colocan la observacion en columnas extra (ej. col S=19) aunque K esté vacía
                        for col_extra in range(11, min(ws.max_column + 1, 22)):
                            v_ex = _limpiar_str(ws.cell(r, col_extra).value)
                            if v_ex and not v_ex.isdigit():
                                obs_raw = v_ex
                                break
                    condicion, observaciones = _mapear_condicion_y_obs(obs_raw)

                    clave_nom = f"{apellidos.upper()}|{nombres.upper()}"
                    est = None
                    if cedula == "__GENERAR__":
                        # Evitar duplicados si el estudiante sin cedula ya fue importado previamente
                        if fnac:
                            cur.execute(
                                "SELECT id, cedula, nombres, apellidos FROM estudiantes "
                                "WHERE UPPER(apellidos) = %s AND UPPER(nombres) = %s AND fecha_nacimiento = %s LIMIT 1",
                                (apellidos.upper(), nombres.upper(), fnac),
                            )
                        else:
                            cur.execute(
                                "SELECT id, cedula, nombres, apellidos FROM estudiantes "
                                "WHERE UPPER(apellidos) = %s AND UPPER(nombres) = %s LIMIT 1",
                                (apellidos.upper(), nombres.upper()),
                            )
                        est = cur.fetchone()
                        if est:
                            cedula = est["cedula"]
                        else:
                            cedula = generar_cedula_provisional(cur)
                            sin_cedula_gen += 1
                    else:
                        if cedula in cedulas_archivo and cedulas_archivo[cedula] != clave_nom:
                            omitidos += 1
                            advertencias.append(
                                f"Hoja '{sheet_name}' fila {r}: cédula {cedula} repetida para distinto estudiante."
                            )
                            continue
                        cur.execute("SELECT id, nombres, apellidos FROM estudiantes WHERE cedula = %s", (cedula,))
                        est = cur.fetchone()
                        if est:
                            nom_bd = f"{_limpiar_str(est['apellidos']).upper()}|{_limpiar_str(est['nombres']).upper()}"
                            if nom_bd != clave_nom:
                                omitidos += 1
                                advertencias.append(
                                    f"Hoja '{sheet_name}' fila {r}: cédula {cedula} ya pertenece a "
                                    f"{est['apellidos']} {est['nombres']}."
                                )
                                continue

                    cedulas_archivo[cedula] = clave_nom
                    if est:
                        id_est = est["id"]
                        cur.execute(
                            "UPDATE estudiantes SET nombres=%s, apellidos=%s, genero=%s, "
                            "fecha_nacimiento=COALESCE(%s, fecha_nacimiento), "
                            "lugar_nacimiento=COALESCE(NULLIF(%s, ''), lugar_nacimiento), "
                            "egresado=FALSE, activo=TRUE WHERE id=%s",
                            (nombres, apellidos, sexo, fnac, lugar_nac, id_est),
                        )
                    else:
                        cur.execute(
                            "INSERT INTO estudiantes (cedula, nombres, apellidos, genero, fecha_nacimiento, lugar_nacimiento, egresado, activo) "
                            "VALUES (%s, %s, %s, %s, %s, %s, FALSE, TRUE)",
                            (cedula, nombres, apellidos, sexo, fnac, lugar_nac),
                        )
                        id_est = cur.lastrowid

                    cur.execute(
                        "INSERT INTO inscripciones (id_periodo, id_estudiante, id_seccion, estado, condicion, observaciones) "
                        "VALUES (%s, %s, %s, 'activo', %s, %s) "
                        "ON DUPLICATE KEY UPDATE id_seccion = VALUES(id_seccion), estado = 'activo', "
                        "condicion = VALUES(condicion), observaciones = VALUES(observaciones)",
                        (id_periodo, id_est, id_sec, condicion, observaciones),
                    )
                    procesados += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        wb.close()
        conn.close()

    return {
        "procesados": procesados,
        "sin_cedula": sin_cedula_gen,
        "omitidos": omitidos,
        "secciones": secciones_usadas,
        "advertencias": advertencias,
    }
