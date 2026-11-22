from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from services.academico_service import listar_docentes
from services.auth_service import (
    actualizar_password,
    admin_required,
    descartar_solicitud_recuperacion,
    editar_usuario,
    listar_solicitudes_recuperacion_pendientes,
    listar_usuarios,
    obtener_usuario_actual,
    registrar_usuario,
    toggle_estado_usuario,
)

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


def _respuesta_usuarios(ok: bool, mensaje: str):
    if request.headers.get("X-Requested-With") == "fetch":
        return jsonify({"ok": ok, "mensaje": mensaje}), (200 if ok else 400)
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("usuarios.index"))


@usuarios_bp.route("/", methods=["GET"])
@admin_required
def index():
    return render_template(
        "usuarios/index.html",
        usuarios=listar_usuarios(),
        docentes=listar_docentes(solo_activos=True),
        solicitudes_pendientes=listar_solicitudes_recuperacion_pendientes(),
    )


@usuarios_bp.route("/crear", methods=["POST"])
@admin_required
def crear():
    try:
        id_doc = request.form.get("id_docente")
        registrar_usuario(
            request.form.get("nombre", ""),
            request.form.get("username", ""),
            request.form.get("password", ""),
            request.form.get("rol", "operador"),
            int(id_doc) if id_doc else None,
            request.form.get("correo", ""),
        )
        return _respuesta_usuarios(True, "Usuario creado. Deberá cambiar su clave al ingresar.")
    except Exception as err:
        return _respuesta_usuarios(False, str(err))


@usuarios_bp.route("/cambiar-password/<int:uid>", methods=["POST"])
@admin_required
def reset_password(uid: int):
    try:
        actual = obtener_usuario_actual()
        actualizar_password(
            uid,
            request.form.get("nueva_password", ""),
            obligar_cambio=True,
            admin_id=actual["id"] if actual else None,
        )
        return _respuesta_usuarios(True, "Contraseña restablecida. El usuario deberá cambiarla al iniciar sesión.")
    except Exception as err:
        return _respuesta_usuarios(False, str(err))


@usuarios_bp.route("/editar/<int:uid>", methods=["POST"])
@admin_required
def editar(uid: int):
    try:
        actual = obtener_usuario_actual()
        id_doc = request.form.get("id_docente")
        editar_usuario(
            uid,
            request.form.get("nombre", ""),
            request.form.get("rol", "operador"),
            actual["id"],
            int(id_doc) if id_doc else None,
            request.form.get("correo", ""),
        )
        return _respuesta_usuarios(True, "Datos del usuario actualizados.")
    except Exception as err:
        return _respuesta_usuarios(False, str(err))


@usuarios_bp.route("/solicitudes/<int:sid>/descartar", methods=["POST"])
@admin_required
def descartar_solicitud(sid: int):
    actual = obtener_usuario_actual()
    descartar_solicitud_recuperacion(sid, actual["id"])
    return _respuesta_usuarios(True, "Solicitud descartada.")


@usuarios_bp.route("/toggle-estado/<int:uid>", methods=["POST"])
@admin_required
def toggle_estado(uid: int):
    try:
        actual = obtener_usuario_actual()
        toggle_estado_usuario(uid, actual["id"])
        return _respuesta_usuarios(True, "Estado de usuario actualizado.")
    except Exception as err:
        return _respuesta_usuarios(False, str(err))
