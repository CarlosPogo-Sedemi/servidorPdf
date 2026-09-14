from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class DatosTrabajador(BaseModel):
    """Corresponde tal cual al bloque `DT` que arma el botón "Enviar" de
    Power Apps (jsonParaServidorPDF.data.DT). Los nombres de campo respetan
    el PascalCase que ya usa Power Apps a propósito, para no tener que
    tocar la app — la traducción a los nombres internos de la plantilla
    (compania, nombres_apellidos, etc.) se hace en pasaporte_service.py.
    Campos que Power Apps manda pero esta plantilla no usa (Medicamentos,
    SeguroPrivado, datos del examen médico, VA de vacunas, etc.) se ignoran
    solos gracias a `extra="ignore"` — no hace falta declararlos aquí."""
    model_config = ConfigDict(extra="ignore")

    FotoPerfil: Optional[str] = None
    Compania: str = ""
    NombreCompleto: str = ""
    Cedula: str = ""
    Nacionalidad: str = ""
    FechaNacimiento: Optional[str] = None
    DireccionDomi: str = ""
    NumeroCelular: str = ""
    Ekon: str = ""
    Cargo: str = ""
    Area: str = ""
    Licencia: str = ""
    FechaCadLic: Optional[str] = None
    Sangre: str = ""
    Enfermedades: str = ""
    Alergias: str = ""
    Contacto: str = ""
    Parentesco: str = ""
    NumeroContacto: str = ""
    Contacto2: str = ""
    Parentesco2: str = ""
    NumeroContacto2: str = ""


class RegistroMesActividad(BaseModel):
    """Forma que comparten `EmpleadoMes` y `BuenasPracticas` en el JSON de
    Power Apps (colEmpleadoMes / colBuenasPracticas): mismos 4 campos, el
    servicio decide a qué etiqueta del PDF va "Actividad" según la lista de
    la que venga. `Anio` se recibe pero no se muestra (así se pidió)."""
    model_config = ConfigDict(extra="ignore")

    Mes: str = ""
    Anio: Optional[str] = None
    FechaEmision: Optional[str] = None
    Actividad: str = ""


class RegistroCompetencia(BaseModel):
    """Power Apps envía aquí su colección de Certificados (colCertificado),
    no cursos de inducción/capacitación — por eso los nombres de campo son
    de certificado. El mapeo a las etiquetas de la tabla del PDF se hace en
    pasaporte_service.py."""
    model_config = ConfigDict(extra="ignore")

    NombreCertificado: str = ""
    AutoraEmisora: str = ""
    FechaEmision: Optional[str] = None
    FechaVencimiento: Optional[str] = None


class DatosPasaporte(BaseModel):
    model_config = ConfigDict(extra="ignore")

    DT: DatosTrabajador
    EmpleadoMes: List[RegistroMesActividad] = []
    BuenasPracticas: List[RegistroMesActividad] = []
    Competencias: List[RegistroCompetencia] = []


class PayloadPasaporte(BaseModel):
    """`template_name`, `data.NombreArchivoPDF` y `data.VA` (fechas de
    vacunas) también llegan en el JSON que arma Power Apps pero no se usan
    en este documento — `extra="ignore"` hace que Pydantic los descarte
    sin error, así no hace falta tocar el Power Fx del botón Enviar para
    que deje de mandarlos."""
    model_config = ConfigDict(extra="ignore")

    data: DatosPasaporte
