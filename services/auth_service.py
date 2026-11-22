from functools import wraps
from flask import flash, g, has_app_context, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from db import ejecutar_accion, ejecutar_consulta

ROLES_VALIDOS = ("admin", "operador", "docente")


def verificar_credenciales(username: str, password: str):
    """Valida usuario activo y hash scrypt; retorna el usuario o None."""
    user = ejecutar_consulta(
        "SELECT id, nombre, username, password_hash, rol, id_docente, activo, debe_cambiar_password "
        "FROM usuarios WHERE username = %s",
        (username.strip(),),
        uno=True,
    )
    if not user or not user["activo"]:
        return None
    if not check_password_hash(user["password_hash"], password):
        return None
    return user


def obtener_usuario_actual():
    """Consulta en vivo el usuario de la sesion (con cache por peticion en g)."""
    if has_app_context() and hasattr(g, "_usuario_actual"):
        return g._usuario_actual
    uid = session.get("usuario_id")
    if not uid:
        return None
    user = ejecutar_consulta(
        "SELECT id, nombre, username, rol, id_docente, activo, debe_cambiar_password "
        "FROM usuarios WHERE id = %s",
        (uid,),
        uno=True,
    )
    if not user or not user["activo"]:
        session.clear()
        if has_app_context():
            g._usuario_actual = None
        return None
    if has_app_context():
        g._usuario_actual = user
    return user


