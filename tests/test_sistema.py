import pytest
from app import create_app
from db import ejecutar_accion, ejecutar_consulta
from inicializar_bd import inicializar
from services.academico_service import (
    cambiar_cierre_periodo,
    copiar_secciones_periodo,
    crear_docente,
    crear_grado,
    crear_materia,
    crear_periodo,
    crear_seccion,
    obtener_periodo_activo,
)
from services.auth_service import actualizar_password, cambiar_password_inicial, registrar_usuario, verificar_credenciales
from services.calificacion_service import calcular_definitiva_mppe, numero_a_letras
from services.estudiante_service import (
    buscar_estudiante_por_cedula,
    buscar_estudiantes_para_inscripcion,
    ejecutar_prosecucion_lote,
    listar_directorio_estudiantes,
    marcar_egresado,
    normalizar_y_validar_cedula,
    obtener_historial_certificable,
    registrar_e_inscribir_estudiante,
    validar_correo_opcional,
    validar_direccion_opcional,
    validar_fecha_nacimiento_opcional,
    validar_telefono_ve,
    validar_texto_persona,
)
from services.horario_service import registrar_bloque_horario
from services.pdf_service import generar_certificado_historial_pdf


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    inicializar()


def test_validaciones_inscripcion_campos():
    assert normalizar_y_validar_cedula("30123456", "cédula") == "V-30123456"
    assert normalizar_y_validar_cedula("v.30.123.456", "cédula") == "V-30123456"
    assert normalizar_y_validar_cedula("E-12345678", "cédula", max_digitos=9) == "E-12345678"
    assert normalizar_y_validar_cedula("11212345678", "cédula escolar", max_digitos=12) == "V-11212345678"
    with pytest.raises(ValueError):
        normalizar_y_validar_cedula("ABC", "cédula")
    with pytest.raises(ValueError):
        normalizar_y_validar_cedula("V-123", "cédula")

    assert validar_texto_persona("  María   José  ", "Nombres") == "María José"
    with pytest.raises(ValueError):
        validar_texto_persona("Ana123", "Nombres")
    with pytest.raises(ValueError):
        validar_texto_persona("A", "Nombres")

    assert validar_telefono_ve("04141234567", "teléfono", obligatorio=True) == "04141234567"
    assert validar_telefono_ve("0414-1234567", "teléfono", obligatorio=True) == "0414-1234567"
    assert validar_telefono_ve("0422-7654321", "teléfono", obligatorio=True) == "0422-7654321"
    assert validar_telefono_ve("", "teléfono trabajo", obligatorio=False) == ""
    with pytest.raises(ValueError):
        validar_telefono_ve("12345", "teléfono", obligatorio=True)
    with pytest.raises(ValueError):
        validar_telefono_ve("", "teléfono", obligatorio=True)

    assert validar_correo_opcional("rep@ejemplo.com") == "rep@ejemplo.com"
    assert validar_correo_opcional("") == ""
    with pytest.raises(ValueError):
        validar_correo_opcional("correo-invalido")

    assert validar_direccion_opcional("Urb. Los Laureles", "dirección") == "Urb. Los Laureles"
    with pytest.raises(ValueError):
        validar_direccion_opcional("Abc", "dirección")

    assert validar_fecha_nacimiento_opcional("2012-05-15") == "2012-05-15"
    assert validar_fecha_nacimiento_opcional("") is None
    with pytest.raises(ValueError):
        validar_fecha_nacimiento_opcional("2099-01-01")
    with pytest.raises(ValueError):
        validar_fecha_nacimiento_opcional("1950-01-01")


