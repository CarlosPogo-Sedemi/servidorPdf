"""Renderiza el modelo MatrizFormato al Excel FOR SEI 02 (openpyxl)."""
from __future__ import annotations

import math
from io import BytesIO
from itertools import groupby

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter, range_boundaries
from openpyxl.worksheet.worksheet import Worksheet

from functions import matriz_ast_config as cfg
from functions.matriz_ast_service import Fila, MatrizFormato

# ----------------------------------------------------------------------------
# Layout de columnas (A..AA)
# ----------------------------------------------------------------------------
ANCHOS = {
    "A": 9, "B": 26, "C": 60, "D": 7, "E": 40,  # Riesgo, Factor, Descripción, N°, Actividad
    "F": 6, "G": 6, "H": 6,            # Probabilidad B M A
    "I": 6, "J": 6, "K": 6,            # Consecuencias LD D ED
    "L": 6, "M": 6, "N": 6, "O": 6, "P": 6,  # Estimación T TO M I IN
    "Q": 70,                           # Medidas de control
    "R": 17, "S": 15, "T": 14,         # Procedimiento / Información / Formación
    "U": 7, "V": 7,                    # ¿Riesgo controlado? SI / NO
    "W": 24, "X": 20, "Y": 15, "Z": 20,  # Plan de acción
}
COL_PROB = {"B": "F", "M": "G", "A": "H"}
COL_CONS = {"LD": "I", "D": "J", "ED": "K"}
COL_NIVEL = {"T": "L", "TO": "M", "M": "N", "I": "O", "IN": "P"}
ULTIMA_COL = "Z"
FILA_DATOS = 15

FUENTE = "Arial"
_fino = Side(style="thin", color="FF000000")
_medio = Side(style="medium", color="FF000000")
BORDE = Border(left=_fino, right=_fino, top=_fino, bottom=_fino)

CENTRO = Alignment(horizontal="center", vertical="center", wrap_text=True)
IZQUIERDA = Alignment(horizontal="left", vertical="center", wrap_text=True)


def _fill(argb: str) -> PatternFill:
    return PatternFill("solid", start_color=argb, end_color=argb)


# ----------------------------------------------------------------------------
# Helpers de pintado
# ----------------------------------------------------------------------------
def celda(
    ws: Worksheet,
    rango: str,
    valor=None,
    *,
    bold: bool = False,
    size: int = 11,
    color_fondo: str | None = None,
    color_fuente: str = "FF000000",
    alinear: Alignment = CENTRO,
    formato: str | None = None,
    borde: bool = True,
) -> None:
    """Escribe valor, combina si es rango y aplica estilo/borde a todas las celdas."""
    min_c, min_r, max_c, max_r = range_boundaries(rango if ":" in rango else f"{rango}:{rango}")
    if (min_c, min_r) != (max_c, max_r):
        ws.merge_cells(start_row=min_r, start_column=min_c, end_row=max_r, end_column=max_c)
    principal = ws.cell(row=min_r, column=min_c)
    if valor is not None:
        principal.value = valor
    principal.font = Font(name=FUENTE, size=size, bold=bold, color=color_fuente)
    principal.alignment = alinear
    if formato:
        principal.number_format = formato
    for r in range(min_r, max_r + 1):
        for c in range(min_c, max_c + 1):
            cel = ws.cell(row=r, column=c)
            if borde:
                cel.border = BORDE
            if color_fondo:
                cel.fill = _fill(color_fondo)


def _marca(condicion: bool) -> str:
    return "X" if condicion else ""


def _lineas(texto: str, ancho_col: float, size: int = 10) -> int:
    if not texto:
        return 1
    chars = max(1, int(ancho_col * 1.15 * 10 / size))
    return sum(max(1, math.ceil(len(p) / chars)) for p in str(texto).split("\n"))


def _contorno_medio(ws: Worksheet, fila_ini: int, fila_fin: int) -> None:
    """Marco exterior grueso del bloque."""
    ultima = ws[f"{ULTIMA_COL}1"].column
    for c in range(1, ultima + 1):
        for r, lado in ((fila_ini, "top"), (fila_fin, "bottom")):
            cel = ws.cell(row=r, column=c)
            b = cel.border
            cel.border = Border(
                left=b.left, right=b.right,
                top=_medio if lado == "top" else b.top,
                bottom=_medio if lado == "bottom" else b.bottom,
            )
    for r in range(fila_ini, fila_fin + 1):
        for c, lado in ((1, "left"), (ultima, "right")):
            cel = ws.cell(row=r, column=c)
            b = cel.border
            cel.border = Border(
                top=b.top, bottom=b.bottom,
                left=_medio if lado == "left" else b.left,
                right=_medio if lado == "right" else b.right,
            )


