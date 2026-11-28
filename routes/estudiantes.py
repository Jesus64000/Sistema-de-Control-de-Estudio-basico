import json
from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from services.academico_service import (
    listar_grados,
    listar_niveles,
    listar_secciones,
    obtener_periodo_activo,
    resolver_periodo_consulta,
)
from services.auth_service import roles_required
from services.import_service import importar_nomina_excel
from services.estudiante_service import (
    actualizar_estudiante,
    buscar_estudiante_por_cedula,
    buscar_estudiantes_para_inscripcion,
    buscar_representante_por_cedula,
    cambiar_estado_inscripcion,
    contar_resumen_estudiantes_periodo,
    ejecutar_prosecucion_lote,
    listar_candidatos_prosecucion,
    listar_directorio_estudiantes,
    marcar_egresado,
    obtener_expediente_completo,
    registrar_e_inscribir_estudiante,
    trasladar_seccion_inscripcion,
)

estudiantes_bp = Blueprint("estudiantes", __name__, url_prefix="/estudiantes")


@estudiantes_bp.route("/", methods=["GET"])
@roles_required("admin", "operador")
def index():
    raw_pid = request.args.get("id_periodo")
    periodo_consulta, periodo_activo, periodos, solo_lectura_ctx = resolver_periodo_consulta(
        int(raw_pid) if (raw_pid and raw_pid.isdigit() and raw_pid != "0") else None,
        session.get("periodo_consulta_id"),
    )
    if raw_pid == "0":
        periodo_sel = None
        id_periodo_sel = 0
        solo_lectura = False
    else:
        periodo_sel = periodo_consulta
        id_periodo_sel = periodo_sel["id"] if periodo_sel else 0
        solo_lectura = solo_lectura_ctx

    filtro = request.args.get("q", "")
    id_nivel = request.args.get("id_nivel", type=int)
    id_grado = request.args.get("id_grado", type=int)
    id_seccion = request.args.get("id_seccion", type=int)

    resumen = contar_resumen_estudiantes_periodo(id_periodo_sel or None)

    estado_param = request.args.get("estado")
    if estado_param in ("activo", "retirado", "sin_inscribir", "egresado", "todos"):
        estado = estado_param
    elif filtro.strip():
        estado = "todos"
    elif id_periodo_sel == 0 or (resumen["inscritos"] == 0 and resumen["total_registrados"] > 0):
        estado = "todos"
    else:
        estado = "activo"

    inscripciones = listar_directorio_estudiantes(
        id_periodo=id_periodo_sel or None,
        filtro=filtro,
        id_nivel=id_nivel,
        id_grado=id_grado,
        id_seccion=id_seccion,
        estado=estado,
    )

    secciones_consulta = listar_secciones(id_periodo_sel) if id_periodo_sel else []
    secciones_activas = (
        listar_secciones(periodo_activo["id"])
        if periodo_activo and not periodo_activo.get("cerrado")
        else []
    )
    periodos_origen = [p for p in periodos if not periodo_activo or p["id"] != periodo_activo["id"]]

    return render_template(
        "estudiantes/index.html",
        periodos=periodos,
        periodos_origen=periodos_origen,
        periodo=periodo_sel,
        periodo_activo=periodo_activo,
        id_periodo_sel=id_periodo_sel,
        solo_lectura=solo_lectura,
        inscripciones=inscripciones,
        resumen=resumen,
        total_retirados=resumen["retirados"],
        niveles=listar_niveles(),
        grados=listar_grados(),
        secciones=secciones_activas,
        secciones_consulta=secciones_consulta,
        filtro=filtro,
        id_nivel=id_nivel,
        id_grado=id_grado,
        id_seccion=id_seccion,
        estado=estado,
    )


@estudiantes_bp.route("/api/representante", methods=["GET"])
@roles_required("admin", "operador")
def api_representante():
    rep = buscar_representante_por_cedula(request.args.get("cedula", ""))
    if not rep:
        return jsonify({"encontrado": False})
    return jsonify({"encontrado": True, "representante": rep})


