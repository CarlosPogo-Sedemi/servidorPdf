import unicodedata
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import weasyprint

env = Environment(loader=FileSystemLoader("templates_html"))

# ==========================================
# ESQUEMA FIJO DE LA SECCIÓN B (Formulario 083) — exactamente estas 6, siempre en
# este orden y siempre impresas aunque no haya datos (relleno en blanco).
# clave_normalizada -> (etiqueta_a_mostrar, base_por_defecto, bases_por_tipo_vacuna)
# bases_por_tipo_vacuna es None si el esquema no depende de TipoVacuna
# ==========================================
FIXED_SCHEMES = [
    ("DIFTERIA Y TETANOS", "Tétanos - Difteria", 5, {"1 DOSIS": 1, "5 DOSIS": 5}),
    ("HEPATITIS A", "Hepatitis A", 3, None),
    ("HEPATITIS B", "Hepatitis B", 3, None),
    ("INFLUENZA", "Influenza estacionaria", 1, None),
    ("FIEBRE AMARILLA", "Fiebre Amarilla", 1, None),
    ("SARAMPION RUBEOLA", "Sarampión-Rubéola", 2, None),
]
FIXED_KEYS = {clave for clave, *_ in FIXED_SCHEMES}

# Vacunas que van en "INMUNIZACIONES DE ACUERDO AL TIPO DE EMPRESA Y RIESGO" (no en la
# sección fija del Form 083) pero que igual siguen un esquema de dosis base + refuerzos
# (a diferencia de COVID y otras 100% dinámicas, que solo cuentan 1°, 2°, 3°... sin
# concepto de refuerzo). Solo se muestran si el paciente tiene registros de esa vacuna.
ESQUEMAS_TOPE_DINAMICOS = [
    ("HEPATITIS A Y B COMBINADA", "Hepatitis A y B (combinada)", 3, None),
    ("TIFOIDEA", "Tifoidea", 1, None),
    ("TETANOS", "Tétanos", 5, None),
]
ESQUEMAS_TOPE_KEYS = {clave for clave, *_ in ESQUEMAS_TOPE_DINAMICOS}


def _normalizar(texto: str) -> str:
    """Mayúsculas, sin tildes, sin guiones/paréntesis ni espacios duplicados. Para comparar
    nombres de vacuna (p.ej. "HEPATITIS A Y B (COMBINADA)" debe calzar con la clave fija
    "HEPATITIS A Y B COMBINADA")."""
    texto = (texto or "").strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.replace("-", " ").replace("(", " ").replace(")", " ")
    return " ".join(texto.split())


def _etiqueta_dosis(indice: int, base: int) -> str:
    if base == 1:
        return "Dosis única"
    return f"{indice}°"


def _extraer_dosis(vac: dict) -> list:
    """Aplana la primera dosis (FechaPrimeraDosis/lote1/...) + ListaActividades de una
    vacuna en una lista plana de filas {fecha, lote, responsable, establecimiento, observacion}.
    IMPORTANTE: la fecha SIEMPRE es la fecha real de aplicación, nunca la tentativa/proyectada.
    Todos los campos usan 'or \"\"' en vez de .get(clave, "") porque el JSON puede traer
    la clave presente con valor null (no ausente), y .get() solo aplica su default cuando
    la clave falta por completo."""
    filas = []
    if vac.get("FechaPrimeraDosis"):
        filas.append({
            "fecha": str(vac.get("FechaPrimeraDosis") or "").replace("-", "/"),
            "lote": vac.get("lote1") or "",
            "responsable": vac.get("Responsable1") or "",
            "establecimiento": vac.get("Establecimiento1") or "",
            "observacion": vac.get("Observacion1") or "",
        })

    for act in vac.get("ListaActividades", []) or []:
        fecha_real = act.get("FechaReal") or ""  # NUNCA usar FechaTentativa aquí
        observacion = act.get("Observacion") or ""
        marca = act.get("MarcaCovid") or ""
        if marca:
            observacion = f"{observacion} (Marca: {marca})".strip()
        filas.append({
            "fecha": str(fecha_real).replace("-", "/") if fecha_real else "",
            "lote": act.get("Lote") or "",
            "responsable": act.get("ResponsableVacuna") or "",
            "establecimiento": act.get("Establecimiento") or "",
            "observacion": observacion,
        })
    return filas


def _dosis_del_anio_en_curso(filas: list) -> list:
    """Influenza es estacional: en el registro puede haber hasta una dosis por año
    (varias en total), pero al Pasaporte solo le interesa la del año en curso. Se busca
    la fila cuya fecha (formato YYYY/MM/DD, ver _extraer_dosis) cae en el año actual; si
    no hay ninguna, se devuelve vacío (no se muestra ninguna dosis vieja ni la más
    reciente por defecto)."""
    anio_actual = str(datetime.now().year)
    for fila in filas:
        fecha = fila.get("fecha") or ""
        if fecha[:4] == anio_actual:
            return [fila]
    return []


