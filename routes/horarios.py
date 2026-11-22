from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from services.academico_service import (
    listar_asignaciones_seccion,
    listar_docentes,
    listar_materias,
    listar_secciones,
    obtener_periodo_activo,
    resolver_periodo_consulta,
)
from services.auth_service import admin_required, login_required, obtener_usuario_actual
from services.horario_service import (
    DIAS_SEMANA,
    actualizar_bloque_horario,
    consultar_disponibilidad_horario,
    eliminar_bloque_horario,
    obtener_horario_docente,
    obtener_horario_seccion,
    registrar_bloque_horario,
)

horarios_bp = Blueprint("horarios", __name__, url_prefix="/horarios")


@horarios_bp.route("/", methods=["GET"])
@login_required
def index():
    periodo, periodo_activo, periodos, solo_lectura = resolver_periodo_consulta(
        request.args.get("id_periodo", type=int),
        session.get("periodo_consulta_id"),
    )
    id_periodo = periodo["id"] if periodo else 0
    secciones = listar_secciones(id_periodo) if id_periodo else []
    docentes = listar_docentes(solo_activos=True)

    user = obtener_usuario_actual()
    modo = request.args.get("modo", "seccion")
    id_grado = request.args.get("id_grado", type=int)
    id_seccion = request.args.get("id_seccion", type=int)
    id_docente = request.args.get("id_docente", type=int)

    if user["rol"] == "docente":
        modo = "docente"
        id_docente = user.get("id_docente")
        id_seccion = None

    grados_vistos = {}
    for s in secciones:
        gid = s["id_grado_anio"]
        if gid not in grados_vistos:
            grados_vistos[gid] = {"id": gid, "nombre": s["grado_nombre"], "nivel_nombre": s["nivel_nombre"]}
    grados_disponibles = list(grados_vistos.values())

    if modo == "seccion":
        if id_seccion:
            sec_tmp = next((s for s in secciones if s["id"] == id_seccion), None)
            if sec_tmp and (not id_grado or sec_tmp["id_grado_anio"] == id_grado):
                id_grado = sec_tmp["id_grado_anio"]
            else:
                id_seccion = None
        if not id_grado and grados_disponibles:
            id_grado = grados_disponibles[0]["id"]
        secciones_grado = [s for s in secciones if s["id_grado_anio"] == id_grado] if id_grado else secciones
        if not id_seccion and secciones_grado:
            id_seccion = secciones_grado[0]["id"]
    else:
        secciones_grado = secciones
        if not id_docente and docentes:
            id_docente = docentes[0]["id"]

    bloques = []
    seccion_actual = None
    docente_actual = None
    materias_grado = []
    mapa_asignaciones = {}

    if id_periodo:
        if modo == "docente" and id_docente:
            bloques = obtener_horario_docente(id_periodo, id_docente)
            docente_actual = next((d for d in docentes if d["id"] == id_docente), None)
        elif id_seccion:
            bloques = obtener_horario_seccion(id_periodo, id_seccion)
            seccion_actual = next((s for s in secciones if s["id"] == id_seccion), None)
            if seccion_actual:
                materias_grado = listar_materias(seccion_actual["id_grado_anio"], solo_activas=True)
                asigs = listar_asignaciones_seccion(id_periodo, id_seccion)
                mapa_asignaciones = {str(a["id_materia"]): a["id_docente"] for a in asigs}

    bloques_por_dia = {d: [] for d in DIAS_SEMANA}
    for b in bloques:
        bloques_por_dia.setdefault(b["dia_semana"], []).append(b)

    return render_template(
        "horarios/index.html",
        periodos=periodos,
        periodo=periodo,
        periodo_activo=periodo_activo,
        id_periodo=id_periodo,
        solo_lectura=solo_lectura,
        modo=modo,
        grados_disponibles=grados_disponibles,
        secciones=secciones_grado,
        docentes=docentes,
        id_grado=id_grado,
        id_seccion=id_seccion,
        id_docente=id_docente,
        seccion_actual=seccion_actual,
        docente_actual=docente_actual,
        materias_grado=materias_grado,
        mapa_asignaciones=mapa_asignaciones,
        dias=DIAS_SEMANA,
        bloques_por_dia=bloques_por_dia,
    )


