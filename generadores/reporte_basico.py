import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def crear_pdf_basico(titulo: str, autor: str, contenido: str) -> str:
    """
    Función que dibuja el PDF usando coordenadas y devuelve la ruta donde se guardó.
    """
    nombre_archivo = f"{titulo.replace(' ', '_')}.pdf"
    ruta_pdf = os.path.join("archivos_salida", nombre_archivo)
    
    # Inicializar el lienzo
    c = canvas.Canvas(ruta_pdf, pagesize=letter)
    
    # Dibujar el contenido
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, f"Título: {titulo}")
    
    c.setFont("Helvetica", 12)
    c.drawString(100, 720, f"Autor: {autor}")
    
    c.drawString(100, 680, "Contenido del Informe:")
    c.drawString(100, 660, contenido)
    
    # Guardar archivo
    c.save()
    
    return ruta_pdf