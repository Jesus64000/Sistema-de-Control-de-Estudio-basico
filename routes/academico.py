from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from services.academico_service import (
    activar_periodo,
    actualizar_docente,
    actualizar_docente_seccion,
    actualizar_grado,
    actualizar_materia,
    actualizar_periodo,
    asignar_docente_materia,
    asignar_titular_a_materias_primaria,
    cambiar_cierre_periodo,
    copiar_secciones_periodo,
    crear_docente,
    crear_grado,
    crear_materia,
    crear_periodo,
    crear_seccion,
    guardar_asignaciones_docente_lote,
    listar_asignaciones_seccion,
    listar_bloques,
    listar_docentes,
    listar_docentes_con_usuario,
    listar_grados_con_resumen,
    listar_materias,
    listar_niveles,
    listar_periodos,
    listar_secciones,
    listar_secciones_con_resumen,
    obtener_carga_editable_docente,
    obtener_periodo_activo,
    obtener_periodo_por_id,
    obtener_resumen_cierre_periodo,
    obtener_resumen_docente,
    resolver_periodo_consulta,
    toggle_docente,
    toggle_materia,
)
from services.auth_service import admin_required, roles_required
from services.horario_service import DIAS_SEMANA, obtener_horario_docente
from services.estudiante_service import listar_inscripciones

academico_bp = Blueprint("academico", __name__, url_prefix="/academico")


def _respuesta_academico(ok: bool, mensaje: str):
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"ok": ok, "mensaje": mensaje}), (200 if ok else 400)
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("academico.index"))


@academico_bp.route("/", methods=["GET"])
@admin_required
def index():
    periodo_sel, periodo_activo, periodos, solo_lectura = resolver_periodo_consulta(
        request.args.get("id_periodo", type=int),
        session.get("periodo_consulta_id"),
    )
    id_periodo = periodo_sel["id"] if periodo_sel else 0
    return render_template(
        "academico/index.html",
        periodos=periodos,
        periodo_activo=periodo_activo,
        periodo_seleccionado=periodo_sel,
        solo_lectura=solo_lectura,
        niveles=listar_niveles(),
        grados=listar_grados_con_resumen(id_periodo),
        docentes=listar_docentes_con_usuario(id_periodo),
        secciones=listar_secciones_con_resumen(id_periodo) if id_periodo else [],
        bloques=listar_bloques(),
        materias=listar_materias(),
    )


@academico_bp.route("/api/secciones", methods=["GET"])
@roles_required("admin", "operador")
def api_secciones_periodo():
    pid = request.args.get("id_periodo", type=int)
    if not pid:
        return jsonify({"secciones": []})
    secs = listar_secciones(pid)
    return jsonify({
        "secciones": [
            {
                "id": s["id"],
                "nombre": s["nombre"],
                "grado_nombre": s["grado_nombre"],
                "nivel_nombre": s["nivel_nombre"],
                "turno": s["turno"],
            }
            for s in secs
        ]
    })


@academico_bp.route("/periodos/crear", methods=["POST"])
@admin_required
def periodo_crear():
    try:
        crear_periodo(
            request.form.get("nombre", ""),
            request.form.get("fecha_inicio"),
            request.form.get("fecha_fin"),
        )
        return _respuesta_academico(True, "Período escolar creado.")
    except Exception as err:
        return _respuesta_academico(False, str(err))


@academico_bp.route("/periodos/editar/<int:pid>", methods=["POST"])
@admin_required
def periodo_editar(pid: int):
    try:
        actualizar_periodo(
            pid,
            request.form.get("nombre", ""),
            request.form.get("fecha_inicio"),
            request.form.get("fecha_fin"),
        )
        return _respuesta_academico(True, "Período escolar actualizado.")
    except Exception as err:
        return _respuesta_academico(False, str(err))


@academico_bp.route("/periodos/activar/<int:pid>", methods=["POST"])
@admin_required
def periodo_activar(pid: int):
    activar_periodo(pid)
    session["periodo_consulta_id"] = pid
    return _respuesta_academico(True, "Período escolar activado.")


@academico_bp.route("/api/periodos/<int:pid>/checklist-cierre", methods=["GET"])
@admin_required
def api_periodo_checklist_cierre(pid: int):
    try:
        resumen = obtener_resumen_cierre_periodo(pid)
        return jsonify({"ok": True, **resumen})
    except Exception as err:
        return jsonify({"ok": False, "mensaje": str(err)}), 404