def _armar_grupo_fijo(nombre_mostrar: str, base: int, filas: list) -> dict:
    """Construye siempre 'base' filas (rellenando en blanco las que falten) y agrega
    cualquier fila extra como 'Refuerzo N'. Marca 'esquema_completo' en la fila que cierra
    el esquema base, únicamente si esa fila tiene fecha REAL."""
    dosis = []
    for i in range(base):
        fila = filas[i] if i < len(filas) else {
            "fecha": "", "lote": "", "responsable": "", "establecimiento": "", "observacion": ""
        }
        dosis.append({**fila, "dosis": _etiqueta_dosis(i + 1, base), "esquema_completo": ""})

    for j, fila in enumerate(filas[base:], start=1):
        dosis.append({**fila, "dosis": f"Refuerzo {j}", "esquema_completo": ""})

    if base > 0 and len(dosis) >= base and dosis[base - 1]["fecha"]:
        dosis[base - 1]["esquema_completo"] = "X"

    return {"nombre": nombre_mostrar, "dosis": dosis}


def _armar_grupo_dinamico(vac: dict) -> dict:
    """Vacunas totalmente fuera de cualquier esquema conocido (COVID, etc.): tantas
    filas como dosis con fecha real tenga, sin relleno ni tope ni concepto de refuerzo."""
    filas = _extraer_dosis(vac)
    if not filas:
        filas = [{"fecha": "", "lote": "", "responsable": "", "establecimiento": "", "observacion": ""}]
    dosis = [
        {**fila, "dosis": f"{i}°", "esquema_completo": ""}
        for i, fila in enumerate(filas, start=1)
    ]
    return {"nombre": vac.get("NombreVacuna", ""), "dosis": dosis}


def construir_seccion_b(vacunas: list) -> tuple:
    """Separa las vacunas recibidas en (grupos_fijos, grupos_dinamicos), respetando el
    orden fijo del Form 083 para la primera sección (siempre esas 6, aunque no haya
    datos). HEPATITIS A Y B COMBINADA, TIFOIDEA y TETANOS (solo) usan el mismo esquema de
    dosis base + refuerzos que la sección fija, pero se listan en "de acuerdo al tipo de
    empresa y riesgo" y solo si el paciente tiene registros — no se fusionan con
    DIFTERIA Y TETANOS ni con las demás."""
    por_clave = {}
    por_clave_tope = {}
    dinamicas = []

    for vac in vacunas:
        clave = _normalizar(vac.get("NombreVacuna", ""))
        if clave in FIXED_KEYS:
            por_clave.setdefault(clave, []).append(vac)
        elif clave in ESQUEMAS_TOPE_KEYS:
            por_clave_tope.setdefault(clave, []).append(vac)
        else:
            dinamicas.append(vac)

    grupos_fijos = []
    for clave, etiqueta, base_defecto, bases_por_tipo in FIXED_SCHEMES:
        vacs_de_esta_clave = por_clave.get(clave, [])
        filas = []
        base = base_defecto
        for vac in vacs_de_esta_clave:
            filas.extend(_extraer_dosis(vac))
            if bases_por_tipo and vac.get("TipoVacuna") in bases_por_tipo:
                base = bases_por_tipo[vac["TipoVacuna"]]
        if clave == "INFLUENZA":
            filas = _dosis_del_anio_en_curso(filas)
        grupos_fijos.append(_armar_grupo_fijo(etiqueta, base, filas))

    grupos_dinamicos = []
    for clave, etiqueta, base_defecto, bases_por_tipo in ESQUEMAS_TOPE_DINAMICOS:
        vacs_de_esta_clave = por_clave_tope.get(clave, [])
        if not vacs_de_esta_clave:
            continue
        filas = []
        base = base_defecto
        for vac in vacs_de_esta_clave:
            filas.extend(_extraer_dosis(vac))
            if bases_por_tipo and vac.get("TipoVacuna") in bases_por_tipo:
                base = bases_por_tipo[vac["TipoVacuna"]]
        grupos_dinamicos.append(_armar_grupo_fijo(etiqueta, base, filas))

    grupos_dinamicos.extend(_armar_grupo_dinamico(vac) for vac in dinamicas)
    return grupos_fijos, grupos_dinamicos


def generar_pdf_vacunas(paciente: dict, vacunas: list) -> bytes:
    grupos_fijos, grupos_dinamicos = construir_seccion_b(vacunas)
    template = env.get_template("vacunas.html")
    html_str = template.render(paciente=paciente, grupos_fijos=grupos_fijos, grupos_dinamicos=grupos_dinamicos)
    return weasyprint.HTML(string=html_str).write_pdf()