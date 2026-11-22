from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from flask import Blueprint, flash, redirect, render_template, request, send_file, session, url_for
from services.academico_service import (
    listar_docentes,
    listar_materias,
    listar_materias_docente_seccion,
    listar_secciones,
    listar_secciones_docente,
    resolver_periodo_consulta,
)
from services.auth_service import login_required, obtener_usuario_actual, roles_required
from services.calificacion_service import (
    numero_a_letras,
    obtener_boletin_estudiante,
    obtener_notas_primaria_seccion,
    obtener_notas_secundaria_seccion_materia,
    obtener_sabana_secundaria_seccion,
)
from services.config_service import obtener_configuracion
from services.estudiante_service import (
    listar_directorio_estudiantes,
    listar_inscripciones,
    listar_inscripciones_por_ids,
    obtener_historial_certificable,
    obtener_inscripcion_detalle,
)
from services.excel_service import (
    exportar_lista_asistencia,
    exportar_nomina_estudiantes,
    exportar_planilla_materia,
    exportar_sabana_primaria,
    exportar_sabana_secundaria,
)
from services.horario_service import DIAS_SEMANA, obtener_horario_docente, obtener_horario_seccion
from services.pdf_service import (
    generar_boletin_lapsos_pdf,
    generar_certificado_historial_pdf,
    generar_certificado_pdf,
    generar_certificados_pdf_lote,
    generar_constancia_estudio_pdf,
    generar_horario_pdf,
    generar_lista_asistencia_pdf,
    generar_sabana_secundaria_pdf,
)

reportes_bp = Blueprint("reportes", __name__, url_prefix="/reportes")


def _parse_ids(raw: str) -> list:
    ids = []
    for part in (raw or "").split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


def _docente_puede_ver_inscripcion(user: dict, detalle: dict) -> bool:
    if user["rol"] in ("admin", "operador"):
        return True
    if not user.get("id_docente"):
        return False
    secs = listar_secciones_docente(detalle["id_periodo"], user["id_docente"])
    return any(s["id"] == detalle["id_seccion"] for s in secs)


@reportes_bp.route("/certificado/<int:id_inscripcion>", methods=["GET"])
@login_required
def certificado_vista(id_inscripcion: int):
    detalle = obtener_inscripcion_detalle(id_inscripcion)
    if not detalle:
        flash("Inscripción no encontrada.", "error")
        return redirect(url_for("estudiantes.index"))
    user = obtener_usuario_actual()
    if not _docente_puede_ver_inscripcion(user, detalle):
        flash("No tiene permiso para consultar el certificado de esta sección.", "error")
        return redirect(url_for("calificaciones.index"))
    boletin = obtener_boletin_estudiante(id_inscripcion)
    return render_template(
        "reportes/certificado.html",
        detalle=detalle,
        boletin=boletin,
        cfg=obtener_configuracion(),
        numero_a_letras=numero_a_letras,
    )


@reportes_bp.route("/certificado/<int:id_inscripcion>/pdf", methods=["GET"])
@login_required
def certificado_pdf(id_inscripcion: int):
    detalle = obtener_inscripcion_detalle(id_inscripcion)
    if not detalle:
        flash("Inscripción no encontrada.", "error")
        return redirect(url_for("estudiantes.index"))
    user = obtener_usuario_actual()
    if not _docente_puede_ver_inscripcion(user, detalle):
        flash("No tiene permiso para descargar el certificado de esta sección.", "error")
        return redirect(url_for("calificaciones.index"))
    boletin = obtener_boletin_estudiante(id_inscripcion)
    pdf_buf = generar_certificado_pdf(detalle, boletin, obtener_configuracion())
    nombre_archivo = f"Certificado_{detalle['cedula']}_{detalle['periodo_nombre']}.pdf"
    return send_file(pdf_buf, mimetype="application/pdf", as_attachment=True, download_name=nombre_archivo)


