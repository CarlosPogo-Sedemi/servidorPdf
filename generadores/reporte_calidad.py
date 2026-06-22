# generadores/reporte_calidad.py
from reportlab.pdfgen import canvas
# ... otras librerías ...

def crear_pdf_calidad(payload):
    # Aquí dibujas tu PDF usando los datos del payload
    # Ejemplo:
    c = canvas.Canvas(f"archivos_salida/Calidad_{payload.orden}.pdf")
    c.drawString(100, 700, f"Reporte de Calidad para Orden: {payload.orden}")
    c.drawString(100, 680, f"Temp: {payload.temperatura} C")
    c.save()
    return f"archivos_salida/Calidad_{payload.orden}.pdf"