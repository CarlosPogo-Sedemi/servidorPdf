from io import BytesIO
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from models.vacunas import PayloadVacunacion
from functions.vacunas_service import generar_pdf_vacunas

router = APIRouter(prefix="/api/v1", tags=["vacunas"])

@router.post("/generar-pdf-vacunas/")
def generar_pdf_vacunas_endpoint(payload: PayloadVacunacion):
    try:
        pdf_bytes = generar_pdf_vacunas(payload.paciente.dict(), payload.vacunas)
        file_stream = BytesIO(pdf_bytes)
        file_stream.seek(0)
        return StreamingResponse(
            file_stream,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="registro_vacunacion.pdf"'}
        )
    except Exception as e:
        print(f"Error generando PDF de vacunas: {e}")
        raise HTTPException(status_code=500, detail=str(e))