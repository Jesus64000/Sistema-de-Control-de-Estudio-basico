from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from db import ejecutar_consulta
from services.academico_service import (
    asignar_titular_a_materias_primaria,
    guardar_asignaciones_seccion_lote,
    listar_asignaciones_seccion,
    listar_docentes,
    listar_materias,
    listar_materias_docente_seccion,
    listar_secciones,
    listar_secciones_docente,
    obtener_periodo_activo,
    resolver_periodo_consulta,
)
from services.auth_service import admin_required, login_required, obtener_usuario_actual
from services.calificacion_service import (
    ESCALA_LITERAL,
    TIPOS_EVALUACION,
    guardar_notas_primaria,
    guardar_notas_secundaria,
    obtener_notas_primaria_seccion,
    obtener_notas_secundaria_seccion_materia,
    obtener_sabana_secundaria_seccion,
)
from services.config_service import obtener_configuracion
from services.horario_service import DIAS_SEMANA, obtener_horario_seccion

calificaciones_bp = Blueprint("calificaciones", __name__, url_prefix="/calificaciones")


@calificaciones_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    user = obtener_usuario_actual()
    periodo, periodo_activo, periodos, solo_lectura = resolver_periodo_consulta(
        request.values.get("id_periodo", type=int),
        session.get("periodo_consulta_id"),
    )
    id_periodo = periodo["id"] if periodo else 0

    if user["rol"] == "docente":
        if not user.get("id_docente"):
            flash("Su cuenta de docente no esta vinculada a un perfil academico.", "error")
            return redirect(url_for("dashboard.index"))
        secciones = listar_secciones_docente(id_periodo, user["id_docente"]) if id_periodo else []
    else:
        secciones = listar_secciones(id_periodo) if id_periodo else []

    id_grado = request.values.get("id_grado", type=int)
    id_seccion = request.values.get("id_seccion", type=int)
    id_materia = request.values.get("id_materia", type=int)
    vista_defecto = "notas" if request.values.get("embed") == "1" else "estudiantes"
    vista = request.values.get("vista", vista_defecto)
    if vista not in ("estudiantes", "notas", "docentes", "horario"):
        vista = vista_defecto
    lapso = request.values.get("lapso", "1")

    # Lista de grados disponibles segun las secciones a las que tiene acceso
    grados_vistos = {}
    for s in secciones:
        gid = s["id_grado_anio"]
        if gid not in grados_vistos:
            grados_vistos[gid] = {
                "id": gid,
                "nombre": s["grado_nombre"],
                "nivel_nombre": s["nivel_nombre"],
            }
    grados_disponibles = list(grados_vistos.values())

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

    seccion_actual = next((s for s in secciones if s["id"] == id_seccion), None)
    if id_seccion and not seccion_actual:
        flash("No tiene acceso a esa sección.", "error")
        return redirect(url_for("calificaciones.index"))

    materias = []
    materias_grado = []
    filas = []
    filas_por_materia = []
    sabana = []
    miembros = []
    asignaciones = []
    docentes = []
    mapa_asignaciones = {}
    bloques_por_dia = {d: [] for d in DIAS_SEMANA}

    if seccion_actual:
        materias_grado = listar_materias(seccion_actual["id_grado_anio"], solo_activas=True)
        if seccion_actual["tipo_escala"] == "numerica":
            if user["rol"] == "docente":
                materias = listar_materias_docente_seccion(id_periodo, user["id_docente"], seccion_actual["id"])
            else:
                materias = materias_grado
            if id_materia and not any(m["id"] == id_materia for m in materias):
                if vista == "notas" or user["rol"] == "docente":
                    flash("No tiene asignada esa materia en esta sección.", "error")
                    return redirect(url_for("calificaciones.index", id_grado=id_grado, id_seccion=seccion_actual["id"], vista=vista))
                id_materia = None

        if request.method == "POST":
            if solo_lectura:
                msg = "El período seleccionado está en modo solo lectura (histórico o cerrado)."
                if request.headers.get("X-Requested-With") == "fetch":
                    return jsonify({"ok": False, "mensaje": msg}), 400
                flash(msg, "error")
                return redirect(
                    url_for(
                        "calificaciones.index",
                        id_periodo=id_periodo,
                        id_seccion=id_seccion,
                        id_materia=id_materia,
                        vista=vista,
                    )
                )
            cfg = obtener_configuracion()
            validos_rows = ejecutar_consulta(
                "SELECT id FROM inscripciones WHERE id_seccion = %s AND estado = 'activo'",
                (seccion_actual["id"],),
            )
            ids_validos = {r["id"] for r in validos_rows}
            inscripciones_ids = [
                iid for iid in request.form.getlist("id_inscripcion")
                if iid.isdigit() and int(iid) in ids_validos
            ]
            try:
                if seccion_actual["tipo_escala"] == "literal":
                    registros = []
                    for iid in inscripciones_ids:
                        registros.append({
                            "id_inscripcion": int(iid),
                            "lapso_1": request.form.get(f"l1_{iid}"),
                            "lapso_2": request.form.get(f"l2_{iid}"),
                            "lapso_3": request.form.get(f"l3_{iid}"),
                            "definitiva": request.form.get(f"def_{iid}"),
                            "observaciones": request.form.get(f"obs_{iid}"),
                        })
                    guardar_notas_primaria(registros, user["id"])
                else:
                    if not id_materia:
                        raise ValueError("Debe seleccionar una materia.")
                    registros = []
                    for iid in inscripciones_ids:
                        registros.append({
                            "id_inscripcion": int(iid),
                            "lapso_1": request.form.get(f"l1_{iid}"),
                            "lapso_2": request.form.get(f"l2_{iid}"),
                            "lapso_3": request.form.get(f"l3_{iid}"),
                            "definitiva": request.form.get(f"def_{iid}"),
                            "tipo_evaluacion": request.form.get(f"te_{iid}"),
                            "mes": request.form.get(f"mes_{iid}"),
                            "anio": request.form.get(f"anio_{iid}"),
                        })
                    guardar_notas_secundaria(
                        id_materia,
                        registros,
                        user["id"],
                        cfg.get("mes_defecto", "07"),
                        cfg.get("anio_defecto", "2026"),
                    )
                if request.headers.get("X-Requested-With") == "fetch":
                    return jsonify({"ok": True, "mensaje": "Calificaciones guardadas correctamente."})
                flash("Calificaciones guardadas correctamente.", "success")
            except Exception as err:
                if request.headers.get("X-Requested-With") == "fetch":
                    return jsonify({"ok": False, "mensaje": str(err)}), 400
                flash(str(err), "error")
            return redirect(
                url_for(
                    "calificaciones.index",
                    id_seccion=id_seccion,
                    id_materia=id_materia,
                    vista=vista,
                    embed=request.values.get("embed") or None,
                )
            )

        if vista == "notas":
            if seccion_actual["tipo_escala"] == "literal":
                filas = obtener_notas_primaria_seccion(id_seccion)
            elif id_materia:
                mat_sel = next((m for m in materias if m["id"] == id_materia), None)
                if mat_sel:
                    filas = obtener_notas_secundaria_seccion_materia(id_seccion, id_materia)
                    filas_por_materia = [(mat_sel, filas)]
            else:
                for m in materias:
                    f_mat = obtener_notas_secundaria_seccion_materia(id_seccion, m["id"])
                    filas_por_materia.append((m, f_mat))
                if filas_por_materia:
                    filas = filas_por_materia[0][1]
        elif vista == "docentes":
            asignaciones = listar_asignaciones_seccion(id_periodo, id_seccion)
            docentes = listar_docentes(solo_activos=True)
        elif vista == "horario":
            asignaciones = listar_asignaciones_seccion(id_periodo, id_seccion)
            mapa_asignaciones = {str(a["id_materia"]): a["id_docente"] for a in asignaciones}
            if user["rol"] == "admin":
                docentes = listar_docentes(solo_activos=True)
            for b in obtener_horario_seccion(id_periodo, id_seccion):
                bloques_por_dia.setdefault(b["dia_semana"], []).append(b)

    lapsos_disponibles = [("1", "1.er Lapso")]
    lapsos_activos = {"l1": True, "l2": False, "l3": False, "def": False}
    if seccion_actual:
        if vista == "notas":
            eval_filas = (
                [f for _, lst in filas_por_materia for f in lst]
                if seccion_actual["tipo_escala"] == "numerica" and filas_por_materia
                else filas
            )
            if eval_filas:
                total_f = len(eval_filas)
                c1 = sum(1 for f in eval_filas if f.get("lapso_1") is not None)
                c2 = sum(1 for f in eval_filas if f.get("lapso_2") is not None)
                c3 = sum(1 for f in eval_filas if f.get("lapso_3") is not None)
                cdef = sum(1 for f in eval_filas if f.get("definitiva") is not None)
                lapsos_activos["l2"] = (c2 > 0) or (c1 * 100 >= total_f * 90)
                lapsos_activos["l3"] = (c3 > 0) or (c2 * 100 >= total_f * 90)
                lapsos_activos["def"] = (cdef > 0) or (c3 > 0) or lapsos_activos["l3"]
        elif vista == "estudiantes":
            if seccion_actual["tipo_escala"] == "literal":
                filas = obtener_notas_primaria_seccion(id_seccion)
                total_f = len(filas)
                if total_f > 0:
                    c1 = sum(1 for f in filas if f.get("lapso_1") is not None)
                    c2 = sum(1 for f in filas if f.get("lapso_2") is not None)
                    c3 = sum(1 for f in filas if f.get("lapso_3") is not None)
                    cdef = sum(1 for f in filas if f.get("definitiva") is not None)
                    if c2 > 0 or c1 * 100 >= total_f * 90:
                        lapsos_disponibles.append(("2", "2.do Lapso"))
                    if c3 > 0 or c2 * 100 >= total_f * 90:
                        lapsos_disponibles.append(("3", "3.er Lapso"))
                    if cdef > 0 or c3 > 0 or len(lapsos_disponibles) >= 3:
                        lapsos_disponibles.append(("final", "Total / Definitiva"))
            else:
                sabana = obtener_sabana_secundaria_seccion(id_seccion)
                mats_eval = (
                    [m for m in materias_grado if m["id"] == id_materia]
                    if id_materia
                    else materias_grado
                )
                total_pares = len(sabana) * len(mats_eval)
                if total_pares > 0:
                    c1 = sum(1 for est in sabana for m in mats_eval if (est["notas"].get(m["id"]) or {}).get("lapso_1") is not None)
                    c2 = sum(1 for est in sabana for m in mats_eval if (est["notas"].get(m["id"]) or {}).get("lapso_2") is not None)
                    c3 = sum(1 for est in sabana for m in mats_eval if (est["notas"].get(m["id"]) or {}).get("lapso_3") is not None)
                    cdef = sum(1 for est in sabana for m in mats_eval if (est["notas"].get(m["id"]) or {}).get("definitiva") is not None)
                    if c2 > 0 or c1 * 100 >= total_pares * 90:
                        lapsos_disponibles.append(("2", "2.do Lapso"))
                    if c3 > 0 or c2 * 100 >= total_pares * 90:
                        lapsos_disponibles.append(("3", "3.er Lapso"))
                    if cdef > 0 or c3 > 0 or len(lapsos_disponibles) >= 3:
                        lapsos_disponibles.append(("final", "Total / Final"))

    if not any(k == lapso for k, _ in lapsos_disponibles):
        lapso = "1"

    return render_template(
        "calificaciones/index.html",
        periodos=periodos,
        periodo=periodo,
        periodo_activo=periodo_activo,
        id_periodo=id_periodo,
        solo_lectura=solo_lectura,
        vista=vista,
        lapso=lapso,
        lapsos_disponibles=lapsos_disponibles,
        grados_disponibles=grados_disponibles,
        secciones=secciones_grado,
        seccion_actual=seccion_actual,
        materias=materias,
        materias_grado=materias_grado,
        id_grado=id_grado,
        id_seccion=id_seccion,
        id_materia=id_materia,
        filas=filas,
        filas_por_materia=filas_por_materia,
        lapsos_activos=lapsos_activos,
        sabana=sabana,
        miembros=miembros,
        asignaciones=asignaciones,
        docentes=docentes,
        mapa_asignaciones=mapa_asignaciones,
        dias=DIAS_SEMANA,
        bloques_por_dia=bloques_por_dia,
        escala_literal=ESCALA_LITERAL,
        tipos_ev=TIPOS_EVALUACION,
        cfg=obtener_configuracion(),
    )


