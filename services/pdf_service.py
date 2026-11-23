from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from services.calificacion_service import numero_a_letras

MESES_ES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _esc(val) -> str:
    return escape(str(val or ""))


def _construir_elementos_certificado(detalle: dict, boletin: dict, cfg: dict, styles) -> list:
    st_center_bold = ParagraphStyle(
        "center_bold", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=9, leading=11
    )
    st_center_sm = ParagraphStyle(
        "center_sm", parent=styles["Normal"], alignment=TA_CENTER, fontSize=8, leading=10
    )
    st_title = ParagraphStyle(
        "title_doc", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=11, spaceBefore=6, spaceAfter=8
    )
    st_cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10, alignment=TA_LEFT)
    st_cell_c = ParagraphStyle("cell_c", parent=styles["Normal"], fontSize=8, leading=10, alignment=TA_CENTER)

    elementos = [
        Paragraph(_esc(cfg.get("encabezado_pais", "REPÚBLICA BOLIVARIANA DE VENEZUELA")), st_center_bold),
        Paragraph(_esc(cfg.get("encabezado_ministerio", "MINISTERIO DEL PODER POPULAR PARA LA EDUCACIÓN")), st_center_bold),
        Paragraph(_esc(cfg.get("nombre_plantel", 'Escuela Básica Nacional "Los Laureles"')), st_center_bold),
        Paragraph(
            f"RIF: {_esc(cfg.get('rif', ''))} | Código DEA: {_esc(cfg.get('codigo_dea', ''))} | "
            f"Código Estadístico: {_esc(cfg.get('codigo_estadistico', ''))}",
            st_center_sm,
        ),
        Paragraph(_esc(cfg.get("direccion", "")), st_center_sm),
    ]

    es_primaria = detalle["tipo_escala"] == "literal"
    titulo = (
        "BOLETÍN DE CALIFICACIONES — EDUCACIÓN PRIMARIA"
        if es_primaria
        else "CERTIFICACIÓN DE CALIFICACIONES — EDUCACIÓN MEDIA GENERAL"
    )
    elementos.append(Paragraph(titulo, st_title))

    guia_label = "Docente Titular" if es_primaria else "Profesor Guía"
    datos_est = [
        [
            Paragraph(f"<b>Apellidos y Nombres:</b> {_esc(detalle['apellidos'])} {_esc(detalle['nombres'])}", st_cell),
            Paragraph(f"<b>Cédula:</b> {_esc(detalle['cedula'])}", st_cell),
        ],
        [
            Paragraph(f"<b>Nivel / Grado:</b> {_esc(detalle['nivel_nombre'])} — {_esc(detalle['grado_nombre'])} ({_esc(detalle['seccion_nombre'])})", st_cell),
            Paragraph(f"<b>Período Escolar:</b> {_esc(detalle['periodo_nombre'])}", st_cell),
        ],
        [
            Paragraph(f"<b>{guia_label}:</b> {_esc(detalle.get('docente_guia_nombre') or 'No asignado')}", st_cell),
            Paragraph(f"<b>Título / Mención:</b> {_esc(detalle.get('titulo_otorga') or cfg.get('titulo_media', ''))}", st_cell),
        ],
    ]
    tabla_est = Table(datos_est, colWidths=[11.5 * cm, 7 * cm])
    tabla_est.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("PADDING", (0, 0), (-1, -1), 4),
        ])
    )
    elementos.extend([tabla_est, Spacer(1, 8)])

    if es_primaria:
        np = boletin.get("primaria") or {}
        data_notas = [
            [
                Paragraph("<b>LAPSO 1</b>", st_cell_c),
                Paragraph("<b>LAPSO 2</b>", st_cell_c),
                Paragraph("<b>LAPSO 3</b>", st_cell_c),
                Paragraph("<b>DEFINITIVA LITERAL</b>", st_cell_c),
            ],
            [
                Paragraph(_esc(np.get("lapso_1") or "-"), st_cell_c),
                Paragraph(_esc(np.get("lapso_2") or "-"), st_cell_c),
                Paragraph(_esc(np.get("lapso_3") or "-"), st_cell_c),
                Paragraph(f"<b>{_esc(np.get('definitiva') or '-')}</b>", st_cell_c),
            ],
        ]
        t_notas = Table(data_notas, colWidths=[4.2 * cm, 4.2 * cm, 4.2 * cm, 5.9 * cm])
        t_notas.setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
                ("PADDING", (0, 0), (-1, -1), 6),
            ])
        )
        elementos.append(t_notas)
        if np.get("observaciones"):
            elementos.extend([Spacer(1, 6), Paragraph(f"<b>Observaciones:</b> {_esc(np['observaciones'])}", st_cell)])
    else:
        filas = [
            [
                Paragraph("<b>ÁREAS DE FORMACIÓN</b>", st_cell_c),
                Paragraph("<b>Nº</b>", st_cell_c),
                Paragraph("<b>LETRAS</b>", st_cell_c),
                Paragraph("<b>T.E.</b>", st_cell_c),
                Paragraph("<b>MES</b>", st_cell_c),
                Paragraph("<b>AÑO</b>", st_cell_c),
            ]
        ]
        bloque_actual = None
        subheaders = []
        for mat in boletin.get("secundaria", []):
            if mat["bloque_nombre"] != bloque_actual:
                bloque_actual = mat["bloque_nombre"]
                subheaders.append(len(filas))
                filas.append([Paragraph(f"<b>{_esc(bloque_actual.upper())}</b>", st_cell), "", "", "", "", ""])
            def_num = mat.get("definitiva")
            def_txt = f"{float(def_num):g}" if def_num is not None else "-"
            filas.append([
                Paragraph(_esc(mat["materia_nombre"]), st_cell),
                Paragraph(def_txt, st_cell_c),
                Paragraph(numero_a_letras(def_num) if def_num is not None else "-", st_cell_c),
                Paragraph(_esc(mat.get("tipo_evaluacion") or cfg.get("te_defecto", "F")), st_cell_c),
                Paragraph(_esc(mat.get("mes") or cfg.get("mes_defecto", "07")), st_cell_c),
                Paragraph(_esc(mat.get("anio") or cfg.get("anio_defecto", "2026")), st_cell_c),
            ])
        t_sec = Table(filas, colWidths=[8.5 * cm, 1.5 * cm, 3.8 * cm, 1.5 * cm, 1.5 * cm, 1.7 * cm])
        ts = [
            ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]
        for sh in subheaders:
            ts.append(("SPAN", (0, sh), (-1, sh)))
            ts.append(("BACKGROUND", (0, sh), (-1, sh), colors.HexColor("#F1F5F9")))
        t_sec.setStyle(TableStyle(ts))
        elementos.append(t_sec)

    elementos.append(Spacer(1, 22))
    firmas = [
        [
            Paragraph(
                f"Para efectos de su Validez Nacional<br/><br/><br/>"
                f"______________________________<br/>"
                f"SELLO DE LA INSTITUCIÓN EDUCATIVA<br/>"
                f"Director(a): {_esc(cfg.get('director', ''))}",
                st_center_sm,
            ),
            Paragraph(
                f"{_esc(cfg.get('centro_calidad', ''))}<br/><br/><br/>"
                f"______________________________<br/>"
                f"SELLO DEL CENTRO DE DESARROLLO DE LA CALIDAD EDUCATIVA ESTATAL",
                st_center_sm,
            ),
        ]
    ]
    t_firmas = Table(firmas, colWidths=[9.2 * cm, 9.3 * cm])
    t_firmas.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, colors.black), ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.black), ("PADDING", (0, 0), (-1, -1), 8)]))
    elementos.extend([t_firmas, Spacer(1, 8), Paragraph(_esc(cfg.get("pie_fiscal", "")), st_center_sm)])
    return elementos


