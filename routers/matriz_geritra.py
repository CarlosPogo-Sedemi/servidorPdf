import json
from io import BytesIO
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from models.matriz_geritra import PayloadMatrizGeritra
from functions.geritra_excel import generar_excel_geritra

router = APIRouter(prefix="/api/v1", tags=["matriz-geritra"])

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/generar-excel-matriz-geritra/")
async def generar_excel_matriz_geritra_endpoint(request: Request):
    # Igual que pasaporte/matriz_ast: Power Automate a veces manda el JSON
    # serializado dos veces; se lee el cuerpo crudo y se re-parsea si hace falta.
    raw = await request.body()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        payload = PayloadMatrizGeritra.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        contenido, nombre = generar_excel_geritra(payload.model_dump())
        stream = BytesIO(contenido)
        stream.seek(0)
        return StreamingResponse(
            stream,
            media_type=XLSX_MIME,
            headers={"Content-Disposition": f'attachment; filename="{nombre}"'}
        )
    except Exception as e:
        print(f"Error generando Excel GERITRA: {e}")
        raise HTTPException(status_code=500, detail=str(e))