@academico_bp.route("/periodos/cerrar/<int:pid>", methods=["POST"])
@admin_required
def periodo_cerrar(pid: int):
    try:
        periodo = obtener_periodo_por_id(pid)
        if not periodo:
            raise ValueError("Período escolar no encontrado.")
        nuevo_estado = not bool(periodo.get("cerrado"))
        cambiar_cierre_periodo(pid, nuevo_estado)
        msg = (
            f"Período {periodo['nombre']} cerrado formalmente (solo lectura)."
            if nuevo_estado
            else f"Período {periodo['nombre']} reabierto para edición."
        )
        return _respuesta_academico(True, msg)
    except Exception as err:
        return _respuesta_academico(False, str(err))


@academico_bp.route("/secciones/copiar", methods=["POST"])
@admin_required
def secciones_copiar():
    periodo_activo = obtener_periodo_activo()
    if not periodo_activo:
        return _respuesta_academico(False, "Debe activar un período escolar destino primero.")
    try:
        id_origen = request.form.get("id_periodo_origen", type=int)
        copiar_guias = request.form.get("copiar_guias") == "1"
        copiar_asigs = request.form.get("copiar_asignaciones") == "1"
        res = copiar_secciones_periodo(
            id_origen,
            periodo_activo["id"],
            copiar_guias=copiar_guias,
            copiar_asignaciones=copiar_asigs,
        )
        msg = (
            f"Copia completada: {res['secciones_creadas']} sección(es) creada(s)"
            + (f", {res['secciones_omitidas']} ya existente(s)" if res["secciones_omitidas"] else "")
            + (f", {res['asignaciones_copiadas']} asignación(es) de materias" if copiar_asigs else "")
            + "."
        )
        return _respuesta_academico(True, msg)
    except Exception as err:
        return _respuesta_academico(False, str(err))


@academico_bp.route("/grados/crear", methods=["POST"])
@admin_required
def grado_crear():
    try:
        crear_grado(
            int(request.form.get("id_nivel")),
            request.form.get("nombre", ""),
            int(request.form.get("orden") or 1),
        )
        return _respuesta_academico(True, "Grado/Año creado correctamente.")
    except Exception as err:
        return _respuesta_academico(False, str(err))


@academico_bp.route("/grados/editar/<int:gid>", methods=["POST"])
@admin_required
def grado_editar(gid: int):
    try:
        actualizar_grado(
            gid,
            int(request.form.get("id_nivel")),
            request.form.get("nombre", ""),
            int(request.form.get("orden") or 1),
        )
        return _respuesta_academico(True, "Grado/Año actualizado correctamente.")
    except Exception as err:
        return _respuesta_academico(False, str(err))


@academico_bp.route("/docentes/crear", methods=["POST"])
@admin_required
def docente_crear():
    try:
        crear_docente(
            request.form.get("cedula", ""),
            request.form.get("nombres", ""),
            request.form.get("apellidos", ""),
            request.form.get("telefono", ""),
            request.form.get("especialidad", ""),
            request.form.get("correo", ""),
            request.form.get("direccion", ""),
            request.form.get("categoria", "Media General"),
        )
        return _respuesta_academico(True, "Docente registrado.")
    except Exception as err:
        return _respuesta_academico(False, str(err))


@academico_bp.route("/docentes/editar/<int:did>", methods=["POST"])
@admin_required
def docente_editar(did: int):
    try:
        actualizar_docente(
            did,
            request.form.get("cedula", ""),
            request.form.get("nombres", ""),
            request.form.get("apellidos", ""),
            request.form.get("telefono", ""),
            request.form.get("especialidad", ""),
            request.form.get("correo", ""),
            request.form.get("direccion", ""),
            request.form.get("categoria", "Media General"),
        )
        return _respuesta_academico(True, "Datos del docente actualizados.")
    except Exception as err:
        return _respuesta_academico(False, str(err))


@academico_bp.route("/docentes/toggle/<int:did>", methods=["POST"])
@admin_required
def docente_toggle(did: int):
    toggle_docente(did)
    return _respuesta_academico(True, "Estado del docente actualizado.")