@reportes_bp.route("/historial/<int:id_estudiante>", methods=["GET"])
@roles_required("admin", "operador")
def historial_vista(id_estudiante: int):
    desde = request.args.get("desde", type=int)
    hasta = request.args.get("hasta", type=int)
    tipo_escala = request.args.get("escala")
    datos = obtener_historial_certificable(
        id_estudiante, desde=desde, hasta=hasta, tipo_escala=tipo_escala
    )
    if not datos:
        flash("Estudiante no encontrado.", "error")
        return redirect(url_for("estudiantes.index"))
    return render_template(
        "reportes/certificado_historial.html",
        datos=datos,
        cfg=obtener_configuracion(),
        numero_a_letras=numero_a_letras,
    )


@reportes_bp.route("/historial/<int:id_estudiante>/pdf", methods=["GET"])
@roles_required("admin", "operador")
def historial_pdf(id_estudiante: int):
    desde = request.args.get("desde", type=int)
    hasta = request.args.get("hasta", type=int)
    tipo_escala = request.args.get("escala")
    datos = obtener_historial_certificable(
        id_estudiante, desde=desde, hasta=hasta, tipo_escala=tipo_escala
    )
    if not datos:
        flash("Estudiante no encontrado.", "error")
        return redirect(url_for("estudiantes.index"))
    if not datos["historial"]:
        flash("El estudiante no tiene calificaciones en el rango seleccionado.", "error")
        return redirect(url_for("estudiantes.index"))
    pdf_buf = generar_certificado_historial_pdf(datos, obtener_configuracion())
    rango_slug = datos["rango_texto"].replace(" ", "_").replace(".", "")
    nombre_archivo = f"Certificacion_Acumulada_{datos['estudiante']['cedula']}_{rango_slug}.pdf"
    return send_file(pdf_buf, mimetype="application/pdf", as_attachment=True, download_name=nombre_archivo)


@reportes_bp.route("/certificados/lote", methods=["GET"])
@roles_required("admin", "operador")
def certificados_lote():
    ids = _parse_ids(request.args.get("ids", ""))
    if not ids:
        flash("Seleccione al menos un estudiante.", "error")
        return redirect(url_for("estudiantes.index"))

    formato = request.args.get("formato", "pdf")
    cfg = obtener_configuracion()
    items = []
    for iid in ids:
        detalle = obtener_inscripcion_detalle(iid)
        if detalle:
            items.append((detalle, obtener_boletin_estudiante(iid)))

    if not items:
        flash("No se encontraron inscripciones válidas.", "error")
        return redirect(url_for("estudiantes.index"))

    if len(items) == 1 and formato != "zip":
        det, bol = items[0]
        pdf_buf = generar_certificado_pdf(det, bol, cfg)
        return send_file(
            pdf_buf,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"Certificado_{det['cedula']}_{det['periodo_nombre']}.pdf",
        )

    if formato == "zip":
        zip_buf = BytesIO()
        with ZipFile(zip_buf, "w", ZIP_DEFLATED) as zf:
            for det, bol in items:
                pdf_bytes = generar_certificado_pdf(det, bol, cfg).getvalue()
                nombre = f"Certificado_{det['cedula']}_{det['periodo_nombre']}.pdf".replace(" ", "_")
                zf.writestr(nombre, pdf_bytes)
        zip_buf.seek(0)
        return send_file(
            zip_buf,
            mimetype="application/zip",
            as_attachment=True,
            download_name="Certificados_Estudiantes.zip",
        )

    pdf_buf = generar_certificados_pdf_lote(items, cfg)
    return send_file(
        pdf_buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="Certificados_Estudiantes.pdf",
    )


@reportes_bp.route("/excel/nomina", methods=["GET"])
@roles_required("admin", "operador")
def excel_nomina():
    raw_pid = request.args.get("id_periodo")
    if raw_pid == "0":
        periodo = None
        id_periodo = 0
        etiqueta_periodo = "Directorio_General"
    else:
        periodo, _, _, _ = resolver_periodo_consulta(
            int(raw_pid) if (raw_pid and raw_pid.isdigit()) else None,
            session.get("periodo_consulta_id"),
        )
        id_periodo = periodo["id"] if periodo else 0
        etiqueta_periodo = periodo["nombre"] if periodo else "Directorio_General"

    cfg = obtener_configuracion()
    ids = _parse_ids(request.args.get("ids", ""))
    if ids:
        filas = listar_inscripciones_por_ids(ids)
    else:
        filas = listar_directorio_estudiantes(
            id_periodo=id_periodo or None,
            filtro=request.args.get("q", ""),
            id_nivel=request.args.get("id_nivel", type=int),
            id_grado=request.args.get("id_grado", type=int),
            id_seccion=request.args.get("id_seccion", type=int),
            estado=request.args.get("estado", "activo"),
        )
    buf = exportar_nomina_estudiantes(filas, cfg.get("nombre_plantel", "Plantel"), etiqueta_periodo)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"Nomina_Estudiantes_{etiqueta_periodo}.xlsx",
    )