@estudiantes_bp.route("/api/estudiante", methods=["GET"])
@roles_required("admin", "operador")
def api_estudiante():
    periodo_activo = obtener_periodo_activo()
    res = buscar_estudiante_por_cedula(
        request.args.get("cedula", ""),
        id_periodo_destino=periodo_activo["id"] if periodo_activo else None,
    )
    if not res:
        return jsonify({"encontrado": False})
    return jsonify({"encontrado": True, **res})


@estudiantes_bp.route("/api/buscar-reinscripcion", methods=["GET"])
@roles_required("admin", "operador")
def api_buscar_reinscripcion():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify({"resultados": []})
    periodo_activo = obtener_periodo_activo()
    resultados = buscar_estudiantes_para_inscripcion(
        q,
        id_periodo_destino=periodo_activo["id"] if periodo_activo else None,
        limite=10,
    )
    return jsonify({"resultados": resultados})


@estudiantes_bp.route("/api/prosecucion", methods=["GET"])
@roles_required("admin", "operador")
def api_prosecucion():
    periodo_activo = obtener_periodo_activo()
    id_periodo_origen = request.args.get("id_periodo_origen", type=int)
    id_seccion_origen = request.args.get("id_seccion_origen", type=int)
    if not id_periodo_origen or not id_seccion_origen:
        return jsonify({"candidatos": []})
    cands = listar_candidatos_prosecucion(
        id_periodo_origen,
        id_seccion_origen,
        periodo_activo["id"] if periodo_activo else 0,
    )
    return jsonify({"candidatos": cands})


@estudiantes_bp.route("/prosecucion", methods=["POST"])
@roles_required("admin", "operador")
def prosecucion_lote():
    es_fetch = request.headers.get("X-Requested-With") == "fetch"
    periodo_activo = obtener_periodo_activo()
    decisiones_raw = request.form.get("decisiones_json")
    try:
        if decisiones_raw:
            decisiones = json.loads(decisiones_raw)
            res = ejecutar_prosecucion_lote(
                periodo_activo["id"] if periodo_activo else 0,
                decisiones=decisiones,
            )
        else:
            ids_est = request.form.getlist("ids_estudiantes")
            accion = request.form.get("accion_prosecucion", "inscribir")
            marcar_egr = accion == "egresar"
            id_seccion_dest = request.form.get("id_seccion_destino", type=int)
            res = ejecutar_prosecucion_lote(
                periodo_activo["id"] if periodo_activo else 0,
                id_seccion_dest or 0,
                ids_est,
                marcar_como_egresados=marcar_egr,
            )
        partes = []
        if res["inscritos"]:
            partes.append(f"{res['inscritos']} reinscrito(s)")
        if res["egresados"]:
            partes.append(f"{res['egresados']} egresado(s)")
        if res["omitidos"]:
            partes.append(f"{res['omitidos']} omitido(s) por ya tener matrícula")
        msg = "Prosecución aplicada: " + ", ".join(partes) + "." if partes else "Sin cambios realizados."
        if es_fetch:
            return jsonify({"ok": True, "mensaje": msg})
        flash(msg, "success")
    except Exception as err:
        if es_fetch:
            return jsonify({"ok": False, "mensaje": str(err)}), 400
        flash(str(err), "error")
    return redirect(url_for("estudiantes.index"))


@estudiantes_bp.route("/<int:eid>/expediente", methods=["GET"])
@roles_required("admin", "operador")
def api_expediente(eid: int):
    exp = obtener_expediente_completo(eid)
    if not exp:
        return jsonify({"encontrado": False}), 404
    return jsonify({"encontrado": True, **exp})


@estudiantes_bp.route("/guardar", methods=["POST"])
@roles_required("admin", "operador")
def guardar():
    destino = "dashboard.index" if request.form.get("next") == "dashboard" else "estudiantes.index"
    periodo = obtener_periodo_activo()
    if not periodo:
        flash("No hay período escolar activo.", "error")
        return redirect(url_for(destino))
    try:
        id_sec = request.form.get("id_seccion", type=int)
        if not id_sec:
            raise ValueError("Debe seleccionar una sección válida del período activo.")
        registrar_e_inscribir_estudiante(
            request.form,
            periodo["id"],
            id_sec,
        )
        flash("Estudiante guardado e inscrito correctamente.", "success")
    except Exception as err:
        flash(str(err), "error")
    return redirect(url_for(destino))


