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


def exportar_nomina_estudiantes(inscripciones: list, plantel: str, periodo: str) -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Nómina Estudiantes"
    cols = [
        "#", "Cédula", "Apellidos", "Nombres", "Nivel", "Grado/Año",
        "Sección", "C.I. Representante", "Representante", "Teléfono Rep.", "Dirección"
    ]
    row = _escribir_encabezado(ws, plantel, f"Nómina de Estudiantes — Período {periodo}", cols)
    for i, est in enumerate(inscripciones, start=1):
        rep_nombre = f"{est.get('rep_apellidos') or ''} {est.get('rep_nombres') or ''}".strip()
        valores = [
            i,
            est["cedula"],
            est["apellidos"],
            est["nombres"],
            est.get("nivel_nombre") or ("Egresado" if est.get("egresado") else "Sin matrícula"),
            est.get("grado_nombre") or est.get("ultimo_grado_nombre") or "-",
            est.get("seccion_nombre") or est.get("ultima_seccion_nombre") or "-",
            est.get("rep_cedula") or "",
            rep_nombre,
            est.get("rep_telefono") or "",
            est.get("direccion") or "",
        ]
        for c, v in enumerate(valores, start=1):
            cell = ws.cell(row=row, column=c, value=v)
            cell.border = THIN_BORDER
        row += 1
    return _finalizar_wb(wb)


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