@reportes_bp.route("/excel/notas", methods=["GET"])
@login_required
def excel_notas():
    periodo, _, _, _ = resolver_periodo_consulta(
        request.args.get("id_periodo", type=int),
        session.get("periodo_consulta_id"),
    )
    id_seccion = request.args.get("id_seccion", type=int)
    id_materia = request.args.get("id_materia", type=int)
    if not periodo or not id_seccion:
        flash("Seleccione una sección.", "error")
        return redirect(url_for("calificaciones.index"))

    user = obtener_usuario_actual()
    if user["rol"] == "docente":
        if not user.get("id_docente"):
            flash("No tiene un perfil docente vinculado.", "error")
            return redirect(url_for("calificaciones.index"))
        secciones = listar_secciones_docente(periodo["id"], user["id_docente"])
    else:
        secciones = listar_secciones(periodo["id"])
    sec = next((s for s in secciones if s["id"] == id_seccion), None)
    if not sec:
        flash("Sección no encontrada o sin acceso.", "error")
        return redirect(url_for("calificaciones.index"))

    cfg = obtener_configuracion()
    if sec["tipo_escala"] == "literal":
        filas = obtener_notas_primaria_seccion(id_seccion)
        buf = exportar_sabana_primaria(sec, filas, cfg.get("nombre_plantel", "Plantel"))
        nombre = f"Notas_Primaria_{sec['grado_nombre']}_{sec['nombre']}.xlsx".replace(" ", "_")
    else:
        if user["rol"] == "docente":
            materias = listar_materias_docente_seccion(periodo["id"], user["id_docente"], id_seccion)
        else:
            materias = listar_materias(sec["id_grado_anio"], solo_activas=True)
        mat = next((m for m in materias if m["id"] == id_materia), None)
        if not mat:
            flash("Seleccione una materia.", "error")
            return redirect(url_for("calificaciones.index", id_seccion=id_seccion))
        filas = obtener_notas_secundaria_seccion_materia(id_seccion, id_materia)
        buf = exportar_planilla_materia(sec, mat["nombre"], filas, cfg.get("nombre_plantel", "Plantel"))
        nombre = f"Notas_{sec['grado_nombre']}_{sec['nombre']}_{mat['nombre']}.xlsx".replace(" ", "_")

    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=nombre,
    )


def _resolver_seccion_autorizada(id_seccion: int, solo_guia_docente: bool = False):
    periodo, _, _, _ = resolver_periodo_consulta(
        request.args.get("id_periodo", type=int),
        session.get("periodo_consulta_id"),
    )
    if not periodo:
        return None, None
    user = obtener_usuario_actual()
    if user["rol"] == "docente":
        if not user.get("id_docente"):
            return periodo, None
        secs = listar_secciones_docente(periodo["id"], user["id_docente"])
        sec = next((s for s in secs if s["id"] == id_seccion), None)
        if sec and solo_guia_docente and sec.get("id_docente_titular_guia") != user["id_docente"]:
            return periodo, None
        return periodo, sec
    secs = listar_secciones(periodo["id"])
    return periodo, next((s for s in secs if s["id"] == id_seccion), None)


@reportes_bp.route("/constancia/<int:id_inscripcion>/pdf", methods=["GET"])
@roles_required("admin", "operador")
def constancia_pdf(id_inscripcion: int):
    detalle = obtener_inscripcion_detalle(id_inscripcion)
    if not detalle:
        flash("Inscripción no encontrada.", "error")
        return redirect(url_for("estudiantes.index"))
    pdf_buf = generar_constancia_estudio_pdf(detalle, obtener_configuracion())
    nombre = f"Constancia_Estudio_{detalle['cedula']}_{detalle['periodo_nombre']}.pdf"
    return send_file(pdf_buf, mimetype="application/pdf", as_attachment=True, download_name=nombre)


