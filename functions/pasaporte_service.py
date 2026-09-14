from jinja2 import Environment, FileSystemLoader
import weasyprint

env = Environment(loader=FileSystemLoader("templates_html"))

REGISTROS_POR_PAGINA = 3


def _en_grupos(items: list) -> list:
    """Reparte una lista en páginas de hasta REGISTROS_POR_PAGINA elementos,
    SIN rellenar con vacíos: 4 registros -> página 1 con 3, página 2 con 1
    solo (no 3). Si la lista viene vacía se muestra una única tarjeta en
    blanco a modo de plantilla, en vez de no mostrar nada — así se decidió
    para que la sección "empiece en 1" visualmente aunque no haya datos."""
    if not items:
        return [[{}]]
    return [items[i:i + REGISTROS_POR_PAGINA] for i in range(0, len(items), REGISTROS_POR_PAGINA)]


def _fecha(valor) -> str:
    """Power Apps manda las fechas como texto ISO (a veces con hora,
    p.ej. '2024-01-15T05:00:00.000Z'). Se toman los primeros 10 caracteres
    (YYYY-MM-DD) y se reordena a DD/MM/YYYY para que se vea igual que el
    resto del documento."""
    if not valor:
        return ""
    texto = str(valor)[:10]
    partes = texto.split("-")
    if len(partes) == 3 and all(partes):
        anio, mes, dia = partes
        return f"{dia}/{mes}/{anio}"
    return texto


def _data_uri(valor) -> str:
    """Power Apps ya manda `FotoPerfil` sin comillas envolventes (le hacen
    Substitute del carácter " antes de meterlo al JSON), así que normalmente
    ya viene como 'data:image/jpeg;base64,...'. Este helper solo cubre el
    caso de que llegue el base64 crudo, sin ese prefijo."""
    if not valor:
        return ""
    if valor.startswith("data:image"):
        return valor
    return f"data:image/jpeg;base64,{valor}"


def generar_pdf_pasaporte(payload: dict) -> bytes:
    data = payload.get("data") or {}
    dt = data.get("DT") or {}

    datos_personales = {
        "compania": dt.get("Compania") or "",
        "nombres_apellidos": dt.get("NombreCompleto") or "",
        "identificacion": dt.get("Cedula") or "",
        "nacionalidad": dt.get("Nacionalidad") or "",
        "fecha_nacimiento": _fecha(dt.get("FechaNacimiento")),
        "direccion": dt.get("DireccionDomi") or "",
        "numero_celular": dt.get("NumeroCelular") or "",
        "codigo_colaborador": dt.get("Ekon") or "",
        "cargo": dt.get("Cargo") or "",
        "area": dt.get("Area") or "",
        "tipo_licencia": dt.get("Licencia") or "",
        "fecha_caducidad_licencia": _fecha(dt.get("FechaCadLic")),
    }
    if dt.get("FotoPerfil"):
        datos_personales["foto_base64"] = _data_uri(dt["FotoPerfil"])

    info_emergencia = {
        "tipo_sangre": dt.get("Sangre") or "",
        "enfermedades": dt.get("Enfermedades") or "",
        "alergias": dt.get("Alergias") or "",
        "contacto1_nombre": dt.get("Contacto") or "",
        "contacto1_parentesco": dt.get("Parentesco") or "",
        "contacto1_numero": dt.get("NumeroContacto") or "",
        "contacto2_nombre": dt.get("Contacto2") or "",
        "contacto2_parentesco": dt.get("Parentesco2") or "",
        "contacto2_numero": dt.get("NumeroContacto2") or "",
    }

    # Power Apps envía aquí su colección de Certificados (colCertificado),
    # no cursos de inducción/capacitación: NombreCertificado -> nombre del
    # curso, AutoraEmisora -> nombre del instructor. No hay dato de
    # Inducción/Capacitación, así que 'tipo' queda vacío (ningún checkbox
    # marcado).
    competencias = [
        {
            "tipo": "",
            "nombre_curso": c.get("NombreCertificado") or "",
            "nombre_instructor": c.get("AutoraEmisora") or "",
            "expedicion": _fecha(c.get("FechaEmision")),
            "vencimiento": _fecha(c.get("FechaVencimiento")),
        }
        for c in (data.get("Competencias") or [])
    ]

    # EmpleadoMes y BuenasPracticas comparten la misma forma (Mes/Actividad)
    # en el JSON; solo cambia a qué etiqueta del PDF va "Actividad" y no
    # existe campo de Firma en ninguna de las dos (queda en blanco).
    reconocimientos = [
        {"mes": r.get("Mes") or "", "actividad": r.get("Actividad") or ""}
        for r in (data.get("EmpleadoMes") or [])
    ]

    buenas_practicas = [
        {"accion_destacada": b.get("Actividad") or "", "mes": b.get("Mes") or ""}
        for b in (data.get("BuenasPracticas") or [])
    ]

    contexto = {
        "datos_personales": datos_personales,
        "info_emergencia": info_emergencia,
        "paginas_competencias": _en_grupos(competencias),
        "paginas_reconocimientos": _en_grupos(reconocimientos),
        "paginas_buenas_practicas": _en_grupos(buenas_practicas),
    }

    template = env.get_template("pasaporte.html")
    html_str = template.render(**contexto)
    return weasyprint.HTML(string=html_str, base_url=".").write_pdf()