# ----------------------------------------------------------------------------
# Secciones
# ----------------------------------------------------------------------------
def _encabezado(ws: Worksheet, m: MatrizFormato) -> None:
    e = m.encabezado
    fmt_fecha = "DD/MM/YYYY"

    ws.row_dimensions[1].height = 80
    celda(ws, "A1:Z1", cfg.TITULO_FORMATO, bold=True, size=20)
    ws.row_dimensions[2].height = 36
    celda(ws, "A2:Z2", cfg.SUBTITULO_FORMATO, bold=True, size=18, color_fondo=cfg.COLOR_TITULO_AMARILLO)

    for r in range(3, 9):
        ws.row_dimensions[r].height = 34
    # Empresa / niveles / descripción del cargo
    celda(ws, "A3:E3", "EMPRESA / ENTIDAD:", bold=True)
    celda(ws, "F3:L3", e.empresa, size=9)
    celda(ws, "M3:U3", "NIVELES DE RIESGO", bold=True, color_fondo=cfg.COLOR_ENCABEZADO)
    celda(ws, "V3:Z3", "DESCRIPCION DEL CARGO", bold=True, color_fondo=cfg.COLOR_ENCABEZADO)
    celda(ws, "V4:Z8", e.descripcion_cargo, alinear=IZQUIERDA)

    # Sector
    celda(ws, "A4:E4", "SECTOR", bold=True)
    celda(ws, "F4", _marca(e.sector == "PLANTA"), bold=True)
    celda(ws, "G4:I4", "PLANTA")
    celda(ws, "J4", _marca(e.sector == "CAMPO"), bold=True)
    celda(ws, "K4:L4", "CAMPO")

    # Leyenda probabilidad / consecuencia
    celda(ws, "A5:E5", "PROBABILIDAD", bold=True, color_fondo=cfg.COLOR_ENCABEZADO)
    celda(ws, "F5:L5", "CONSECUENCIA", bold=True, color_fondo=cfg.COLOR_ENCABEZADO)
    leyenda = [
        ("ALTA (A)", "(A)", "EXTREMADAMENTE DAÑINO (ED)", "(ED)"),
        ("MEDIA (M)", "(M)", "DAÑINO (D)", "(D)"),
        ("BAJA (B)", "(B)", "LIGERAMENTE DAÑINO (LD)", "(LD)"),
    ]
    for i, (p, pc, c, cc) in enumerate(leyenda):
        r = 6 + i
        celda(ws, f"A{r}:D{r}", p)
        celda(ws, f"E{r}", pc, bold=True)
        celda(ws, f"F{r}:K{r}", c)
        celda(ws, f"L{r}", cc, bold=True)

    # Niveles de riesgo (leyenda con colores)
    for i, cod in enumerate(("T", "TO", "M", "I", "IN")):
        r = 4 + i
        celda(ws, f"M{r}:O{r}", cfg.NIVEL_NOMBRE[cod].upper(), bold=True, color_fondo=cfg.COLOR_NIVEL[cod])
        celda(ws, f"P{r}:U{r}", cfg.TEXTO_NIVEL[cod], size=8, alinear=IZQUIERDA)
    ws.row_dimensions[6].height = 58
    ws.row_dimensions[7].height = 44

    # Localización / puesto / trabajadores / evaluación
    for r in (9, 10, 11):
        ws.row_dimensions[r].height = 30
    celda(ws, "A9:C9", "LOCALIZACIÓN", bold=True)
    celda(ws, "D9:P9", e.localizacion)
    celda(ws, "A10:C10", "PUESTO DE TRABAJO", bold=True)
    celda(ws, "D10:P10", e.puesto)
    celda(ws, "A11:C11", "NUMERO DE TRABAJADORES", bold=True)
    celda(ws, "D11:P11", e.numero_trabajadores)

    celda(ws, "Q9:U10", "EVALUACIÓN", bold=True, color_fondo=cfg.COLOR_ENCABEZADO)
    celda(ws, "Q11", "INICIAL", bold=True, size=9)
    celda(ws, "R11", _marca(e.evaluacion_inicial), bold=True)
    celda(ws, "S11:T11", "PERIÓDICA", bold=True, size=9)
    celda(ws, "U11", _marca(not e.evaluacion_inicial), bold=True)

    celda(ws, "V9:X9", "PROCESO", bold=True)
    celda(ws, "Y9:Z9", e.proceso)
    celda(ws, "V10:X10", "FECHA DE EVALUACIÓN", bold=True)
    celda(ws, "Y10:Z10", e.fecha_evaluacion, formato=fmt_fecha)
    celda(ws, "V11:X11", "FECHA DE LA PROX. EVALUACIÓN", bold=True)
    celda(ws, "Y11:Z11", e.fecha_proxima, formato=fmt_fecha)

    # Títulos de la tabla
    ws.row_dimensions[12].height = 40
    celda(ws, "A12:P12", "EVALUACIÓN DE RIESGOS", bold=True, size=18, color_fuente="FFFFFFFF",
          color_fondo=cfg.COLOR_SECCION)
    celda(ws, "Q12:V12", "Medidas de control establecidas para el factor de riesgo:", bold=True)
    celda(ws, "W12:Z12", "Si el riesgo no está controlado, completar la siguiente tabla:", bold=True)

    ws.row_dimensions[13].height = 34
    ws.row_dimensions[14].height = 34
    gris = cfg.COLOR_ENCABEZADO
    for rango, txt in (
        ("A13:C14", "FACTORES DE RIESGO"), ("D13:D14", "N°"), ("E13:E14", "ACTIVIDAD"),
        ("F13:H13", "PROBABILIDAD"),
        ("I13:K13", "CONSECUENCIAS"), ("L13:P13", "ESTIMACIÓN DEL RIESGO"),
        ("Q13:Q14", "MEDIDAS DE CONTROL"), ("R13:R14", "PROCEDIMIENTO DE TRABAJO"),
        ("S13:S14", "INFORMACION"), ("T13:T14", "FORMACION"),
        ("U13:V13", "¿Riesgo Controlado?"), ("W13:W14", "Acción Requerida"),
        ("X13:X14", "Responsable"), ("Y13:Y14", "Fecha finalización"),
        ("Z13", "Comprobación de eficacia"), ("Z14", "Firma y Fecha"),
    ):
        celda(ws, rango, txt, bold=True, size=10, color_fondo=gris)
    for cod, col in COL_PROB.items():
        celda(ws, f"{col}14", cod, bold=True, color_fondo=gris)
    for cod, col in COL_CONS.items():
        celda(ws, f"{col}14", cod, bold=True, color_fondo=gris)
    for cod, col in COL_NIVEL.items():
        celda(ws, f"{col}14", cod, bold=True, color_fondo=cfg.COLOR_NIVEL[cod])
    celda(ws, "U14", "SI", bold=True, color_fondo=gris)
    celda(ws, "V14", "NO", bold=True, color_fondo=gris)