@horarios_bp.route("/api/disponibilidad", methods=["GET"])
@admin_required
def api_disponibilidad():
    periodo = obtener_periodo_activo()
    if not periodo:
        return jsonify({"ok": False, "mensaje": "No hay período escolar activo."}), 400
    data = consultar_disponibilidad_horario(
        periodo["id"],
        id_seccion=request.args.get("id_seccion", type=int) or 0,
        id_docente=request.args.get("id_docente", type=int) or 0,
        dia_semana=request.args.get("dia_semana", type=int) or 1,
        hora_inicio=request.args.get("hora_inicio", "").strip(),
        hora_fin=request.args.get("hora_fin", "").strip(),
        aula=request.args.get("aula", "").strip(),
        excluir_id=request.args.get("excluir_id", type=int),
    )
    return jsonify({"ok": True, **data})


@horarios_bp.route("/crear", methods=["POST"])
@admin_required
def crear():
    es_fetch = request.headers.get("X-Requested-With") == "fetch"
    periodo = obtener_periodo_activo()
    if not periodo:
        msg = "No hay período escolar activo."
        if es_fetch:
            return jsonify({"ok": False, "mensaje": msg}), 400
        flash(msg, "error")
        return redirect(url_for("horarios.index"))

    id_seccion = request.form.get("id_seccion", type=int)
    try:
        if not id_seccion:
            raise ValueError("Debe seleccionar una sección.")
        id_mat = request.form.get("id_materia")
        registrar_bloque_horario(
            periodo["id"],
            id_seccion,
            int(request.form.get("id_docente")),
            int(request.form.get("dia_semana")),
            request.form.get("hora_inicio", ""),
            request.form.get("hora_fin", ""),
            id_materia=int(id_mat) if id_mat else None,
            aula=request.form.get("aula", ""),
            descripcion_bloque=request.form.get("descripcion_bloque", ""),
            guardar_asignacion=request.form.get("guardar_asignacion") == "1",
        )
        msg = "Bloque horario agregado sin conflictos."
        if es_fetch:
            return jsonify({"ok": True, "mensaje": msg})
        flash(msg, "success")
    except Exception as err:
        if es_fetch:
            return jsonify({"ok": False, "mensaje": str(err)}), 400
        flash(str(err), "error")
    return redirect(url_for("horarios.index", modo="seccion", id_seccion=id_seccion))


@horarios_bp.route("/editar/<int:hid>", methods=["POST"])
@admin_required
def editar(hid: int):
    es_fetch = request.headers.get("X-Requested-With") == "fetch"
    periodo = obtener_periodo_activo()
    if not periodo:
        msg = "No hay período escolar activo."
        if es_fetch:
            return jsonify({"ok": False, "mensaje": msg}), 400
        flash(msg, "error")
        return redirect(url_for("horarios.index"))

    id_seccion = request.form.get("id_seccion", type=int)
    try:
        if not id_seccion:
            raise ValueError("Sección inválida.")
        id_mat = request.form.get("id_materia")
        actualizar_bloque_horario(
            hid,
            periodo["id"],
            id_seccion,
            int(request.form.get("id_docente")),
            int(request.form.get("dia_semana")),
            request.form.get("hora_inicio", ""),
            request.form.get("hora_fin", ""),
            id_materia=int(id_mat) if id_mat else None,
            aula=request.form.get("aula", ""),
            descripcion_bloque=request.form.get("descripcion_bloque", ""),
            guardar_asignacion=request.form.get("guardar_asignacion") == "1",
        )
        msg = "Bloque horario actualizado sin conflictos."
        if es_fetch:
            return jsonify({"ok": True, "mensaje": msg})
        flash(msg, "success")
    except Exception as err:
        if es_fetch:
            return jsonify({"ok": False, "mensaje": str(err)}), 400
        flash(str(err), "error")
    return redirect(url_for("horarios.index", modo="seccion", id_seccion=id_seccion))


@horarios_bp.route("/eliminar/<int:hid>", methods=["POST"])
@admin_required
def eliminar(hid: int):
    es_fetch = request.headers.get("X-Requested-With") == "fetch"
    id_seccion = request.form.get("id_seccion", type=int)
    try:
        eliminar_bloque_horario(hid)
        msg = "Bloque horario eliminado."
        if es_fetch:
            return jsonify({"ok": True, "mensaje": msg})
        flash(msg, "success")
    except Exception as err:
        if es_fetch:
            return jsonify({"ok": False, "mensaje": str(err)}), 400
        flash(str(err), "error")
    return redirect(url_for("horarios.index", modo="seccion", id_seccion=id_seccion))
