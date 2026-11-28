from datetime import date
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

HEADER_FILL = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
HEADER_FONT = Font(color="FFFFFF", bold=True, size=10)
TITLE_FONT = Font(color="0F172A", bold=True, size=12)
THIN_BORDER = Border(
    left=Side(style="thin", color="CBD5E1"),
    right=Side(style="thin", color="CBD5E1"),
    top=Side(style="thin", color="CBD5E1"),
    bottom=Side(style="thin", color="CBD5E1"),
)


def _autoajustar_columnas(ws):
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            val = str(cell.value or "")
            if len(val) > max_len:
                max_len = len(val)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 42)


def _escribir_encabezado(ws, titulo: str, subtitulo: str, columnas: list):
    ws["A1"] = titulo
    ws["A1"].font = TITLE_FONT
    ws["A2"] = subtitulo
    ws["A2"].font = Font(color="475569", size=10)
    fila_header = 4
    for idx, nombre_col in enumerate(columnas, start=1):
        celda = ws.cell(row=fila_header, column=idx, value=nombre_col)
        celda.fill = HEADER_FILL
        celda.font = HEADER_FONT
        celda.alignment = Alignment(horizontal="center", vertical="center")
        celda.border = THIN_BORDER
    return fila_header + 1


def _finalizar_wb(wb: Workbook) -> BytesIO:
    _autoajustar_columnas(wb.active)
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def _fmt_nota_excel(val):
    if val is None:
        return "-"
    num = float(val)
    return int(num) if num.is_integer() else round(num, 1)


def _calcular_edad(fecha_nac) -> int | None:
    if not fecha_nac:
        return None
    if isinstance(fecha_nac, str):
        try:
            fecha_nac = date.fromisoformat(fecha_nac[:10])
        except ValueError:
            return None
    hoy = date.today()
    return hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))


