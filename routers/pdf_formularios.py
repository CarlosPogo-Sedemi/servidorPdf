# routers/pdf_formularios.py
import re
from io import BytesIO
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from models.pdf_formularios import PayloadLlenarPdf
from functions.pdf_form_service import (
    PdfSinCamposError,
    PlantillaNoExisteError,
    cargar_alias,
    cargar_plantilla,
    listar_campos,
    llenar_pdf,
    payload_ejemplo,
)

router = APIRouter(prefix="/api/v1", tags=["pdf-formularios"])


def _ascii(texto: str, limite: int = 900) -> str:
    """Los headers HTTP deben ser ASCII y cortos."""
    return texto.encode("ascii", "replace").decode("ascii")[:limite]


@router.post("/llenar-pdf/")
def llenar_pdf_endpoint(payload: PayloadLlenarPdf):
    """Rellena templates_pdf/<template_name>.pdf con `data` y devuelve el PDF con los
    campos todavía editables. En los headers X-Campos-* viene el resumen del llenado."""
    try:
        pdf_plantilla = cargar_plantilla(payload.template_name)
        pdf_bytes, reporte = llenar_pdf(pdf_plantilla, payload.data, cargar_alias(payload.template_name))

        problemas = reporte["no_encontrados"] + reporte["ambiguos"] + reporte["invalidos"]
        if problemas:
            print(f"[llenar-pdf] {payload.template_name}: {reporte}")
        if payload.estricto and problemas:
            raise HTTPException(status_code=422, detail=reporte)

        nombre = re.sub(r"[^\w\-]", "_", payload.nombre_archivo or payload.template_name, flags=re.ASCII)
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{nombre}.pdf"',
                "X-Campos-Aplicados": str(len(reporte["aplicados"])),
                "X-Campos-No-Encontrados": _ascii(",".join(reporte["no_encontrados"])),
                "X-Campos-Ambiguos": _ascii(",".join(reporte["ambiguos"])),
                "X-Campos-Invalidos": _ascii(",".join(reporte["invalidos"])),
                "X-Campos-Desbordados": _ascii(",".join(reporte["desbordados"])),
            },
        )
    except HTTPException:
        raise
    except PlantillaNoExisteError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PdfSinCamposError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"Error llenando PDF '{payload.template_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pdf-campos/{template_name}")
def campos_de_plantilla(template_name: str):
    """Lista los campos de una plantilla guardada en templates_pdf/ y un JSON de ejemplo."""
    try:
        campos = listar_campos(cargar_plantilla(template_name))
        return {"template_name": template_name, "alias": cargar_alias(template_name), "campos": campos, "data_ejemplo": payload_ejemplo(campos)}
    except PlantillaNoExisteError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PdfSinCamposError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"Error leyendo campos de '{template_name}': {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pdf-campos/")
async def campos_de_pdf_subido(archivo: UploadFile = File(...)):
    """Igual que el GET, pero subiendo cualquier PDF (útil para descubrir los nombres de
    los campos antes de copiarlo a templates_pdf/)."""
    try:
        campos = listar_campos(await archivo.read())
        return {"archivo": archivo.filename, "campos": campos, "data_ejemplo": payload_ejemplo(campos)}
    except PdfSinCamposError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        print(f"Error leyendo campos del PDF subido: {e}")
        raise HTTPException(status_code=500, detail=str(e))
