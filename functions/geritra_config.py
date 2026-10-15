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


# ----------------------------------------------------------------------------
# Hoja REFERENCIAS GERITRA (Guía del Usuario, Pasos 11 a 20)
#   Reúne las tablas que antes estaban como leyenda "NIVELES DE RIESGO" en la hoja principal.
#   Los niveles (Pasos 18 y 19) salen de MATRIZ_NIVELES / VALORES_NIVEL / ACCION_NIVEL, definidos arriba.
# ----------------------------------------------------------------------------
NOMBRE_HOJA_REFERENCIAS = "REFERENCIAS GERITRA"

NOTA_REFERENCIAS = (
    "Tablas y descripciones de la Guía del Usuario GERITRA (Pasos 1 a 37). El número de cada paso es el del "
    "encabezado de la matriz. Las tablas de valoración (Pasos 12 a 19) aplican igual a la valoración inicial y a "
    "la residual (Pasos 26 a 33)."
)

COLOR_INDICE = {1: "FFFFFF99", 2: "FFFFC000", 3: "FFFF0000"}  # BAJA / MEDIA / ALTA (Pasos 12 a 15 y 17)

PASO_11_TEXTO = (
    "Número de trabajadores expuestos al peligro descrito en la columna 10. Lo registra el equipo evaluador "
    "(no se calcula): se cuentan las personas que realizan la actividad y están en contacto con el peligro. "
    "Esta cantidad determina el índice del Paso 12."
)

# paso -> (título de la sección, explicación, encabezado de la 3.ª columna, [(índice, calificación, descripción)])
TABLAS_INDICE = {
    12: (
        "PASO 12 · ÍNDICE DE PERSONAS EXPUESTAS (columna 12)",
        "Valor de 1 a 3 según la cantidad de personas expuestas registrada en la columna 11.",
        "PERSONAS EXPUESTAS",
        [(1, "BAJA", "De 1 a 5"), (2, "MEDIA", "De 6 a 12"), (3, "ALTA", "Más de 12")],
    ),
    13: (
        "PASO 13 · ÍNDICE DE PROCEDIMIENTOS EXISTENTES (columna 13)",
        "Valor de 1 a 3 según la existencia de controles, normas, planes, instructivos, permisos de trabajo "
        "o procedimientos para la actividad que se ejecuta en el puesto de trabajo.",
        "PROCEDIMIENTOS EXISTENTES",
        [
            (1, "BAJA", "Existen y son satisfactorios y suficientes"),
            (2, "MEDIA", "Existen parcialmente o no son satisfactorios o suficientes"),
            (3, "ALTA", "No existen"),
        ],
    ),
    14: (
        "PASO 14 · ÍNDICE DE CAPACITACIONES Y CAPACIDADES HUMANAS (columna 14)",
        "Valor de 1 a 3 según el nivel de información, formación y capacitación del trabajador para "
        "desarrollar la actividad en su puesto de trabajo.",
        "CAPACITACIÓN Y CAPACIDADES HUMANAS",
        [
            (1, "BAJA", "Personal entrenado, conoce el peligro y lo previene"),
            (2, "MEDIA", "Personal parcialmente entrenado. Conoce el peligro, pero no toma acciones de control"),
            (3, "ALTA", "Personal no entrenado, no conoce el peligro, no toma acciones de control"),
        ],
    ),
    15: (
        "PASO 15 · ÍNDICE DE EXPOSICIÓN AL RIESGO (columna 15)",
        "Valor de 1 a 3 según la frecuencia con la que las personas expuestas (Paso 12) se exponen al peligro.",
        "EXPOSICIÓN AL RIESGO",
        [
            (1, "BAJA", "Las personas se exponen al peligro en raras ocasiones, de manera muy inusual, casi nunca "
                        "y en largos periodos transcurridos"),
            (2, "MEDIA", "Las personas se exponen al peligro de manera eventual, ocasional, en lapsos de tiempo "
                         "medio y no seguido"),
            (3, "ALTA", "Las personas se exponen al peligro de manera continua, frecuente, en forma recurrente, "
                        "en periodos de tiempo cortos y seguidos"),
        ],
    ),
    17: (
        "PASO 17 · CONSECUENCIAS - SEVERIDAD (columna 17)",
        "Valor de 1 a 3 según el daño que produciría la materialización del peligro.",
        "CONSECUENCIAS-SEVERIDAD",
        [
            (1, "LIGERAMENTE DAÑINO",
             "(Seguridad) Sin lesión / lesión sin discapacidad, pequeños cortes o magulladuras, disconfort.\n"
             "(Salud ocupacional) Malestar, molestias e irritación, dolor de cabeza, irritación de ojos."),
            (2, "DAÑINO",
             "(Seguridad) Lesión con incapacidad temporal, fracturas menores, cortes, quemaduras, conmociones, "
             "torceduras importantes.\n"
             "(Salud ocupacional) Daño a la salud reversible: dermatitis, asmas, trastornos musculoesqueléticos."),
            (3, "EXTREMADAMENTE DAÑINO",
             "(Seguridad) Lesión con incapacidad permanente / muerte, amputaciones, fracturas mayores.\n"
             "(Salud ocupacional) Daño a la salud irreversible: intoxicaciones, lesiones múltiples, lesiones "
             "fatales, pérdida auditiva, cáncer y otras enfermedades, enfermedades crónicas."),
        ],
    ),
}

