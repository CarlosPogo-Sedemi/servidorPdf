# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es esto

Un microservicio FastAPI ("Servidor Universal de Reportes - SEDEMI") que convierte payloads JSON
en documentos de oficina descargables. Tiene dos pipelines de renderizado independientes:

1. **DOCX** — rellena plantillas de Word en `templates/*.docx` usando `docxtpl` (Jinja2 para Word).
2. **PDF** — renderiza HTML con Jinja2 desde `templates_html/` a PDF con WeasyPrint.

Todas las respuestas son `StreamingResponse` (descarga de archivo); nada se guarda en disco.

## Comandos

```bash
# Preparación (Windows PowerShell)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Ejecutar localmente (cualquiera de estos; --reload para desarrollo)
uvicorn main:app --reload
fastapi dev main.py

# Documentación interactiva de la API mientras corre
# http://localhost:8000/docs

# Docker (refleja producción: WeasyPrint necesita las librerías nativas pango/cairo
# incluidas en la imagen)
docker build -t servidor-pdf .
docker run -p 10000:10000 servidor-pdf
```

No hay suite de tests, linter ni CI configurados. El contenedor sirve en el puerto **10000**
(`/api/v1/ping/` existe para mantener despierto un host que se duerme).

## Arquitectura

`main.py` es solo un punto de composición: crea la app `FastAPI`, monta `assets/` en `/assets`
(imágenes de encabezado/pie que usan las plantillas) e incluye los routers. Todos los endpoints
van bajo el prefijo `/api/v1`.

| Capa | Directorio | Rol |
|------|------------|-----|
| Routers | `routers/` | Endpoints HTTP, manejo de request/response, streaming |
| Servicios | `functions/` | Lógica de generación de documentos, sin imports de FastAPI |
| Esquemas | `models/` | Modelos Pydantic de request |

Endpoints:

- `POST /api/v1/generar-reporte/` (`routers/reportes.py` → `functions/docx_service.py`) —
  la funcionalidad principal. El payload es `{ template_name, data }`; `template_name` selecciona
  `templates/<nombre>.docx`. Ver el pipeline DOCX más abajo.
- `POST /api/v1/comprimir-fotos/` (`routers/reportes.py`) — helper independiente que recibe una
  lista de fotos en base64 y las devuelve redimensionadas (máx. 800px de ancho) y recodificadas
  como JPEG q70. Pensado para que el cliente lo llame antes de `generar-reporte` para reducir el
  tamaño del payload.
- `POST /api/v1/generar-pdf-vacunas/` (`routers/vacunas.py` → `functions/vacunas_service.py`) —
  produce un PDF de registro de vacunación ecuatoriano (A4 horizontal) desde
  `templates_html/vacunas.html`.
- `POST /api/v1/generar-pdf-pasaporte/` (`routers/pasaporte.py` → `functions/pasaporte_service.py`) —
  produce el PDF de "Pasaporte de Seguridad" desde `templates_html/pasaporte.html`. Payload
  `{ data: { DT, EmpleadoMes, BuenasPracticas, Competencias } }` (ver pipeline PDF Pasaporte
  más abajo). Nota: los `templates/PASAPORTE_SEGURIDAD*.docx` en `templates/` son versiones
  previas del intento DOCX para este mismo documento; el pipeline vigente es este de PDF/HTML,
  no `generar-reporte`.
- `POST /api/v1/generar-excel-matriz-ast/` (`routers/matriz_ast.py` → `functions/matriz_ast_service.py`
  + `functions/matriz_ast_excel.py`) — genera el Excel FOR SEI 02 (Matriz de riesgos por puesto,
  método INSST) con openpyxl desde la columna MATRIZ_RIESGOS de AST_PUESTO_TRABAJO. Reglas y colores
  en `functions/matriz_ast_config.py`; descripciones por factor en `assets/matriz_ast/catalogo_factores.json`.
- `POST /api/v1/generar-excel-matriz-geritra/` (`routers/matriz_geritra.py` → `functions/geritra_service.py`
  + `functions/geritra_excel.py`) — genera la Matriz GERITRA (columnas A..AO) desde MATRIZ_RIESGOS, ENTREVISTAS_AST,
  ACTIVIDADES_COMUNES_AST y UTENSILIOS/MATERIALES/EQUIPOS de AST_PUESTO_TRABAJO. Jerarquía de controles por medida en
  `assets/matriz_ast/jerarquia_medidas.json`; reglas y colores en `functions/geritra_config.py`. Incluye las hojas
  "REFERENCIAS GERITRA" (tablas y descripciones de la Guía, Pasos 1 a 37: índices, probabilidad, consecuencias,
  matriz y niveles de riesgo; ya no hay leyenda en la hoja principal) y "PERSONAS CON DISCAPACIDAD".
- `GET /api/v1/ping/` (`routers/utils.py`) — salud / keep-alive.

### Pipeline DOCX (la parte delicada)

`functions/docx_service.py` ejecuta dos pasadas antes de `doc.render()`:

1. **`reparar_tags_rotos(doc)`** — Word suele partir un mismo tag de bucle de tabla
   `{%tr ... %}` en varios "runs" del XML e inserta espacios sobrantes (`{% tr`, `{%  tr`), lo
   que rompe docxtpl. Esto recorre cada párrafo (incluidos los de celdas de tabla) y, *solo*
   para párrafos que contienen a la vez `{%` y `tr`, concatena el texto de todos los runs en
   `runs[0]`, normaliza `{% tr` → `{%tr` y vacía los runs restantes. El guard de `{%`+`tr` es
   intencional — evita tocar tags normales `{{ variable }}`. Si cambias la lógica de reparación
   de tags, conserva ese guard.