@reportes_bp.route("/boletin/<int:id_inscripcion>/pdf", methods=["GET"])
@login_required
def boletin_pdf(id_inscripcion: int):
    detalle = obtener_inscripcion_detalle(id_inscripcion)
    if not detalle:
        flash("Inscripción no encontrada.", "error")
        return redirect(url_for("estudiantes.index"))
    user = obtener_usuario_actual()
    if not _docente_puede_ver_inscripcion(user, detalle):
        flash("No tiene permiso para descargar el boletín de esta sección.", "error")
        return redirect(url_for("calificaciones.index"))
    boletin = obtener_boletin_estudiante(id_inscripcion)
    pdf_buf = generar_boletin_lapsos_pdf(detalle, boletin, obtener_configuracion())
    nombre = f"Boletin_Lapsos_{detalle['cedula']}_{detalle['periodo_nombre']}.pdf"
    return send_file(pdf_buf, mimetype="application/pdf", as_attachment=True, download_name=nombre)


@reportes_bp.route("/excel/sabana/<int:id_seccion>", methods=["GET"])
@login_required
def excel_sabana(id_seccion: int):
    periodo, sec = _resolver_seccion_autorizada(id_seccion, solo_guia_docente=True)
    if not sec:
        flash("Sección no encontrada o requiere ser Profesor Guía / Administrador.", "error")
        return redirect(url_for("calificaciones.index"))
    cfg = obtener_configuracion()
    if sec["tipo_escala"] == "literal":
        filas = obtener_notas_primaria_seccion(id_seccion)
        buf = exportar_sabana_primaria(sec, filas, cfg.get("nombre_plantel", "Plantel"))
        nombre = f"Sabana_{sec['grado_nombre']}_{sec['nombre']}.xlsx".replace(" ", "_")
    else:
        lapso = request.args.get("lapso", "final")
        materias = listar_materias(sec["id_grado_anio"], solo_activas=True)
        sabana = obtener_sabana_secundaria_seccion(id_seccion)
        buf = exportar_sabana_secundaria(
            sec, materias, sabana, cfg.get("nombre_plantel", "Plantel"), periodo["nombre"], lapso=lapso
        )
        nombre = f"Sabana_{sec['grado_nombre']}_{sec['nombre']}_{lapso}.xlsx".replace(" ", "_")
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=nombre,
    )


@reportes_bp.route("/pdf/sabana/<int:id_seccion>", methods=["GET"])
@login_required
def pdf_sabana(id_seccion: int):
    periodo, sec = _resolver_seccion_autorizada(id_seccion, solo_guia_docente=True)
    if not sec or sec["tipo_escala"] != "numerica":
        flash("Sábana PDF disponible para Media General (Admin, Operador o Profesor Guía).", "error")
        return redirect(url_for("calificaciones.index"))
    lapso = request.args.get("lapso", "final")
    materias = listar_materias(sec["id_grado_anio"], solo_activas=True)
    sabana = obtener_sabana_secundaria_seccion(id_seccion)
    pdf_buf = generar_sabana_secundaria_pdf(
        sec, materias, sabana, obtener_configuracion(), periodo["nombre"], lapso=lapso
    )
    nombre = f"Sabana_{sec['grado_nombre']}_{sec['nombre']}_{lapso}.pdf".replace(" ", "_")
    return send_file(pdf_buf, mimetype="application/pdf", as_attachment=True, download_name=nombre)


