from datetime import datetime
from io import BytesIO
from config import Config
from db import obtener_conexion


def generar_respaldo_sql() -> BytesIO:
    """Genera un archivo .sql completo de la base de datos usando PyMySQL (sin depender de mysqldump)."""
    conn = obtener_conexion(usar_bd=True)
    lineas = [
        f"-- Respaldo completo de Control de Estudio ({Config.DB_NAME})",
        f"-- Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "",
    ]
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            tablas = [next(iter(r.values())) for r in cur.fetchall()]

            for tabla in tablas:
                cur.execute(f"SHOW CREATE TABLE `{tabla}`")
                row_create = cur.fetchone()
                create_sql = row_create.get("Create Table") or list(row_create.values())[1]
                lineas.append(f"-- Estructura de `{tabla}`")
                lineas.append(f"DROP TABLE IF EXISTS `{tabla}`;")
                lineas.append(f"{create_sql};")
                lineas.append("")

                cur.execute(f"SELECT * FROM `{tabla}`")
                filas = cur.fetchall()
                if not filas:
                    continue

                cols = list(filas[0].keys())
                cols_sql = ", ".join(f"`{c}`" for c in cols)
                lineas.append(f"-- Datos de `{tabla}` ({len(filas)} registros)")
                for i in range(0, len(filas), 100):
                    lote = filas[i : i + 100]
                    valores_lote = []
                    for fila in lote:
                        vals = [conn.escape(fila[c]) for c in cols]
                        valores_lote.append("(" + ", ".join(vals) + ")")
                    lineas.append(
                        f"INSERT INTO `{tabla}` ({cols_sql}) VALUES\n  "
                        + ",\n  ".join(valores_lote)
                        + ";"
                    )
                lineas.append("")

        lineas.append("SET FOREIGN_KEY_CHECKS = 1;")
        buf = BytesIO("\n".join(lineas).encode("utf-8"))
        buf.seek(0)
        return buf
    finally:
        conn.close()
