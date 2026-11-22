import secrets
from flask import Flask, abort, g, request, session
from config import Config
from db import cerrar_conexion_peticion
from routes.academico import academico_bp
from routes.auth import auth_bp
from routes.calificaciones import calificaciones_bp
from routes.configuracion import configuracion_bp
from routes.dashboard import dashboard_bp
from routes.estudiantes import estudiantes_bp
from routes.horarios import horarios_bp
from routes.reportes import reportes_bp
from routes.usuarios import usuarios_bp
from services.academico_service import resolver_periodo_consulta
from services.auth_service import (
    contar_solicitudes_recuperacion_pendientes,
    listar_solicitudes_recuperacion_pendientes,
    obtener_usuario_actual,
)
from services.calificacion_service import numero_a_letras
from services.config_service import obtener_configuracion


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 86400
    app.teardown_appcontext(cerrar_conexion_peticion)

    @app.before_request
    def gestionar_csrf():
        if "_csrf_token" not in session:
            session["_csrf_token"] = secrets.token_hex(24)
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            token_enviado = request.form.get("_csrf_token") or request.headers.get("X-CSRFToken", "")
            if not secrets.compare_digest(session["_csrf_token"], token_enviado):
                abort(400, description="Token CSRF invalido o expirado.")

    @app.context_processor
    def inyectar_datos_globales():
        try:
            cfg = obtener_configuracion()
            periodo_consulta, periodo_activo, periodos_globales, periodo_solo_lectura = (
                resolver_periodo_consulta(id_periodo_sesion=session.get("periodo_consulta_id"))
            )
            usuario_actual = getattr(g, "_usuario_actual", None)
            if usuario_actual is None and session.get("usuario_id"):
                usuario_actual = obtener_usuario_actual()
            solicitudes_rec = (
                contar_solicitudes_recuperacion_pendientes()
                if usuario_actual and usuario_actual.get("rol") == "admin"
                else 0
            )
            notificaciones_rec = (
                listar_solicitudes_recuperacion_pendientes()[:5]
                if usuario_actual and usuario_actual.get("rol") == "admin" and solicitudes_rec > 0
                else []
            )
        except Exception:
            cfg = {}
            periodo_activo = None
            periodo_consulta = None
            periodos_globales = []
            periodo_solo_lectura = False
            usuario_actual = None
            solicitudes_rec = 0
            notificaciones_rec = []
        return {
            "csrf_token": session.get("_csrf_token", ""),
            "cfg_global": cfg,
            "periodo_global": periodo_activo,
            "periodo_consulta": periodo_consulta,
            "periodos_globales": periodos_globales,
            "periodo_solo_lectura": periodo_solo_lectura,
            "es_periodo_historico": bool(periodo_consulta and not periodo_consulta.get("activo")),
            "usuario_actual": usuario_actual,
            "solicitudes_rec_pendientes": solicitudes_rec,
            "notificaciones_rec": notificaciones_rec,
        }

    app.jinja_env.filters["numero_a_letras"] = numero_a_letras

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(configuracion_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(academico_bp)
    app.register_blueprint(horarios_bp)
    app.register_blueprint(estudiantes_bp)
    app.register_blueprint(calificaciones_bp)
    app.register_blueprint(reportes_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=Config.PORT, debug=Config.FLASK_DEBUG)
