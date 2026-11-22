from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from db import ejecutar_consulta
from services.academico_service import (
    listar_secciones,
    obtener_resumen_docente,
    resolver_periodo_consulta,
)
from services.auth_service import obtener_usuario_actual
from services.config_service import obtener_configuracion
from services.horario_service import DIAS_SEMANA, obtener_horario_docente

dashboard_bp = Blueprint("dashboard", __name__)


def _construir_avance(fila) -> dict:
    total = int(fila["total"] or 0) if fila else 0
    if total == 0:
        return {"total": 0, "tiene_notas": False, "lapsos_visibles": []}
    l1 = int(fila["l1"] or 0)
    l2 = int(fila["l2"] or 0)
    l3 = int(fila["l3"] or 0)
    de = int(fila["def"] or 0)
    tiene_notas = (l1 > 0 or l2 > 0 or l3 > 0 or de > 0)

    lapsos_visibles = []
    if tiene_notas:
        p1 = round(l1 * 100 / total)
        p2 = round(l2 * 100 / total)
        p3 = round(l3 * 100 / total)
        pdef = round(de * 100 / total)
        lapsos_visibles.append({"label": "Lapso 1", "cargados": l1, "total": total, "pct": p1})
        if l2 > 0 or p1 >= 90:
            lapsos_visibles.append({"label": "Lapso 2", "cargados": l2, "total": total, "pct": p2})
        if l3 > 0 or p2 >= 90:
            lapsos_visibles.append({"label": "Lapso 3", "cargados": l3, "total": total, "pct": p3})
        if de > 0 or l3 > 0:
            lapsos_visibles.append({"label": "Definitiva", "cargados": de, "total": total, "pct": pdef})

    return {
        "total": total,
        "tiene_notas": tiene_notas,
        "lapsos_visibles": lapsos_visibles,
    }


