"""Llenado de PDFs con campos de formulario (AcroForm) conservando los campos editables.

Flujo: plantilla PDF (templates_pdf/<nombre>.pdf) + JSON {nombre_campo: valor}
-> mismo PDF con los campos rellenados y SIN aplanar (el usuario puede seguir editando).

Sin imports de FastAPI: esta capa solo recibe y devuelve bytes / dicts.
"""
import base64
import json
import math
import re
import unicodedata
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image
from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import ArrayObject, NameObject, TextStringObject

# True: los campos quedan con letra "Auto" para que, al editarlos, el texto se ajuste solo.
FUENTE_AUTO_AL_EDITAR = True

DIRECTORIO_PLANTILLAS = Path(__file__).resolve().parent.parent / "templates_pdf"

# Banderas (/Ff) del estándar PDF: el bit N vale 1 << (N - 1)
_FF_SOLO_LECTURA = 1 << 0
_FF_MULTILINEA = 1 << 12
_FF_RADIO = 1 << 15
_FF_BOTON = 1 << 16
_FF_COMBO = 1 << 17

_VALORES_VERDADEROS = {"true", "1", "si", "sí", "x", "yes", "on", "y", "verdadero", "marcado"}


# Anchos (milésimas de em) de Helvetica para ASCII 32..126: sirven para medir texto y repartirlo/ajustarlo.
_HELV = [
    278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278,
    556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015,
    667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722,
    667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333,
    556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333,
    500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584,
]
assert len(_HELV) == 95


def _ancho_texto(texto: str, fuente: float) -> float:
    """Ancho aproximado (pt) del texto en Helvetica; las letras con tilde miden como su base."""
    total = 0
    for ch in texto:
        o = ord(unicodedata.normalize("NFD", ch)[0])
        total += _HELV[o - 32] if 32 <= o <= 126 else 556
    return total * fuente / 1000


class PdfSinCamposError(ValueError):
    """El PDF no contiene campos de formulario (AcroForm)."""


class PlantillaNoExisteError(FileNotFoundError):
    """No existe templates_pdf/<nombre>.pdf."""


# ---------------------------------------------------------------------------
# Lectura de campos
# ---------------------------------------------------------------------------
def _heredado(obj, clave: str):
    """Lee un atributo del campo subiendo por /Parent (FT, Ff y V se heredan)."""
    actual = obj
    for _ in range(32):
        if actual is None:
            return None
        if clave in actual:
            return actual[clave]
        padre = actual.get("/Parent")
        actual = padre.get_object() if padre is not None else None
    return None


def _anotaciones(pagina) -> list:
    """Anotaciones de la página ya resueltas (/Annots puede ser una referencia indirecta)."""
    annots = pagina.get("/Annots")
    return list(annots.get_object()) if annots is not None else []


def _nombre_calificado(obj) -> str:
    """Nombre completo del campo: 'Grupo.Sub.campo' (une los /T de la jerarquía)."""
    partes: List[str] = []
    actual = obj
    for _ in range(32):
        if actual is None:
            break
        t = actual.get("/T")
        if t is not None:
            partes.append(str(t))
        padre = actual.get("/Parent")
        actual = padre.get_object() if padre is not None else None
    return ".".join(reversed(partes))


def _objeto_campo(widget):
    """El objeto 'lógico' del campo: el widget si tiene /T; si no (radio), su padre."""
    actual = widget
    for _ in range(32):
        if "/T" in actual:
            return actual
        padre = actual.get("/Parent")
        if padre is None:
            return widget
        actual = padre.get_object()
    return widget


def _tipo_campo(campo) -> str:
    ft = _heredado(campo, "/FT")
    ff = int(_heredado(campo, "/Ff") or 0)
    if ft == "/Tx":
        return "texto"
    if ft == "/Btn":
        if ff & _FF_BOTON:
            return "boton"
        if ff & _FF_RADIO:
            return "radio"
        return "casilla"
    if ft == "/Ch":
        return "combo" if ff & _FF_COMBO else "lista"
    if ft == "/Sig":
        return "firma"
    return "desconocido"


def _tamano_fuente(campo) -> float:
    """Tamaño de letra del /DA del campo ('/Helv 12 Tf'); 12 si es automático o no existe."""
    m = re.search(r"([\d.]+)\s+Tf", str(_heredado(campo, "/DA") or ""))
    tam = float(m.group(1)) if m else 0.0
    return tam if tam > 0 else 12.0