# Paso 20: clasificación de los riesgos (columna 20)
CLASIFICACIONES_RIESGO = [
    "Factores de riesgo del medio ambiente físico",
    "Factores de riesgo por contaminantes químico-biológicos",
    "Factores de riesgo ergonómico",
    "Factores de riesgo psicosocial",
    "Factores de riesgo a la seguridad",
    "Factores de riesgo ambiental",
]

NOTA_RESIDUAL = (
    "Después de aplicar los controles (columnas 21 a 25) el riesgo se reevalúa con las mismas tablas: índice de "
    "personas expuestas (26), de procedimientos existentes (27), de capacitaciones y capacidades humanas (28), "
    "de exposición al riesgo (29), probabilidad (30), consecuencias (31), valoración (32) y nivel de riesgo (33)."
)

# Descripción de cada paso/columna de la matriz (Guía del Usuario, sección 7)
# sección de la matriz -> [(paso, nombre de la columna, qué se registra)]
PASOS_DESCRIPCION = {
    "ID": [
        ("1", "PROCESO",
         "Procesos que se desarrollan en el centro de trabajo: conjunto de actividades relacionadas entre sí que "
         "transforman elementos de entrada en elementos de salida. Se levantan con investigación documental, "
         "entrevista directa a trabajadores y directivos, y observación de campo (Anexo 03)."),
        ("2", "PUESTO DE TRABAJO",
         "Espacio en el que uno o más trabajadores desarrollan la actividad laboral necesaria para cumplir el "
         "proceso identificado. Se levanta con observación de campo y entrevista directa a los trabajadores "
         "(Anexos 03 y 04)."),
        ("3", "PERSONA CON DISCAPACIDAD",
         "Tipo de discapacidad de la persona que trabaja en el puesto, escogido de la lista de la matriz (tipos "
         "más abajo). Si no hay personas con discapacidad en el puesto se coloca N/A."),
        ("4", "PORCENTAJE DE DISCAPACIDAD",
         "Porcentaje de discapacidad que consta en el carné de la persona. N/A si no hay una persona con "
         "discapacidad en el puesto."),
        ("5", "AYUDAS TÉCNICAS EN EL TRABAJO",
         "Nombre de la ayuda técnica que usa la persona con discapacidad, escogida de la lista de la matriz. Si no "
         "consta en la lista se elige Otra y se especifica en observaciones. N/A si no hay una persona con "
         "discapacidad."),
        ("6", "OBSERVACIÓN",
         "Observación especial sobre la persona con discapacidad: descripción puntual de su discapacidad, si toma "
         "algún medicamento diario, si es alérgica a alguna medicación, etc. N/A si no hay una persona con "
         "discapacidad."),
        ("7", "ACTIVIDAD RUTINARIA",
         "Actividades permanentes y diarias que forman parte de un proceso de la organización, planificadas y "
         "estandarizadas, que cumplen los trabajadores de los puestos descritos en el Paso 2. N/A si no "
         "corresponde a una actividad rutinaria."),
        ("8", "ACTIVIDAD NO RUTINARIA",
         "Actividades que se realizan con frecuencia baja y que no han sido planificadas ni estandarizadas. Se "
         "identifican con investigación documental, observación de campo y entrevista directa a los trabajadores "
         "(Anexo 04)."),
        ("9", "MÁQUINAS, EQUIPOS, SUSTANCIAS Y ENERGÍAS EMPLEADAS",
         "Equipos, herramientas, máquinas, sustancias y energías (o combustible) usados en la actividad. Se "
         "levanta un inventario práctico en planta, con las hojas de seguridad de las sustancias y los manuales "
         "técnicos de las máquinas, para detectar posibles fallos o deficiencias que provoquen un accidente o "
         "enfermedad."),
    ],
    "PELIGROS": [
        ("10", "PELIGRO",
         "Principal peligro inherente a la actividad, a los equipos, energías, máquinas y herramientas: toda "
         "condición, situación o acción con capacidad de producir daño a las personas, a los bienes del centro de "
         "trabajo o al medio ambiente. Se identifica un peligro por celda; si la actividad tiene otro peligro se "
         "registra en una nueva fila."),
    ],
    "JERARQUIA": [
        ("21", "ELIMINAR",
         "Primera técnica de control: eliminar la fuente de daño, adaptando el trabajo a los trabajadores. "
         "Ejemplo: separación física entre el tráfico vehicular y los peatones para dejar de exponer al trabajador "
         "al atropellamiento."),
        ("22", "SUSTITUIR POR",
         "Segunda técnica, control en el origen: sustituir materiales peligrosos por otros menos peligrosos o "
         "cambiar el tipo de energía por una de menor riesgo. Ejemplo: adhesivo sintético derivado del petróleo "
         "por uno de origen vegetal. Su suma permite generar un Plan de sustitución de activos."),
        ("23", "CONTROL DE INGENIERÍA Y DISEÑO",
         "Si el riesgo no se superó con los dos controles anteriores: rediseño del equipamiento o del proceso. "
         "Ejemplo: barreras físicas o resguardos, como protectores de plástico transparente o vidrio contra "
         "estornudos. Su suma permite elaborar un Plan de acciones correctivas de ingeniería."),
        ("24 a)", "CONTROL ADMINISTRATIVO: NORMAS, PLANES, PROCEDIMIENTOS, PERMISOS",
         "Procedimientos, instrucciones de trabajo, guías, buenas prácticas o permisos de trabajo para controlar "
         "el riesgo evaluado. Su suma permite generar el Manual de procedimientos de seguridad."),
        ("24 b)", "CONTROL ADMINISTRATIVO: ORGANIZACIÓN DE HORARIOS, DESCANSOS, ROTACIÓN DE PUESTOS",
         "Horarios de trabajo, descansos intermedios y rotación del personal para reducir los niveles de "
         "exposición. Su suma da el Plan de jornada de trabajo y rotación de puestos."),
        ("24 c)", "CONTROL ADMINISTRATIVO: SEÑALIZACIÓN",
         "Señales de advertencia, obligatoriedad de uso de EPP, prohibición, lucha contra incendios, salvamento o "
         "evacuación. Su suma da el Plan de señalización."),
        ("25 a)", "CONTROL EN EL TRABAJADOR: FORMACIÓN, INFORMACIÓN Y CAPACITACIÓN",
         "Inducciones, información, cursos de formación y capacitación necesarios para el trabajador expuesto a "
         "los riesgos de su puesto, registrados con la firma del trabajador. Su suma genera el Plan anual de "
         "capacitación en seguridad."),
        ("25 b)", "CONTROL EN EL TRABAJADOR: EQUIPOS DE PROTECCIÓN COLECTIVA E INDIVIDUAL",
         "Equipos de protección que debe usar el trabajador, ubicando primero los colectivos y luego los "
         "individuales, para reducir la exposición al riesgo. Su suma permite elaborar el Plan de manejo de "
         "equipos de protección colectiva e individual."),
    ],
    "RESIDUAL": [
        ("34", "EFECTOS SOBRE LA SALUD DE LOS TRABAJADORES",
         "Efectos que provoca la exposición al riesgo sobre la salud del trabajador, registrados con apoyo del "
         "médico ocupacional. El nivel de detalle depende de su conocimiento y experticia."),
        ("35", "VIGILANCIA DE LA SALUD",
         "Procedimiento que establece el médico ocupacional para vigilar la salud del trabajador: control "
         "preempleo, periódico, de retiro o reingreso, con los exámenes de gabinete y su periodicidad o fechas. "
         "Su suma arroja el Plan de vigilancia de la salud."),
        ("36", "FECHA DE CONTROL E INSPECCIONES",
         "Fechas en las que la organización planifica revisar el cumplimiento de la jerarquía de controles. Su "
         "suma arroja el Plan de inspecciones y seguimiento."),
        ("37", "ACTIVIDADES DE MEJORA CONTINUA",
         "Novedades, observaciones, ajustes o decisión de aplicar una metodología de evaluación específica "
         "surgidos tras las inspecciones y el seguimiento, siguiendo el ciclo de Deming (PHVA). Su suma da el "
         "Plan de mejora continua de la organización."),
    ],
}