@calificaciones_bp.route("/asignaciones", methods=["POST"])
@admin_required
def guardar_asignaciones():
    periodo = obtener_periodo_activo()
    if not periodo:
        msg = "No hay período escolar activo."
        if request.headers.get("X-Requested-With") == "fetch":
            return jsonify({"ok": False, "mensaje": msg}), 400
        flash(msg, "error")
        return redirect(url_for("calificaciones.index"))

    id_seccion = request.form.get("id_seccion", type=int)
    id_grado = request.form.get("id_grado", type=int)
    if not id_seccion:
        msg = "Sección inválida."
        if request.headers.get("X-Requested-With") == "fetch":
            return jsonify({"ok": False, "mensaje": msg}), 400
        flash(msg, "error")
        return redirect(url_for("calificaciones.index"))

    try:
        accion = request.form.get("accion")
        if accion == "titular_primaria":
            id_doc_guia = request.form.get("id_docente_guia", type=int)
            if not id_doc_guia:
                raise ValueError("Seleccione primero un Docente Titular para la sección.")
            guardar_asignaciones_seccion_lote(periodo["id"], id_seccion, id_doc_guia, {})
            cant = asignar_titular_a_materias_primaria(periodo["id"], id_seccion, id_doc_guia)
            msg = f"Docente titular asignado a {cant} materias regulares."
        else:
            id_doc_guia = request.form.get("id_docente_guia", type=int)
            asig = {}
            for key, val in request.form.items():
                if key.startswith("docente_") and key[8:].isdigit():
                    asig[int(key[8:])] = int(val) if val.isdigit() else None
            guardar_asignaciones_seccion_lote(periodo["id"], id_seccion, id_doc_guia, asig)
            msg = "Asignaciones docentes guardadas correctamente."

        if request.headers.get("X-Requested-With") == "fetch":
            return jsonify({"ok": True, "mensaje": msg})
        flash(msg, "success")
    except Exception as err:
        if request.headers.get("X-Requested-With") == "fetch":
            return jsonify({"ok": False, "mensaje": str(err)}), 400
        flash(str(err), "error")
    return redirect(url_for("calificaciones.index", id_grado=id_grado, id_seccion=id_seccion, vista="docentes"))