def _resumen_secciones(filas: list, limite: int = 3) -> str:
    nombres = [f'{f["grado"]} "{f["seccion"]}"' for f in filas[:limite]]
    extra = len(filas) - limite
    texto = ", ".join(nombres)
    if extra > 0:
        texto += f" (+{extra} más)"
    return texto


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
def index():
    user = obtener_usuario_actual()
    if not user:
        flash("Debe iniciar sesión para acceder.", "error")
        return redirect(url_for("auth.login"))

    periodo, periodo_activo, periodos, solo_lectura = resolver_periodo_consulta(
        request.args.get("id_periodo", type=int),
        session.get("periodo_consulta_id"),
    )
    es_historico = bool(periodo and not periodo["activo"])

    stats = {
        "estudiantes": 0,
        "retirados": 0,
        "primaria": 0,
        "media": 0,
        "docentes": 0,
        "usuarios": 0,
        "usr_admin": 0,
        "usr_operador": 0,
        "usr_docente": 0,
    }
    prosecucion = {
        "nuevos_ingresos": 0,
        "reinscritos": 0,
        "sin_reinscribir": 0,
        "egresados": 0,
        "total_registrados": 0,
    }
    alertas_pendientes = []
    avance_primaria = _construir_avance(None)
    avance_media = _construir_avance(None)
    ultimos_estudiantes = []
    cumpleaneros = []
    secciones = []
    secciones_activas = (
        listar_secciones(periodo_activo["id"])
        if periodo_activo and not periodo_activo.get("cerrado")
        else []
    )

    # KPI Docentes activos (general)
    stats["docentes"] = ejecutar_consulta(
        "SELECT COUNT(*) AS c FROM docentes WHERE activo = TRUE",
        uno=True,
    )["c"]

    # KPI Cuentas de Acceso por rol
    usr_roles = ejecutar_consulta(
        "SELECT rol, COUNT(*) AS c FROM usuarios WHERE activo = TRUE GROUP BY rol"
    )
    for ur in usr_roles:
        stats["usuarios"] += ur["c"]
        if ur["rol"] == "admin":
            stats["usr_admin"] = ur["c"]
        elif ur["rol"] == "operador":
            stats["usr_operador"] = ur["c"]
        elif ur["rol"] == "docente":
            stats["usr_docente"] = ur["c"]

    es_admin = user["rol"] == "admin"

    if user["rol"] in ("admin", "operador"):
        # 1. Configuracion institucional: Director(a)
        cfg = obtener_configuracion()
        director = (cfg.get("director") or "").strip()
        if not director or "por definir" in director.lower():
            alertas_pendientes.append({
                "titulo": "Director(a) del plantel sin definir",
                "detalle": "Configura el nombre del Director(a) para emitir certificados PDF oficiales.",
                "url": url_for("configuracion.index") if es_admin else None,
                "prioridad": "critica",
                "tipo": "config",
            })

        if not periodo:
            # 2. Sin periodo escolar activo
            alertas_pendientes.append({
                "titulo": "No hay período escolar activo",
                "detalle": "Activa un período para habilitar inscripciones, horarios y calificaciones.",
                "url": url_for("academico.index") if es_admin else None,
                "prioridad": "critica",
                "tipo": "periodo",
            })
        else:
            pid = periodo["id"]
            if user["rol"] in ("admin", "operador"):
                secciones = listar_secciones(pid)

            prosecucion["total_registrados"] = ejecutar_consulta(
                "SELECT COUNT(*) AS c FROM estudiantes WHERE activo = TRUE", uno=True
            )["c"]
            prosecucion["egresados"] = ejecutar_consulta(
                "SELECT COUNT(*) AS c FROM estudiantes WHERE activo = TRUE AND egresado = TRUE", uno=True
            )["c"]
            prosecucion["reinscritos"] = ejecutar_consulta(
                "SELECT COUNT(*) AS c FROM inscripciones i "
                "WHERE i.id_periodo = %s AND i.estado = 'activo' "
                "AND EXISTS (SELECT 1 FROM inscripciones i2 WHERE i2.id_estudiante = i.id_estudiante AND i2.id_periodo < i.id_periodo)",
                (pid,),
                uno=True,
            )["c"]
            prosecucion["sin_reinscribir"] = ejecutar_consulta(
                "SELECT COUNT(*) AS c FROM estudiantes e "
                "WHERE e.activo = TRUE AND e.egresado = FALSE "
                "AND NOT EXISTS (SELECT 1 FROM inscripciones i WHERE i.id_estudiante = e.id AND i.id_periodo = %s)",
                (pid,),
                uno=True,
            )["c"]

            stats["estudiantes"] = ejecutar_consulta(
                "SELECT COUNT(*) AS c FROM inscripciones WHERE id_periodo = %s AND estado = 'activo'",
                (pid,),
                uno=True,
            )["c"]
            prosecucion["nuevos_ingresos"] = max(stats["estudiantes"] - prosecucion["reinscritos"], 0)

            # Guia de arranque si el periodo consultado no tiene secciones o tiene alumnos sin reinscribir
            if not secciones:
                alertas_pendientes.append({
                    "titulo": f"El período {periodo['nombre']} aún no tiene secciones",
                    "detalle": "Crea secciones o copia las del período anterior para comenzar a inscribir.",
                    "url": url_for("academico.index") if es_admin else None,
                    "prioridad": "critica",
                    "tipo": "seccion",
                })
            if prosecucion["sin_reinscribir"] > 0 and not es_historico:
                alertas_pendientes.append({
                    "titulo": f"{prosecucion['sin_reinscribir']} estudiante(s) registrado(s) sin matrícula en {periodo['nombre']}",
                    "detalle": "Revisa el directorio o usa Prosecución Masiva para reinscribirlos.",
                    "url": url_for("estudiantes.index", id_periodo=pid, estado="sin_inscribir"),
                    "prioridad": "normal",
                    "tipo": "estudiante",
                })
            stats["retirados"] = ejecutar_consulta(
                "SELECT COUNT(*) AS c FROM inscripciones WHERE id_periodo = %s AND estado = 'retirado'",
                (pid,),
                uno=True,
            )["c"]
            desglose = ejecutar_consulta(
                "SELECT n.tipo_escala, COUNT(*) AS c "
                "FROM inscripciones i "
                "JOIN secciones s ON s.id = i.id_seccion "
                "JOIN grados_anios g ON g.id = s.id_grado_anio "
                "JOIN niveles_educativos n ON n.id = g.id_nivel "
                "WHERE i.id_periodo = %s AND i.estado = 'activo' "
                "GROUP BY n.tipo_escala",
                (pid,),
            )
            for fila in desglose:
                if fila["tipo_escala"] == "literal":
                    stats["primaria"] = fila["c"]
                else:
                    stats["media"] = fila["c"]

            # 3. Secciones sin Docente Titular / Profesor Guia
            sec_sin_guia = ejecutar_consulta(
                "SELECT s.id, g.nombre AS grado, s.nombre AS seccion "
                "FROM secciones s "
                "JOIN grados_anios g ON g.id = s.id_grado_anio "
                "WHERE s.id_periodo = %s AND s.activo = TRUE AND s.id_docente_titular_guia IS NULL "
                "ORDER BY g.orden ASC, s.nombre ASC",
                (pid,),
            )
            if sec_sin_guia:
                alertas_pendientes.append({
                    "titulo": f"{len(sec_sin_guia)} sección(es) sin Docente Titular / Guía",
                    "detalle": _resumen_secciones(sec_sin_guia),
                    "url": url_for("academico.index") if es_admin else None,
                    "prioridad": "normal",
                    "tipo": "seccion",
                })

            # 4. Secciones sin horario cargado
            sec_sin_horario = ejecutar_consulta(
                "SELECT s.id, g.nombre AS grado, s.nombre AS seccion "
                "FROM secciones s "
                "JOIN grados_anios g ON g.id = s.id_grado_anio "
                "WHERE s.id_periodo = %s AND s.activo = TRUE "
                "AND NOT EXISTS (SELECT 1 FROM horarios h WHERE h.id_periodo = s.id_periodo AND h.id_seccion = s.id) "
                "ORDER BY g.orden ASC, s.nombre ASC",
                (pid,),
            )
            if sec_sin_horario:
                alertas_pendientes.append({
                    "titulo": f"{len(sec_sin_horario)} sección(es) sin horario cargado",
                    "detalle": _resumen_secciones(sec_sin_horario),
                    "url": url_for("horarios.index", id_seccion=sec_sin_horario[0]["id"]),
                    "prioridad": "normal",
                    "tipo": "horario",
                })

            # 5. Secciones con materias activas sin docente asignado
            sec_sin_mat_doc = ejecutar_consulta(
                "SELECT s.id, g.nombre AS grado, s.nombre AS seccion, COUNT(*) AS faltantes "
                "FROM secciones s "
                "JOIN grados_anios g ON g.id = s.id_grado_anio "
                "JOIN materias m ON m.id_grado_anio = s.id_grado_anio AND m.activo = TRUE "
                "LEFT JOIN asignaciones_docentes a ON a.id_periodo = s.id_periodo AND a.id_seccion = s.id AND a.id_materia = m.id "
                "WHERE s.id_periodo = %s AND s.activo = TRUE AND a.id IS NULL "
                "GROUP BY s.id, g.nombre, s.nombre, g.orden "
                "ORDER BY g.orden ASC, s.nombre ASC",
                (pid,),
            )
            if sec_sin_mat_doc:
                alertas_pendientes.append({
                    "titulo": f"{len(sec_sin_mat_doc)} sección(es) con materias sin docente",
                    "detalle": _resumen_secciones(sec_sin_mat_doc),
                    "url": url_for("academico.seccion_asignaciones", sid=sec_sin_mat_doc[0]["id"]) if es_admin else None,
                    "prioridad": "normal",
                    "tipo": "materia",
                })

            # 6. Secciones activas sin estudiantes inscritos
            sec_vacias = ejecutar_consulta(
                "SELECT s.id, g.nombre AS grado, s.nombre AS seccion "
                "FROM secciones s "
                "JOIN grados_anios g ON g.id = s.id_grado_anio "
                "WHERE s.id_periodo = %s AND s.activo = TRUE "
                "AND NOT EXISTS (SELECT 1 FROM inscripciones i WHERE i.id_periodo = s.id_periodo AND i.id_seccion = s.id AND i.estado = 'activo') "
                "ORDER BY g.orden ASC, s.nombre ASC",
                (pid,),
            )
            if sec_vacias:
                alertas_pendientes.append({
                    "titulo": f"{len(sec_vacias)} sección(es) sin estudiantes inscritos",
                    "detalle": _resumen_secciones(sec_vacias),
                    "url": url_for("estudiantes.index"),
                    "prioridad": "normal",
                    "tipo": "seccion",
                })

            # 7. Estudiantes sin fecha de nacimiento
            est_sin_fnac = ejecutar_consulta(
                "SELECT COUNT(*) AS c FROM inscripciones i "
                "JOIN estudiantes e ON e.id = i.id_estudiante "
                "WHERE i.id_periodo = %s AND i.estado = 'activo' AND e.activo = TRUE AND e.fecha_nacimiento IS NULL",
                (pid,),
                uno=True,
            )["c"]
            if est_sin_fnac > 0:
                alertas_pendientes.append({
                    "titulo": f"{est_sin_fnac} estudiante(s) sin fecha de nacimiento",
                    "detalle": "Completa la ficha del estudiante para su expediente.",
                    "url": url_for("estudiantes.index"),
                    "prioridad": "normal",
                    "tipo": "estudiante",
                })

            # 8. Estudiantes sin direccion
            est_sin_dir = ejecutar_consulta(
                "SELECT COUNT(*) AS c FROM inscripciones i "
                "JOIN estudiantes e ON e.id = i.id_estudiante "
                "WHERE i.id_periodo = %s AND i.estado = 'activo' AND e.activo = TRUE "
                "AND (e.direccion IS NULL OR TRIM(e.direccion) = '')",
                (pid,),
                uno=True,
            )["c"]
            if est_sin_dir > 0:
                alertas_pendientes.append({
                    "titulo": f"{est_sin_dir} estudiante(s) sin dirección registrada",
                    "detalle": "Actualiza la dirección de habitación en Estudiantes.",
                    "url": url_for("estudiantes.index"),
                    "prioridad": "normal",
                    "tipo": "estudiante",
                })

            # 9. Estudiantes sin representante principal
            est_sin_rep = ejecutar_consulta(
                "SELECT COUNT(*) AS c FROM inscripciones i "
                "JOIN estudiantes e ON e.id = i.id_estudiante "
                "WHERE i.id_periodo = %s AND i.estado = 'activo' AND e.activo = TRUE "
                "AND NOT EXISTS (SELECT 1 FROM estudiante_representantes er WHERE er.id_estudiante = e.id AND er.es_principal = TRUE)",
                (pid,),
                uno=True,
            )["c"]
            if est_sin_rep > 0:
                alertas_pendientes.append({
                    "titulo": f"{est_sin_rep} estudiante(s) sin representante principal",
                    "detalle": "Vincula un representante legal en el módulo Estudiantes.",
                    "url": url_for("estudiantes.index"),
                    "prioridad": "normal",
                    "tipo": "estudiante",
                })

            # 10. Representantes sin correo o sin direccion
            rep_incompletos = ejecutar_consulta(
                "SELECT COUNT(DISTINCT r.id) AS c FROM inscripciones i "
                "JOIN estudiante_representantes er ON er.id_estudiante = i.id_estudiante AND er.es_principal = TRUE "
                "JOIN representantes r ON r.id = er.id_representante "
                "WHERE i.id_periodo = %s AND i.estado = 'activo' "
                "AND (r.correo IS NULL OR TRIM(r.correo) = '' OR r.direccion IS NULL OR TRIM(r.direccion) = '')",
                (pid,),
                uno=True,
            )["c"]
            if rep_incompletos > 0:
                alertas_pendientes.append({
                    "titulo": f"{rep_incompletos} representante(s) con datos incompletos",
                    "detalle": "Falta correo o dirección en la ficha del representante.",
                    "url": url_for("estudiantes.index"),
                    "prioridad": "normal",
                    "tipo": "estudiante",
                })

            # Avance de calificaciones
            fila_prim = ejecutar_consulta(
                "SELECT COUNT(i.id) AS total, "
                "SUM(CASE WHEN cp.lapso_1 IS NOT NULL THEN 1 ELSE 0 END) AS l1, "
                "SUM(CASE WHEN cp.lapso_2 IS NOT NULL THEN 1 ELSE 0 END) AS l2, "
                "SUM(CASE WHEN cp.lapso_3 IS NOT NULL THEN 1 ELSE 0 END) AS l3, "
                "SUM(CASE WHEN cp.definitiva IS NOT NULL THEN 1 ELSE 0 END) AS def "
                "FROM inscripciones i "
                "JOIN secciones s ON s.id = i.id_seccion "
                "JOIN grados_anios g ON g.id = s.id_grado_anio "
                "JOIN niveles_educativos n ON n.id = g.id_nivel "
                "LEFT JOIN calificaciones_primaria cp ON cp.id_inscripcion = i.id "
                "WHERE i.id_periodo = %s AND i.estado = 'activo' AND n.tipo_escala = 'literal'",
                (pid,),
                uno=True,
            )
            avance_primaria = _construir_avance(fila_prim)

            fila_med = ejecutar_consulta(
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN cs.lapso_1 IS NOT NULL THEN 1 ELSE 0 END) AS l1, "
                "SUM(CASE WHEN cs.lapso_2 IS NOT NULL THEN 1 ELSE 0 END) AS l2, "
                "SUM(CASE WHEN cs.lapso_3 IS NOT NULL THEN 1 ELSE 0 END) AS l3, "
                "SUM(CASE WHEN cs.definitiva IS NOT NULL THEN 1 ELSE 0 END) AS def "
                "FROM inscripciones i "
                "JOIN secciones s ON s.id = i.id_seccion "
                "JOIN grados_anios g ON g.id = s.id_grado_anio "
                "JOIN niveles_educativos n ON n.id = g.id_nivel "
                "JOIN materias m ON m.id_grado_anio = s.id_grado_anio AND m.activo = TRUE "
                "LEFT JOIN calificaciones_secundaria cs ON cs.id_inscripcion = i.id AND cs.id_materia = m.id "
                "WHERE i.id_periodo = %s AND i.estado = 'activo' AND n.tipo_escala = 'numerica'",
                (pid,),
                uno=True,
            )
            avance_media = _construir_avance(fila_med)

            ultimos_estudiantes = ejecutar_consulta(
                "SELECT i.id AS id_inscripcion, i.fecha_inscripcion, e.cedula, e.apellidos, e.nombres, "
                "g.nombre AS grado, s.nombre AS seccion, s.turno, n.nombre AS nivel, n.tipo_escala "
                "FROM inscripciones i "
                "JOIN estudiantes e ON e.id = i.id_estudiante "
                "JOIN secciones s ON s.id = i.id_seccion "
                "JOIN grados_anios g ON g.id = s.id_grado_anio "
                "JOIN niveles_educativos n ON n.id = g.id_nivel "
                "WHERE i.id_periodo = %s AND i.estado = 'activo' "
                "ORDER BY i.id DESC LIMIT 6",
                (pid,),
            )

            cumpleaneros = ejecutar_consulta(
                "SELECT e.id, e.apellidos, e.nombres, e.fecha_nacimiento, "
                "g.nombre AS grado, s.nombre AS seccion, "
                "DATE_FORMAT(e.fecha_nacimiento, '%%d/%%m') AS dia_mes, "
                "TIMESTAMPDIFF(YEAR, e.fecha_nacimiento, CURDATE()) AS edad_actual "
                "FROM inscripciones i "
                "JOIN estudiantes e ON e.id = i.id_estudiante "
                "JOIN secciones s ON s.id = i.id_seccion "
                "JOIN grados_anios g ON g.id = s.id_grado_anio "
                "WHERE i.id_periodo = %s AND i.estado = 'activo' AND e.activo = TRUE "
                "AND e.fecha_nacimiento IS NOT NULL "
                "AND ("
                "  DATE_FORMAT(e.fecha_nacimiento, '%%m-%%d') BETWEEN DATE_FORMAT(CURDATE(), '%%m-%%d') AND DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL 7 DAY), '%%m-%%d') "
                "  OR ("
                "    DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL 7 DAY), '%%m-%%d') < DATE_FORMAT(CURDATE(), '%%m-%%d') "
                "    AND ("
                "      DATE_FORMAT(e.fecha_nacimiento, '%%m-%%d') >= DATE_FORMAT(CURDATE(), '%%m-%%d') "
                "      OR DATE_FORMAT(e.fecha_nacimiento, '%%m-%%d') <= DATE_FORMAT(DATE_ADD(CURDATE(), INTERVAL 7 DAY), '%%m-%%d')"
                "    )"
                "  )"
                ") "
                "ORDER BY DATE_FORMAT(e.fecha_nacimiento, '%%m-%%d') ASC, e.apellidos ASC LIMIT 6",
                (pid,),
            )

        # 11. Docentes activos sin cuenta de usuario
        if es_admin:
            doc_sin_usr = ejecutar_consulta(
                "SELECT COUNT(*) AS c FROM docentes d "
                "WHERE d.activo = TRUE "
                "AND NOT EXISTS (SELECT 1 FROM usuarios u WHERE u.id_docente = d.id AND u.activo = TRUE)",
                uno=True,
            )["c"]
            if doc_sin_usr > 0:
                alertas_pendientes.append({
                    "titulo": f"{doc_sin_usr} docente(s) activo(s) sin cuenta de acceso",
                    "detalle": "Crea su usuario vinculado en Gestión de Usuarios para que carguen notas.",
                    "url": url_for("usuarios.index"),
                    "prioridad": "normal",
                    "tipo": "usuario",
                })

    resumen_docente = None
    bloques_docente = {d: [] for d in DIAS_SEMANA}
    if user["rol"] == "docente" and user.get("id_docente") and periodo:
        resumen_docente = obtener_resumen_docente(periodo["id"], user["id_docente"])
        for b in obtener_horario_docente(periodo["id"], user["id_docente"]):
            bloques_docente.setdefault(b["dia_semana"], []).append(b)

    return render_template(
        "dashboard/index.html",
        periodos=periodos,
        periodo=periodo,
        periodo_activo=periodo_activo,
        es_historico=es_historico,
        stats=stats,
        prosecucion=prosecucion,
        alertas_pendientes=alertas_pendientes,
        avance_primaria=avance_primaria,
        avance_media=avance_media,
        ultimos_estudiantes=ultimos_estudiantes,
        cumpleaneros=cumpleaneros,
        secciones=secciones_activas,
        resumen_docente=resumen_docente,
        dias_semana=DIAS_SEMANA,
        bloques_docente=bloques_docente,
    )
