from typing import Any, Dict, Optional
from pydantic import BaseModel


class PayloadLlenarPdf(BaseModel):
    """Misma forma que PayloadUniversal (template_name + data) para que el flujo de
    Power Automate solo cambie de URL. `data` = {nombre_del_campo_en_el_PDF: valor}."""
    template_name: str
    data: Dict[str, Any]
    estricto: bool = False  # True: responde 422 si alguna clave no coincide con un campo
    nombre_archivo: Optional[str] = None  # nombre de descarga (sin extensión)