def login_required(f):
    """Exige sesion valida, usuario activo y cambio de clave obligatorio completado."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = obtener_usuario_actual()
        if not user:
            flash("Debe iniciar sesion para acceder.", "error")
            return redirect(url_for("auth.login"))
        if user["debe_cambiar_password"]:
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    return decorated


def roles_required(*roles):
    """Exige usuario activo con uno de los roles permitidos."""
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = obtener_usuario_actual()
            if not user:
                flash("Debe iniciar sesion para acceder.", "error")
                return redirect(url_for("auth.login"))
            if user["debe_cambiar_password"]:
                return redirect(url_for("dashboard.index"))
            if user["rol"] not in roles:
                flash("No tiene permisos para acceder a este modulo.", "error")
                return redirect(url_for("dashboard.index"))
            return f(*args, **kwargs)
        return decorated
    return wrapper


def admin_required(f):
    """Exige usuario activo con rol admin."""
    return roles_required("admin")(f)


def listar_usuarios():
    return ejecutar_consulta(
        "SELECT u.id, u.nombre, u.username, COALESCE(NULLIF(u.correo, ''), d.correo) AS correo, "
        "u.correo AS correo_usuario, u.rol, u.id_docente, u.activo, u.debe_cambiar_password, u.creado_en, "
        "CONCAT(d.apellidos, ' ', d.nombres) AS docente_nombre "
        "FROM usuarios u LEFT JOIN docentes d ON d.id = u.id_docente "
        "ORDER BY u.id ASC"
    )


def registrar_usuario(nombre: str, username: str, password: str, rol: str, id_docente: int = None, correo: str = ""):
    if rol not in ROLES_VALIDOS:
        raise ValueError("Rol inválido.")
    if len(password) < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres.")
    if rol == "docente" and not id_docente:
        raise ValueError("Debe vincular un docente registrado para el rol Docente.")
    existente = ejecutar_consulta(
        "SELECT id FROM usuarios WHERE username = %s", (username.strip(),), uno=True
    )
    if existente:
        raise ValueError("El nombre de usuario ya existe.")
    correo_limpio = (correo or "").strip().lower() or None
    return ejecutar_accion(
        "INSERT INTO usuarios (nombre, username, correo, password_hash, rol, id_docente, activo, debe_cambiar_password) "
        "VALUES (%s, %s, %s, %s, %s, %s, TRUE, TRUE)",
        (
            nombre.strip(),
            username.strip(),
            correo_limpio,
            generate_password_hash(password, method="scrypt"),
            rol,
            id_docente if rol == "docente" else None,
        ),
    )


def actualizar_password(usuario_id: int, nueva_password: str, obligar_cambio: bool = False, admin_id: int = None):
    if len(nueva_password) < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres.")
    ejecutar_accion(
        "UPDATE usuarios SET password_hash = %s, debe_cambiar_password = %s WHERE id = %s",
        (generate_password_hash(nueva_password, method="scrypt"), obligar_cambio, usuario_id),
    )
    if obligar_cambio:
        ejecutar_accion(
            "UPDATE solicitudes_recuperacion SET estado = 'atendida', atendido_en = NOW(), atendido_por = %s "
            "WHERE id_usuario = %s AND estado = 'pendiente'",
            (admin_id, usuario_id),
        )


def cambiar_password_propia(usuario_id: int, actual: str, nueva: str, confirmar: str):
    if nueva != confirmar:
        raise ValueError("La nueva contrasena y su confirmacion no coinciden.")
    if len(nueva) < 6:
        raise ValueError("La nueva contrasena debe tener al menos 6 caracteres.")
    if actual == nueva:
        raise ValueError("La nueva contrasena debe ser distinta a la actual.")
    user = ejecutar_consulta(
        "SELECT password_hash FROM usuarios WHERE id = %s", (usuario_id,), uno=True
    )
    if not user or not check_password_hash(user["password_hash"], actual):
        raise ValueError("La contrasena actual es incorrecta.")
    actualizar_password(usuario_id, nueva, obligar_cambio=False)


def cambiar_password_inicial(usuario_id: int, nueva: str, confirmar: str):
    """Cambio obligatorio al ingresar por primera vez sin volver a pedir la clave temporal."""
    if nueva != confirmar:
        raise ValueError("La nueva contrasena y su confirmacion no coinciden.")
    if len(nueva) < 6:
        raise ValueError("La nueva contrasena debe tener al menos 6 caracteres.")
    user = ejecutar_consulta(
        "SELECT password_hash FROM usuarios WHERE id = %s", (usuario_id,), uno=True
    )
    if not user:
        raise ValueError("Usuario no encontrado.")
    if check_password_hash(user["password_hash"], nueva):
        raise ValueError("La nueva contrasena debe ser distinta a la clave temporal.")
    actualizar_password(usuario_id, nueva, obligar_cambio=False)


def editar_usuario(usuario_id: int, nombre: str, rol: str, admin_actual_id: int, id_docente: int = None, correo: str = ""):
    if rol not in ROLES_VALIDOS:
        raise ValueError("Rol inválido.")
    if not nombre.strip():
        raise ValueError("El nombre es obligatorio.")
    if usuario_id == admin_actual_id and rol != "admin":
        raise ValueError("No puede quitarse su propio rol de Administrador.")
    if rol == "docente" and not id_docente:
        raise ValueError("Debe vincular un docente para el rol Docente.")
    correo_limpio = (correo or "").strip().lower() or None
    ejecutar_accion(
        "UPDATE usuarios SET nombre = %s, correo = %s, rol = %s, id_docente = %s WHERE id = %s",
        (nombre.strip(), correo_limpio, rol, id_docente if rol == "docente" else None, usuario_id),
    )


def toggle_estado_usuario(usuario_id: int, admin_actual_id: int):
    if usuario_id == admin_actual_id:
        raise ValueError("No puede suspender su propia cuenta en sesión.")
    ejecutar_accion("UPDATE usuarios SET activo = NOT activo WHERE id = %s", (usuario_id,))


def solicitar_recuperacion_por_correo(correo: str) -> bool:
    """Registra una notificacion al administrador si el correo pertenece a un usuario activo."""
    correo_limpio = (correo or "").strip().lower()
    if not correo_limpio or "@" not in correo_limpio:
        raise ValueError("Ingrese un correo electrónico válido.")

    usuario = ejecutar_consulta(
        "SELECT u.id FROM usuarios u "
        "LEFT JOIN docentes d ON d.id = u.id_docente "
        "WHERE u.activo = TRUE AND (LOWER(TRIM(u.correo)) = %s OR LOWER(TRIM(d.correo)) = %s) "
        "LIMIT 1",
        (correo_limpio, correo_limpio),
        uno=True,
    )
    if not usuario:
        return False

    pendiente = ejecutar_consulta(
        "SELECT id FROM solicitudes_recuperacion WHERE id_usuario = %s AND estado = 'pendiente' LIMIT 1",
        (usuario["id"],),
        uno=True,
    )
    if pendiente:
        ejecutar_accion(
            "UPDATE solicitudes_recuperacion SET correo_solicitado = %s, creado_en = NOW() WHERE id = %s",
            (correo_limpio, pendiente["id"]),
        )
    else:
        ejecutar_accion(
            "INSERT INTO solicitudes_recuperacion (id_usuario, correo_solicitado, estado) VALUES (%s, %s, 'pendiente')",
            (usuario["id"], correo_limpio),
        )
    return True


def listar_solicitudes_recuperacion_pendientes():
    return ejecutar_consulta(
        "SELECT s.id, s.id_usuario, s.correo_solicitado, s.creado_en, "
        "u.nombre, u.username, u.rol "
        "FROM solicitudes_recuperacion s "
        "JOIN usuarios u ON u.id = s.id_usuario "
        "WHERE s.estado = 'pendiente' "
        "ORDER BY s.creado_en DESC"
    )


def contar_solicitudes_recuperacion_pendientes() -> int:
    fila = ejecutar_consulta(
        "SELECT COUNT(*) AS c FROM solicitudes_recuperacion WHERE estado = 'pendiente'",
        uno=True,
    )
    return fila["c"] if fila else 0


def descartar_solicitud_recuperacion(solicitud_id: int, admin_id: int):
    ejecutar_accion(
        "UPDATE solicitudes_recuperacion SET estado = 'descartada', atendido_en = NOW(), atendido_por = %s "
        "WHERE id = %s AND estado = 'pendiente'",
        (admin_id, solicitud_id),
    )
