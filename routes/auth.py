import secrets
import time
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from services.academico_service import obtener_periodo_por_id
from services.auth_service import (
    cambiar_password_inicial,
    cambiar_password_propia,
    login_required,
    obtener_usuario_actual,
    solicitar_recuperacion_por_correo,
    verificar_credenciales,
)

auth_bp = Blueprint("auth", __name__)

_INTENTOS_FALLIDOS = {}
_MAX_INTENTOS_LOGIN = 5
_BLOQUEO_SEGUNDOS = 300


def _clave_intento_login(username: str) -> tuple:
    ip = (request.remote_addr or "local").strip()
    return (ip, username.strip().lower())


def _segundos_bloqueo_restantes(clave: tuple) -> int:
    rec = _INTENTOS_FALLIDOS.get(clave)
    if not rec:
        return 0
    bloqueado_hasta = rec.get("bloqueado_hasta", 0)
    ahora = time.time()
    if bloqueado_hasta > ahora:
        return int(bloqueado_hasta - ahora) + 1
    if bloqueado_hasta:
        _INTENTOS_FALLIDOS.pop(clave, None)
    return 0


def _registrar_fallo_login(clave: tuple):
    ahora = time.time()
    rec = _INTENTOS_FALLIDOS.get(clave, {"count": 0, "bloqueado_hasta": 0})
    rec["count"] += 1
    if rec["count"] >= _MAX_INTENTOS_LOGIN:
        rec["bloqueado_hasta"] = ahora + _BLOQUEO_SEGUNDOS
        rec["count"] = 0
    _INTENTOS_FALLIDOS[clave] = rec


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("usuario_id") and obtener_usuario_actual():
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        clave = _clave_intento_login(username)
        restante = _segundos_bloqueo_restantes(clave)
        if restante > 0:
            mins = max(1, (restante + 59) // 60)
            flash(f"Demasiados intentos fallidos. Espera {mins} minuto(s) antes de volver a intentar.", "error")
            return render_template("auth/login.html", username_previo=username, error_login=True)

        user = verificar_credenciales(username, password)
        if not user:
            _registrar_fallo_login(clave)
            flash("Usuario o contraseña inválidos, o cuenta suspendida.", "error")
            return render_template("auth/login.html", username_previo=username, error_login=True)

        _INTENTOS_FALLIDOS.pop(clave, None)
        session.clear()
        session.permanent = True
        session["_csrf_token"] = secrets.token_hex(24)
        session["usuario_id"] = user["id"]
        session["usuario_rol"] = user["rol"]
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/recuperar-acceso", methods=["POST"])
def recuperar_acceso():
    correo = request.form.get("correo", "").strip()
    try:
        encontrado = solicitar_recuperacion_por_correo(correo)
        if encontrado:
            flash(
                "Solicitud enviada. El Administrador recibió la notificación y le asignará una clave temporal.",
                "success",
            )
        else:
            flash(
                "Si el correo está registrado en el sistema, el Administrador recibirá la notificación para restablecer su acceso.",
                "success",
            )
    except ValueError as err:
        flash(str(err), "error")
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Sesion cerrada correctamente.", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/cambiar-password-obligatorio", methods=["POST"])
def cambiar_password_obligatorio():
    user = obtener_usuario_actual()
    if not user:
        return redirect(url_for("auth.login"))
    if not user["debe_cambiar_password"]:
        return redirect(url_for("dashboard.index"))

    try:
        cambiar_password_inicial(
            user["id"],
            request.form.get("nueva", ""),
            request.form.get("confirmar", ""),
        )
        flash("Contrasena personal guardada. Bienvenido al sistema.", "success")
    except ValueError as err:
        flash(str(err), "error")
    return redirect(url_for("dashboard.index"))


@auth_bp.route("/cambiar-periodo-consulta", methods=["POST"])
@login_required
def cambiar_periodo_consulta():
    raw = (request.form.get("id_periodo") or "").strip()
    if raw == "activo" or not raw:
        session.pop("periodo_consulta_id", None)
    elif raw.isdigit():
        p = obtener_periodo_por_id(int(raw))
        if p:
            session["periodo_consulta_id"] = p["id"]
    destino = (request.form.get("next") or "").strip()
    if not destino.startswith("/") or destino.startswith("//"):
        destino = url_for("dashboard.index")
    # Limpiar parametros de seccion/grado/periodo de la URL destino para evitar conflictos entre periodos
    base_path = destino.split("?", 1)[0]
    return redirect(base_path)


@auth_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    user = obtener_usuario_actual()
    if request.method == "POST":
        try:
            cambiar_password_propia(
                user["id"],
                request.form.get("actual", ""),
                request.form.get("nueva", ""),
                request.form.get("confirmar", ""),
            )
            flash("Contrasena actualizada correctamente.", "success")
        except ValueError as err:
            flash(str(err), "error")
        return redirect(url_for("auth.perfil"))

    return render_template("auth/perfil.html", usuario=user)
