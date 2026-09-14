from typing import List, Optional
from pydantic import BaseModel


class DatosPersonales(BaseModel):
    compania: str = ""
    nombres_apellidos: str = ""
    identificacion: str = ""
    nacionalidad: str = ""
    fecha_nacimiento: str = ""
    direccion: str = ""
    numero_celular: str = ""
    codigo_colaborador: str = ""
    cargo: str = ""
    area: str = ""
    tipo_licencia: str = ""
    fecha_caducidad_licencia: str = ""
    foto_base64: Optional[str] = None


class InfoEmergencia(BaseModel):
    tipo_sangre: str = ""
    enfermedades: str = ""
    alergias: str = ""
    contacto1_nombre: str = ""
    contacto1_parentesco: str = ""
    contacto1_numero: str = ""
    contacto2_nombre: str = ""
    contacto2_parentesco: str = ""
    contacto2_numero: str = ""


class Competencia(BaseModel):
    """Una fila de la sección de Inducción/Capacitación. Esta lista puede crecer
    indefinidamente (es la sección que en Word rompía el loop {%tr%})."""
    tipo: str = ""  # "Inducción" o "Capacitación"
    nombre_curso: str = ""
    nombre_instructor: str = ""
    expedicion: str = ""
    vencimiento: str = ""
    firma_sello_base64: Optional[str] = None


class Reconocimiento(BaseModel):
    """Registro de 'Empleado seguro del mes'. Lista dinámica."""
    mes: str = ""
    actividad: str = ""
    firma_base64: Optional[str] = None


class BuenaPractica(BaseModel):
    """Registro de 'Buenas prácticas ambientales'. Lista dinámica."""
    accion_destacada: str = ""
    mes: str = ""
    firma_base64: Optional[str] = None


class PayloadPasaporte(BaseModel):
    datos_personales: DatosPersonales
    info_emergencia: InfoEmergencia
    competencias: List[Competencia] = []
    reconocimientos: List[Reconocimiento] = []
    buenas_practicas: List[BuenaPractica] = []