@academico_bp.route("/api/docentes/<int:did>/ficha", methods=["GET"])
@admin_required
def api_docente_ficha(did: int):
    periodo_sel, periodo_activo, _, _ = resolver_periodo_consulta(
        request.args.get("id_periodo", type=int),
        session.get("periodo_consulta_id"),
    )
    periodo_ref = periodo_sel or periodo_activo
    pid = periodo_ref["id"] if periodo_ref else 0
    resumen = obtener_resumen_docente(pid, did)
    if not resumen:
        return jsonify({"ok": False, "mensaje": "Docente no encontrado."}), 404
    horario_raw = obtener_horario_docente(pid, did) if pid else []
    bloques_dia = []
    minutos_total = 0
    for dnum, dnom in DIAS_SEMANA.items():
        items = []
        for b in horario_raw:
            if b["dia_semana"] == dnum:
                hi_str = str(b["hora_inicio"])[:5]
                hf_str = str(b["hora_fin"])[:5]
                try:
                    h1, m1 = map(int, hi_str.split(":"))
                    h2, m2 = map(int, hf_str.split(":"))
                    minutos_total += max(0, (h2 * 60 + m2) - (h1 * 60 + m1))
                except Exception:
                    pass
                items.append({
                    "hi": hi_str,
                    "hf": hf_str,
                    "grado": b["grado_nombre"],
                    "seccion": b["seccion_nombre"],
                    "materia": b.get("materia_nombre") or b.get("descripcion_bloque") or "Bloque",
                    "aula": b.get("aula") or "",
                })
        bloques_dia.append({"dia": dnom, "bloques": items})

    return jsonify({
        "ok": True,
        "periodo_nombre": periodo_ref["nombre"] if periodo_ref else "Sin período",
        "docente": resumen["docente"],
        "usuario": resumen.get("usuario"),
        "guias": resumen["guias"],
        "asignaciones": resumen["asignaciones"],
        "horario": bloques_dia,
        "total_bloques": len(horario_raw),
        "horas_semana": round(minutos_total / 60.0, 1),
    })


@academico_bp.route("/api/docentes/<int:did>/carga", methods=["GET"])
@admin_required
def api_docente_carga(did: int):
    periodo = obtener_periodo_activo()
    if not periodo:
        return jsonify({"ok": False, "mensaje": "No hay período escolar activo."}), 400
    datos = obtener_carga_editable_docente(periodo["id"], did)
    if not datos:
        return jsonify({"ok": False, "mensaje": "Docente no encontrado."}), 404
    return jsonify({"ok": True, "periodo_nombre": periodo["nombre"], **datos})


@academico_bp.route("/docentes/<int:did>/asignaciones", methods=["POST"])
@admin_required
def docente_asignaciones(did: int):
    periodo = obtener_periodo_activo()
    if not periodo:
        return _respuesta_academico(False, "No hay período escolar activo.")
    try:
        pares = request.form.getlist("asig_par")
        res = guardar_asignaciones_docente_lote(periodo["id"], did, pares)
        return _respuesta_academico(
            True, f"Materias asignadas al docente actualizadas ({res['total']} en el período {periodo['nombre']})."
        )
    except Exception as err:
        return _respuesta_academico(False, str(err))


@academico_bp.route("/secciones/crear", methods=["POST"])
@admin_required
def seccion_crear():
    periodo = obtener_periodo_activo()
    if not periodo:
        return _respuesta_academico(False, "Debe activar un período escolar primero.")
    try:
        id_doc = request.form.get("id_docente_titular_guia")
        crear_seccion(
            periodo["id"],
            int(request.form.get("id_grado_anio")),
            request.form.get("nombre", ""),
            request.form.get("turno", "Mañana"),
            int(id_doc) if id_doc else None,
        )
        return _respuesta_academico(True, "Sección creada.")
    except Exception as err:
        return _respuesta_academico(False, str(err))


@academico_bp.route("/secciones/<int:sid>/guia", methods=["POST"])
@admin_required
def seccion_guia(sid: int):
    try:
        id_doc = request.form.get("id_docente")
        actualizar_docente_seccion(sid, int(id_doc) if id_doc else None)
        return _respuesta_academico(True, "Docente Titular / Profesor Guía actualizado.")
    except Exception as err:
        return _respuesta_academico(False, str(err))


