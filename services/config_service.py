from db import ejecutar_consulta, obtener_conexion

_cache_config = None


def obtener_configuracion() -> dict:
    """Retorna la configuracion institucional (cacheada en memoria con invalidacion al guardar)."""
    global _cache_config
    if _cache_config is not None:
        return _cache_config
    filas = ejecutar_consulta("SELECT clave, valor FROM configuracion_institucional")
    _cache_config = {f["clave"]: f["valor"] for f in filas}
    return _cache_config


def invalidar_cache_config():
    global _cache_config
    _cache_config = None


def guardar_configuracion(datos: dict):
    """Actualiza multiples claves de configuracion institucional en una transaccion."""
    conn = obtener_conexion()
    try:
        with conn.cursor() as cur:
            for clave, valor in datos.items():
                cur.execute(
                    "INSERT INTO configuracion_institucional (clave, valor) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE valor = VALUES(valor)",
                    (clave, str(valor).strip()),
                )
        conn.commit()
        invalidar_cache_config()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
