from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict

# Columnas JSON de SharePoint: Power Automate puede mandarlas como texto JSON
# o ya parseadas (arreglo). Se aceptan ambas formas.
JsonLista = Optional[Union[str, List[Any]]]


class PayloadMatrizGeritra(BaseModel):
    """Campos de la lista AST_PUESTO_TRABAJO para la matriz GERITRA.

    - matriz_riesgos        -> columna MATRIZ_RIESGOS (nombre interno MATRIZ_RIESGO)
    - entrevistas_ast       -> ENTREVISTAS_AST (discapacidad, actividades y eventos por persona)
    - actividades_comunes_ast -> ACTIVIDADES_COMUNES_AST (aplican a todas las personas)
    - utensilios, materiales, equipos, equipos_tecnologicos -> columna 9 de la GERITRA
    """
    model_config = ConfigDict(extra="ignore")

    codigo_ast: Optional[str] = None
    cargo: Optional[str] = None
    area: Optional[str] = None
    grupo: Optional[str] = None
    numero_trabajadores: Optional[Union[str, int, float]] = None
    muestra_requerida: Optional[Union[str, int, float]] = None
    fecha: Optional[str] = None

    matriz_riesgos: JsonLista = None
    entrevistas_ast: JsonLista = None
    actividades_comunes_ast: JsonLista = None
    utensilios: JsonLista = None
    materiales: JsonLista = None
    equipos: JsonLista = None
    equipos_tecnologicos: JsonLista = None