def test_semilla_estructura_base_y_estudiantes_sin_asignar():
    grados = ejecutar_consulta("SELECT nombre FROM grados_anios")
    nombres_g = {g["nombre"] for g in grados}
    for esperado in ("1.º Grado", "6.º Grado", "1.º Año", "3.º Año", "5.º Año"):
        assert esperado in nombres_g

    docentes = ejecutar_consulta("SELECT COUNT(*) AS c FROM docentes WHERE activo = TRUE", uno=True)
    assert docentes["c"] >= 8

    # Materias basicas: Fisica/Quimica/Biologia solo desde 3.o Anio
    mats_1 = {
        m["nombre"]
        for m in ejecutar_consulta(
            "SELECT m.nombre FROM materias m JOIN grados_anios g ON g.id = m.id_grado_anio WHERE g.nombre = '1.º Año'"
        )
    }
    assert {"Matemáticas", "Castellano", "Inglés", "Educación Física"}.issubset(mats_1)
    assert "Física" not in mats_1 and "Química" not in mats_1 and "Biología" not in mats_1

    mats_3 = {
        m["nombre"]
        for m in ejecutar_consulta(
            "SELECT m.nombre FROM materias m JOIN grados_anios g ON g.id = m.id_grado_anio WHERE g.nombre = '3.º Año'"
        )
    }
    assert {"Matemáticas", "Castellano", "Inglés", "Educación Física", "Física", "Química", "Biología"}.issubset(mats_3)

    # Al menos 10 estudiantes registrados en semilla sin seccion asignada inicialmente
    est_sem = ejecutar_consulta(
        "SELECT COUNT(*) AS c FROM estudiantes WHERE cedula IN "
        "('V-33101001','V-33101002','V-33101003','V-33101004','V-33101005',"
        "'V-32101006','V-32101007','V-31101008','V-31101009','V-30101010')",
        uno=True,
    )
    assert est_sem["c"] == 10

    # Los 5 estudiantes pre-5to anio recomiendan 5.o Anio (solo_superiores=True) y permiten PDF multi-anio 1.o a 3.o
    periodo = obtener_periodo_activo()
    info = buscar_estudiante_por_cedula("V-32101006", id_periodo_destino=periodo["id"])
    assert info is not None
    assert info["recomendacion"]["solo_superiores"] is True
    assert info["recomendacion"]["grado_sugerido_nombre"] == "5.º Año"

    hist_1_3 = obtener_historial_certificable(info["estudiante"]["id"], desde=201, hasta=203)
    assert len(hist_1_3["historial"]) == 3
    assert hist_1_3["rango_texto"] == "1.º Año a 3.º Año"
    pdf_buf = generar_certificado_historial_pdf(hist_1_3, {"nombre_plantel": "Prueba", "director": "Dir"})
    assert pdf_buf.getvalue().startswith(b"%PDF")


def test_calculo_mppe_y_letras():
    assert calcular_definitiva_mppe(14, 15, 15) == 15  # 14.66 -> 15
    assert calcular_definitiva_mppe(14, 14, 15) == 14  # 14.33 -> 14
    assert calcular_definitiva_mppe(15, 14, None) is None
    assert numero_a_letras(15) == "QUINCE"
    assert numero_a_letras(20) == "VEINTE"
    assert numero_a_letras(99) == ""


def test_login_csrf_y_proteccion_rutas():
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    # Sin sesion redirige a /login
    res = client.get("/dashboard")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]

    # POST sin token CSRF falla con 400
    res_csrf = client.post("/login", data={"username": "admin", "password": "admin123"})
    assert res_csrf.status_code == 400


def test_horario_anti_choques():
    periodo = obtener_periodo_activo()
    assert periodo is not None

    # Crear datos de prueba unicos
    niveles = ejecutar_consulta("SELECT id FROM niveles_educativos WHERE tipo_escala='numerica' LIMIT 1", uno=True)
    bloques = ejecutar_consulta("SELECT id FROM bloques_formacion LIMIT 1", uno=True)

    d_ex = ejecutar_consulta("SELECT id FROM docentes WHERE cedula='V-99900011'", uno=True)
    id_doc = d_ex["id"] if d_ex else crear_docente("V-99900011", "Carlos", "Prueba", "04140000000", "Matematica")

    g_ex = ejecutar_consulta("SELECT id FROM grados_anios WHERE nombre='1.º Año Test'", uno=True)
    id_grado = g_ex["id"] if g_ex else crear_grado(niveles["id"], "1.º Año Test", 99)

    s1_ex = ejecutar_consulta(
        "SELECT id FROM secciones WHERE id_periodo=%s AND id_grado_anio=%s AND nombre='T1'",
        (periodo["id"], id_grado),
        uno=True,
    )
    id_sec1 = s1_ex["id"] if s1_ex else crear_seccion(periodo["id"], id_grado, "T1", "Mañana", id_doc)

    s2_ex = ejecutar_consulta(
        "SELECT id FROM secciones WHERE id_periodo=%s AND id_grado_anio=%s AND nombre='T2'",
        (periodo["id"], id_grado),
        uno=True,
    )
    id_sec2 = s2_ex["id"] if s2_ex else crear_seccion(periodo["id"], id_grado, "T2", "Mañana", id_doc)

    m_ex = ejecutar_consulta("SELECT id FROM materias WHERE id_grado_anio=%s AND nombre='Matematica Test'", (id_grado,), uno=True)
    id_mat = m_ex["id"] if m_ex else crear_materia(id_grado, bloques["id"], "Matematica Test")

    ejecutar_accion("DELETE FROM horarios WHERE id_docente=%s", (id_doc,))

    # Bloque valido
    registrar_bloque_horario(periodo["id"], id_sec1, id_doc, 1, "07:00", "08:30", id_mat, "Aula 1")

    # Choque en misma seccion
    with pytest.raises(ValueError, match="Choque de horario en la sección"):
        registrar_bloque_horario(periodo["id"], id_sec1, id_doc, 1, "08:00", "09:00", id_mat, "Aula 1")

    # Choque de docente en otra seccion a la misma hora
    with pytest.raises(ValueError, match="docente ya tiene clase"):
        registrar_bloque_horario(periodo["id"], id_sec2, id_doc, 1, "07:30", "08:30", id_mat, "Aula 2")


