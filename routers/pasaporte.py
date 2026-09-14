from io import BytesIO
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models.pasaporte import PayloadPasaporte
from functions.pasaporte_service import generar_pdf_pasaporte

router = APIRouter(prefix="/api/v1", tags=["pasaporte"])


@router.post("/generar-pdf-pasaporte/")
def generar_pdf_pasaporte_endpoint(payload: PayloadPasaporte):
    try:
        pdf_bytes = generar_pdf_pasaporte(payload.dict())
        file_stream = BytesIO(pdf_bytes)
        file_stream.seek(0)
        return StreamingResponse(
            file_stream,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="pasaporte_seguridad.pdf"'}
        )
    except Exception as e:
        print(f"Error generando PDF de pasaporte: {e}")
        raise HTTPException(status_code=500, detail=str(e))