def _estados_widget(widget) -> List[str]:
    """Estados 'encendido' de una casilla/radio (claves de /AP /N distintas de /Off)."""
    ap = widget.get("/AP")
    if ap is None:
        return []
    normal = ap.get_object().get("/N")
    if normal is None:
        return []
    normal = normal.get_object()
    if not hasattr(normal, "keys"):
        return []
    return [str(k) for k in normal.keys() if str(k) != "/Off"]


def _opciones(campo) -> List[str]:
    opt = _heredado(campo, "/Opt")
    if opt is None:
        return []
    salida = []
    for item in opt.get_object():
        item = item.get_object()
        if isinstance(item, list):
            salida.append(str(item[0].get_object()))  # [valor_exportado, texto_visible]
        else:
            salida.append(str(item))
    return salida


def recolectar_campos(reader: PdfReader) -> Dict[str, Dict[str, Any]]:
    """Devuelve {nombre_calificado: info} recorriendo los widgets de todas las páginas."""
    campos: Dict[str, Dict[str, Any]] = {}
    for num_pagina, pagina in enumerate(reader.pages, start=1):
        for ref in _anotaciones(pagina):
            widget = ref.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue
            nombre = _nombre_calificado(widget)
            if not nombre:
                continue
            campo = _objeto_campo(widget)
            info = campos.get(nombre)
            if info is None:
                tipo = _tipo_campo(campo)
                valor = _heredado(campo, "/V")
                ff = int(_heredado(campo, "/Ff") or 0)
                info = {
                    "nombre": nombre,
                    "nombre_corto": nombre.rsplit(".", 1)[-1],
                    "tipo": tipo,
                    "valor_actual": str(valor.get_object()) if valor is not None else "",
                    "opciones": _opciones(campo) if tipo in ("combo", "lista") else [],
                    "multilinea": bool(tipo == "texto" and ff & _FF_MULTILINEA),
                    "solo_lectura": bool(ff & _FF_SOLO_LECTURA),
                    "pagina": num_pagina,
                    "ancho": round(abs(float(widget["/Rect"][2]) - float(widget["/Rect"][0])), 1),
                    "alto": round(abs(float(widget["/Rect"][3]) - float(widget["/Rect"][1])), 1),
                    "fuente": _tamano_fuente(campo),
                    "widgets": 0,
                }
                campos[nombre] = info
            info["widgets"] += 1
            if info["tipo"] in ("casilla", "radio"):
                for estado in _estados_widget(widget):
                    if estado not in info["opciones"]:
                        info["opciones"].append(estado)
    return campos


def _abrir(pdf_bytes: bytes) -> PdfReader:
    reader = PdfReader(BytesIO(pdf_bytes))
    if "/AcroForm" not in reader.trailer["/Root"]:
        raise PdfSinCamposError("El PDF no tiene campos de formulario (AcroForm).")
    return reader