def test_inscripcion_y_reporte_pdf():
    periodo = obtener_periodo_activo()
    sec = ejecutar_consulta("SELECT id FROM secciones WHERE id_periodo=%s LIMIT 1", (periodo["id"],), uno=True)
    id_insc = registrar_e_inscribir_estudiante(
        {
            "cedula": "V-30111222",
            "nombres": "Ana",
            "apellidos": "Test",
            "rep_cedula": "V-12111222",
            "rep_nombres": "Maria",
            "rep_apellidos": "Test",
            "rep_parentesco": "Madre",
            "rep_telefono": "04141234567",
            "rep_telefono_trabajo": "02641234567",
            "rep_correo": "maria@example.com",
            "rep_direccion": "Cabimas",
        },
        periodo["id"],
        sec["id"],
    )
    assert id_insc > 0


def test_rol_docente_y_vinculacion():
    d_ex = ejecutar_consulta("SELECT id FROM docentes WHERE cedula='V-99900011'", uno=True)
    id_doc = d_ex["id"]
    ejecutar_accion("DELETE FROM usuarios WHERE username = 'docente_test'")
    uid = registrar_usuario("Prof. Prueba", "docente_test", "docente123", "docente", id_doc)
    user = verificar_credenciales("docente_test", "docente123")
    assert user["rol"] == "docente"
    assert user["id_docente"] == id_doc
    ejecutar_accion("DELETE FROM usuarios WHERE id = %s", (uid,))


def test_cambio_clave_inicial_sin_temporal():
    ejecutar_accion("DELETE FROM usuarios WHERE username = 'user_test_modal'")
    uid = registrar_usuario("Usuario Test", "user_test_modal", "temp1234", "operador")
    with pytest.raises(ValueError, match="distinta"):
        cambiar_password_inicial(uid, "temp1234", "temp1234")
    cambiar_password_inicial(uid, "nuevaClave99", "nuevaClave99")
    user = verificar_credenciales("user_test_modal", "nuevaClave99")
    assert user is not None
    assert user["debe_cambiar_password"] == 0
    ejecutar_accion("DELETE FROM usuarios WHERE id = %s", (uid,))


