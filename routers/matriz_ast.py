import json
from io import BytesIO
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from models.matriz_ast import PayloadMatrizAST
from functions.matriz_ast_excel import generar_excel_matriz_ast

router = APIRouter(prefix="/api/v1", tags=["matriz-ast"])

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.post("/generar-excel-matriz-ast/")
async def generar_excel_matriz_ast_endpoint(request: Request):
    # Igual que en pasaporte: Power Automate a veces manda el JSON
    # serializado dos veces, así que se lee el cuerpo crudo y se re-parsea
    # si el primer json.loads devuelve un str.
    raw = await request.body()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, str):
            parsed = json.loads(parsed)
        payload = PayloadMatrizAST.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        contenido, nombre = generar_excel_matriz_ast(payload.model_dump())
        file_stream = BytesIO(contenido)
        file_stream.seek(0)
        return StreamingResponse(
            file_stream,
            media_type=XLSX_MIME,
            headers={"Content-Disposition": f'attachment; filename="{nombre}"'}
        )
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"MATRIZ_RIESGOS no es un JSON válido: {e}")
    except Exception as e:
        print(f"Error generando Excel de matriz AST: {e}")
        raise HTTPException(status_code=500, detail=str(e))
