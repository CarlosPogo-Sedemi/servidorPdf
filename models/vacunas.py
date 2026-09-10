from typing import Dict, Any, List
from pydantic import BaseModel

class PacienteInfo(BaseModel):
    institucion: str = ""
    ruc: str = ""
    ciiu: str = ""
    establecimiento_salud: str = ""
    historia_clinica: str = ""
    numero_archivo: str = ""
    primer_apellido: str = ""
    segundo_apellido: str = ""
    primer_nombre: str = ""
    segundo_nombre: str = ""
    sexo: str = ""
    cargo: str = ""

class PayloadVacunacion(BaseModel):
    paciente: PacienteInfo
    vacunas: List[Dict[str, Any]]