def test_cierre_periodo_copia_secciones_y_prosecucion():
    p_orig = ejecutar_consulta("SELECT id FROM periodos_escolares WHERE nombre='2098-2099'", uno=True)
    pid_orig = p_orig["id"] if p_orig else crear_periodo("2098-2099", "2098-09-15", "2099-07-31")
    p_dest = ejecutar_consulta("SELECT id FROM periodos_escolares WHERE nombre='2099-2100'", uno=True)
    pid_dest = p_dest["id"] if p_dest else crear_periodo("2099-2100", "2099-09-15", "2100-07-31")

    cambiar_cierre_periodo(pid_orig, False)
    cambiar_cierre_periodo(pid_dest, False)

    niv = ejecutar_consulta("SELECT id FROM niveles_educativos WHERE tipo_escala='numerica' LIMIT 1", uno=True)
    g_ex = ejecutar_consulta("SELECT id FROM grados_anios WHERE nombre='1.º Año Test'", uno=True)
    id_grado = g_ex["id"] if g_ex else crear_grado(niv["id"], "1.º Año Test", 99)

    s_ex = ejecutar_consulta(
        "SELECT id FROM secciones WHERE id_periodo=%s AND id_grado_anio=%s AND nombre='P1'",
        (pid_orig, id_grado),
        uno=True,
    )
    id_sec_orig = s_ex["id"] if s_ex else crear_seccion(pid_orig, id_grado, "P1", "Mañana", None)

    registrar_e_inscribir_estudiante(
        {
            "cedula": "V-30999888",
            "nombres": "Luis",
            "apellidos": "Prosecucion",
            "rep_cedula": "V-12999888",
            "rep_nombres": "Pedro",
            "rep_apellidos": "Prosecucion",
            "rep_parentesco": "Padre",
            "rep_telefono": "04149998888",
        },
        pid_orig,
        id_sec_orig,
    )

    # Limpiar destino antes de copiar
    ejecutar_accion("DELETE FROM inscripciones WHERE id_periodo=%s", (pid_dest,))
    ejecutar_accion("DELETE FROM secciones WHERE id_periodo=%s", (pid_dest,))

    # Copiar secciones al periodo destino
    res_copia = copiar_secciones_periodo(pid_orig, pid_dest, copiar_guias=True, copiar_asignaciones=False)
    assert res_copia["secciones_creadas"] >= 1

    # Alumno aparece como sin_inscribir en destino y con historial del periodo origen
    sin_insc = listar_directorio_estudiantes(id_periodo=pid_dest, filtro="V-30999888", estado="sin_inscribir")
    assert len(sin_insc) == 1
    assert sin_insc[0]["ultimo_periodo_nombre"] == "2098-2099"

    # Buscador rapido de reinscripcion (por CI o nombre/apellido)
    busq = buscar_estudiantes_para_inscripcion("Prosecucion", id_periodo_destino=pid_dest)
    assert any(r["cedula"] == "V-30999888" for r in busq)

    # Autocompletado de estudiante por cedula + recomendacion academica
    encontrado = buscar_estudiante_por_cedula("V-30999888", id_periodo_destino=pid_dest)
    assert encontrado is not None
    assert encontrado["estudiante"]["nombres"] == "Luis"
    assert encontrado["recomendacion"]["tiene_historial"] is True
    assert encontrado["recomendacion"]["evaluacion_incompleta"] is True

    # Prosecucion masiva con decisiones individuales (incluyendo condicion repitiente)
    sec_dest = ejecutar_consulta("SELECT id FROM secciones WHERE id_periodo=%s LIMIT 1", (pid_dest,), uno=True)
    res_pros = ejecutar_prosecucion_lote(
        pid_dest,
        decisiones=[{
            "id_estudiante": encontrado["estudiante"]["id"],
            "accion": "inscribir",
            "id_seccion_destino": sec_dest["id"],
            "condicion": "repitiente",
        }],
    )
    assert res_pros["inscritos"] == 1
    insc_dest = ejecutar_consulta(
        "SELECT condicion FROM inscripciones WHERE id_periodo=%s AND id_estudiante=%s",
        (pid_dest, encontrado["estudiante"]["id"]),
        uno=True,
    )
    assert insc_dest["condicion"] == "repitiente"

    # Cierre formal del periodo destino bloquea nuevas secciones
    cambiar_cierre_periodo(pid_dest, True)
    with pytest.raises(ValueError, match="cerrado"):
        crear_seccion(pid_dest, id_grado, "Z9", "Tarde", None)
    cambiar_cierre_periodo(pid_dest, False)

    # Marcar como egresado y limpiar
    marcar_egresado(encontrado["estudiante"]["id"], True)
    egresados = listar_directorio_estudiantes(id_periodo=pid_dest, filtro="V-30999888", estado="egresado")
    assert len(egresados) == 1
    marcar_egresado(encontrado["estudiante"]["id"], False)

    # Limpieza de datos temporales de test
    ejecutar_accion("DELETE FROM inscripciones WHERE id_periodo IN (%s, %s)", (pid_orig, pid_dest))
    ejecutar_accion("DELETE FROM secciones WHERE id_periodo IN (%s, %s)", (pid_orig, pid_dest))
    ejecutar_accion("DELETE FROM estudiantes WHERE cedula='V-30999888'")
    ejecutar_accion("DELETE FROM representantes WHERE cedula='V-12999888'")
    ejecutar_accion("DELETE FROM periodos_escolares WHERE id IN (%s, %s)", (pid_orig, pid_dest))