def exportar_nomina_estudiantes(inscripciones: list, plantel: str, periodo: str) -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Nómina Estudiantes"
    cols = [
        "#", "Cédula", "Apellidos", "Nombres", "Sexo", "Edad", "Fecha Nac.", "Lugar de Nacimiento",
        "Nivel", "Grado/Año", "Sección", "Condición", "Observaciones",
        "C.I. Representante", "Representante", "Teléfono Rep.", "Dirección"
    ]
    row = _escribir_encabezado(ws, plantel, f"Nómina de Estudiantes — Período {periodo}", cols)
    for i, est in enumerate(inscripciones, start=1):
        rep_nombre = f"{est.get('rep_apellidos') or ''} {est.get('rep_nombres') or ''}".strip()
        fnac = est.get("fecha_nacimiento")
        fnac_str = fnac.strftime("%d/%m/%Y") if hasattr(fnac, "strftime") else (str(fnac)[:10] if fnac else "")
        edad = _calcular_edad(fnac)
        valores = [
            i,
            est["cedula"],
            est["apellidos"],
            est["nombres"],
            est.get("genero") or "",
            edad if edad is not None else "",
            fnac_str,
            est.get("lugar_nacimiento") or "",
            est.get("nivel_nombre") or ("Egresado" if est.get("egresado") else "Sin matrícula"),
            est.get("grado_nombre") or est.get("ultimo_grado_nombre") or "-",
            est.get("seccion_nombre") or est.get("ultima_seccion_nombre") or "-",
            (est.get("condicion") or "regular").replace("_", " ").title(),
            est.get("observaciones") or "",
            est.get("rep_cedula") or "",
            rep_nombre,
            est.get("rep_telefono") or "",
            est.get("direccion") or "",
        ]
        for c, v in enumerate(valores, start=1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.border = THIN_BORDER
            if c in (1, 5, 6, 7):
                cell.alignment = Alignment(horizontal="center")
        row += 1
    return _finalizar_wb(wb)


def _formatear_observacion_matricula(condicion: str, observaciones: str) -> str:
    """Combina condicion y observaciones sin duplicar cuando la observacion ya expresa la condicion."""
    cond = (condicion or "regular").strip()
    obs = str(observaciones or "").strip()
    if cond == "regular":
        return obs
    if not obs:
        return cond.replace("_", " ").upper()
    u = obs.upper()
    redundante = (
        (cond == "repitiente" and any(k in u for k in ("REP", "REPITE", "REPITIENTE")))
        or (cond == "materia_pendiente" and (u in ("MP", "PEN", "P") or "PENDIENTE" in u))
        or (cond == "nuevo_ingreso" and "NUEV" in u)
        or (cond == "reingreso" and "REINGRESO" in u)
    )
    if redundante:
        return obs
    return f"{cond.replace('_', ' ').upper()} — {obs}"


def _poblar_hoja_matricula_inicial(
    ws,
    seccion_info: dict,
    estudiantes: list,
    cfg: dict,
    periodo: str,
):
    """Llena una hoja de calculo con el formato oficial de Matricula Inicial MPPE."""
    bold_10 = Font(bold=True, size=10)
    bold_11 = Font(bold=True, size=11)
    norm_10 = Font(size=10)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_mid = Alignment(horizontal="left", vertical="center")

    plantel = cfg.get("nombre_plantel", 'Escuela Básica Nacional "Los Laureles"')
    pais = cfg.get("encabezado_pais", "REPÚBLICA BOLIVARIANA DE VENEZUELA")
    ministerio = cfg.get("encabezado_ministerio", "MINISTERIO DEL PODER POPULAR PARA LA EDUCACIÓN")
    guia = seccion_info.get("docente_guia_nombre") or "Sin asignar"
    etiqueta_guia = "DOCENTE TITULAR" if seccion_info.get("tipo_escala") == "literal" else "PROFESOR GUÍA"

    ws["B1"] = pais
    ws["B1"].font = bold_10
    ws["B2"] = ministerio
    ws["B2"].font = bold_10
    ws["B3"] = plantel.upper()
    ws["B3"].font = bold_11
    ws["B4"] = "MATRÍCULA INICIAL"
    ws["B4"].font = bold_11
    ws["B5"] = f"{etiqueta_guia}: {guia.upper()}"
    ws["B5"].font = bold_10
    ws["B6"] = f"GRADO / AÑO: {seccion_info.get('grado_nombre', '').upper()}    SECCIÓN: \"{seccion_info.get('nombre', '')}\""
    ws["B6"].font = bold_10

    ws["H1"] = f"AÑO ESCOLAR {periodo}"
    ws["H1"].font = bold_11
    ws["H3"] = "DATOS DE LOS ESTUDIANTES POR EDAD Y SEXO"
    ws["H3"].font = bold_10

    # Calcular estadistica por edad y sexo (H = Femenino, V = Masculino)
    edades_set = set()
    conteo_h = {}
    conteo_v = {}
    total_h = 0
    total_v = 0
    filas_prep = []
    for est in estudiantes:
        fnac = est.get("fecha_nacimiento")
        if isinstance(fnac, str):
            try:
                fnac = date.fromisoformat(fnac[:10])
            except ValueError:
                fnac = None
        edad = _calcular_edad(fnac)
        sexo = (est.get("genero") or "M").upper()
        if sexo == "F":
            total_h += 1
        else:
            total_v += 1
        if edad is not None:
            edades_set.add(edad)
            if sexo == "F":
                conteo_h[edad] = conteo_h.get(edad, 0) + 1
            else:
                conteo_v[edad] = conteo_v.get(edad, 0) + 1
        filas_prep.append((est, fnac, edad, sexo))

    edades_ord = sorted(edades_set)
    # Cuadro resumen en columnas K.. (fila 3: EDAD, fila 4 a 7: SEXO/edades/H/V/TOTAL)
    ws.cell(row=4, column=11, value="SEXO").font = bold_10
    ws.cell(row=5, column=11, value="H").font = bold_10
    ws.cell(row=6, column=11, value="V").font = bold_10
    ws.cell(row=7, column=11, value="TOTAL").font = bold_10
    for r_stat in (4, 5, 6, 7):
        ws.cell(row=r_stat, column=11).border = THIN_BORDER
        ws.cell(row=r_stat, column=11).alignment = center

    if edades_ord:
        fin_ed_col = 11 + len(edades_ord)
        if fin_ed_col > 12:
            ws.merge_cells(start_row=3, start_column=12, end_row=3, end_column=fin_ed_col)
        c_ed_lbl = ws.cell(row=3, column=12, value="EDAD")
        c_ed_lbl.font = bold_10
        c_ed_lbl.alignment = center

    col_idx = 12
    for ed in edades_ord:
        ch = conteo_h.get(ed, 0)
        cv = conteo_v.get(ed, 0)
        for r_stat, val in ((4, ed), (5, ch), (6, cv), (7, ch + cv)):
            c = ws.cell(row=r_stat, column=col_idx, value=val)
            c.font = bold_10 if r_stat in (4, 7) else norm_10
            c.border = THIN_BORDER
            c.alignment = center
        col_idx += 1

    # Columna total general del cuadro estadistico
    for r_stat, val in ((4, "TOTAL"), (5, total_h), (6, total_v), (7, total_h + total_v)):
        c = ws.cell(row=r_stat, column=col_idx, value=val)
        c.font = bold_10
        c.border = THIN_BORDER
        c.alignment = center

    # Cabecera de tabla principal (filas 9-10)
    ws.merge_cells("H9:J9")
    headers_sup = {
        1: "N°",
        2: "CÉDULA DE IDENTIDAD",
        3: "APELLIDOS",
        4: "NOMBRES",
        5: "LUGAR DE NACIMIENTO",
        6: "ED",
        7: "SEXO",
        8: "FECHA DE NACIMIENTO",
        11: "OBSERVACIONES",
    }
    for col_i, txt in headers_sup.items():
        cell = ws.cell(row=9, column=col_i, value=txt)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = center
        cell.border = THIN_BORDER
    for col_i in (9, 10):
        cell = ws.cell(row=9, column=col_i)
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER

    for col_i in range(1, 12):
        sub_txt = {8: "DÍA", 9: "MES", 10: "AÑO"}.get(col_i, "")
        cell = ws.cell(row=10, column=col_i, value=sub_txt)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = center
        cell.border = THIN_BORDER

    for col_i in (1, 2, 3, 4, 5, 6, 7, 11):
        ws.merge_cells(start_row=9, start_column=col_i, end_row=10, end_column=col_i)

    r_actual = 11
    for idx_est, (est, fnac, edad, sexo) in enumerate(filas_prep, start=1):
        obs_txt = _formatear_observacion_matricula(est.get("condicion"), est.get("observaciones"))
        vals = [
            idx_est,
            est["cedula"],
            (est["apellidos"] or "").upper(),
            (est["nombres"] or "").upper(),
            (est.get("lugar_nacimiento") or "").upper(),
            edad if edad is not None else "",
            sexo,
            f"{fnac.day:02d}" if fnac else "",
            f"{fnac.month:02d}" if fnac else "",
            str(fnac.year) if fnac else "",
            obs_txt,
        ]
        for c_i, val in enumerate(vals, start=1):
            cell = ws.cell(row=r_actual, column=c_i, value=val)
            cell.border = THIN_BORDER
            cell.font = norm_10
            cell.alignment = center if c_i in (1, 6, 7, 8, 9, 10) else left_mid
        r_actual += 1

    anchos = {
        "A": 5, "B": 16, "C": 26, "D": 26, "E": 20,
        "F": 6, "G": 7, "H": 6, "I": 6, "J": 8, "K": 26,
    }
    for col_let, w in anchos.items():
        ws.column_dimensions[col_let].width = w
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0


def exportar_matricula_inicial(
    seccion_info: dict,
    estudiantes: list,
    cfg: dict,
    periodo: str,
) -> BytesIO:
    """Exporta la Matricula Inicial oficial por seccion con resumen por edad y sexo (formato MPPE)."""
    wb = Workbook()
    ws = wb.active
    ws.title = f"{seccion_info.get('grado_nombre', 'Sec')[:20]} {seccion_info.get('nombre', '')}".strip()[:31]
    _poblar_hoja_matricula_inicial(ws, seccion_info, estudiantes, cfg, periodo)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def exportar_matricula_inicial_multiple(
    secciones_estudiantes: list[tuple[dict, list]],
    cfg: dict,
    periodo: str,
) -> BytesIO:
    """Exporta la Matricula Inicial oficial en un libro multi-hoja (una hoja por seccion)."""
    wb = Workbook()
    primera = True
    usados = set()
    for seccion_info, estudiantes in secciones_estudiantes:
        base_title = f"{seccion_info.get('grado_nombre', 'Sec')[:20]} {seccion_info.get('nombre', '')}".strip()[:31] or "Seccion"
        title = base_title
        idx_dup = 2
        while title in usados:
            suf = f" ({idx_dup})"
            title = base_title[: 31 - len(suf)] + suf
            idx_dup += 1
        usados.add(title)

        ws = wb.active if primera else wb.create_sheet()
        primera = False
        ws.title = title
        _poblar_hoja_matricula_inicial(ws, seccion_info, estudiantes, cfg, periodo)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def exportar_sabana_primaria(seccion_info: dict, filas: list, plantel: str) -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen Primaria"
    cols = ["#", "Cédula", "Apellidos y Nombres", "Lapso 1", "Lapso 2", "Lapso 3", "Definitiva", "Observaciones"]
    sub = f"{seccion_info['grado_nombre']} Sección {seccion_info['nombre']} — Educación Primaria"
    row = _escribir_encabezado(ws, plantel, sub, cols)
    for i, f in enumerate(filas, start=1):
        vals = [
            i,
            f["cedula"],
            f"{f['apellidos']} {f['nombres']}",
            f.get("lapso_1") or "-",
            f.get("lapso_2") or "-",
            f.get("lapso_3") or "-",
            f.get("definitiva") or "-",
            f.get("observaciones") or "",
        ]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.border = THIN_BORDER
            if 4 <= c <= 7:
                cell.alignment = Alignment(horizontal="center")
        row += 1
    return _finalizar_wb(wb)


def exportar_planilla_materia(seccion_info: dict, materia_nombre: str, filas: list, plantel: str) -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Notas por Materia"
    cols = ["#", "Cédula", "Apellidos y Nombres", "Lapso 1", "Lapso 2", "Lapso 3", "Definitiva", "T.E.", "Mes", "Año"]
    sub = f"{seccion_info['grado_nombre']} Sección {seccion_info['nombre']} — Materia: {materia_nombre}"
    row = _escribir_encabezado(ws, plantel, sub, cols)
    for i, f in enumerate(filas, start=1):
        vals = [
            i,
            f["cedula"],
            f"{f['apellidos']} {f['nombres']}",
            _fmt_nota_excel(f.get("lapso_1")),
            _fmt_nota_excel(f.get("lapso_2")),
            _fmt_nota_excel(f.get("lapso_3")),
            _fmt_nota_excel(f.get("definitiva")),
            f.get("tipo_evaluacion") or "-",
            f.get("mes") or "-",
            f.get("anio") or "-",
        ]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.border = THIN_BORDER
            if c >= 4:
                cell.alignment = Alignment(horizontal="center")
        row += 1
    return _finalizar_wb(wb)


def exportar_sabana_secundaria(
    seccion_info: dict,
    materias: list,
    sabana: list,
    plantel: str,
    periodo: str,
    lapso: str = "final",
) -> BytesIO:
    """Exporta la sabana completa de Media General (todas las materias en una hoja)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen Media General"
    etiquetas_lapso = {
        "1": "1.er Lapso",
        "2": "2.do Lapso",
        "3": "3.er Lapso",
        "final": "Definitiva Final",
    }
    lbl_lap = etiquetas_lapso.get(lapso, "Definitiva Final")
    cols = ["#", "Cédula", "Apellidos y Nombres"] + [m.get("codigo") or m["nombre"] for m in materias] + [f"Prom. ({lbl_lap})", "Def. Acumulado"]
    sub = f"{seccion_info['grado_nombre']} Sección \"{seccion_info['nombre']}\" — Período {periodo} ({lbl_lap})"
    row = _escribir_encabezado(ws, plantel, sub, cols)

    campo_nota = {"1": "lapso_1", "2": "lapso_2", "3": "lapso_3"}.get(lapso, "definitiva")
    campo_prom = {"1": "prom_l1", "2": "prom_l2", "3": "prom_l3"}.get(lapso, "prom_final")

    for i, est in enumerate(sabana, start=1):
        vals = [i, est["cedula"], f"{est['apellidos']} {est['nombres']}"]
        for m in materias:
            nm = (est.get("notas") or {}).get(m["id"])
            vals.append(_fmt_nota_excel(nm.get(campo_nota) if nm else None))
        vals.append(est.get(campo_prom, "-"))
        vals.append(est.get("prom_acumulado", "-"))
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.border = THIN_BORDER
            if c == 1 or c >= 4:
                cell.alignment = Alignment(horizontal="center")
        row += 1

    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    return _finalizar_wb(wb)


def exportar_lista_asistencia(
    seccion_info: dict,
    estudiantes: list,
    plantel: str,
    periodo: str,
    mes_label: str = "",
) -> BytesIO:
    """Exporta la lista de asistencia / control en blanco por seccion con 20 dias habiles."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Lista de Asistencia"
    dias_cols = [str(d) for d in range(1, 21)]
    cols = ["#", "Cédula", "Apellidos y Nombres"] + dias_cols + ["Inasist."]
    extra_mes = f" · Mes: {mes_label}" if mes_label else " · Mes: ________________"
    guia = seccion_info.get("docente_guia_nombre") or "Sin asignar"
    sub = (
        f"Control de Asistencia — {seccion_info['grado_nombre']} Sección \"{seccion_info['nombre']}\" "
        f"({seccion_info.get('turno', '')}) · Período {periodo} · Docente: {guia}{extra_mes}"
    )
    row = _escribir_encabezado(ws, plantel, sub, cols)

    for i, est in enumerate(estudiantes, start=1):
        vals = [i, est["cedula"], f"{est['apellidos']} {est['nombres']}"] + [""] * 20 + [""]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.border = THIN_BORDER
            if c == 1 or c >= 4:
                cell.alignment = Alignment(horizontal="center")
        row += 1

    _autoajustar_columnas(ws)
    ws.column_dimensions["A"].width = 5
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 34
    for idx_col in range(4, 24):
        col_letter = ws.cell(row=4, column=idx_col).column_letter
        ws.column_dimensions[col_letter].width = 4.2
    ws.column_dimensions[ws.cell(row=4, column=24).column_letter].width = 10
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