NOTA_JERARQUIA = (
    "Orden de aplicación: eliminar, sustituir, control de ingeniería y diseño, control administrativo y control "
    "en el trabajador. Se da prioridad a las medidas colectivas sobre las individuales."
)

# Paso 3: lista de selección (definiciones de la guía, sección 5)
TIPOS_DISCAPACIDAD = [
    ("Física",
     "Deficiencias corporales y/o viscerales, evidentes (amputaciones, paraplejia, hemiparesia) o imperceptibles "
     "(enfermedades cardíacas), que ocasionan dificultad significativa o imposibilidad para caminar, correr, "
     "manipular objetos, subir o bajar gradas, levantarse, sentarse, mantener el equilibrio, controlar esfínteres, "
     "entre otros."),
    ("Intelectual",
     "Especial dificultad en la comprensión de ideas complejas, el razonamiento, la resolución de problemas y la "
     "toma de decisiones; repercute en la socialización, el relacionamiento interpersonal y el desenvolvimiento "
     "en la vida diaria."),
    ("Visual",
     "Ceguera y baja visión: alto grado de pérdida de visión, aun con la mejor corrección posible (lentes), "
     "sin posibilidad de mejoría con cirugía o tratamiento. Incluye la desfiguración de un ojo y el uso de "
     "prótesis ocular."),
    ("Auditiva",
     "Sordera total y/o moderada y severa de ambos oídos, que dificulta la comunicación con el entorno. Puede "
     "deberse a causas genéticas, congénitas, infecciosas, ocupacionales, traumáticas, tóxicas, envejecimiento "
     "y otras."),
    ("Psicosocial",
     "Deficiencias y/o trastornos de la conciencia, del comportamiento, del razonamiento, de los estados de "
     "ánimo, de la afectividad y de la comprensión de la realidad (irritabilidad, depresión, inestabilidad "
     "emocional crónica); generalmente por enfermedades mentales como esquizofrenia, trastorno bipolar, "
     "psicosis y otras."),
]

# Paso 5: lista de selección
AYUDAS_TECNICAS = ["Silla de ruedas", "Bastón", "Audífonos", "Lupas", "Órtesis", "Prótesis", "Otra (especificar en observaciones)"]
