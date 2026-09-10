from typing import Dict, Any, List
from pydantic import BaseModel

class PayloadUniversal(BaseModel):
    template_name: str
    data: Dict[str, Any]

class FotoItem(BaseModel):
    NombreArchivo: str
    NovedadFoto: str
    SubirNube: bool

class LoteFotos(BaseModel):
    fotos: List[FotoItem]