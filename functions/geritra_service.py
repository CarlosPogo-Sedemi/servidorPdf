"""Lógica de negocio de la Matriz GERITRA: arma el modelo desde los JSON de la app.

Sin imports de FastAPI (convención de functions/). El pintado vive en geritra_excel.py.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from typing import Any, Optional

from functions import geritra_config as cfg


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def normalizar(texto: Any) -> str:
    t = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", t.lower().replace(";", ",")).strip(" .")


def sin_numeracion(texto: str) -> str:
    return re.sub(r"^\s*\d+\s*\.\s*", "", texto or "").strip()


def legible(texto: Any) -> str:
    """Power Apps (región ES) guarda ',' como ';' dentro de los textos."""
    return re.sub(r"\s*;\s*", ", ", " ".join(str(texto or "").split())).strip()


def a_lista(valor: Any) -> list:
    """Acepta lista, texto JSON (incluso doblemente serializado) o vacío."""
    for _ in range(3):
        if isinstance(valor, str):
            valor = valor.strip()
            if not valor:
                return []
            try:
                valor = json.loads(valor)
            except json.JSONDecodeError:
                return []
        else:
            break
    if isinstance(valor, dict):
        return [valor]
    return valor if isinstance(valor, list) else []


def a_entero(valor: Any) -> Optional[int]:
    try:
        return int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return None


def a_fecha(valor: Any) -> Optional[date]:
    texto = str(valor or "").strip()[:10]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def texto_actividad(valor: Any) -> str:
    if isinstance(valor, dict):
        valor = valor.get("Descripcion") or valor.get("Value") or ""
    return " ".join(str(valor or "").split())


def nivel_por_valoracion(v: Optional[float]) -> str:
    if not v or v <= 0:
        return ""
    for limite, nombre in cfg.RANGOS_NIVEL:
        if v < limite:
            return nombre
    return "Intolerable"


def descripcion_item(item: Any) -> str:
    """Texto de un ítem de UTENSILIOS / MATERIALES / EQUIPOS (estructura variable)."""
    if isinstance(item, str):
        return item.strip()
    if not isinstance(item, dict):
        return ""
    for k in ("Descripcion", "DescripcionMaterial", "DescripcionEquipo", "Equipo", "Nombre", "Value"):
        if item.get(k):
            return str(item[k]).strip()
    for k, v in item.items():
        if isinstance(v, str) and v.strip() and "id" not in k.lower() and "cantidad" not in k.lower():
            return v.strip()
    return ""


# ----------------------------------------------------------------------------
# Catálogo de jerarquía de controles
# ----------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _jerarquia() -> dict:
    with open(cfg.ASSETS_DIR / "jerarquia_medidas.json", encoding="utf-8") as fh:
        return json.load(fh)


def jerarquia_de(medida: str, factor: str = "") -> str:
    """Primero por factor + medida (una misma medida puede clasificarse distinto según el factor);
    si no existe, solo por el texto de la medida; si tampoco, el valor por defecto."""
    cat = _jerarquia()
    m = normalizar(sin_numeracion(medida))
    return (cat.get("por_factor", {}).get(f"{normalizar(factor)}|{m}")
            or cat.get("medidas", {}).get(m)
            or cfg.JERARQUIA_DEFECTO)


# ----------------------------------------------------------------------------
# Modelo
# ----------------------------------------------------------------------------
@dataclass
class Persona:
    nombre: str
    cargo: str
    tipo: str
    porcentaje: str
    ayuda: str
    observacion: str
    categoria: str
    actividades: set[str]           # descripciones normalizadas
    actividades_txt: list[str]      # descripciones legibles
    eventos: list[str]

    @property
    def con_discapacidad(self) -> bool:
        return normalizar(self.tipo) not in cfg.SIN_DISCAPACIDAD


@dataclass
class Evaluacion:
    cantidad: Optional[int]
    i_personas: Optional[int]
    i_procedimientos: Optional[int]
    i_capacitaciones: Optional[int]
    i_exposicion: Optional[int]
    i_consecuencias: Optional[int]

    @property
    def probabilidad(self) -> Optional[int]:
        idx = [self.i_personas, self.i_procedimientos, self.i_capacitaciones, self.i_exposicion]
        return sum(idx) if all(i for i in idx) else None

    @property
    def valoracion(self) -> Optional[int]:
        p = self.probabilidad
        return p * self.i_consecuencias if p and self.i_consecuencias else None

    @property
    def nivel(self) -> str:
        """Guía GERITRA, Paso 19: nivel según la VALORACIÓN (P x C)."""
        return nivel_por_valoracion(self.valoracion)


@dataclass
class Fila:
    actividad: str
    peligro: str
    factor: str
    clasificacion: str
    inicial: Evaluacion
    residual: Optional[Evaluacion]
    jerarquia: dict[str, list[str]]
    efectos: str = ""
    vigilancia: str = ""
    fecha_control: Optional[date] = None
    mejora: str = ""
    orden: tuple = ()
    # discapacidad (opción A: solo quienes hacen esta actividad)
    disc_personas: list[Persona] = field(default_factory=list)
    total_personas_actividad: int = 0
    # columna 9: lo seleccionado en el combo de máquinas/equipos de la app (por registro)
    maquinas: list[tuple[str, str]] = field(default_factory=list)
    maquinas_informado: bool = False


@dataclass
class MatrizGeritra:
    codigo_ast: str
    razon_social: str
    ruc: str
    direccion: str
    telefono: str
    responsable_evaluacion: str
    responsable_sso: str
    fecha_evaluacion: Optional[date]
    proceso: str
    puesto: str
    numero_trabajadores: Optional[int]
    personas_entrevistadas: int
    no_rutinarias: list[str]
    maquinas: dict[str, list[str]]
    filas: list[Fila]
    personas_discapacidad: list[Persona]
    maquinas_por_actividad: dict[str, list[tuple[str, str]]] = field(default_factory=dict)


# ----------------------------------------------------------------------------
# Construcción
# ----------------------------------------------------------------------------
def _personas(entrevistas: list, comunes_txt: list[str]) -> list[Persona]:
    comunes_n = {normalizar(c) for c in comunes_txt}
    salida = []
    for e in entrevistas:
        if not isinstance(e, dict):
            continue
        acts = [texto_actividad(a) for a in a_lista(e.get("ActividadesPrincipalesJSON"))]
        acts = [a for a in acts if a]
        eventos = [texto_actividad(ev) for ev in a_lista(e.get("EventosJSON"))]
        salida.append(Persona(
            nombre=str(e.get("Nombre") or "").strip(),
            cargo=str(e.get("Cargo") or "").strip(),
            tipo=str(e.get("TipoDiscapacidad") or "").strip(),
            porcentaje=str(e.get("PorcentajeDiscapacidad") or "").strip(),
            ayuda=str(e.get("AyudaTecnica") or "").strip(),
            observacion=str(e.get("ObservacionDiscapacidad") or "").strip(),
            categoria=str(e.get("CategoriaVulnerabilidad") or "").strip(),
            actividades={normalizar(a) for a in acts} | comunes_n,
            actividades_txt=list(dict.fromkeys(comunes_txt + acts)),
            eventos=[x for x in eventos if x],
        ))
    return salida


def _equipos_tecnologicos(valor: Any) -> list:
    """EQUIPOS_TECNOLOGICOS viene como {Categorias: [{Categoria, Equipos: [{Equipo, ...}]}], TotalGeneral}
    o como lista simple. Se aplana a textos 'Categoría - Equipo'."""
    salida = []
    for item in a_lista(valor):
        if isinstance(item, dict) and "Categorias" in item:
            for cat in a_lista(item.get("Categorias")):
                if not isinstance(cat, dict):
                    continue
                nombre_cat = str(cat.get("Categoria") or "").strip()
                for eq in a_lista(cat.get("Equipos")):
                    txt = descripcion_item(eq)
                    if txt:
                        salida.append(f"{nombre_cat} - {txt}" if nombre_cat else txt)
        else:
            salida.append(item)
    return salida


def _maquinas(data: dict, entrevistas: list) -> dict[str, list[str]]:
    grupos = {
        "Herramientas / utensilios": a_lista(data.get("utensilios")),
        "Materiales / sustancias": a_lista(data.get("materiales")),
        "Equipos": a_lista(data.get("equipos")),
        "Equipos tecnológicos": _equipos_tecnologicos(data.get("equipos_tecnologicos")),
    }
    for e in entrevistas:
        if isinstance(e, dict):
            grupos["Herramientas / utensilios"] += a_lista(e.get("UtensiliosJSON"))
            grupos["Materiales / sustancias"] += a_lista(e.get("MaterialesJSON"))
            grupos["Equipos tecnológicos"] += _equipos_tecnologicos(e.get("EquiposTecnologicosJSON"))
    salida = {}
    for grupo, items in grupos.items():
        vistos, lista = set(), []
        for it in items:
            txt = descripcion_item(it)
            if txt and normalizar(txt) not in vistos:
                vistos.add(normalizar(txt))
                lista.append(txt)
        if lista:
            salida[grupo] = lista
    return salida


GRUPO_POR_TIPO = {
    "herramienta / utensilio": "Herramientas / utensilios",
    "utensilio": "Herramientas / utensilios",
    "material / sustancia": "Materiales / sustancias",
    "material": "Materiales / sustancias",
    "equipo": "Equipos",
    "equipo tecnologico": "Equipos tecnológicos",
}
NO_APLICA = "No aplica"


def _maquinas_registro(valor: Any) -> list[tuple[str, str]]:
    """MaquinasEquipos del registro: [{Tipo, Descripcion}] o texto 'a | b | c'."""
    if isinstance(valor, str) and valor.strip() and not valor.strip().startswith(("[", "{", '"')):
        items: list = [x for x in valor.split("|")]
    else:
        items = a_lista(valor)
    salida = []
    for it in items:
        txt = descripcion_item(it)
        if not txt:
            continue
        tipo = str(it.get("Tipo") or "").strip() if isinstance(it, dict) else ""
        salida.append((GRUPO_POR_TIPO.get(normalizar(tipo), tipo or "Otros"), txt))
    return salida


def _maquinas_por_actividad(valor: Any) -> dict[str, list[tuple[str, str]]]:
    """Columna MAQUINAS_ACTIVIDAD: [{Actividad, Maquinas: [{Tipo, Descripcion}]}]."""
    salida = {}
    for it in a_lista(valor):
        if isinstance(it, dict) and texto_actividad(it.get("Actividad")):
            salida[normalizar(texto_actividad(it.get("Actividad")))] = _maquinas_registro(it.get("Maquinas"))
    return salida


def maquinas_de_actividad(filas: list[Fila], por_actividad: Optional[dict] = None) -> Optional[dict[str, list[str]]]:
    """Columna 9 de una actividad. Prioridad:
    1) MAQUINAS_ACTIVIDAD (guardado único por actividad)
    2) MaquinasEquipos dentro de los registros (unión)
    None -> no hay dato: usar el listado general del puesto."""
    clave = normalizar(filas[0].actividad) if filas else ""
    if por_actividad and clave in por_actividad:
        pares = por_actividad[clave]
    elif any(f.maquinas_informado for f in filas):
        pares = [p for f in filas for p in f.maquinas]
    else:
        return None
    grupos: dict[str, list[str]] = {}
    vistos = set()
    for grupo, txt in pares:
        if normalizar(txt) == normalizar(NO_APLICA) or normalizar(txt) in vistos:
            continue
        vistos.add(normalizar(txt))
        grupos.setdefault(grupo, []).append(txt)
    return grupos  # {} = "No aplica"


def _evaluacion(d: dict) -> Evaluacion:
    c = a_entero(d.get("IndiceConsecuencias")) or cfg.CONSECUENCIA_IDX.get(str(d.get("Consecuencias") or ""))
    return Evaluacion(
        cantidad=a_entero(d.get("CantidadPersonasExpuestas")),
        i_personas=a_entero(d.get("IndicePersonasExpuestas")),
        i_procedimientos=a_entero(d.get("IndiceProcedimientosExistentes")),
        i_capacitaciones=a_entero(d.get("IndiceCapacitaciones")),
        i_exposicion=a_entero(d.get("IndiceExposicionRiesgo")),
        i_consecuencias=c,
    )


def _medidas(mr: dict) -> list[str]:
    lista = mr.get("MedidasControl")
    if isinstance(lista, list) and lista:
        meds = [m.get("Medida") if isinstance(m, dict) else m for m in lista]
    else:
        meds = str(mr.get("MedidasTexto") or "").split(" | ")
    return list(dict.fromkeys(str(m).strip() for m in meds if m and str(m).strip()))


def construir(data: dict) -> MatrizGeritra:
    registros = [r for r in a_lista(data.get("matriz_riesgos")) if isinstance(r, dict)]
    entrevistas = a_lista(data.get("entrevistas_ast"))
    comunes_txt = [texto_actividad(a) for a in a_lista(data.get("actividades_comunes_ast"))]
    comunes_txt = [c for c in comunes_txt if c]
    personas = _personas(entrevistas, comunes_txt)

    generales = next((r["DatosGenerales"] for r in registros if r.get("DatosGenerales")), {}) or {}
    responsable = generales.get("ResponsableCargo") or {}

    filas: list[Fila] = []
    orden_act: dict[str, int] = {}
    no_rutinarias: list[str] = []
    for r in registros:
        mr = r.get("MatrizRiesgo") or {}
        rr = r.get("RiesgoResidual") or None
        actividad = texto_actividad(r.get("ActividadRutinaria"))
        nr = texto_actividad(r.get("ActividadNoRutinaria"))
        if nr:
            no_rutinarias.append(nr)
        act_n = normalizar(actividad)
        orden_act.setdefault(act_n, len(orden_act))

        jer: dict[str, list[str]] = {k: [] for k, _ in cfg.JERARQUIA_COLUMNAS}
        for m in _medidas(mr):
            jer[jerarquia_de(m, mr.get("FactorRiesgo"))].append(legible(sin_numeracion(m)))

        quienes = [p for p in personas if act_n in p.actividades]
        riesgo = str(mr.get("ClasificacionFactor") or "").upper()
        filas.append(Fila(
            actividad=actividad,
            peligro=str(mr.get("Peligro") or "").strip(),
            factor=legible(mr.get("FactorRiesgo")),
            clasificacion=str(mr.get("ClasificacionRiesgo") or "").strip()
                          or cfg.CLASIFICACION_POR_RIESGO.get(riesgo, ""),
            inicial=_evaluacion(mr),
            residual=_evaluacion(rr) if isinstance(rr, dict) else None,
            jerarquia=jer,
            efectos=str((rr or {}).get("EfectosSalud") or "").strip(),
            vigilancia=str((rr or {}).get("VigilanciaSalud") or "").strip(),
            fecha_control=a_fecha((rr or {}).get("FechaControlInspecciones")),
            mejora=str((rr or {}).get("ActividadesMejoraContinua") or "").strip(),
            orden=(orden_act[act_n], a_entero(r.get("NumeroRegistroMatriz")) or 0),
            disc_personas=[p for p in quienes if p.con_discapacidad],
            total_personas_actividad=len(quienes),
            maquinas=_maquinas_registro(r.get("MaquinasEquipos")),
            maquinas_informado="MaquinasEquipos" in r and bool(_maquinas_registro(r.get("MaquinasEquipos"))),
        ))
    filas.sort(key=lambda f: f.orden)

    for p in personas:
        no_rutinarias += p.eventos
    no_rut = list({normalizar(x): x for x in no_rutinarias if x}.values())

    telefono = " / ".join(x for x in (str(generales.get("TelefonoFijo") or "").strip(),
                                      str(generales.get("TelefonoCelular") or "").strip()) if x)
    return MatrizGeritra(
        codigo_ast=str(data.get("codigo_ast") or ""),
        razon_social=str(generales.get("RazonSocial") or "").strip(),
        ruc=str(generales.get("RUC") or "").strip(),
        direccion=str(generales.get("Direccion") or "").strip(),
        telefono=telefono,
        responsable_evaluacion=str(generales.get("ResponsableEvaluacion") or "").strip(),
        responsable_sso=str(generales.get("ResponsableSSO") or "").strip(),
        fecha_evaluacion=a_fecha(generales.get("FechaEvaluacion")) or a_fecha(data.get("fecha")),
        proceso=str(responsable.get("Proceso") or next((r.get("Proceso") for r in registros if r.get("Proceso")), "") or ""),
        puesto=str(data.get("cargo") or responsable.get("Cargo") or ""),
        numero_trabajadores=a_entero(data.get("numero_trabajadores")),
        personas_entrevistadas=len(personas),
        no_rutinarias=no_rut,
        maquinas=_maquinas(data, entrevistas),
        filas=filas,
        personas_discapacidad=[p for p in personas if p.con_discapacidad],
        maquinas_por_actividad=_maquinas_por_actividad(data.get("maquinas_actividad")),
    )
