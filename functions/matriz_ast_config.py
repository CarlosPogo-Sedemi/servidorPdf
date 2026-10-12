"""Reglas y constantes del formato FOR SEI 02 (método INSST).

Todo lo que se pueda querer ajustar sin tocar lógica vive aquí: etiquetas de
la columna A, colores, textos de la leyenda y años para la próxima evaluación.
"""
from pathlib import Path
from zoneinfo import ZoneInfo

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "matriz_ast"
TZ = ZoneInfo("America/Guayaquil")

# ----------------------------------------------------------------------------
# Encabezado
# ----------------------------------------------------------------------------
TITULO_FORMATO = (
    "MATRIZ  DE RIESGOS LABORALES POR PUESTO DE TRABAJO\n"
    "FOR SEI 02  VER: 05  FECHA: 17 01 22"
)
SUBTITULO_FORMATO = "EVALUACION DE RIESGOS LABORALES INSST"
EMPRESA_DEFECTO = "SEDEMI SCC"
ANIOS_PROXIMA_EVALUACION = 2

# ----------------------------------------------------------------------------
# Riesgo asociado (clasificación de la app) -> etiqueta columna A + orden
# ----------------------------------------------------------------------------
CLASIFICACIONES = {
    "BIOLÓGICOS": {"orden": 1, "etiqueta": "RIESGO BIOLÓGICO"},
    "ERGONÓMICOS": {"orden": 2, "etiqueta": "RIESGO ERGONÓMICO"},
    "FÍSICOS": {"orden": 3, "etiqueta": "RIESGO FÍSICO"},
    "DE SEGURIDAD": {"orden": 4, "etiqueta": "RIESGO MECÁNICO"},
    "PSICOSOCIALES": {"orden": 5, "etiqueta": "FACTORES PSICOSOCIALES"},
    "QUÍMICOS": {"orden": 6, "etiqueta": "FACTOR DE RIESGO QUÍMICO"},
}

# ----------------------------------------------------------------------------
# Método INSST
#   Probabilidad (suma de 4 índices, 4-12): 4 Baja | 5-8 Media | 9-12 Alta
#   Nivel = tabla 3x3 == (idxProbabilidad + idxConsecuencia)
# ----------------------------------------------------------------------------
PROBABILIDAD_IDX = {"Baja": 1, "Media": 2, "Alta": 3}
PROBABILIDAD_COD = {"Baja": "B", "Media": "M", "Alta": "A"}

CONSECUENCIA_IDX = {
    "Ligeramente dañino": 1,
    "Dañino": 2,
    "Extremadamente dañino": 3,
}
CONSECUENCIA_COD = {1: "LD", 2: "D", 3: "ED"}

NIVEL_POR_SUMA = {2: "T", 3: "TO", 4: "M", 5: "I", 6: "IN"}
NIVEL_NOMBRE = {
    "T": "Trivial",
    "TO": "Tolerable",
    "M": "Moderado",
    "I": "Importante",
    "IN": "Intolerable",
}

# Colores ARGB (tomados del formato original)
COLOR_NIVEL = {
    "T": "FFFFFF99",
    "TO": "FFFFFF00",
    "M": "FFFF6699",
    "I": "FFFF9900",
    "IN": "FFFF0000",
}
COLOR_TITULO_AMARILLO = "FFFFFF99"
COLOR_CATEGORIA = "FFFF99CC"
COLOR_ENCABEZADO = "FFD9E1F2"
COLOR_SECCION = "FF0070C0"

TEXTO_NIVEL = {
    "T": "No se requiere acción específica",
    "TO": (
        "No se necesita mejorar la acción preventiva. Sin embargo se deben considerar "
        "soluciones más rentables o mejoras que no supongan una carga económica importante. "
        "Se requieren comprobaciones periódicas para asegurar que se mantiene la eficacia "
        "de las medidas de control"
    ),
    "M": (
        "Se deben hacer esfuerzos para reducir el riesgo, determinando las inversiones precisas, "
        "Las medidas para reducir el riesgo deben implementarse en un período determinado. "
        "Cuando el riesgo moderado está asociado con consecuencias extremadamente dañinas se "
        "precisará una acción posterior para establecer con más precisión la probabilidad de "
        "daño como base para determinar la necesidad de mejora de las medidas de control."
    ),
    "I": (
        "No debe comenzarse el trabajo hasta que se haya reducido el riesgo. Pueda que se "
        "precisen recursos considerables para controlar el riesgo. Cuando el riesgo corresponda "
        "a un trabajo que se está realizando, debe remediarse el problema en un tiempo inferior "
        "a el de los riesgos moderados."
    ),
    "IN": (
        "No se debe comenzar o continuar con el trabajo hasta que se reduzca el riesgo. Si no es "
        "posible reducir el riesgo, incluso con recursos ilimitados, debe prohibirse el trabajo."
    ),
}
