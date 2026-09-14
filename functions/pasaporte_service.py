from jinja2 import Environment, FileSystemLoader
import weasyprint

env = Environment(loader=FileSystemLoader("templates_html"))

# Cuántos registros entran por página en cada sección dinámica (según el layout
# original en Word). Si el diseño final cambia el espacio disponible por página,
# ajustar solo estos valores.
COMPETENCIAS_POR_PAGINA = 3
RECONOCIMIENTOS_POR_PAGINA = 3
BUENAS_PRACTICAS_POR_PAGINA = 3


def _en_grupos(items: list, tamano: int) -> list:
    """Divide una lista plana en páginas de 'tamano' elementos, rellenando la
    última página con registros vacíos para que la cuadrícula quede completa."""
    grupos = []
    for i in range(0, len(items), tamano):
        grupo = items[i:i + tamano]
        while len(grupo) < tamano:
            grupo.append({})
        grupos.append(grupo)
    if not grupos:
        grupos = [[{} for _ in range(tamano)]]
    return grupos


def _data_uri(valor: str) -> str:
    """Si 'valor' ya viene con el prefijo data:image lo deja igual; si es un
    base64 crudo le agrega el prefijo para que <img> lo pueda renderizar."""
    if not valor:
        return ""
    if valor.startswith("data:image"):
        return valor
    return f"data:image/jpeg;base64,{valor}"


def generar_pdf_pasaporte(payload: dict) -> bytes:
    datos_personales = dict(payload.get("datos_personales") or {})
    if datos_personales.get("foto_base64"):
        datos_personales["foto_base64"] = _data_uri(datos_personales["foto_base64"])

    info_emergencia = payload.get("info_emergencia") or {}

    competencias = [dict(c) for c in (payload.get("competencias") or [])]
    for c in competencias:
        if c.get("firma_sello_base64"):
            c["firma_sello_base64"] = _data_uri(c["firma_sello_base64"])

    reconocimientos = [dict(r) for r in (payload.get("reconocimientos") or [])]
    for r in reconocimientos:
        if r.get("firma_base64"):
            r["firma_base64"] = _data_uri(r["firma_base64"])

    buenas_practicas = [dict(b) for b in (payload.get("buenas_practicas") or [])]
    for b in buenas_practicas:
        if b.get("firma_base64"):
            b["firma_base64"] = _data_uri(b["firma_base64"])

    contexto = {
        "datos_personales": datos_personales,
        "info_emergencia": info_emergencia,
        "paginas_competencias": _en_grupos(competencias, COMPETENCIAS_POR_PAGINA),
        "paginas_reconocimientos": _en_grupos(reconocimientos, RECONOCIMIENTOS_POR_PAGINA),
        "paginas_buenas_practicas": _en_grupos(buenas_practicas, BUENAS_PRACTICAS_POR_PAGINA),
    }

    template = env.get_template("pasaporte.html")
    html_str = template.render(**contexto)
    return weasyprint.HTML(string=html_str, base_url=".").write_pdf()