def generar_certificado_pdf(detalle: dict, boletin: dict, cfg: dict) -> BytesIO:
    """Genera el PDF oficial de Certificacion de Calificaciones (Media) o Boletin (Primaria)."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    elementos = _construir_elementos_certificado(detalle, boletin, cfg, styles)
    doc.build(elementos)
    buf.seek(0)
    return buf


def generar_certificados_pdf_lote(items: list, cfg: dict) -> BytesIO:
    """Genera un solo PDF multipagina con los certificados/boletines de varios estudiantes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    elementos = []
    for idx, (detalle, boletin) in enumerate(items):
        if idx > 0:
            elementos.append(PageBreak())
        elementos.extend(_construir_elementos_certificado(detalle, boletin, cfg, styles))
    doc.build(elementos)
    buf.seek(0)
    return buf


def generar_certificado_historial_pdf(datos_hist: dict, cfg: dict) -> BytesIO:
    """Genera PDF oficial de Certificacion de Calificaciones Acumulada (multi-anio / hasta el momento)."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    st_center_bold = ParagraphStyle(
        "h_center_bold", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=9, leading=11
    )
    st_center_sm = ParagraphStyle(
        "h_center_sm", parent=styles["Normal"], alignment=TA_CENTER, fontSize=7.8, leading=10
    )
    st_title = ParagraphStyle(
        "h_title", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=11, spaceBefore=6, spaceAfter=6
    )
    st_cell = ParagraphStyle("h_cell", parent=styles["Normal"], fontSize=7.8, leading=9.8, alignment=TA_LEFT)
    st_cell_c = ParagraphStyle("h_cell_c", parent=styles["Normal"], fontSize=7.8, leading=9.8, alignment=TA_CENTER)
    st_cell_r = ParagraphStyle("h_cell_r", parent=styles["Normal"], fontSize=7.8, leading=9.8, alignment=TA_RIGHT)

    est = datos_hist["estudiante"]
    rep = datos_hist.get("representante") or {}
    historial = datos_hist.get("historial") or []
    rango_texto = datos_hist.get("rango_texto", "Historial Académico")
    fecha_emision = date.today().strftime("%d/%m/%Y")

    elementos = [
        Paragraph(_esc(cfg.get("encabezado_pais", "REPÚBLICA BOLIVARIANA DE VENEZUELA")), st_center_bold),
        Paragraph(_esc(cfg.get("encabezado_ministerio", "MINISTERIO DEL PODER POPULAR PARA LA EDUCACIÓN")), st_center_bold),
        Paragraph(_esc(cfg.get("nombre_plantel", 'Escuela Básica Nacional "Los Laureles"')), st_center_bold),
        Paragraph(
            f"RIF: {_esc(cfg.get('rif', ''))} | Código DEA: {_esc(cfg.get('codigo_dea', ''))} | "
            f"Código Estadístico: {_esc(cfg.get('codigo_estadistico', ''))}",
            st_center_sm,
        ),
        Paragraph(_esc(cfg.get("direccion", "")), st_center_sm),
        Paragraph(f"CERTIFICACIÓN DE CALIFICACIONES ACUMULADA — {_esc(rango_texto.upper())}", st_title),
    ]

    rep_nombre = f"{rep.get('apellidos', '')} {rep.get('nombres', '')}".strip() or "No registrado"
    titulo_otorga = (
        next((h.get("titulo_otorga") for h in reversed(historial) if h.get("titulo_otorga")), None)
        or cfg.get("titulo_media", "")
    )
    datos_est = [
        [
            Paragraph(f"<b>Apellidos y Nombres:</b> {_esc(est['apellidos'])} {_esc(est['nombres'])}", st_cell),
            Paragraph(f"<b>Cédula:</b> {_esc(est['cedula'])}", st_cell),
        ],
        [
            Paragraph(
                f"<b>Fecha de Nacimiento:</b> {_esc(est.get('fecha_nacimiento') or 'No registrada')} · "
                f"<b>Género:</b> {'Femenino' if est.get('genero') == 'F' else 'Masculino'}",
                st_cell,
            ),
            Paragraph(f"<b>Fecha de Emisión:</b> {fecha_emision}", st_cell),
        ],
        [
            Paragraph(f"<b>Representante Legal:</b> {_esc(rep_nombre)} ({_esc(rep.get('cedula') or '-')})", st_cell),
            Paragraph(f"<b>Rango Certificado:</b> {_esc(rango_texto)}", st_cell),
        ],
        [
            Paragraph(f"<b>Mención / Título:</b> {_esc(titulo_otorga)}", st_cell),
            Paragraph(
                f"<b>Años Certificados:</b> {len(historial)} · "
                f"<b>Promedio Acum.:</b> {_esc(datos_hist.get('promedio_acumulado', '-'))}",
                st_cell,
            ),
        ],
    ]
    t_est = Table(datos_est, colWidths=[11.5 * cm, 7 * cm])
    t_est.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("PADDING", (0, 0), (-1, -1), 4),
        ])
    )
    elementos.extend([t_est, Spacer(1, 8)])

    if not historial:
        elementos.append(Paragraph("No se encontraron registros académicos en el rango seleccionado.", st_center_sm))
    else:
        for h in historial:
            enc_anio = (
                f"<b>{_esc(h['grado_nombre'].upper())}</b> — {_esc(h['nivel_nombre'])} · "
                f"Período Escolar {_esc(h['periodo_nombre'])} · Sección \"{_esc(h['seccion_nombre'])}\""
            )
            if h["tipo_escala"] == "literal":
                np = (h.get("boletin") or {}).get("primaria") or {}
                filas_p = [
                    [Paragraph(enc_anio, st_cell), "", "", ""],
                    [
                        Paragraph("<b>LAPSO 1</b>", st_cell_c),
                        Paragraph("<b>LAPSO 2</b>", st_cell_c),
                        Paragraph("<b>LAPSO 3</b>", st_cell_c),
                        Paragraph("<b>DEFINITIVA LITERAL</b>", st_cell_c),
                    ],
                    [
                        Paragraph(_esc(np.get("lapso_1") or "-"), st_cell_c),
                        Paragraph(_esc(np.get("lapso_2") or "-"), st_cell_c),
                        Paragraph(_esc(np.get("lapso_3") or "-"), st_cell_c),
                        Paragraph(f"<b>{_esc(np.get('definitiva') or '-')}</b>", st_cell_c),
                    ],
                ]
                t_p = Table(filas_p, colWidths=[4.2 * cm, 4.2 * cm, 4.2 * cm, 5.9 * cm])
                t_p.setStyle(
                    TableStyle([
                        ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
                        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
                        ("SPAN", (0, 0), (-1, 0)),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#CBD5E1")),
                        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#E2E8F0")),
                        ("PADDING", (0, 0), (-1, -1), 4),
                    ])
                )
                elementos.append(KeepTogether([t_p, Spacer(1, 7)]))
            else:
                filas = [
                    [Paragraph(enc_anio, st_cell), "", "", "", "", ""],
                    [
                        Paragraph("<b>ÁREAS DE FORMACIÓN</b>", st_cell_c),
                        Paragraph("<b>Nº</b>", st_cell_c),
                        Paragraph("<b>LETRAS</b>", st_cell_c),
                        Paragraph("<b>T.E.</b>", st_cell_c),
                        Paragraph("<b>MES</b>", st_cell_c),
                        Paragraph("<b>AÑO</b>", st_cell_c),
                    ],
                ]
                bloque_actual = None
                subheaders = []
                mats = (h.get("boletin") or {}).get("secundaria", [])
                for mat in mats:
                    if mat["bloque_nombre"] != bloque_actual:
                        bloque_actual = mat["bloque_nombre"]
                        subheaders.append(len(filas))
                        filas.append([Paragraph(f"<b>{_esc(bloque_actual.upper())}</b>", st_cell), "", "", "", "", ""])
                    def_num = mat.get("definitiva")
                    def_txt = f"{float(def_num):g}" if def_num is not None else "-"
                    filas.append([
                        Paragraph(_esc(mat["materia_nombre"]), st_cell),
                        Paragraph(def_txt, st_cell_c),
                        Paragraph(numero_a_letras(def_num) if def_num is not None else "-", st_cell_c),
                        Paragraph(_esc(mat.get("tipo_evaluacion") or cfg.get("te_defecto", "F")), st_cell_c),
                        Paragraph(_esc(mat.get("mes") or cfg.get("mes_defecto", "07")), st_cell_c),
                        Paragraph(_esc(mat.get("anio") or cfg.get("anio_defecto", "2026")), st_cell_c),
                    ])
                filas.append([
                    Paragraph(f"<b>PROMEDIO {_esc(h['grado_nombre'].upper())}:</b>", st_cell_r),
                    Paragraph(f"<b>{_esc(h.get('promedio') or '-')}</b>", st_cell_c),
                    "", "", "", "",
                ])
                idx_prom = len(filas) - 1
                t_sec = Table(filas, colWidths=[8.5 * cm, 1.5 * cm, 3.8 * cm, 1.5 * cm, 1.5 * cm, 1.7 * cm])
                ts = [
                    ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
                    ("SPAN", (0, 0), (-1, 0)),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#CBD5E1")),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#E2E8F0")),
                    ("SPAN", (2, idx_prom), (-1, idx_prom)),
                    ("BACKGROUND", (0, idx_prom), (-1, idx_prom), colors.HexColor("#F1F5F9")),
                    ("PADDING", (0, 0), (-1, -1), 3.5),
                ]
                for sh in subheaders:
                    ts.append(("SPAN", (0, sh), (-1, sh)))
                    ts.append(("BACKGROUND", (0, sh), (-1, sh), colors.HexColor("#F8FAFC")))
                t_sec.setStyle(TableStyle(ts))
                elementos.append(KeepTogether([t_sec, Spacer(1, 7)]))

    if datos_hist.get("promedio_acumulado") and datos_hist["promedio_acumulado"] != "-":
        t_res = Table(
            [[
                Paragraph(
                    f"<b>RESUMEN ACUMULADO ({_esc(rango_texto)}):</b> "
                    f"{datos_hist.get('total_materias_evaluadas', 0)} áreas evaluadas",
                    st_cell,
                ),
                Paragraph(f"<b>PROMEDIO GENERAL: {_esc(datos_hist['promedio_acumulado'])} pts</b>", st_cell_r),
            ]],
            colWidths=[11.5 * cm, 7 * cm],
        )
        t_res.setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#E2E8F0")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ])
        )
        elementos.extend([t_res, Spacer(1, 12)])

    firmas = [
        [
            Paragraph(
                f"Para efectos de su Validez Nacional<br/><br/><br/>"
                f"______________________________<br/>"
                f"SELLO DE LA INSTITUCIÓN EDUCATIVA<br/>"
                f"Director(a): {_esc(cfg.get('director', ''))}",
                st_center_sm,
            ),
            Paragraph(
                f"{_esc(cfg.get('centro_calidad', ''))}<br/><br/><br/>"
                f"______________________________<br/>"
                f"SELLO DEL CENTRO DE DESARROLLO DE LA CALIDAD EDUCATIVA ESTATAL",
                st_center_sm,
            ),
        ]
    ]
    t_firmas = Table(firmas, colWidths=[9.2 * cm, 9.3 * cm])
    t_firmas.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.black),
            ("PADDING", (0, 0), (-1, -1), 8),
        ])
    )
    elementos.append(
        KeepTogether([
            Spacer(1, 6),
            t_firmas,
            Spacer(1, 6),
            Paragraph(_esc(cfg.get("pie_fiscal", "")), st_center_sm),
        ])
    )

    doc.build(elementos)
    buf.seek(0)
    return buf


def _encabezado_membrete(cfg: dict, styles) -> list:
    st_cb = ParagraphStyle(
        "m_cb", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=9, leading=11
    )
    st_cs = ParagraphStyle(
        "m_cs", parent=styles["Normal"], alignment=TA_CENTER, fontSize=8, leading=10
    )
    return [
        Paragraph(_esc(cfg.get("encabezado_pais", "REPÚBLICA BOLIVARIANA DE VENEZUELA")), st_cb),
        Paragraph(_esc(cfg.get("encabezado_ministerio", "MINISTERIO DEL PODER POPULAR PARA LA EDUCACIÓN")), st_cb),
        Paragraph(_esc(cfg.get("nombre_plantel", 'Escuela Básica Nacional "Los Laureles"')), st_cb),
        Paragraph(
            f"RIF: {_esc(cfg.get('rif', ''))} | Código DEA: {_esc(cfg.get('codigo_dea', ''))} | "
            f"Código Estadístico: {_esc(cfg.get('codigo_estadistico', ''))}",
            st_cs,
        ),
        Paragraph(_esc(cfg.get("direccion", "")), st_cs),
    ]


def generar_constancia_estudio_pdf(detalle: dict, cfg: dict) -> BytesIO:
    """Genera el PDF oficial de Constancia de Estudio / Inscripcion."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )
    styles = getSampleStyleSheet()
    st_title = ParagraphStyle(
        "c_title", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=13, spaceBefore=20, spaceAfter=18
    )
    st_body = ParagraphStyle(
        "c_body", parent=styles["Normal"], alignment=TA_JUSTIFY, fontSize=11, leading=18, spaceAfter=14
    )
    st_center = ParagraphStyle("c_center", parent=styles["Normal"], alignment=TA_CENTER, fontSize=9.5, leading=13)
    st_footer = ParagraphStyle("c_footer", parent=styles["Normal"], alignment=TA_CENTER, fontSize=8, leading=10)

    hoy = date.today()
    mes_es = MESES_ES.get(hoy.month, "")
    articulo = "la" if detalle.get("genero") == "F" else "el"
    nombre_completo = f"{detalle['apellidos']} {detalle['nombres']}"
    director = cfg.get("director") or "Director(a) del Plantel"
    plantel = cfg.get("nombre_plantel", 'Escuela Básica Nacional "Los Laureles"')
    rep_nombre = f"{detalle.get('rep_apellidos') or ''} {detalle.get('rep_nombres') or ''}".strip()

    elementos = _encabezado_membrete(cfg, styles)
    elementos.append(Paragraph("CONSTANCIA DE ESTUDIO", st_title))

    elementos.append(
        Paragraph(
            f"Quien suscribe, <b>{_esc(director)}</b>, Director(a) de la institución educativa "
            f"<b>{_esc(plantel)}</b>, inscrita en el Ministerio del Poder Popular para la Educación bajo el "
            f"Código DEA <b>{_esc(cfg.get('codigo_dea', ''))}</b> y Código Estadístico <b>{_esc(cfg.get('codigo_estadistico', ''))}</b>, "
            f"hace constar por medio de la presente que {articulo} estudiante:",
            st_body,
        )
    )

    st_est = ParagraphStyle(
        "c_est", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=12, leading=16, spaceBefore=4, spaceAfter=14
    )
    elementos.append(
        Paragraph(
            f"{_esc(nombre_completo.upper())}<br/>"
            f"<font size='10'>Titular de la Cédula de Identidad / Escolar Nº <b>{_esc(detalle['cedula'])}</b></font>",
            st_est,
        )
    )

    rep_texto = (
        f", representado(a) legalmente por <b>{_esc(rep_nombre)}</b> (C.I. {_esc(detalle.get('rep_cedula') or '-')})"
        if rep_nombre
        else ""
    )
    elementos.append(
        Paragraph(
            f"Cursa regularmente el <b>{_esc(detalle['grado_nombre'])}</b>, Sección <b>\"{_esc(detalle['seccion_nombre'])}\"</b>, "
            f"Turno <b>{_esc(detalle.get('turno') or 'Mañana')}</b>, del nivel de <b>{_esc(detalle['nivel_nombre'])}</b>, "
            f"correspondiente al Período Escolar <b>{_esc(detalle['periodo_nombre'])}</b>{rep_texto}.",
            st_body,
        )
    )
    elementos.append(
        Paragraph(
            f"Constancia que se expide a petición de la parte interesada, para los fines legales y administrativos "
            f"pertinentes, a los <b>{hoy.day}</b> días del mes de <b>{mes_es}</b> del año <b>{hoy.year}</b>.",
            st_body,
        )
    )
    elementos.extend([
        Spacer(1, 48),
        Paragraph(
            f"________________________________________<br/>"
            f"<b>{_esc(director)}</b><br/>"
            f"Director(a) — {_esc(cfg.get('nombre_corto', plantel))}<br/>"
            f"<font size='8'>SELLO DE LA INSTITUCIÓN EDUCATIVA</font>",
            st_center,
        ),
        Spacer(1, 24),
        Paragraph(_esc(cfg.get("pie_fiscal", "")), st_footer),
    ])

    doc.build(elementos)
    buf.seek(0)
    return buf


