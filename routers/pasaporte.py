import json
from io import BytesIO
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from models.pasaporte import PayloadPasaporte
from functions.pasaporte_service import generar_pdf_pasaporte

router = APIRouter(prefix="/api/v1", tags=["pasaporte"])


@router.post("/generar-pdf-pasaporte/")
async def generar_pdf_pasaporte_endpoint(request: Request):
    # Power Automate a veces manda el JSON serializado dos veces (el body
    # llega como un string que contiene el JSON, en vez de un objeto), por
    # eso no se usa el parseo automático de FastAPI/Pydantic acá: se lee el
    # cuerpo crudo y, si el primer json.loads devuelve un str en vez de un
    # dict, se vuelve a parsear.
    raw = await request.body()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        payload = PayloadPasaporte.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        pdf_bytes = generar_pdf_pasaporte(payload.model_dump())
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
