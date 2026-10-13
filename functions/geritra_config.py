"""Reglas, textos y colores de la Matriz GERITRA (Gestión de Riesgos del Trabajo)."""
from pathlib import Path
from zoneinfo import ZoneInfo

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "matriz_ast"
TZ = ZoneInfo("America/Guayaquil")

TITULO = "MATRIZ DE GESTIÓN DE RIESGOS DEL TRABAJO"
SUBTITULO = "GERITRA · Una herramienta técnica para la gestión de seguridad y salud laboral"

# ----------------------------------------------------------------------------
# Nivel de riesgo por VALORACIÓN (P x C), igual que el VBA de la GERITRA
#   (se>0 y <5) Trivial · (<9) Tolerable · (<17) Moderado · (<25) Importante · (<37) Intolerable
# ----------------------------------------------------------------------------
RANGOS_NIVEL = [(5, "Trivial"), (9, "Tolerable"), (17, "Moderado"), (25, "Importante"), (37, "Intolerable")]

COLOR_NIVEL = {  # colores de la Guía del Usuario GERITRA (Pasos 18 y 19)
    "Trivial": "FFFFFFCC",
    "Tolerable": "FFFFFF00",
    "Moderado": "FFFFC000",
    "Importante": "FFD9667A",
    "Intolerable": "FFFF0000",
}

ACCION_NIVEL = {
    "Trivial": "Mantener las acciones que se vienen realizando. No se requiere acción específica.",
    "Tolerable": (
        "No se necesita mejorar la acción preventiva. Sin embargo se deben considerar soluciones más "
        "rentables o mejoras que no supongan una carga económica importante. Se requieren comprobaciones "
        "periódicas de las medidas de control."
    ),
    "Moderado": (
        "Se deben hacer esfuerzos para reducir el riesgo, determinando las inversiones precisas. Las "
        "medidas para reducir el riesgo deben implantarse en un período determinado."
    ),
    "Importante": (
        "No debe comenzarse el trabajo hasta que se haya reducido el riesgo. Puede que se precisen recursos "
        "considerables para controlar el riesgo y debe remediarse el problema en un tiempo inferior al de "
        "los riesgos moderados."
    ),
    "Intolerable": (
        "No debe comenzar ni continuar el trabajo hasta que se reduzca el riesgo. Si no es posible reducir "
        "el riesgo, incluso con recursos ilimitados, debe prohibirse el trabajo."
    ),
}

CODIGO_NIVEL = {"Trivial": "T", "Tolerable": "TO", "Moderado": "MO", "Importante": "I", "Intolerable": "IN"}

# Guía GERITRA, Paso 18: matriz Probabilidad x Consecuencias-Severidad (rango de valoración por celda)
MATRIZ_NIVELES = [
    [("Trivial", "4"), ("Tolerable", "5 – 8"), ("Moderado", "9 – 16")],
    [("Tolerable", "5 – 8"), ("Moderado", "9 – 16"), ("Importante", "17 – 24")],
    [("Moderado", "9 – 16"), ("Importante", "17 – 24"), ("Intolerable", "25 – 36")],
]
# Guía GERITRA, Paso 19: tabla de niveles de riesgo
VALORES_NIVEL = {"Trivial": "4", "Tolerable": "5 – 8", "Moderado": "9 – 16", "Importante": "17 – 24", "Intolerable": "25 – 36"}
NOTA_VALORACION = "Valoración (Paso 18) = Probabilidad (Σ de los 4 índices, 4 a 12) × Consecuencias (1 a 3). Nivel según la tabla de valores (Paso 19)."

CONSECUENCIA_IDX = {"Ligeramente dañino": 1, "Dañino": 2, "Extremadamente dañino": 3}

# Columna 20 (Clasificación de los riesgos): respaldo si el registro no la trae
CLASIFICACION_POR_RIESGO = {
    "FÍSICOS": "Factores de riesgo del medio ambiente físico",
    "QUÍMICOS": "Factores de riesgo por contaminantes químico-biológicos",
    "BIOLÓGICOS": "Factores de riesgo por contaminantes químico-biológicos",
    "ERGONÓMICOS": "Factores de riesgo ergonómico",
    "DE SEGURIDAD": "Factores de riesgo a la seguridad",
    "PSICOSOCIALES": "Factores de riesgo psicosocial",
}

# ----------------------------------------------------------------------------
# Jerarquía de controles (columnas 21-25) -> clave del catálogo jerarquia_medidas.json
# ----------------------------------------------------------------------------
JERARQUIA_COLUMNAS = [
    ("ELIMINAR", "V"),
    ("SUSTITUIR", "W"),
    ("INGENIERIA", "X"),
    ("ADM_NORMAS", "Y"),
    ("ADM_HORARIOS", "Z"),
    ("ADM_SENALIZACION", "AA"),
    ("TRAB_FORMACION", "AB"),
    ("TRAB_EPP", "AC"),
]
JERARQUIA_DEFECTO = "ADM_NORMAS"

# Valores de TipoDiscapacidad que significan "sin discapacidad"
SIN_DISCAPACIDAD = {"", "no aplica", "ninguna", "ninguno", "n/a", "na", "no", "-"}

COLOR_AZUL = "FF1F3864"
COLOR_GRIS = "FFD9E1F2"
COLOR_SECCION = {
    "ID": "FFDDEBF7",
    "PELIGROS": "FFFCE4D6",
    "JERARQUIA": "FFE2EFDA",
    "RESIDUAL": "FFFFF2CC",
}
