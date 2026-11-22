import pymysql
from flask import g, has_app_context
from pymysql.cursors import DictCursor
from config import Config


def _nueva_conexion(usar_bd: bool = True):
    params = {
        "host": Config.DB_HOST,
        "port": Config.DB_PORT,
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False,
    }
    if usar_bd:
        params["database"] = Config.DB_NAME
    return pymysql.connect(**params)


def obtener_conexion(usar_bd: bool = True):
    """Retorna una conexion PyMySQL. Para transacciones compuestas abre una dedicada."""
    return _nueva_conexion(usar_bd=usar_bd)


def obtener_conexion_peticion():
    """Reutiliza una sola conexion TCP por peticion HTTP dentro de Flask."""
    if not has_app_context():
        return _nueva_conexion(usar_bd=True), True
    conn = getattr(g, "_db_conn", None)
    if conn is None or not conn.open:
        conn = _nueva_conexion(usar_bd=True)
        g._db_conn = conn
    return conn, False


def cerrar_conexion_peticion(exception=None):
    conn = g.pop("_db_conn", None)
    if conn is not None and conn.open:
        conn.close()


def ejecutar_consulta(sql: str, params: tuple = (), uno: bool = False):
    """Ejecuta un SELECT parametrizado reutilizando la conexion de la peticion."""
    conn, cerrar = obtener_conexion_peticion()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone() if uno else cur.fetchall()
    finally:
        if cerrar:
            conn.close()


def ejecutar_accion(sql: str, params: tuple = ()) -> int:
    """Ejecuta INSERT/UPDATE/DELETE parametrizado con commit y retorna lastrowid o rowcount."""
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.lastrowid if cur.lastrowid else cur.rowcount
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