@reportes_bp.route("/horario/seccion/<int:id_seccion>/pdf", methods=["GET"])
@login_required
def horario_seccion_pdf(id_seccion: int):
    periodo, sec = _resolver_seccion_autorizada(id_seccion, solo_guia_docente=False)
    if not sec:
        flash("Sección no encontrada o sin acceso.", "error")
        return redirect(url_for("horarios.index"))
    bloques_por_dia = {d: [] for d in DIAS_SEMANA}
    for b in obtener_horario_seccion(periodo["id"], id_seccion):
        bloques_por_dia.setdefault(b["dia_semana"], []).append(b)
    titulo = f"HORARIO SEMANAL — {sec['grado_nombre'].upper()} SECCIÓN \"{sec['nombre']}\""
    subtitulo = f"Nivel: {sec['nivel_nombre']} · Turno: {sec['turno']} · Período Escolar {periodo['nombre']}"
    pdf_buf = generar_horario_pdf(titulo, subtitulo, bloques_por_dia, DIAS_SEMANA, obtener_configuracion(), modo="seccion")
    nombre = f"Horario_{sec['grado_nombre']}_{sec['nombre']}_{periodo['nombre']}.pdf".replace(" ", "_")
    return send_file(pdf_buf, mimetype="application/pdf", as_attachment=True, download_name=nombre)


@reportes_bp.route("/horario/docente/<int:id_docente>/pdf", methods=["GET"])
@login_required
def horario_docente_pdf(id_docente: int):
    user = obtener_usuario_actual()
    if user["rol"] == "docente" and user.get("id_docente") != id_docente:
        flash("Solo puede descargar su propio horario docente.", "error")
        return redirect(url_for("dashboard.index"))
    periodo, _, _, _ = resolver_periodo_consulta(
        request.args.get("id_periodo", type=int),
        session.get("periodo_consulta_id"),
    )
    if not periodo:
        flash("No hay período escolar disponible.", "error")
        return redirect(url_for("horarios.index"))
    doc = next((d for d in listar_docentes(solo_activos=False) if d["id"] == id_docente), None)
    if not doc:
        flash("Docente no encontrado.", "error")
        return redirect(url_for("horarios.index"))
    bloques_por_dia = {d: [] for d in DIAS_SEMANA}
    for b in obtener_horario_docente(periodo["id"], id_docente):
        bloques_por_dia.setdefault(b["dia_semana"], []).append(b)
    titulo = f"HORARIO DOCENTE — {doc['apellidos'].upper()} {doc['nombres'].upper()}"
    subtitulo = f"C.I.: {doc['cedula']} · {doc.get('especialidad') or doc.get('categoria', '')} · Período Escolar {periodo['nombre']}"
    pdf_buf = generar_horario_pdf(titulo, subtitulo, bloques_por_dia, DIAS_SEMANA, obtener_configuracion(), modo="docente")
    nombre = f"Horario_Docente_{doc['cedula']}_{periodo['nombre']}.pdf".replace(" ", "_")
    return send_file(pdf_buf, mimetype="application/pdf", as_attachment=True, download_name=nombre)


@reportes_bp.route("/asistencia/<int:id_seccion>/pdf", methods=["GET"])
@login_required
def asistencia_pdf(id_seccion: int):
    periodo, sec = _resolver_seccion_autorizada(id_seccion, solo_guia_docente=False)
    if not sec:
        flash("Sección no encontrada o sin acceso.", "error")
        return redirect(url_for("calificaciones.index"))
    estudiantes = listar_inscripciones(periodo["id"], id_seccion=id_seccion, estado="activo")
    pdf_buf = generar_lista_asistencia_pdf(sec, estudiantes, obtener_configuracion(), periodo["nombre"])
    nombre = f"Asistencia_{sec['grado_nombre']}_{sec['nombre']}_{periodo['nombre']}.pdf".replace(" ", "_")
    return send_file(pdf_buf, mimetype="application/pdf", as_attachment=True, download_name=nombre)


@reportes_bp.route("/asistencia/<int:id_seccion>/excel", methods=["GET"])
@login_required
def asistencia_excel(id_seccion: int):
    periodo, sec = _resolver_seccion_autorizada(id_seccion, solo_guia_docente=False)
    if not sec:
        flash("Sección no encontrada o sin acceso.", "error")
        return redirect(url_for("calificaciones.index"))
    estudiantes = listar_inscripciones(periodo["id"], id_seccion=id_seccion, estado="activo")
    cfg = obtener_configuracion()
    buf = exportar_lista_asistencia(sec, estudiantes, cfg.get("nombre_plantel", "Plantel"), periodo["nombre"])
    nombre = f"Asistencia_{sec['grado_nombre']}_{sec['nombre']}_{periodo['nombre']}.xlsx".replace(" ", "_")
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=nombre,
    )