def generar_boletin_lapsos_pdf(detalle: dict, boletin: dict, cfg: dict) -> BytesIO:
    """Genera Boletin Informativo por Lapsos (L1, L2, L3 y Definitiva) para entrega a representantes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    st_title = ParagraphStyle(
        "b_title", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=11, spaceBefore=6, spaceAfter=8
    )
    st_cell = ParagraphStyle("b_cell", parent=styles["Normal"], fontSize=8, leading=10, alignment=TA_LEFT)
    st_cell_c = ParagraphStyle("b_cell_c", parent=styles["Normal"], fontSize=8, leading=10, alignment=TA_CENTER)
    st_cell_r = ParagraphStyle("b_cell_r", parent=styles["Normal"], fontSize=8, leading=10, alignment=TA_RIGHT)
    st_sm = ParagraphStyle("b_sm", parent=styles["Normal"], alignment=TA_CENTER, fontSize=8, leading=10)

    elementos = _encabezado_membrete(cfg, styles)
    elementos.append(Paragraph("BOLETÍN INFORMATIVO DE RENDIMIENTO POR LAPSOS", st_title))

    es_primaria = detalle["tipo_escala"] == "literal"
    guia_label = "Docente Titular" if es_primaria else "Profesor Guía"
    rep_nombre = f"{detalle.get('rep_apellidos') or ''} {detalle.get('rep_nombres') or ''}".strip() or "No registrado"
    datos_est = [
        [
            Paragraph(f"<b>Estudiante:</b> {_esc(detalle['apellidos'])} {_esc(detalle['nombres'])}", st_cell),
            Paragraph(f"<b>Cédula:</b> {_esc(detalle['cedula'])}", st_cell),
        ],
        [
            Paragraph(f"<b>Grado / Sección:</b> {_esc(detalle['grado_nombre'])} \"{_esc(detalle['seccion_nombre'])}\" ({_esc(detalle.get('turno') or '')})", st_cell),
            Paragraph(f"<b>Período Escolar:</b> {_esc(detalle['periodo_nombre'])}", st_cell),
        ],
        [
            Paragraph(f"<b>{guia_label}:</b> {_esc(detalle.get('docente_guia_nombre') or 'No asignado')}", st_cell),
            Paragraph(f"<b>Representante:</b> {_esc(rep_nombre)}", st_cell),
        ],
    ]
    t_est = Table(datos_est, colWidths=[11.5 * cm, 7 * cm])
    t_est.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, colors.black), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black), ("PADDING", (0, 0), (-1, -1), 4)]))
    elementos.extend([t_est, Spacer(1, 8)])

    if es_primaria:
        np = boletin.get("primaria") or {}
        t_prim = Table(
            [
                [Paragraph("<b>1.er LAPSO</b>", st_cell_c), Paragraph("<b>2.do LAPSO</b>", st_cell_c), Paragraph("<b>3.er LAPSO</b>", st_cell_c), Paragraph("<b>DEFINITIVA LITERAL</b>", st_cell_c)],
                [Paragraph(_esc(np.get("lapso_1") or "-"), st_cell_c), Paragraph(_esc(np.get("lapso_2") or "-"), st_cell_c), Paragraph(_esc(np.get("lapso_3") or "-"), st_cell_c), Paragraph(f"<b>{_esc(np.get('definitiva') or '-')}</b>", st_cell_c)],
            ],
            colWidths=[4.2 * cm, 4.2 * cm, 4.2 * cm, 5.9 * cm],
        )
        t_prim.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, colors.black), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")), ("PADDING", (0, 0), (-1, -1), 6)]))
        elementos.append(t_prim)
        if np.get("observaciones"):
            elementos.extend([Spacer(1, 8), Paragraph(f"<b>Observaciones Pedagógicas:</b> {_esc(np['observaciones'])}", st_cell)])
    else:
        filas = [[
            Paragraph("<b>ÁREA DE FORMACIÓN</b>", st_cell),
            Paragraph("<b>L1</b>", st_cell_c),
            Paragraph("<b>L2</b>", st_cell_c),
            Paragraph("<b>L3</b>", st_cell_c),
            Paragraph("<b>DEF.</b>", st_cell_c),
            Paragraph("<b>ESTADO</b>", st_cell_c),
        ]]
        def _fn(v):
            return f"{float(v):g}" if v is not None else "-"
        s_l1, s_l2, s_l3, s_def = [], [], [], []
        for m in boletin.get("secundaria", []):
            l1, l2, l3, df = m.get("lapso_1"), m.get("lapso_2"), m.get("lapso_3"), m.get("definitiva")
            if l1 is not None: s_l1.append(float(l1))
            if l2 is not None: s_l2.append(float(l2))
            if l3 is not None: s_l3.append(float(l3))
            if df is not None: s_def.append(float(df))
            est_txt = ("Aprobado" if float(df) >= 10 else "Aplazado") if df is not None else "En curso"
            filas.append([
                Paragraph(_esc(m["materia_nombre"]), st_cell),
                Paragraph(_fn(l1), st_cell_c),
                Paragraph(_fn(l2), st_cell_c),
                Paragraph(_fn(l3), st_cell_c),
                Paragraph(f"<b>{_fn(df)}</b>", st_cell_c),
                Paragraph(est_txt, st_cell_c),
            ])
        filas.append([
            Paragraph("<b>PROMEDIO DEL ESTUDIANTE:</b>", st_cell_r),
            Paragraph(f"<b>{sum(s_l1)/len(s_l1):.1f}</b>" if s_l1 else "-", st_cell_c),
            Paragraph(f"<b>{sum(s_l2)/len(s_l2):.1f}</b>" if s_l2 else "-", st_cell_c),
            Paragraph(f"<b>{sum(s_l3)/len(s_l3):.1f}</b>" if s_l3 else "-", st_cell_c),
            Paragraph(f"<b>{sum(s_def)/len(s_def):.1f}</b>" if s_def else "-", st_cell_c),
            Paragraph("", st_cell_c),
        ])
        t_sec = Table(filas, colWidths=[9.3 * cm, 1.6 * cm, 1.6 * cm, 1.6 * cm, 1.8 * cm, 2.6 * cm])
        t_sec.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, len(filas) - 1), (-1, len(filas) - 1), colors.HexColor("#F1F5F9")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        elementos.append(t_sec)

    elementos.append(Spacer(1, 28))
    firmas = [[
        Paragraph(f"___________________________<br/><b>{guia_label}</b><br/>{_esc(detalle.get('docente_guia_nombre') or '')}", st_sm),
        Paragraph(f"___________________________<br/><b>Director(a)</b><br/>{_esc(cfg.get('director', ''))}", st_sm),
        Paragraph("___________________________<br/><b>Representante Legal</b><br/>Firma de Recibido", st_sm),
    ]]
    t_f = Table(firmas, colWidths=[6.1 * cm, 6.2 * cm, 6.2 * cm])
    elementos.append(KeepTogether([t_f, Spacer(1, 10), Paragraph(f"Emitido el {date.today().strftime('%d/%m/%Y')}", st_sm)]))
    doc.build(elementos)
    buf.seek(0)
    return buf


def generar_sabana_secundaria_pdf(
    seccion_info: dict,
    materias: list,
    sabana: list,
    cfg: dict,
    periodo: str,
    lapso: str = "final",
) -> BytesIO:
    """Genera PDF horizontal (landscape) con la sabana completa de Media General."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        leftMargin=1.0 * cm,
        rightMargin=1.0 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
    )
    styles = getSampleStyleSheet()
    st_title = ParagraphStyle(
        "s_title", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=10.5, spaceBefore=4, spaceAfter=6
    )
    st_cell = ParagraphStyle("s_cell", parent=styles["Normal"], fontSize=7.2, leading=9, alignment=TA_LEFT)
    st_cell_c = ParagraphStyle("s_cell_c", parent=styles["Normal"], fontSize=7.2, leading=9, alignment=TA_CENTER)

    etiquetas = {"1": "1.er Lapso", "2": "2.do Lapso", "3": "3.er Lapso", "final": "Definitiva Final"}
    lbl_lap = etiquetas.get(lapso, "Definitiva Final")
    campo_nota = {"1": "lapso_1", "2": "lapso_2", "3": "lapso_3"}.get(lapso, "definitiva")
    campo_prom = {"1": "prom_l1", "2": "prom_l2", "3": "prom_l3"}.get(lapso, "prom_final")

    elementos = _encabezado_membrete(cfg, styles)
    elementos.append(
        Paragraph(
            f"CUADRO RESUMEN DE CALIFICACIONES — {_esc(seccion_info['grado_nombre'].upper())} SECCIÓN \"{_esc(seccion_info['nombre'])}\" "
            f"({lbl_lap.upper()}) · PERÍODO {_esc(periodo)}",
            st_title,
        )
    )

    headers = [Paragraph("<b>#</b>", st_cell_c), Paragraph("<b>Cédula</b>", st_cell_c), Paragraph("<b>Apellidos y Nombres</b>", st_cell)]
    for m in materias:
        headers.append(Paragraph(f"<b>{_esc(m.get('codigo') or m['nombre'][:8])}</b>", st_cell_c))
    headers.extend([Paragraph("<b>Prom.</b>", st_cell_c), Paragraph("<b>Acum.</b>", st_cell_c)])

    filas = [headers]
    for i, est in enumerate(sabana, start=1):
        row = [
            Paragraph(str(i), st_cell_c),
            Paragraph(_esc(est["cedula"]), st_cell_c),
            Paragraph(f"{_esc(est['apellidos'])} {_esc(est['nombres'])}", st_cell),
        ]
        for m in materias:
            nm = (est.get("notas") or {}).get(m["id"])
            val = nm.get(campo_nota) if nm else None
            txt = f"{float(val):g}" if val is not None else "-"
            row.append(Paragraph(txt, st_cell_c))
        row.append(Paragraph(f"<b>{_esc(est.get(campo_prom, '-'))}</b>", st_cell_c))
        row.append(Paragraph(f"<b>{_esc(est.get('prom_acumulado', '-'))}</b>", st_cell_c))
        filas.append(row)

    ancho_total = 25.9 * cm
    ancho_fijo = 0.8 * cm + 2.4 * cm + 5.6 * cm + 1.4 * cm + 1.4 * cm
    ancho_mat = max(1.1 * cm, (ancho_total - ancho_fijo) / max(len(materias), 1))
    col_widths = [0.8 * cm, 2.4 * cm, 5.6 * cm] + [ancho_mat] * len(materias) + [1.4 * cm, 1.4 * cm]

    t = Table(filas, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
        ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    elementos.append(t)

    leyenda_mats = " · ".join(f"{m.get('codigo') or m['nombre'][:8]}: {m['nombre']}" for m in materias)
    if leyenda_mats:
        elementos.extend([Spacer(1, 6), Paragraph(f"<b>Leyenda:</b> {_esc(leyenda_mats)}", st_cell)])

    doc.build(elementos)
    buf.seek(0)
    return buf


def generar_horario_pdf(
    titulo: str,
    subtitulo: str,
    bloques_por_dia: dict,
    dias: dict,
    cfg: dict,
    modo: str = "seccion",
) -> BytesIO:
    """Genera PDF horizontal (landscape) del horario semanal de Lunes a Viernes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        leftMargin=1.0 * cm,
        rightMargin=1.0 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
    )
    styles = getSampleStyleSheet()
    st_title = ParagraphStyle(
        "hor_t", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=11, spaceBefore=4, spaceAfter=2
    )
    st_sub = ParagraphStyle("hor_s", parent=styles["Normal"], alignment=TA_CENTER, fontSize=8.5, spaceAfter=8)
    st_hdr = ParagraphStyle("hor_h", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=8.5, textColor=colors.white)
    st_cell = ParagraphStyle("hor_c", parent=styles["Normal"], fontSize=7.8, leading=10, alignment=TA_LEFT)
    st_empty = ParagraphStyle("hor_e", parent=styles["Normal"], fontSize=7.5, alignment=TA_CENTER, textColor=colors.HexColor("#64748B"))

    elementos = _encabezado_membrete(cfg, styles)
    elementos.append(Paragraph(_esc(titulo), st_title))
    elementos.append(Paragraph(_esc(subtitulo), st_sub))

    orden_dias = sorted(dias.keys())
    headers = [Paragraph(_esc(dias[d].upper()), st_hdr) for d in orden_dias]
    max_filas = max((len(bloques_por_dia.get(d, [])) for d in orden_dias), default=0)
    filas = [headers]

    if max_filas == 0:
        filas.append([Paragraph("Sin bloques", st_empty) for _ in orden_dias])
    else:
        for idx in range(max_filas):
            fila = []
            for d in orden_dias:
                lista = bloques_por_dia.get(d, [])
                if idx < len(lista):
                    b = lista[idx]
                    mat = b.get("materia_nombre") or b.get("descripcion_bloque") or "Bloque Titular"
                    extra = b.get("docente_nombre") or "" if modo == "seccion" else f"{b.get('grado_nombre', '')} \"{b.get('seccion_nombre', '')}\""
                    aula = f"<br/>Aula: {_esc(b['aula'])}" if b.get("aula") else ""
                    fila.append(
                        Paragraph(
                            f"<b>{_esc(b.get('hi'))} - {_esc(b.get('hf'))}</b><br/>"
                            f"<b>{_esc(mat)}</b><br/>{_esc(extra)}{aula}",
                            st_cell,
                        )
                    )
                else:
                    fila.append(Paragraph("", st_cell))
            filas.append(fila)

    ancho_col = (25.9 * cm) / max(len(orden_dias), 1)
    t = Table(filas, colWidths=[ancho_col] * len(orden_dias), repeatRows=1)
    t.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F294A")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elementos.append(t)
    doc.build(elementos)
    buf.seek(0)
    return buf


def generar_lista_asistencia_pdf(
    seccion_info: dict,
    estudiantes: list,
    cfg: dict,
    periodo: str,
) -> BytesIO:
    """Genera Lista de Asistencia / Control en blanco en PDF horizontal (20 dias habiles)."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        leftMargin=1.0 * cm,
        rightMargin=1.0 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
    )
    styles = getSampleStyleSheet()
    st_title = ParagraphStyle(
        "a_title", parent=styles["Normal"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=10.5, spaceBefore=4, spaceAfter=4
    )
    st_meta = ParagraphStyle("a_meta", parent=styles["Normal"], fontSize=8, spaceAfter=6)
    st_cell = ParagraphStyle("a_cell", parent=styles["Normal"], fontSize=7.5, leading=9.5, alignment=TA_LEFT)
    st_cell_c = ParagraphStyle("a_cell_c", parent=styles["Normal"], fontSize=7.2, leading=9, alignment=TA_CENTER)

    elementos = _encabezado_membrete(cfg, styles)
    elementos.append(
        Paragraph(
            f"CONTROL DE ASISTENCIA — {_esc(seccion_info['grado_nombre'].upper())} SECCIÓN \"{_esc(seccion_info['nombre'])}\" "
            f"· PERÍODO {_esc(periodo)}",
            st_title,
        )
    )
    guia = seccion_info.get("docente_guia_nombre") or "____________________________"
    elementos.append(
        Paragraph(
            f"<b>Turno:</b> {_esc(seccion_info.get('turno') or '')} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Docente:</b> {_esc(guia)} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Materia / Mes:</b> ____________________________ &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Matrícula:</b> {len(estudiantes)}",
            st_meta,
        )
    )

    headers = (
        [Paragraph("<b>#</b>", st_cell_c), Paragraph("<b>Cédula</b>", st_cell_c), Paragraph("<b>Apellidos y Nombres</b>", st_cell)]
        + [Paragraph(f"<b>{d}</b>", st_cell_c) for d in range(1, 21)]
        + [Paragraph("<b>Inas.</b>", st_cell_c)]
    )
    filas = [headers]
    for i, est in enumerate(estudiantes, start=1):
        filas.append(
            [
                Paragraph(str(i), st_cell_c),
                Paragraph(_esc(est["cedula"]), st_cell_c),
                Paragraph(f"{_esc(est['apellidos'])} {_esc(est['nombres'])}", st_cell),
            ]
            + [""] * 21
        )
    if not estudiantes:
        filas.append([Paragraph("Sin estudiantes inscritos en esta sección.", st_cell_c)] + [""] * 23)

    col_widths = [0.75 * cm, 2.35 * cm, 6.2 * cm] + [0.76 * cm] * 20 + [1.4 * cm]
    t = Table(filas, colWidths=col_widths, repeatRows=1)
    ts = [
        ("BOX", (0, 0), (-1, -1), 0.7, colors.black),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E2E8F0")),
        ("PADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if not estudiantes:
        ts.append(("SPAN", (0, 1), (-1, 1)))
    t.setStyle(TableStyle(ts))
    elementos.append(t)

    doc.build(elementos)
    buf.seek(0)
    return buf