def _fila_datos(ws: Worksheet, r: int, n: int, f: Fila) -> None:
    medidas_txt = "\n".join(f"• {m}" for m in f.medidas)
    celda(ws, f"B{r}", f.factor, size=10)
    celda(ws, f"C{r}", f.descripcion, size=9, alinear=IZQUIERDA)
    celda(ws, f"D{r}", n, bold=True)
    celda(ws, f"E{r}", f.actividad, size=10, alinear=IZQUIERDA)
    for cod, col in COL_PROB.items():
        celda(ws, f"{col}{r}", _marca(f.probabilidad == cod), bold=True)
    for cod, col in COL_CONS.items():
        celda(ws, f"{col}{r}", _marca(f.consecuencia == cod), bold=True)
    for cod, col in COL_NIVEL.items():
        activo = f.nivel == cod
        celda(ws, f"{col}{r}", cod if activo else "", bold=True,
              color_fondo=cfg.COLOR_NIVEL[cod] if activo else None)
    celda(ws, f"Q{r}", medidas_txt, size=9, alinear=IZQUIERDA)
    # Regla del formato: si hay medidas -> X en Procedimiento, Información, Formación y SI
    for col in ("R", "S", "T", "U"):
        celda(ws, f"{col}{r}", _marca(f.tiene_medidas), bold=True)
    for col in ("V", "W", "X", "Y", "Z"):
        celda(ws, f"{col}{r}", "")

    alto = max(
        _lineas(f.descripcion, ANCHOS["C"], 9),
        _lineas(f.actividad, ANCHOS["E"], 10),
        _lineas(medidas_txt, ANCHOS["Q"], 9),
        _lineas(f.factor, ANCHOS["B"], 10),
        3,
    )
    ws.row_dimensions[r].height = min(409, alto * 13 + 8)


def _asegurar_alto(ws: Worksheet, ini: int, fin: int, minimo: float) -> None:
    """El texto vertical de la columna A necesita alto suficiente en el bloque."""
    actual = sum(ws.row_dimensions[i].height or 15 for i in range(ini, fin + 1))
    if actual < minimo:
        extra = (minimo - actual) / (fin - ini + 1)
        for i in range(ini, fin + 1):
            ws.row_dimensions[i].height = (ws.row_dimensions[i].height or 15) + extra


