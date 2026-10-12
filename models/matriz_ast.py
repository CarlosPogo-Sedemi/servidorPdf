from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict


class PayloadMatrizAST(BaseModel):
    """Campos de la lista SharePoint AST_PUESTO_TRABAJO que usa el formato
    FOR SEI 02 (Matriz de riesgos laborales por puesto de trabajo, INSST).

    `matriz_riesgos` es la columna MATRIZ_RIESGOS (nombre interno
    MATRIZ_RIESGO): se acepta tal cual la guarda Power Apps (texto JSON) o
    ya parseada como arreglo. `numero_trabajadores` llega como texto porque
    la columna en SharePoint es de tipo Texto. Campos extra que mande Power
    Automate se ignoran (`extra="ignore"`)."""
    model_config = ConfigDict(extra="ignore")

    codigo_ast: Optional[str] = None
    cargo: Optional[str] = None
    area: Optional[str] = None
    grupo: Optional[str] = None
    numero_trabajadores: Optional[Union[str, int, float]] = None
    fecha: Optional[str] = None
    matriz_riesgos: Optional[Union[str, List[Dict[str, Any]]]] = None
