from datetime import datetime
from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, url_for
from services.academico_service import obtener_periodo_activo
from services.auth_service import admin_required
from services.backup_service import generar_respaldo_sql
from services.config_service import guardar_configuracion, obtener_configuracion

configuracion_bp = Blueprint("configuracion", __name__, url_prefix="/configuracion")

CLAVES_EDITABLES = [
    "nombre_plantel",
    "nombre_corto",
    "dependencia",
    "rif",
    "codigo_dea",
    "codigo_estadistico",
    "direccion",
    "director",
    "titulo_media",
    "encabezado_pais",
    "encabezado_ministerio",
    "centro_calidad",
    "pie_fiscal",
    "te_defecto",
    "mes_defecto",
    "anio_defecto",
]


@configuracion_bp.route("/", methods=["GET", "POST"])
@admin_required
def index():
    if request.method == "POST":
        datos = {k: request.form.get(k, "").strip() for k in CLAVES_EDITABLES}
        if datos["te_defecto"] not in ("F", "R", "A", "M", "***"):
            datos["te_defecto"] = "F"
        mes = datos["mes_defecto"].zfill(2) if datos["mes_defecto"].isdigit() else "07"
        if not ("01" <= mes <= "12"):
            msg = "El mes por defecto debe estar entre 01 (Enero) y 12 (Diciembre)."
            if request.headers.get("X-Requested-With") == "fetch":
                return jsonify({"ok": False, "mensaje": msg}), 400
            flash(msg, "error")
            return redirect(url_for("configuracion.index"))
        datos["mes_defecto"] = mes
        if not (datos["anio_defecto"].isdigit() and 2000 <= int(datos["anio_defecto"]) <= 2099):
            msg = "El año por defecto debe ser un año válido de 4 dígitos (ej. 2027)."
            if request.headers.get("X-Requested-With") == "fetch":
                return jsonify({"ok": False, "mensaje": msg}), 400
            flash(msg, "error")
            return redirect(url_for("configuracion.index"))
        guardar_configuracion(datos)
        msg = "Configuración institucional actualizada."
        if request.headers.get("X-Requested-With") == "fetch":
            return jsonify({"ok": True, "mensaje": msg})
        flash(msg, "success")
        return redirect(url_for("configuracion.index"))

    periodo_activo = obtener_periodo_activo()
    anio_sugerido = ""
    if periodo_activo and periodo_activo.get("nombre"):
        partes = str(periodo_activo["nombre"]).split("-")
        if len(partes) == 2 and partes[1].strip().isdigit():
            anio_sugerido = partes[1].strip()
    return render_template(
        "configuracion/index.html",
        cfg=obtener_configuracion(),
        periodo_activo=periodo_activo,
        anio_sugerido=anio_sugerido,
    )


@configuracion_bp.route("/respaldo-sql", methods=["GET"])
@admin_required
def respaldo_sql():
    try:
        buf = generar_respaldo_sql()
        marca = datetime.now().strftime("%Y%m%d_%H%M")
        return send_file(
            buf,
            mimetype="application/sql",
            as_attachment=True,
            download_name=f"Respaldo_Control_Estudio_{marca}.sql",
        )
    except Exception as err:
        flash(f"No se pudo generar el respaldo: {err}", "error")
        return redirect(url_for("configuracion.index"))
