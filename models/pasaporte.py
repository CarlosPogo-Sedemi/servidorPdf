from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class DatosTrabajador(BaseModel):
    """Corresponde tal cual al bloque `DT` que arma el botón "Enviar" de
    Power Apps (jsonParaServidorPDF.data.DT). Los nombres de campo respetan
    el PascalCase que ya usa Power Apps a propósito, para no tener que
    tocar la app — la traducción a los nombres internos de la plantilla
    (compania, nombres_apellidos, etc.) se hace en pasaporte_service.py.
    Campos que Power Apps manda pero esta plantilla no usa (Medicamentos,
    SeguroPrivado, etc.) se ignoran solos gracias a `extra="ignore"` — no
    hace falta declararlos aquí. Todos son `Optional[str]` (no `str = ""`)
    porque Power Apps manda `null` cuando un campo queda en blanco (p.ej.
    Contacto2/Parentesco2 sin diligenciar); pasaporte_service.py ya hace
    `dt.get(campo) or ""` para cada uno, así que aquí basta con aceptar
    `None` sin rechazarlo.

    FechaExa..FechaExaCad son el bloque de "Exámen Médico Ocupacional" de la
    página Historial Médico (Lugar es el centro/proveedor médico, no una
    dirección de domicilio; NombreMedico + CedulaMedico arman "Nombre y
    apellido del médico y código MSP" en una sola línea)."""
    model_config = ConfigDict(extra="ignore")

    FotoPerfil: Optional[str] = None
    Compania: Optional[str] = None
    NombreCompleto: Optional[str] = None
    Cedula: Optional[str] = None
    Nacionalidad: Optional[str] = None
    FechaNacimiento: Optional[str] = None
    DireccionDomi: Optional[str] = None
    NumeroCelular: Optional[str] = None
    Ekon: Optional[str] = None
    Cargo: Optional[str] = None
    Area: Optional[str] = None
    Licencia: Optional[str] = None
    FechaCadLic: Optional[str] = None
    Sangre: Optional[str] = None
    Enfermedades: Optional[str] = None
    Alergias: Optional[str] = None
    Contacto: Optional[str] = None
    Parentesco: Optional[str] = None
    NumeroContacto: Optional[str] = None
    Contacto2: Optional[str] = None
    Parentesco2: Optional[str] = None
    NumeroContacto2: Optional[str] = None
    FechaExa: Optional[str] = None
    Lugar: Optional[str] = None
    NombreMedico: Optional[str] = None
    CedulaMedico: Optional[str] = None
    Aptitud: Optional[str] = None
    Restricciones: Optional[str] = None
    FechaExaCad: Optional[str] = None


class DatosVacunas(BaseModel):
    """Bloque `VA` que ya arma Power Apps (fechas de dosis por vacuna):
    F=Fiebre Amarilla, HA=Hepatitis A, HB=Hepatitis B, HAB=Hepatitis A y B
    combinada, TF=Tifoidea, DT=Difteria y Tétanos, T=Tétanos, C=Covid,
    INF=Influenza, SR=Sarampión-Rubéola. F/INF son de una sola dosis
    (F1/INF1) e INF además es estacional — Power Apps ya manda ahí la dosis
    del año en curso, no hace falta resolver eso acá. SR es de 2 dosis
    (SR1/SR2). El resto admite hasta 5 (X1..X5). Usado en la tabla de
    Vacunas de Historial Médico."""
    model_config = ConfigDict(extra="ignore")

    F1: Optional[str] = None
    HA1: Optional[str] = None
    HA2: Optional[str] = None
    HA3: Optional[str] = None
    HA4: Optional[str] = None
    HA5: Optional[str] = None
    HB1: Optional[str] = None
    HB2: Optional[str] = None
    HB3: Optional[str] = None
    HB4: Optional[str] = None
    HB5: Optional[str] = None
    HAB1: Optional[str] = None
    HAB2: Optional[str] = None
    HAB3: Optional[str] = None
    HAB4: Optional[str] = None
    HAB5: Optional[str] = None
    TF1: Optional[str] = None
    TF2: Optional[str] = None
    TF3: Optional[str] = None
    TF4: Optional[str] = None
    TF5: Optional[str] = None
    DT1: Optional[str] = None
    DT2: Optional[str] = None
    DT3: Optional[str] = None
    DT4: Optional[str] = None
    DT5: Optional[str] = None
    T1: Optional[str] = None
    T2: Optional[str] = None
    T3: Optional[str] = None
    T4: Optional[str] = None
    T5: Optional[str] = None
    C1: Optional[str] = None
    C2: Optional[str] = None
    C3: Optional[str] = None
    C4: Optional[str] = None
    C5: Optional[str] = None
    INF1: Optional[str] = None
    SR1: Optional[str] = None
    SR2: Optional[str] = None


class RegistroMesActividad(BaseModel):
    """Forma que comparten `EmpleadoMes` y `BuenasPracticas` en el JSON de
    Power Apps (colEmpleadoMes / colBuenasPracticas): mismos 4 campos, el
    servicio decide a qué etiqueta del PDF va "Actividad" según la lista de
    la que venga. `Anio` se recibe pero no se muestra (así se pidió)."""
    model_config = ConfigDict(extra="ignore")

    Mes: Optional[str] = None
    Anio: Optional[str] = None
    FechaEmision: Optional[str] = None
    Actividad: Optional[str] = None


class RegistroCompetencia(BaseModel):
    """Power Apps envía aquí su colección de Certificados (colCertificado),
    no cursos de inducción/capacitación — por eso los nombres de campo son
    de certificado. El mapeo a las etiquetas de la tabla del PDF se hace en
    pasaporte_service.py."""
    model_config = ConfigDict(extra="ignore")

    NombreCertificado: Optional[str] = None
    AutoraEmisora: Optional[str] = None
    FechaEmision: Optional[str] = None
    FechaVencimiento: Optional[str] = None


class DatosPasaporte(BaseModel):
    model_config = ConfigDict(extra="ignore")

    DT: DatosTrabajador
    VA: DatosVacunas = DatosVacunas()
    EmpleadoMes: List[RegistroMesActividad] = []
    BuenasPracticas: List[RegistroMesActividad] = []
    Competencias: List[RegistroCompetencia] = []


class PayloadPasaporte(BaseModel):
    """`template_name` y `data.NombreArchivoPDF` también llegan en el JSON
    que arma Power Apps pero no se usan en este documento — `extra="ignore"`
    hace que Pydantic los descarte sin error, así no hace falta tocar el
    Power Fx del botón Enviar para que deje de mandarlos."""
    model_config = ConfigDict(extra="ignore")

    data: DatosPasaporte