@academico_bp.route("/materias/crear", methods=["POST"])
@admin_required
def materia_crear():
    try:
        crear_materia(
            int(request.form.get("id_grado_anio")),
            int(request.form.get("id_bloque")),
            request.form.get("nombre", ""),
            request.form.get("codigo", ""),
            request.form.get("es_especial") == "1",
        )
        return _respuesta_academico(True, "Materia registrada.")
    except Exception as err:
        return _respuesta_academico(False, str(err))


@academico_bp.route("/materias/editar/<int:mid>", methods=["POST"])
@admin_required
def materia_editar(mid: int):
    try:
        actualizar_materia(
            mid,
            int(request.form.get("id_grado_anio")),
            int(request.form.get("id_bloque")),
            request.form.get("nombre", ""),
            request.form.get("codigo", ""),
            request.form.get("es_especial") == "1",
        )
        return _respuesta_academico(True, "Materia actualizada.")
    except Exception as err:
        return _respuesta_academico(False, str(err))


@academico_bp.route("/materias/toggle/<int:mid>", methods=["POST"])
@admin_required
def materia_toggle(mid: int):
    toggle_materia(mid)
    return _respuesta_academico(True, "Estado de materia actualizado.")


@academico_bp.route("/secciones/<int:sid>/asignaciones", methods=["GET", "POST"])
@admin_required
def seccion_asignaciones(sid: int):
    periodo = obtener_periodo_activo()
    if not periodo:
        flash("No hay periodo escolar activo.", "error")
        return redirect(url_for("academico.index"))

    secciones = listar_secciones(periodo["id"])
    seccion = next((s for s in secciones if s["id"] == sid), None)
    if not seccion:
        flash("Seccion no encontrada.", "error")
        return redirect(url_for("academico.index"))

    if request.method == "POST":
        accion = request.form.get("accion")
        if accion == "titular_primaria":
            if not seccion["id_docente_titular_guia"]:
                flash("Asigne primero un Docente Titular a esta seccion.", "error")
            else:
                cant = asignar_titular_a_materias_primaria(
                    periodo["id"], sid, seccion["id_docente_titular_guia"]
                )
                flash(f"Docente titular asignado a {cant} materias regulares.", "success")
        else:
            id_mat = int(request.form.get("id_materia"))
            id_doc = int(request.form.get("id_docente"))
            asignar_docente_materia(periodo["id"], sid, id_mat, id_doc)
            flash("Docente asignado a la materia.", "success")
        return redirect(url_for("academico.seccion_asignaciones", sid=sid))

    return render_template(
        "academico/asignaciones.html",
        seccion=seccion,
        materias=listar_materias(seccion["id_grado_anio"], solo_activas=True),
        docentes=listar_docentes(solo_activos=True),
        asignaciones=listar_asignaciones_seccion(periodo["id"], sid),
    )


@academico_bp.route("/secciones/<int:sid>/miembros", methods=["GET"])
@admin_required
def seccion_miembros(sid: int):
    periodo = obtener_periodo_activo()
    if not periodo:
        flash("No hay periodo escolar activo.", "error")
        return redirect(url_for("academico.index"))
    secciones = listar_secciones(periodo["id"])
    seccion = next((s for s in secciones if s["id"] == sid), None)
    if not seccion:
        flash("Seccion no encontrada.", "error")
        return redirect(url_for("academico.index"))
    miembros = listar_inscripciones(periodo["id"], id_seccion=sid)
    return render_template("academico/miembros.html", seccion=seccion, miembros=miembros, periodo=periodo)


@academico_bp.route("/docentes/<int:did>/detalle", methods=["GET"])
@admin_required
def docente_detalle(did: int):
    periodo = obtener_periodo_activo()
    id_periodo = periodo["id"] if periodo else 0
    resumen = obtener_resumen_docente(id_periodo, did)
    if not resumen:
        flash("Docente no encontrado.", "error")
        return redirect(url_for("academico.index"))
    bloques_docente = {d: [] for d in DIAS_SEMANA}
    if id_periodo:
        for b in obtener_horario_docente(id_periodo, did):
            bloques_docente.setdefault(b["dia_semana"], []).append(b)
    return render_template(
        "academico/docente_detalle.html",
        resumen=resumen,
        periodo=periodo,
        dias_semana=DIAS_SEMANA,
        bloques_docente=bloques_docente,
    )
