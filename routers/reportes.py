# routers/reportes.py
import base64
from io import BytesIO
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from docxtpl import DocxTemplate
from docx import Document
from PIL import Image
from models.reportes import PayloadUniversal, LoteFotos
from functions.docx_service import reparar_tags_rotos, procesar_datos_rec

router = APIRouter(prefix="/api/v1", tags=["reportes"])

@router.post("/comprimir-fotos/")
def comprimir_fotos(payload: LoteFotos):
    fotos_optimizadas = []
    for foto in payload.fotos:
        if foto.SubirNube and foto.NovedadFoto:
            try:
                if "base64," in foto.NovedadFoto:
                    b64_data = foto.NovedadFoto.split("base64,")[-1]
                else:
                    b64_data = foto.NovedadFoto

                img_bytes = base64.b64decode(b64_data)
                img = Image.open(BytesIO(img_bytes)).convert("RGB")

                max_width = 800
                if img.width > max_width:
                    wpercent = max_width / float(img.width)
                    hsize = int(float(img.height) * wpercent)
                    img = img.resize((max_width, hsize), Image.Resampling.LANCZOS)

                buffer_optimizado = BytesIO()
                img.save(buffer_optimizado, format="JPEG", optimize=True, quality=70)

                nueva_b64 = f"data:image/jpeg;base64,{base64.b64encode(buffer_optimizado.getvalue()).decode()}"
                foto.NovedadFoto = nueva_b64
            except Exception as e:
                print(f"Error comprimiendo la foto {foto.NombreArchivo}: {e}")
                pass

        fotos_optimizadas.append(foto)

    return fotos_optimizadas


@router.post("/generar-reporte/")
def generar_reporte_universal(payload: PayloadUniversal):
    try:
        ruta_plantilla = f"templates/{payload.template_name}.docx"
        try:
            doc_puro = Document(ruta_plantilla)
        except Exception:
            raise HTTPException(status_code=404, detail=f"La plantilla '{payload.template_name}.docx' no existe.")

        reparar_tags_rotos(doc_puro)
        buffer_reparado = BytesIO()
        doc_puro.save(buffer_reparado)
        buffer_reparado.seek(0)

        doc = DocxTemplate(buffer_reparado)
        contexto = payload.data
        procesar_datos_rec(contexto, doc)
        doc.render(contexto)

        file_stream = BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)

        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="Reporte_{payload.template_name}.docx"'}
        )
    except Exception as e:
        print(f"Error crítico en el servidor: {e}")
        raise HTTPException(status_code=500, detail=str(e))