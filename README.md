# Sistema de Control de Estudio — E. B. N. "Los Laureles"

Sistema web local (100% offline en interfaz y operación) para la gestión académica y administrativa de **Educación Primaria** (escala literal `A–E`) y **Educación Media General** (escala numérica `01–20` con normativa MPPE), diseñado para ejecutarse en **Windows 10 + XAMPP (MySQL / MariaDB)** con Python y Flask.

---

## Características principales

- **Control de acceso y roles:** Administrador, Operador y Docente (con Portal Docente propio), contraseñas cifradas con `scrypt`, cambio obligatorio de clave inicial, protección contra fuerza bruta en login (bloqueo temporal tras 5 intentos fallidos), cookies `HttpOnly`/`SameSite=Lax`, páginas de error institucionales y protección CSRF en todas las mutaciones.
- **Gestión de períodos escolares:** selector global de período, modo consulta histórica de solo lectura, cierre formal con checklist previo de verificación (notas pendientes y asignaciones) y copia automática de secciones/asignaciones entre años escolares.
- **Estructura académica completa:** niveles educativos, grados (`1.º` a `6.º Grado`) y años (`1.º` a `5.º Año`), secciones por turno, materias por bloque de formación, gestión de materias asignadas directo desde la tabla de docentes (con resumen de carga) y asignaciones por sección.
- **Matrícula, inscripción y traslados:** buscador rápido de reinscripción, asistente en 3 pasos con validación campo por campo, restricción de grados superiores al aprobar y traslado de sección dentro del período activo conservando calificaciones.
- **Prosecución masiva inteligente:** reinscripción asistida por sección con sugerencias individuales (Promovido, Materia Pendiente, Repitiente, Egresado).
- **Calificaciones y horarios:** carga de notas por lapso con cálculo automático de definitiva MPPE, y horarios semanales inteligentes (auto-docente al elegir materia, ficha de carga, disponibilidad en vivo y **bloqueo estricto** ante choques de sección, docente o aula/salón).
- **Exportaciones oficiales y respaldo preventivo:**
  - **PDF:** Certificación de Calificaciones MPPE por período, Certificación Acumulada Multi-Año (rango Desde–Hasta), Lote PDF/ZIP, Constancia de Estudio, Boletín por Lapsos, Sábana Media General, Horarios Semanales y Lista de Asistencia (20 días).
  - **Excel (`.xlsx`):** Nómina de Estudiantes, Planilla por Materia, Sábana Primaria, Sábana Media General y Lista de Asistencia.
  - **Respaldo (`.sql`):** Descarga completa de la base de datos desde Configuración (solo Administrador) con recordatorio preventivo en el Dashboard cuando pasan más de 15 días sin respaldar.

---

## Instalación rápida en Windows 10 + XAMPP

### Requisitos previos
- **Windows 10 / 11** (64 bits)
- **Python 3.10 o superior** (marcar *"Add Python to PATH"* durante la instalación)
- **XAMPP** (módulo **MySQL / MariaDB** en el puerto `3306`)

### Pasos
1. Enciende **MySQL** en el Panel de Control de XAMPP (o deja que el instalador intente arrancarlo automáticamente).
2. Haz doble clic en **`instalar_w10.bat`**:
   - Crea el entorno virtual `venv` e instala las librerías de `requirements.txt`.
   - Crea `.env` desde `.env.example`.
   - Crea la base de datos `los_laureles_ce` importando `database/instalacion_completa_xampp.sql` y verifica integridad con `inicializar_bd.py`.
3. Haz doble clic en **`iniciar_w10.bat`** para levantar el servidor local y abrir automáticamente `http://127.0.0.1:5000`.

### Credenciales iniciales *(el sistema exige cambiarlas al primer ingreso)*
| Rol | Usuario | Contraseña inicial |
| --- | --- | --- |
| **Administrador** | `admin` | `admin123` |
| **Operador** | `operador` | `operador123` |

---

## Documentación entregable (`documentacion/`)

1. `01_Vision_General_y_Tecnologias.pdf` — Visión general, stack tecnológico, arquitectura en capas y matriz de roles.
2. `02_Guia_de_Instalacion_y_Configuracion_W10.pdf` — Requisitos, instalación en Windows 10 + XAMPP, configuración inicial y resolución de problemas.
3. `03_Diagramas_del_Sistema_y_Arquitectura_Tecnica.pdf` — Diagrama ER (16 tablas), Casos de Uso, Diagramas de Flujo y Secuencia.
4. `04_Manual_de_Usuario_y_Flujo_Operativo.pdf` — Manual paso a paso del ciclo escolar por módulo y rol.
5. `05_Catalogo_de_Reportes_y_Exportaciones.pdf` — Catálogo de PDFs, Excel, respaldo SQL, parámetros MPPE y matriz de permisos.
6. `06_Seguridad_Pruebas_y_Mantenimiento.pdf` — Seguridad aplicada, pruebas automatizadas (`pytest`), respaldos y mantenimiento preventivo.

---

## Estructura del proyecto

```text
├── app.py                     # Fábrica Flask, CSRF global e inyección de contexto
├── config.py                  # Configuración desde .env y clave secreta persistida
├── db.py                      # Conexiones PyMySQL (DictCursor) y helpers SQL
├── inicializar_bd.py          # Inicialización idempotente, migraciones y datos base
├── instalar_w10.bat           # Instalador automático 1 clic (Windows 10 + XAMPP)
├── iniciar_w10.bat            # Lanzador diario 1 clic (abre el navegador automáticamente)
├── database/
│   ├── schema.sql                       # Esquema relacional de 16 tablas InnoDB
│   └── instalacion_completa_xampp.sql   # Script SQL completo listo para XAMPP / phpMyAdmin
├── routes/                    # 9 Blueprints modulares (auth, dashboard, estudiantes, ...)
├── services/                  # Capa de lógica de negocio, PDFs, Excel y respaldos SQL
├── templates/                 # Vistas HTML5 + Jinja2
├── static/css/                # Tailwind CSS precompilado (100% offline)
├── tests/                     # Suite de pruebas automatizadas con pytest
└── documentacion/             # 6 documentos ejecutivos y técnicos en PDF
```
