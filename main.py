import base64
from io import BytesIO
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from PIL import Image
import re  # agrégalo arriba del archivo, junto a los otros imports
from docx import Document  # <-- Fundamental para abrir el Word puro primero

app = FastAPI(title="Servidor Universal de Reportes - SEDEMI")

# ==========================================
# MODELO DE ENTRADA GENÉRICO (Igual a tu Next.js)
# ==========================================
class PayloadUniversal(BaseModel):
    template_name: str         # Ej: "reporte_fase3", "for_sei_11"
    data: Dict[str, Any]       # Cualquier estructura JSON libre

def reparar_tags_rotos(documento_docx):
    """
    Recorre todos los párrafos del documento (incluidas tablas anidadas),
    fusiona los runs partidos por el corrector de Word y normaliza
    la sintaxis especial {%tr ...%} de docxtpl (sin espacio tras {%).
    """
    def fusionar_parrafo(p):
        texto_completo = "".join(run.text for run in p.runs)
        if "{%" in texto_completo or "{{" in texto_completo:
            # Normaliza "{% tr" -> "{%tr" (con cualquier cantidad de espacios)
            texto_corregido = re.sub(r'\{%\s*tr\b', '{%tr', texto_completo)

            if texto_corregido != texto_completo or len(p.runs) > 1:
                p.runs[0].text = texto_corregido
                for run in p.runs[1:]:
                    run.text = ""

    def procesar_parrafos(parrafos):
        for p in parrafos:
            fusionar_parrafo(p)

    def procesar_tablas(tablas):
        for tabla in tablas:
            for fila in tabla.rows:
                for celda in fila.cells:
                    # Primero reparamos párrafos
                    procesar_parrafos(celda.paragraphs)
                    # Y luego limpiamos los bordes de la celda por si Word metió ahí el tag
                    for run in celda.paragraphs[0].runs:
                         run.text = run.text.replace(" ", "") # Elimina espacios basura en los tags
                    
                    # Llamada recursiva para tablas anidadas
                    procesar_tablas(celda.tables)

    procesar_parrafos(documento_docx.paragraphs)
    procesar_tablas(documento_docx.tables)

# ==========================================
# MAGIA: ESCANER AUTOMÁTICO DE IMÁGENES
# ==========================================
def procesar_imagenes_rec(sub_contexto, doc):
    """
    Recorre recursivamente el JSON buscando cadenas Base64 o claves de imagen
    y las reemplaza "in-place" por objetos InlineImage listos para el Word.
    """
    if isinstance(sub_contexto, dict):
        for k, v in list(sub_contexto.items()):
            # Detectar si el valor es una imagen base64 (por su prefijo o contenido)
            if isinstance(v, str) and ("base64," in v or v.startswith("data:image")):
                try:
                    # Limpiar y decodificar base64
                    foto_str = v.split("base64,")[-1]
                    img_bytes_raw = base64.b64decode(foto_str)

                    # Procesar con Pillow en RAM para asegurar los DPI
                    pil_img = Image.open(BytesIO(img_bytes_raw)).convert("RGB")
                    buffer_corregido = BytesIO()
                    pil_img.save(buffer_corregido, format="JPEG", dpi=(96, 96))
                    buffer_corregido.seek(0)

                    # REEMPLAZO: Cambiamos la cadena de texto base64 por el objeto InlineImage
                    sub_contexto[k] = InlineImage(doc, buffer_corregido, width=Mm(50))
                except Exception as e:
                    print(f"No se pudo procesar la imagen automática en la clave '{k}': {e}")
            else:
                # Seguir buscando dentro del diccionario
                procesar_imagenes_rec(v, doc)
                
    elif isinstance(sub_contexto, list):
        for item in sub_contexto:
            procesar_imagenes_rec(item, doc)

# ==========================================
# ENDPOINT UNIVERSAL
# ==========================================
@app.post("/api/v1/generar-reporte/")
def generar_reporte_universal(payload: PayloadUniversal):
    try:
        ruta_plantilla = f"templates/{payload.template_name}.docx"
        
        # 1. CARGAR EL WORD PURO CON PYTHON-DOCX
        try:
            doc_puro = Document(ruta_plantilla)
        except Exception:
            raise HTTPException(status_code=404, detail=f"La plantilla '{payload.template_name}.docx' no existe.")

        # 2. APLICAR TU FUNCIÓN PARA REPARAR LOS TAGS ROTOS POR WORD
        reparar_tags_rotos(doc_puro)

        # 3. GUARDAR EL WORD YA REPARADO EN LA MEMORIA RAM
        buffer_reparado = BytesIO()
        doc_puro.save(buffer_reparado)
        buffer_reparado.seek(0) # Rebobinar la memoria

        # 4. AHORA SÍ, INICIAR DOCXTPL CON EL ARCHIVO IMPECABLE
        doc = DocxTemplate(buffer_reparado)

        # 5. Extraer los datos y ejecutar el escáner de imágenes Base64
        contexto = payload.data
        procesar_imagenes_rec(contexto, doc)

        # 6. Renderizar la plantilla
        doc.render(contexto)

        # 7. Guardar el PDF/Word final en RAM
        file_stream = BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)

        nombre_descarga = f"Reporte_{payload.template_name}.docx"
        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{nombre_descarga}"'}
        )

    except Exception as e:
        print(f"Error crítico en el servidor: {e}")
        raise HTTPException(status_code=500, detail=str(e))