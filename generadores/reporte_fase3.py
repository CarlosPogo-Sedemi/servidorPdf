import os
import base64
from io import BytesIO
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from PIL import Image  # <-- Agregar esto

def crear_pdf_fase3(payload) -> str:
    # 1. Rutas
    template_path = "templates/reporte_fase3.docx"
    orden = payload.Metadatos.Orden
    nombre_archivo = f"Reporte_Fase3_Orden_{orden}.docx"
    ruta_salida = os.path.join("archivos_salida", nombre_archivo)

    # 2. Cargar plantilla
    doc = DocxTemplate(template_path)

    # 3. Preparar contexto
    context = {
        "Metadatos": payload.Metadatos,
        "Items": []
    }

    # 4. Procesar ítems e imágenes
    for item in payload.ItemsChecklist:
        imagen_obj = None

        if item.FotoBase64:
            try:
                # Limpiar base64
                foto_str = item.FotoBase64.split("base64,")[-1]
                img_bytes_raw = base64.b64decode(foto_str)

                # ✅ Forzar DPI con Pillow para evitar ZeroDivisionError
                pil_img = Image.open(BytesIO(img_bytes_raw))
                pil_img = pil_img.convert("RGB")  # Normalizar formato

                buffer_corregido = BytesIO()
                pil_img.save(buffer_corregido, format="JPEG", dpi=(96, 96))
                buffer_corregido.seek(0)

                imagen_obj = InlineImage(doc, buffer_corregido, width=Mm(50))

            except Exception as e:
                print(f"Error procesando imagen del ítem {item.ID_Item}: {e}")
                imagen_obj = None  # La celda quedará vacía, no rompe el doc

        context["Items"].append({
            "ID_Item":       item.ID_Item,
            "Descripcion":   item.Descripcion,
            "Cumple_X":      item.Cumple_X,
            "NoCumple_X":    item.NoCumple_X,
            "Observaciones": item.Observaciones,
            "Imagen":        imagen_obj
        })

    # 5. Renderizar y guardar
    doc.render(context)
    doc.save(ruta_salida)

    return ruta_salida