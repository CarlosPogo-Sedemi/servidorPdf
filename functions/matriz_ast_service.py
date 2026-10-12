"""Transforma MATRIZ_RIESGOS (JSON de Power Apps) en el modelo del formato
FOR SEI 02. Toda la lógica de negocio vive aquí; matriz_ast_excel.py solo pinta.
Sin imports de FastAPI (convención de functions/)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

import re
import unicodedata
from functools import lru_cache

from functions import matriz_ast_config as cfg


# ----------------------------------------------------------------------------
# Catálogo de factores (descripción técnica por factor)
# ----------------------------------------------------------------------------
def normalizar(texto: str) -> str:
    """Clave de comparación: sin tildes, minúsculas, ';' -> ',' y espacios simples."""
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = t.lower().replace(";", ",")
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=1)
def _catalogo() -> dict:
    with open(cfg.ASSETS_DIR / "catalogo_factores.json", encoding="utf-8") as fh:
        crudo = json.load(fh)
    return {normalizar(k): v for k, v in crudo.items()}


def descripcion_factor(factor: str) -> str:
    return _catalogo().get(normalizar(factor), {}).get("descripcion", "")


# ----------------------------------------------------------------------------
# Modelos
# ----------------------------------------------------------------------------
@dataclass
class Encabezado:
    empresa: str
    sector: str  # "PLANTA" | "CAMPO" | ""
    descripcion_cargo: str
    localizacion: str
    puesto: str
    numero_trabajadores: Optional[int]
    proceso: str
    fecha_evaluacion: Optional[date]
    fecha_proxima: date
    evaluacion_inicial: bool
    evaluado_por: str
    fecha_evaluado_por: Optional[date]
    codigo_ast: str


@dataclass
class Fila:
    clasificacion: str          # clave de la app (DE SEGURIDAD, FÍSICOS...)
    factor: str
    descripcion: str
    actividad: str
    peligro: str
    probabilidad: str           # B | M | A | ""
    consecuencia: str           # LD | D | ED | ""
    nivel: str                  # T | TO | M | I | IN | ""
    medidas: list[str] = field(default_factory=list)
    registro_app: int = 0       # NumeroRegistroMatriz (solo para ordenar)

    @property
    def tiene_medidas(self) -> bool:
        return bool(self.medidas)


@dataclass
class MatrizFormato:
    encabezado: Encabezado
    filas: list[Fila]


# ----------------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------------
def _texto(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, dict):  # p.ej. ActividadRutinaria guardada como registro
        valor = valor.get("Descripcion") or valor.get("Value") or ""
    return " ".join(str(valor).split())


def _legible(texto: str) -> str:
    """Power Apps (región ES) guarda ',' como ';' en textos de catálogo."""
    return texto.replace(";", ",").replace(" ,", ",")


def _entero(valor: Any) -> Optional[int]:
    try:
        return int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return None


def _fecha(valor: Any) -> Optional[date]:
    if not valor:
        return None
    texto = str(valor).strip()[:10]
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def _sumar_anios(base: date, anios: int) -> date:
    try:
        return base.replace(year=base.year + anios)
    except ValueError:  # 29 de febrero
        return base.replace(year=base.year + anios, day=28)


def _parse_matriz(raw: Any) -> list[dict]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, str):
        raw = json.loads(raw)
    return [r for r in raw if isinstance(r, dict)]


# ----------------------------------------------------------------------------
# Reglas INSST
# ----------------------------------------------------------------------------
def nivel_probabilidad(mr: dict) -> str:
    """'Baja' | 'Media' | 'Alta' | ''  (recalcula si el registro es antiguo)."""
    guardado = _texto(mr.get("ProbabilidadNivel"))
    if guardado in cfg.PROBABILIDAD_IDX:
        return guardado
    indices = [
        _entero(mr.get(k))
        for k in (
            "IndicePersonasExpuestas",
            "IndiceProcedimientosExistentes",
            "IndiceCapacitaciones",
            "IndiceExposicionRiesgo",
        )
    ]
    if any(i is None or i == 0 for i in indices):
        return ""
    suma = sum(indices)
    return "Baja" if suma <= 4 else "Media" if suma <= 8 else "Alta"


def indice_consecuencia(mr: dict) -> Optional[int]:
    idx = _entero(mr.get("IndiceConsecuencias"))
    if idx in (1, 2, 3):
        return idx
    return cfg.CONSECUENCIA_IDX.get(_texto(mr.get("Consecuencias")))


def nivel_riesgo(prob: str, c_idx: Optional[int]) -> str:
    p_idx = cfg.PROBABILIDAD_IDX.get(prob)
    if not p_idx or not c_idx:
        return ""
    return cfg.NIVEL_POR_SUMA[p_idx + c_idx]


def _medidas(mr: dict) -> list[str]:
    lista = mr.get("MedidasControl")
    if isinstance(lista, list) and lista:
        medidas = [_texto(m.get("Medida") if isinstance(m, dict) else m) for m in lista]
    else:
        medidas = [_texto(m) for m in _texto(mr.get("MedidasTexto")).split(" | ")]
    vistos, salida = set(), []
    for m in medidas:
        if m and m not in vistos:
            vistos.add(m)
            salida.append(_legible(m))
    return salida


# ----------------------------------------------------------------------------
# Construcción
# ----------------------------------------------------------------------------
def _fila(reg: dict) -> Fila:
    mr = reg.get("MatrizRiesgo") or {}
    actividad = _texto(reg.get("ActividadRutinaria"))
    no_rutinaria = _texto(reg.get("ActividadNoRutinaria"))
    if no_rutinaria:
        actividad = f"{actividad}\n(No rutinaria: {no_rutinaria})" if actividad else no_rutinaria

    prob = nivel_probabilidad(mr)
    c_idx = indice_consecuencia(mr)
    factor = _texto(mr.get("FactorRiesgo"))

    return Fila(
        clasificacion=_texto(mr.get("ClasificacionFactor")).upper(),
        factor=_legible(factor),
        descripcion=descripcion_factor(factor),
        actividad=actividad,
        peligro=_texto(mr.get("Peligro")),
        probabilidad=cfg.PROBABILIDAD_COD.get(prob, ""),
        consecuencia=cfg.CONSECUENCIA_COD.get(c_idx, ""),
        nivel=nivel_riesgo(prob, c_idx),
        medidas=_medidas(mr),
        registro_app=_entero(reg.get("NumeroRegistroMatriz")) or 0,
    )


def _orden(f: Fila) -> tuple:
    orden_cat = cfg.CLASIFICACIONES.get(f.clasificacion, {}).get("orden", 99)
    return (orden_cat, f.factor.lower(), f.registro_app)


def construir(data: dict) -> MatrizFormato:
    """`data` = PayloadMatrizAST.model_dump()."""
    registros = _parse_matriz(data.get("matriz_riesgos"))
    generales = next((r["DatosGenerales"] for r in registros if r.get("DatosGenerales")), {}) or {}
    responsable = generales.get("ResponsableCargo") or {}

    filas = sorted((_fila(r) for r in registros), key=_orden)

    # N.º de trabajadores: columna de la lista; respaldo = máx. personas expuestas
    num_trab = _entero(data.get("numero_trabajadores"))
    if not num_trab:
        expuestas = [
            _entero((r.get("MatrizRiesgo") or {}).get("CantidadPersonasExpuestas")) or 0
            for r in registros
        ]
        num_trab = max(expuestas, default=0) or None

    proceso = _texto(responsable.get("Proceso")) or next(
        (_texto(r.get("Proceso")) for r in registros if r.get("Proceso")), ""
    )
    fecha_eval = _fecha(generales.get("FechaEvaluacion")) or _fecha(data.get("fecha"))
    hoy = datetime.now(cfg.TZ).date()
    grupo = _texto(data.get("grupo")).upper()

    encabezado = Encabezado(
        empresa=_texto(generales.get("RazonSocial")) or cfg.EMPRESA_DEFECTO,
        sector=grupo if grupo in ("PLANTA", "CAMPO") else "",
        descripcion_cargo="",
        localizacion=_texto(data.get("area")),
        puesto=_texto(data.get("cargo")) or _texto(responsable.get("Cargo")),
        numero_trabajadores=num_trab,
        proceso=proceso,
        fecha_evaluacion=fecha_eval,
        fecha_proxima=_sumar_anios(hoy, cfg.ANIOS_PROXIMA_EVALUACION),
        evaluacion_inicial=True,
        evaluado_por=_texto(generales.get("ResponsableEvaluacion")),
        fecha_evaluado_por=fecha_eval,
        codigo_ast=_texto(data.get("codigo_ast")),
    )
    return MatrizFormato(encabezado=encabezado, filas=filas)