def listar_campos(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """Lista los campos del PDF (para saber con qué nombre mandarlos en el JSON)."""
    campos = recolectar_campos(_abrir(pdf_bytes))
    if not campos:
        raise PdfSinCamposError("El PDF no tiene campos de formulario (AcroForm).")
    return list(campos.values())


def payload_ejemplo(campos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Esqueleto del JSON 'data' listo para copiar a Power Automate / Power Apps."""
    ejemplo: Dict[str, Any] = {}
    for c in campos:
        if c["tipo"] == "casilla":
            ejemplo[c["nombre"]] = False
        elif c["tipo"] == "radio":
            ejemplo[c["nombre"]] = c["opciones"][0].lstrip("/") if c["opciones"] else ""
        elif c["tipo"] in ("combo", "lista"):
            ejemplo[c["nombre"]] = c["opciones"][0] if c["opciones"] else ""
        elif c["tipo"] == "firma":
            continue  # las firmas digitales no se rellenan
        else:  # texto y boton (imagen en base64)
            ejemplo[c["nombre"]] = ""
    return ejemplo


# ---------------------------------------------------------------------------
# Plantillas en disco
# ---------------------------------------------------------------------------
def _nombre_plantilla(template_name: str) -> str:
    nombre = re.sub(r"\.pdf$", "", (template_name or "").strip(), flags=re.IGNORECASE)
    if not re.fullmatch(r"[\w\- ]+", nombre):  # evita rutas tipo ../../algo
        raise PlantillaNoExisteError(f"La plantilla '{template_name}.pdf' no existe.")
    return nombre


def cargar_plantilla(template_name: str) -> bytes:
    nombre = _nombre_plantilla(template_name)
    ruta = DIRECTORIO_PLANTILLAS / f"{nombre}.pdf"
    if not ruta.is_file():
        raise PlantillaNoExisteError(f"La plantilla '{nombre}.pdf' no existe.")
    return ruta.read_bytes()


def cargar_alias(template_name: str) -> Dict[str, Any]:
    """Alias opcionales (templates_pdf/<nombre>.alias.json): nombres amigables del JSON ->
    nombres reales de los campos del PDF. {} si la plantilla no tiene archivo de alias."""
    ruta = DIRECTORIO_PLANTILLAS / f"{_nombre_plantilla(template_name)}.alias.json"
    if not ruta.is_file():
        return {}
    return json.loads(ruta.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Llenado
# ---------------------------------------------------------------------------
def _a_texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "Sí" if valor else ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)


def _es_verdadero(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, (int, float)):
        return valor != 0
    return str(valor or "").strip().lower() in _VALORES_VERDADEROS


def _resolver_nombres(clave: str, campos: Dict[str, Dict[str, Any]]) -> Tuple[Optional[str], str]:
    """Clave del JSON -> nombre calificado del campo. Acepta el nombre completo o el corto
    (último segmento) siempre que no sea ambiguo."""
    if clave in campos:
        return clave, "ok"
    coincidencias = [n for n, i in campos.items() if i["nombre_corto"] == clave]
    if len(coincidencias) == 1:
        return coincidencias[0], "ok"
    if len(coincidencias) > 1:
        return None, "ambiguo"
    return None, "no_encontrado"


def _envolver(texto: str, infos: List[Dict[str, Any]], tam: float) -> Tuple[List[str], bool]:
    """Reparte las palabras en las líneas (campos) con letra de `tam` pt. Devuelve (líneas, sobra)."""
    lineas: List[str] = []
    actual = ""
    for palabra in texto.split():
        info = infos[min(len(lineas), len(infos) - 1)]
        limite = (info["ancho"] - 4) * 0.97
        candidato = f"{actual} {palabra}".strip()
        if not actual or _ancho_texto(candidato, tam) <= limite:
            actual = candidato
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    sobra = len(lineas) > len(infos)
    if sobra:  # no cabe: lo que sobra queda en la última línea
        lineas = lineas[:len(infos) - 1] + [" ".join(lineas[len(infos) - 1:])]
    return lineas + [""] * (len(infos) - len(lineas)), sobra


def _dividir_texto(texto: str, infos: List[Dict[str, Any]]) -> Tuple[List[str], float, bool]:
    """Reparte un texto largo entre varios campos de una línea usando UN MISMO tamaño de letra
    para todas: parte del tamaño del formulario y lo baja de 0.5 en 0.5 pt (mínimo 6) hasta que
    todo quepa. Devuelve (líneas, tamaño, desbordó)."""
    texto = " ".join(texto.split())
    con_tilde = any(c.isupper() and len(unicodedata.normalize("NFD", c)) > 1 for c in texto)
    por_alto = min((i["alto"] - 1.5) / (0.95 if con_tilde else 0.8) for i in infos)
    tam = math.floor(min(min(i["fuente"] for i in infos), por_alto) * 2) / 2
    while True:
        lineas, sobra = _envolver(texto, infos, tam)
        if not sobra or tam <= 6.0:
            return lineas, tam, sobra
        tam = max(6.0, tam - 0.5)


def _expandir_alias(data: Dict[str, Any], alias: Dict[str, Any], campos: Dict[str, Dict[str, Any]]):
    """Convierte las claves del JSON en tuplas (clave_original, campo_real, valor).

    Entrada del alias: "campo" | ["campo1", "campo2"] (el mismo valor a varios campos) |
    {"campo": ..., "dividir": true (reparte texto largo en varias líneas),
                    "valores": {"SI": "0", "NO": "1"} (traduce el valor, p. ej. para radios)}"""
    elementos: List[Tuple[str, str, Any]] = []
    desbordados: List[str] = []
    tamanos: Dict[str, float] = {}  # tamaño de letra común a las líneas de un grupo 'dividir'
    for clave, valor in (data or {}).items():
        if str(clave).startswith("_"):  # claves "_xxx": datos para el flujo (p. ej. _codigo), no son del PDF
            continue
        spec = alias.get(clave)
        if spec is None:
            elementos.append((clave, clave, valor))
            continue
        if not isinstance(spec, dict):
            spec = {"campo": spec}
        destinos = spec["campo"] if isinstance(spec["campo"], list) else [spec["campo"]]
        valores = {str(k).strip().upper(): v for k, v in (spec.get("valores") or {}).items()}
        if valores and not _es_imagen(valor):
            llave = str(valor).upper() if isinstance(valor, bool) else _a_texto(valor).strip().upper()
            valor = valores.get(llave, valor)
        if spec.get("dividir") and len(destinos) > 1 and not _es_imagen(valor) and all(d in campos for d in destinos):
            infos = [campos[d] for d in destinos]
            lineas, tam, desbordo = _dividir_texto(_a_texto(valor), infos)
            if desbordo:
                desbordados.append(clave)
            if any(abs(i["fuente"] - tam) > 1e-6 for i in infos):
                tamanos.update({d: tam for d in destinos})
            elementos.extend((clave, d, linea) for d, linea in zip(destinos, lineas))
            continue
        elementos.extend((clave, d, valor) for d in destinos)
    return elementos, desbordados, tamanos


def _es_imagen(valor: Any) -> bool:
    return isinstance(valor, str) and (valor.startswith("data:image") or "base64," in valor)


def _decodificar_imagen(valor: str) -> Image.Image:
    b64 = valor.split("base64,")[-1]
    img = Image.open(BytesIO(base64.b64decode(b64)))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        fondo = Image.new("RGB", img.size, (255, 255, 255))
        fondo.paste(img, mask=img.split()[-1])
        return fondo
    return img.convert("RGB")


def _insertar_imagen(writer: PdfWriter, nombre: str, valor: str) -> int:
    """Estampa la imagen dentro del recuadro (widget) del campo, centrada y sin deformar.

    La imagen pasa a ser contenido fijo de la página y el recuadro del campo se quita:
    así ningún visor puede taparla con la apariencia (fondo) del campo."""
    img = _decodificar_imagen(valor)
    buf = BytesIO()
    img.save(buf, format="PDF", resolution=72.0)  # 1 px = 1 pt
    ancho_img, alto_img = img.size
    colocadas = 0
    for pagina in writer.pages:
        restantes = ArrayObject()
        for ref in _anotaciones(pagina):
            widget = ref.get_object()
            if widget.get("/Subtype") != "/Widget" or _nombre_calificado(widget) != nombre:
                restantes.append(ref)
                continue
            x0, y0, x1, y1 = [float(v) for v in widget["/Rect"]]
            x0, x1 = min(x0, x1), max(x0, x1)
            y0, y1 = min(y0, y1), max(y0, y1)
            escala = min((x1 - x0) / ancho_img, (y1 - y0) / alto_img)
            tx = x0 + ((x1 - x0) - ancho_img * escala) / 2
            ty = y0 + ((y1 - y0) - alto_img * escala) / 2
            buf.seek(0)
            overlay = PdfReader(buf).pages[0]
            pagina.merge_transformed_page(overlay, Transformation().scale(escala, escala).translate(tx, ty))
            colocadas += 1
        if len(restantes) != len(_anotaciones(pagina)):
            pagina[NameObject("/Annots")] = restantes
    if colocadas:  # saca de /Fields el campo que se quedó sin recuadro
        acro = writer._root_object["/AcroForm"]
        acro[NameObject("/Fields")] = ArrayObject(
            f for f in acro.get("/Fields", [])
            if not (f.get_object().get("/T") == nombre and "/Kids" not in f.get_object())
        )
    return colocadas


def _ajustar_fuentes(writer: PdfWriter, ajustes: Dict[str, float]) -> None:
    """Baja el tamaño de letra (/DA) de los campos de una línea cuyo texto no cabe."""
    for pagina in writer.pages:
        for ref in _anotaciones(pagina):
            widget = ref.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue
            nombre = _nombre_calificado(widget)
            if nombre in ajustes:
                da = str(_heredado(widget, "/DA") or "/Helv 12 Tf 0 g")
                widget[NameObject("/DA")] = TextStringObject(
                    re.sub(r"[\d.]+(\s+Tf)", lambda m: f"{ajustes[nombre]:g}{m.group(1)}", da)
                )


def _fuente_automatica(writer: PdfWriter, campos: Dict[str, Dict[str, Any]]) -> None:
    """Pone la letra en 'Auto' (0 pt) en los campos de texto de una línea. La apariencia ya
    generada se conserva; al EDITAR el campo (incluso en Reader gratis) el texto se ajusta solo."""
    for pagina in writer.pages:
        for ref in _anotaciones(pagina):
            widget = ref.get_object()
            if widget.get("/Subtype") != "/Widget":
                continue
            info = campos.get(_nombre_calificado(widget))
            if not info or info["tipo"] != "texto" or info["multilinea"]:
                continue
            da = str(_heredado(widget, "/DA") or "/Helv 0 Tf 0 g")
            widget[NameObject("/DA")] = TextStringObject(re.sub(r"[\d.]+(\s+Tf)", lambda m: "0" + m.group(1), da))


def llenar_pdf(pdf_bytes: bytes, data: Dict[str, Any], alias: Optional[Dict[str, Any]] = None) -> Tuple[bytes, Dict[str, List[str]]]:
    """Rellena los campos del PDF con `data` ({nombre_campo: valor}) y devuelve
    (pdf_bytes, reporte). Los campos NO se aplanan: siguen siendo editables.

    reporte = {"aplicados", "no_encontrados", "ambiguos", "invalidos", "desbordados"} (listas de claves)
    """
    reader = _abrir(pdf_bytes)
    campos = recolectar_campos(reader)
    if not campos:
        raise PdfSinCamposError("El PDF no tiene campos de formulario (AcroForm).")

    reporte: Dict[str, List[str]] = {"aplicados": [], "no_encontrados": [], "ambiguos": [], "invalidos": [], "desbordados": []}
    valores: Dict[str, Any] = {}
    imagenes: Dict[str, str] = {}

    elementos, reporte["desbordados"], tamanos = _expandir_alias(data, alias or {}, campos)

    def marcar(lista: str, clave: str) -> None:
        if clave not in reporte[lista]:
            reporte[lista].append(clave)

    for clave, destino, valor in elementos:
        nombre, estado = _resolver_nombres(destino, campos)
        if nombre is None:
            marcar("ambiguos" if estado == "ambiguo" else "no_encontrados", clave)
            continue
        info = campos[nombre]
        tipo = info["tipo"]

        if tipo == "boton" or _es_imagen(valor):
            if valor and _es_imagen(valor):
                imagenes[nombre] = valor
                marcar("aplicados", clave)
            elif valor:
                marcar("invalidos", clave)  # el campo es imagen y el valor no lo es
            continue
        if tipo == "firma":
            marcar("invalidos", clave)
            continue
        if tipo == "casilla":
            on = info["opciones"][0] if info["opciones"] else "/Yes"
            if isinstance(valor, str) and valor.lstrip("/") in [o.lstrip("/") for o in info["opciones"]]:
                valores[nombre] = "/" + valor.lstrip("/")
            else:
                valores[nombre] = on if _es_verdadero(valor) else "/Off"
        elif tipo == "radio":
            elegido = "/" + _a_texto(valor).lstrip("/")
            if elegido in info["opciones"]:
                valores[nombre] = elegido
            elif _a_texto(valor) == "":
                valores[nombre] = "/Off"
            else:
                marcar("invalidos", clave)
                continue
        else:  # texto, combo, lista
            valores[nombre] = _a_texto(valor)
        marcar("aplicados", clave)

    writer = PdfWriter(clone_from=reader)

    ajustes: Dict[str, float] = {}
    for nombre, texto in valores.items():
        info = campos[nombre]
        if nombre in tamanos:
            ajustes[nombre] = tamanos[nombre]
            continue
        if info["tipo"] == "texto" and not info["multilinea"] and isinstance(texto, str) and texto:
            # la letra debe caber en alto (si hay mayúsculas con tilde, las tildes necesitan más) y en ancho
            con_tilde = any(c.isupper() and len(unicodedata.normalize("NFD", c)) > 1 for c in texto)
            tam = min(info["fuente"], (info["alto"] - 1.5) / (0.95 if con_tilde else 0.8))
            ancho = _ancho_texto(texto, tam)
            if ancho > info["ancho"] - 4:
                tam = tam * (info["ancho"] - 4) / ancho
            tam = max(6.0, math.floor(tam * 2) / 2)
            if tam < info["fuente"]:
                ajustes[nombre] = tam
    if ajustes:
        _ajustar_fuentes(writer, ajustes)

    if valores:
        for pagina in writer.pages:
            writer.update_page_form_field_values(pagina, valores, auto_regenerate=False)

    for nombre, b64 in imagenes.items():
        _insertar_imagen(writer, nombre, b64)

    if FUENTE_AUTO_AL_EDITAR:
        _fuente_automatica(writer, campos)

    acro = writer._root_object["/AcroForm"]
    if "/XFA" in acro:  # Adobe ignora AcroForm si queda el XFA (LiveCycle): se elimina
        del acro["/XFA"]

    salida = BytesIO()
    writer.write(salida)
    return salida.getvalue(), reporte
