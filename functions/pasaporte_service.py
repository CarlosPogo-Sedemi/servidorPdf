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


def _tamano_dinamico(texto, base: float = 7.0, minimo: float = 5.0, umbral: int = 30, tope: int = 150) -> float:
    """WeasyPrint no puede "autoajustar" el tamaño de letra a como venga el
    texto (no hay JS ni medición real de ancho en tiempo de render), así que
    ese cálculo se hace acá: hasta `umbral` caracteres se usa el tamaño
    normal (`base`, el mismo que el resto de campos); de ahí en adelante se
    reduce linealmente hasta `minimo` conforme el texto se acerca a `tope`
    caracteres (y se queda en `minimo` si lo supera), en vez de quedar fijo
    en un tamaño chico aunque el texto sea corto."""
    largo = len(str(texto or ""))
    if largo <= umbral:
        return base
    largo = min(largo, tope)
    proporcion = (largo - umbral) / (tope - umbral)
    return round(base - proporcion * (base - minimo), 2)


def _data_uri(valor) -> str:
    """Power Apps ya manda `FotoPerfil` sin comillas envolventes (le hacen
    Substitute del carácter " antes de meterlo al JSON), así que normalmente
    ya viene como 'data:image/jpeg;base64,...'. Este helper solo cubre el
    caso de que llegue el base64 crudo, sin ese prefijo.

    El `JSON()` de Power Apps escapa "/" como "\\/", y el Substitute que le
    hacen del lado de Power Apps solo quita comillas, no esas barras
    invertidas — así que "image/png" llega como "image\\/png" (un mediatype
    inválido: rompe el patrón data:<mediatype>;base64,<datos> y el PDF
    termina con el recuadro de foto en blanco). Revertir "\\/" -> "/" es
    seguro siempre: una data URI válida nunca trae barras invertidas."""
    if not valor:
        return ""
    valor = valor.replace("\\/", "/")
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
    # Caja angosta (51.39mm) que además comparte espacio con la línea de
    # abajo: a 7pt (el tamaño normal del resto de campos) una razón social
    # larga se corta. Se achica sólo cuando hace falta, no siempre.
    datos_personales["compania_size"] = _tamano_dinamico(
        datos_personales["compania"], base=7.0, minimo=5.0, umbral=27, tope=59
    )

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
    competencias = []
    for c in (data.get("Competencias") or []):
        nombre_curso = c.get("NombreCertificado") or ""
        nombre_instructor = c.get("AutoraEmisora") or ""
        competencias.append({
            "tipo": "",
            "nombre_curso": nombre_curso,
            "nombre_curso_size": _tamano_dinamico(nombre_curso, base=7.0, minimo=4.8, umbral=30, tope=110),
            "nombre_instructor": nombre_instructor,
            "nombre_instructor_size": _tamano_dinamico(nombre_instructor, base=7.0, minimo=4.8, umbral=30, tope=110),
            "expedicion": _fecha(c.get("FechaEmision")),
            "vencimiento": _fecha(c.get("FechaVencimiento")),
        })

    # EmpleadoMes y BuenasPracticas comparten la misma forma (Mes/Actividad)
    # en el JSON; solo cambia a qué etiqueta del PDF va "Actividad" y no
    # existe campo de Firma en ninguna de las dos (queda en blanco). Ambas
    # cajas de texto son de 38.65mm (más angostas que la tabla de
    # Competencias) y hoy recortan en silencio con white-space:nowrap si el
    # texto es largo, así que llevan el mismo tamaño dinámico calculado acá.
    reconocimientos = []
    for r in (data.get("EmpleadoMes") or []):
        actividad = r.get("Actividad") or ""
        reconocimientos.append({
            "mes": r.get("Mes") or "",
            "actividad": actividad,
            "actividad_size": _tamano_dinamico(actividad, base=7.0, minimo=5.0, umbral=20, tope=45),
        })

    buenas_practicas = []
    for b in (data.get("BuenasPracticas") or []):
        accion = b.get("Actividad") or ""
        buenas_practicas.append({
            "accion_destacada": accion,
            "accion_destacada_size": _tamano_dinamico(accion, base=7.0, minimo=5.0, umbral=20, tope=45),
            "mes": b.get("Mes") or "",
        })

    # Historial Médico: tabla de Vacunas. F=Fiebre Amarilla, HA/HB=Hepatitis
    # A/B, HAB=Hepatitis A y B combinada, TF=Tifoidea, DT=Difteria y
    # Tétanos, T=Tétanos, C=Covid, INF=Influenza, SR=Sarampión-Rubéola.
    # F e INF son de 1 sola dosis (INF además estacional: Power Apps ya
    # manda ahí la dosis del año en curso), SR es de 2, el resto hasta 5.
    va = data.get("VA") or {}
    vacunas = [
        {"nombre": "Fiebre Amarilla", "dosis": [_fecha(va.get("F1")), "", "", "", ""]},
        {"nombre": "Hepatitis A", "dosis": [_fecha(va.get(f"HA{i}")) for i in range(1, 6)]},
        {"nombre": "Hepatitis B", "dosis": [_fecha(va.get(f"HB{i}")) for i in range(1, 6)]},
        {"nombre": "Hepatitis A y B (combinada)", "dosis": [_fecha(va.get(f"HAB{i}")) for i in range(1, 6)]},
        {"nombre": "Tifoidea", "dosis": [_fecha(va.get(f"TF{i}")) for i in range(1, 6)]},
        {"nombre": "Difteria y Tétanos", "dosis": [_fecha(va.get(f"DT{i}")) for i in range(1, 6)]},
        {"nombre": "Tétanos", "dosis": [_fecha(va.get(f"T{i}")) for i in range(1, 6)]},
        {"nombre": "Covid - 19", "dosis": [_fecha(va.get(f"C{i}")) for i in range(1, 6)]},
        {"nombre": "Influenza", "dosis": [_fecha(va.get("INF1")), "", "", "", ""]},
        {"nombre": "Sarampión - Rubéola", "dosis": [_fecha(va.get("SR1")), _fecha(va.get("SR2")), "", "", ""]},
    ]

    nombre_medico = dt.get("NombreMedico") or ""
    cedula_medico = dt.get("CedulaMedico") or ""
    if nombre_medico and cedula_medico:
        medico_codigo = f"{nombre_medico} - MSP {cedula_medico}"
    else:
        medico_codigo = nombre_medico or cedula_medico

    lugar = dt.get("Lugar") or ""
    historial_medico = {
        "vacunas": vacunas,
        "examen_fecha": _fecha(dt.get("FechaExa")),
        "examen_lugar": lugar,
        "examen_medico": medico_codigo,
        "grupo_sanguineo": dt.get("Sangre") or "",
        "alergias": dt.get("Alergias") or "",
        "aptitud": dt.get("Aptitud") or "",
        "aptitud_fecha_caducidad": _fecha(dt.get("FechaExaCad")),
        "restricciones": dt.get("Restricciones") or "",
    }

    contexto = {
        "datos_personales": datos_personales,
        "info_emergencia": info_emergencia,
        "historial_medico": historial_medico,
        "paginas_competencias": _en_grupos(competencias),
        "paginas_reconocimientos": _en_grupos(reconocimientos),
        "paginas_buenas_practicas": _en_grupos(buenas_practicas),
    }

    template = env.get_template("pasaporte.html")
    html_str = template.render(**contexto)
    return weasyprint.HTML(string=html_str, base_url=".").write_pdf()