def _cuerpo(ws: Worksheet, m: MatrizFormato) -> int:
    """Pinta filas; combina columna A por riesgo asociado y B/C por factor repetido."""
    r = FILA_DATOS
    n = 1
    for clasif, grupo_cat in groupby(m.filas, key=lambda f: f.clasificacion):
        ini_cat = r
        for _, grupo_fac in groupby(list(grupo_cat), key=lambda f: f.factor):
            ini_fac = r
            filas_fac = list(grupo_fac)
            for f in filas_fac:
                _fila_datos(ws, r, n, f)
                r += 1
                n += 1
            if len(filas_fac) > 1:
                ws.merge_cells(f"B{ini_fac}:B{r - 1}")
                ws.merge_cells(f"C{ini_fac}:C{r - 1}")
        etiqueta = cfg.CLASIFICACIONES.get(clasif, {}).get("etiqueta", clasif)
        _asegurar_alto(ws, ini_cat, r - 1, len(etiqueta) * 7.5 + 16)
        celda(ws, f"A{ini_cat}:A{r - 1}", etiqueta, bold=True, size=11,
              color_fondo=cfg.COLOR_CATEGORIA,
              alinear=Alignment(horizontal="center", vertical="center",
                                wrap_text=True, text_rotation=90))
    return r  # siguiente fila libre


def _pie(ws: Worksheet, m: MatrizFormato, r: int) -> int:
    e = m.encabezado
    fmt = "DD/MM/YYYY"
    filas = (
        ("EVALUACIÓN REALIZADA POR:", e.evaluado_por, e.fecha_evaluado_por),
        ("PLAN DE ACCIÓN REALIZADO POR:", "", None),
    )
    for etiqueta, nombre, fecha in filas:
        ws.row_dimensions[r].height = 40
        celda(ws, f"A{r}:P{r}", etiqueta, bold=True, size=12)
        celda(ws, f"Q{r}:U{r}", nombre)
        celda(ws, f"V{r}:W{r}", "FECHA:", bold=True)
        celda(ws, f"X{r}:Z{r}", fecha, formato=fmt)
        r += 1
    ws.row_dimensions[r].height = 40
    celda(ws, f"A{r}:P{r}", "FECHA PRÓXIMA EVALUACIÓN:", bold=True, size=12)
    celda(ws, f"Q{r}:Z{r}", e.fecha_proxima, formato=fmt)
    return r


def _logos(ws: Worksheet) -> None:
    for archivo, ancla, alto in (("logo_sedemi.png", "A1", 50), ("logo_mrl.png", "W1", 70)):
        ruta = cfg.ASSETS_DIR / archivo
        if not ruta.exists():
            continue
        img = XLImage(str(ruta))
        escala = alto / img.height
        img.height, img.width = alto, int(img.width * escala)
        ws.add_image(img, ancla)


def _impresion(ws: Worksheet, ultima_fila: int) -> None:
    # Sin paneles inmovilizados (a pedido). Para activarlos: ws.freeze_panes = "F15"
    ws.print_title_rows = "13:14"
    ws.print_area = f"A1:{ULTIMA_COL}{ultima_fila}"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True
    ws.sheet_view.zoomScale = 70


# ----------------------------------------------------------------------------
# API pública
# ----------------------------------------------------------------------------
def generar_excel(m: MatrizFormato) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = (m.encabezado.codigo_ast or "MATRIZ")[:31]
    for col, ancho in ANCHOS.items():
        ws.column_dimensions[col].width = ancho

    _encabezado(ws, m)
    siguiente = _cuerpo(ws, m) if m.filas else FILA_DATOS
    if not m.filas:
        celda(ws, f"A{FILA_DATOS}:{ULTIMA_COL}{FILA_DATOS}",
              "El AST no tiene registros en la matriz de riesgos.", bold=True)
        siguiente = FILA_DATOS + 1
    ultima = _pie(ws, m, siguiente)

    _contorno_medio(ws, 1, ultima)
    _logos(ws)
    _impresion(ws, ultima)

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def nombre_archivo(m: MatrizFormato) -> str:
    puesto = "".join(ch if ch.isalnum() else "_" for ch in m.encabezado.puesto)[:60].strip("_")
    return f"FOR_SEI_02_{m.encabezado.codigo_ast}_{puesto}.xlsx"


def generar_excel_matriz_ast(data: dict) -> tuple[bytes, str]:
    """Punto de entrada del router: payload -> (bytes del .xlsx, nombre de archivo)."""
    from functions.matriz_ast_service import construir

    modelo = construir(data)
    return generar_excel(modelo), nombre_archivo(modelo)
