import unicodedata
from jinja2 import Environment, FileSystemLoader
import weasyprint

env = Environment(loader=FileSystemLoader("templates_html"))

# ==========================================
# ESQUEMA FIJO DE LA SECCIÓN B (Formulario 083)
# (clave_normalizada, etiqueta_a_mostrar, dosis_base_del_esquema)
# El orden de esta lista es el orden en que aparecen las filas en el PDF.
# ==========================================
FIXED_SCHEMES = [
    ("DIFTERIA Y TETANOS", "Tétanos - Difteria", 5),
    ("HEPATITIS A", "Hepatitis A", 3),
    ("HEPATITIS B", "Hepatitis B", 3),
    ("INFLUENZA", "Influenza estacionaria", 1),
    ("FIEBRE AMARILLA", "Fiebre Amarilla", 1),
    ("SARAMPION RUBEOLA", "Sarampión-Rubéola", 2),
]
FIXED_KEYS = {clave for clave, _, _ in FIXED_SCHEMES}


def _normalizar(texto: str) -> str:
    """Mayúsculas, sin tildes, sin guiones ni espacios duplicados. Para comparar nombres de vacuna."""
    texto = (texto or "").strip().upper()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.replace("-", " ")
    return " ".join(texto.split())


def _etiqueta_dosis(indice: int, base: int) -> str:
    if base == 1:
        return "Dosis única"
    return f"{indice}°"


def _extraer_dosis(vac: dict) -> list:
    """Aplana la primera dosis (FechaPrimeraDosis/lote1/...) + ListaActividades de una
    vacuna en una lista plana de filas {fecha, lote, responsable, establecimiento, observacion}."""
    filas = []
    if vac.get("FechaPrimeraDosis"):
        filas.append({
            "fecha": str(vac.get("FechaPrimeraDosis", "")).replace("-", "/"),
            "lote": vac.get("lote1", ""),
            "responsable": vac.get("Responsable1", ""),
            "establecimiento": vac.get("Establecimiento1", ""),
            "observacion": vac.get("Observacion1", ""),
        })

    for act in vac.get("ListaActividades", []) or []:
        fecha = act.get("FechaReal") or act.get("FechaTentativa") or ""
        observacion = act.get("Observacion", "") or ""
        marca = act.get("MarcaCovid", "")
        if marca:
            # La plantilla no tiene columna "Marca" propia (el Form 083 no la tiene);
            # se anexa a Observaciones para no perder el dato.
            observacion = f"{observacion} (Marca: {marca})".strip()
        filas.append({
            "fecha": str(fecha).replace("-", "/"),
            "lote": act.get("Lote", ""),
            "responsable": act.get("ResponsableVacuna", ""),
            "establecimiento": act.get("Establecimiento", ""),
            "observacion": observacion,
        })
    return filas


def _armar_grupo_fijo(nombre_mostrar: str, base: int, filas: list) -> dict:
    """Construye siempre 'base' filas (rellenando en blanco las que falten) y agrega
    cualquier fila extra como 'Refuerzo N'. Marca 'esquema_completo' en la fila que cierra
    el esquema base, únicamente si esa fila tiene fecha."""
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
    """Vacunas fuera del esquema fijo (COVID, TETANOS solo, HEPATITIS A Y B COMBINADA,
    TIFOIDEA, etc.): tantas filas como dosis reales tenga, sin relleno ni tope."""
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
    orden fijo del Form 083 para la primera sección."""
    por_clave = {}
    dinamicas = []

    for vac in vacunas:
        clave = _normalizar(vac.get("NombreVacuna", ""))
        if clave in FIXED_KEYS:
            por_clave.setdefault(clave, []).append(vac)
        else:
            dinamicas.append(vac)

    grupos_fijos = []
    for clave, etiqueta, base in FIXED_SCHEMES:
        filas = []
        for vac in por_clave.get(clave, []):
            filas.extend(_extraer_dosis(vac))
        grupos_fijos.append(_armar_grupo_fijo(etiqueta, base, filas))

    grupos_dinamicos = [_armar_grupo_dinamico(vac) for vac in dinamicas]
    return grupos_fijos, grupos_dinamicos


def generar_pdf_vacunas(paciente: dict, vacunas: list) -> bytes:
    grupos_fijos, grupos_dinamicos = construir_seccion_b(vacunas)
    template = env.get_template("vacunas.html")
    html_str = template.render(paciente=paciente, grupos_fijos=grupos_fijos, grupos_dinamicos=grupos_dinamicos)
    return weasyprint.HTML(string=html_str).write_pdf()