2. **`procesar_datos_rec(context, doc)`** — muta el dict `data` del payload **in situ**, de forma
   recursiva: `None` → `""` (para que los campos faltantes salgan en blanco y no como "None"), y
   cualquier string que parezca una imagen base64 (prefijo `data:image` o que contenga
   `base64,`) se decodifica, se re-guarda como JPEG a 96 DPI y se reemplaza por un `InlineImage`
   de docxtpl. El tamaño se decide por el nombre de la clave: `FotoPerfil` → 30×40 mm, el resto
   → 50 mm de ancho.

El archivo de plantilla se carga dos veces: primero como `Document` plano de `python-docx` para
la reparación de tags, luego se reabre desde un buffer en memoria como `DocxTemplate` para el
renderizado.

### Pipeline PDF (vacunas)

`functions/vacunas_service.py` mantiene un `Environment` de Jinja2 a nivel de módulo apuntando a
`templates_html/`. `construir_seccion_b()` aplana el modelo de dominio (primera dosis + una
lista `ListaActividades` de dosis posteriores) en grupos de filas por vacuna que la plantilla
itera. Las fechas se reformatean `-` → `/` aquí, no en la plantilla. Solo el `PacienteInfo` de
`models/vacunas.py` está tipado; la lista `vacunas` es `Dict[str, Any]` sin tipar, así que el
acceso a campos en el servicio usa `.get()` con valores por defecto.

### Pipeline PDF (pasaporte de seguridad)

`functions/pasaporte_service.py` recibe el JSON tal como lo arma el botón "Enviar" de Power Apps
(`models/pasaporte.py`, todos los modelos con `extra="ignore"` para poder tolerar campos que
Power Apps manda pero esta plantilla no usa, sin tener que tocar el Power Fx). Los nombres de
campo del payload respetan el PascalCase que ya usa Power Apps (`DT.NombreCompleto`,
`DT.Cedula`, etc.); la traducción a los nombres internos de la plantilla (`nombres_apellidos`,
`identificacion`, etc.) ocurre en el servicio, no en el modelo ni en la plantilla. Tres listas
(`Competencias`, `EmpleadoMes`, `BuenasPracticas`) se reparten en páginas de hasta
`REGISTROS_POR_PAGINA = 3` vía `_en_grupos()`; una lista vacía produce una página con una
tarjeta en blanco (no cero páginas), a propósito. Las fechas llegan en ISO y se reformatean con
`_fecha()` (mismo patrón `-` → `/` que en vacunas).

## Convenciones

- El código de los endpoints, los comentarios, los mensajes de error y las variables de las
  plantillas están en **español**. Mantenlo así.
- Agregar un endpoint: nuevo módulo en `routers/`, `APIRouter(prefix="/api/v1", tags=[...])`,
  registrarlo en `main.py`. La lógica de generación va en `functions/`.
- Agregar una plantilla DOCX: coloca `templates/<nombre>.docx` y ya está; no hace falta cambiar
  código — se selecciona por `template_name` en tiempo de request. Los tags de bucle de la
  plantilla deben usar la sintaxis `{%tr %}`.
- Los errores se capturan de forma amplia y se devuelven como `HTTPException` 500 (404 si falta
  la plantilla), con el detalle impreso en stdout.

### Pipeline PDF editable (AcroForm)

`POST /api/v1/llenar-pdf/` (`routers/pdf_formularios.py` → `functions/pdf_form_service.py`) rellena
`templates_pdf/<template_name>.pdf` (un PDF que ya tiene campos de formulario) con `data` =
`{nombre_del_campo: valor}` y devuelve el mismo PDF **sin aplanar**: los campos siguen editables.
No pasa por DOCX ni WeasyPrint (convertir a PDF destruye los campos). Usa `pypdf` + Pillow.

- Descubrir nombres de campos: `GET /api/v1/pdf-campos/<plantilla>`, `POST /api/v1/pdf-campos/`
  (subiendo un PDF) o `python -m scripts.inspeccionar_pdf templates_pdf/X.pdf` (genera `X.campos.json`).
- Tipos: texto/combo → string; casilla → bool; radio → nombre de la opción; imagen (firma/foto) →
  base64/`data:image` (se estampa en el recuadro del campo y el recuadro se quita).
- La clave puede ser el nombre completo (`Grupo.campo`) o el corto si no es ambiguo. Las claves que
  no coinciden se reportan en los headers `X-Campos-*` (y `estricto: true` responde 422).
- Se elimina `/XFA` del AcroForm (si no, Adobe ignora los valores) y NO se activa `NeedAppearances` (degradaba los radios); pypdf genera la apariencia del texto.
- `templates_pdf/<nombre>.alias.json` (opcional) traduce nombres amigables del JSON a los campos reales
  (uno a varios campos; `dividir` reparte texto largo en varias líneas; `valores` traduce p. ej. SI/NO a radios).
- Las claves del JSON que empiezan con `_` (p. ej. `_codigo`) se ignoran: son datos para el flujo de Power Automate.
- Los textos que no caben en un campo de una línea reducen la letra (mín. 6 pt). En los grupos `dividir` todas las líneas comparten el mismo tamaño.
- `FUENTE_AUTO_AL_EDITAR` (True) deja los campos de texto con letra "Auto": lo ya escrito se ve con el tamaño calculado y, al editar en Reader, el texto se ajusta solo (Reader gratis no puede cambiar el tamaño de un campo).
- Agregar una plantilla: copiar el PDF a `templates_pdf/`; no hace falta cambiar código.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