@estudiantes_bp.route("/importar-excel", methods=["POST"])
@roles_required("admin", "operador")
def importar_excel():
    periodo = obtener_periodo_activo()
    if not periodo:
        flash("No hay período escolar activo.", "error")
        return redirect(url_for("estudiantes.index"))
    archivo = request.files.get("archivo")
    if not archivo or not archivo.filename.lower().endswith(".xlsx"):
        flash("Debe seleccionar un archivo Excel (.xlsx) válido.", "error")
        return redirect(url_for("estudiantes.index"))
    id_sec = request.form.get("id_seccion", type=int)
    try:
        res = importar_nomina_excel(archivo.stream, periodo["id"], id_seccion_fija=id_sec or None)
        if res["procesados"] == 0:
            flash("No se encontraron estudiantes válidos para importar en el archivo.", "error")
        else:
            flash(
                f"Importación completada: {res['procesados']} estudiante(s) procesado(s) "
                f"en {len(res['secciones'])} hoja(s) ({res['sin_cedula']} sin cédula con código SC, "
                f"{res['omitidos']} omitidos).",
                "success",
            )
        advs = res.get("advertencias") or []
        if advs:
            muestra = "; ".join(advs[:4])
            extra = f" (+{len(advs) - 4} más)" if len(advs) > 4 else ""
            flash(f"Advertencias de importación: {muestra}{extra}", "error")
    except Exception as err:
        flash(f"Error al importar nómina: {err}", "error")
    return redirect(url_for("estudiantes.index"))


@estudiantes_bp.route("/editar/<int:eid>", methods=["POST"])
@roles_required("admin", "operador")
def editar(eid: int):
    try:
        actualizar_estudiante(eid, request.form)
        flash("Ficha del estudiante actualizada.", "success")
    except Exception as err:
        flash(str(err), "error")
    return redirect(url_for("estudiantes.index"))


@estudiantes_bp.route("/retirar/<int:id_inscripcion>", methods=["POST"])
@roles_required("admin", "operador")
def retirar(id_inscripcion: int):
    try:
        cambiar_estado_inscripcion(id_inscripcion, "retirado")
        flash("Estudiante marcado como retirado en el período.", "success")
    except Exception as err:
        flash(str(err), "error")
    return redirect(url_for("estudiantes.index"))


@estudiantes_bp.route("/reactivar/<int:id_inscripcion>", methods=["POST"])
@roles_required("admin", "operador")
def reactivar(id_inscripcion: int):
    try:
        cambiar_estado_inscripcion(id_inscripcion, "activo")
        flash("Inscripción del estudiante reactivada.", "success")
    except Exception as err:
        flash(str(err), "error")
    return redirect(url_for("estudiantes.index", estado="todos"))


@estudiantes_bp.route("/trasladar/<int:id_inscripcion>", methods=["POST"])
@roles_required("admin", "operador")
def trasladar_seccion(id_inscripcion: int):
    id_sec_dest = request.form.get("id_seccion_destino", type=int)
    try:
        if not id_sec_dest:
            raise ValueError("Debe seleccionar la sección de destino.")
        res = trasladar_seccion_inscripcion(id_inscripcion, id_sec_dest)
        flash(f"Estudiante trasladado de {res['origen']} a {res['destino']}.", "success")
    except Exception as err:
        flash(str(err), "error")
    return redirect(url_for("estudiantes.index"))


@estudiantes_bp.route("/egresar/<int:eid>", methods=["POST"])
@roles_required("admin", "operador")
def toggle_egresado(eid: int):
    try:
        nuevo = request.form.get("egresado") == "1"
        marcar_egresado(eid, nuevo)
        flash(
            "Estudiante marcado como egresado." if nuevo else "Estudiante restaurado como regular.",
            "success",
        )
    except Exception as err:
        flash(str(err), "error")
    return redirect(url_for("estudiantes.index", estado="todos"))
