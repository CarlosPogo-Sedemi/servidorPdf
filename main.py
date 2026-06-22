import os
import shutil
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Importar generadores existentes
from generadores.reporte_basico import crear_pdf_basico
from generadores.reporte_fase3 import crear_pdf_fase3


app = FastAPI(title="Servidor de Reportes PDF Local")

# Crear directorios si no existen
os.makedirs("archivos_entrada", exist_ok=True)
os.makedirs("archivos_salida", exist_ok=True)
os.makedirs("static", exist_ok=True)

# MODELOS DE DATOS PARA LA FASE 3 / GALVANIZADO
class Parametro(BaseModel):
    Value: str

class MetadatosFase3(BaseModel):
    Acabado: str
    Cantidad: str
    Cliente: str
    CorreoResponsable: str
    CorreosDestino: str
    Estado: str
    FechaRegistro: str
    Fig: str
    Kilos: str
    NombreResponsable: str
    Orden: str
    Parametros: List[Parametro]
    Posicion: str
    Sector: str
    UsuarioEmisor: str
    UsuarioResponsable: str

class ItemChecklist(BaseModel):
    Descripcion:    str
    FotoBase64:     Optional[str] = None
    ID_Item:        int
    Observaciones:  str
    Cumple_X:       Optional[str] = ""
    NoCumple_X:     Optional[str] = ""
    FechaRevision:  Optional[str] = ""
    FechaValidacion: Optional[str] = ""

class PayloadFase3(BaseModel):
    Metadatos: MetadatosFase3
    ItemsChecklist: List[ItemChecklist]

# ==========================================
# ENDPOINTS (RUTAS NUEVAS Y DE INTERFAZ)
# ==========================================

# 1. Servir la Consola Web en la Raíz
@app.get("/")
def ruta_raiz():
    """
    Devuelve la pantalla del panel de control web en local de forma directa.
    """
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"mensaje": "Servidor funcionando. Carga los archivos del frontend en la carpeta static."}

# 2. Listar Reportes del Historial
@app.get("/api/reportes")
def listar_reportes():
    """
    Obtiene la lista de todos los PDFs generados en la carpeta archivos_salida/
    """
    ruta = "archivos_salida"
    if not os.path.exists(ruta):
        return []
    
    reportes = []
    for f in os.listdir(ruta):
        if f.endswith(".pdf"):
            path_completo = os.path.join(ruta, f)
            stat = os.stat(path_completo)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M:%S")
            reportes.append({
                "name": f,
                "size": stat.st_size,
                "date": mtime
            })
            
    # Ordenar por fecha de modificación, el más reciente primero
    reportes.sort(key=lambda x: x["date"], reverse=True)
    return reportes

# 3. Eliminar Reporte del Servidor Local
@app.delete("/api/reportes/{filename}")
def eliminar_reporte(filename: str):
    """
    Elimina permanentemente un reporte en archivos_salida/
    """
    filename_limpio = os.path.basename(filename) # Prevenir vulnerabilidades Path Traversal
    path_completo = os.path.join("archivos_salida", filename_limpio)
    
    if os.path.exists(path_completo):
        try:
            os.remove(path_completo)
            return {"mensaje": "Reporte eliminado exitosamente."}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"No se pudo eliminar el archivo: {e}")
            
    raise HTTPException(status_code=404, detail="El archivo no existe.")

# 4. NUEVO ENDPOINT MULTIPART: Generador de Reporte Técnico con CAD e Imágenes
@app.post("/api/generar-pdf-tecnico/")
async def generar_pdf_tecnico(
    titulo: str = Form(...),
    subtitulo: Optional[str] = Form(None),
    autor: str = Form(...),
    descripcion: str = Form(...),
    cad_file: Optional[UploadFile] = File(None),
    imagenes: List[UploadFile] = File([])
):
    """
    Carga múltiples imágenes de inspección, un plano CAD (.dwg/.dxf),
    los guarda temporalmente y genera un reporte técnico PDF completo.
    """
    rutas_imagenes = []
    cad_temporal_path = None
    cad_filename = None
    cad_size = 0
    
    try:
        # Guardar archivo CAD de entrada si se subió
        if cad_file and cad_file.filename:
            cad_filename = cad_file.filename
            extension = os.path.splitext(cad_filename)[1].lower()
            if extension not in [".dwg", ".dxf"]:
                raise HTTPException(status_code=400, detail="Formato CAD no soportado. Sube un archivo .dwg o .dxf.")
                
            cad_temporal_path = os.path.join("archivos_entrada", cad_filename)
            with open(cad_temporal_path, "wb") as buffer:
                shutil.copyfileobj(cad_file.file, buffer)
            
            # Obtener tamaño
            cad_size = os.path.getsize(cad_temporal_path)

        # Guardar imágenes de entrada
        for idx, img in enumerate(imagenes):
            if img.filename:
                # Filtrar extensiones válidas de imagen
                ext = os.path.splitext(img.filename)[1].lower()
                if ext not in [".png", ".jpg", ".jpeg"]:
                    continue
                
                # Nombre único para la imagen guardada localmente
                nombre_img = f"inspeccion_{idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                ruta_img = os.path.join("archivos_entrada", nombre_img)
                
                with open(ruta_img, "wb") as buffer:
                    shutil.copyfileobj(img.file, buffer)
                    
                rutas_imagenes.append(ruta_img)

        # Invocar al generador ReportLab
        ruta_pdf_generado = crear_pdf_dwg_imagenes(
            titulo=titulo,
            subtitulo=subtitulo,
            autor=autor,
            descripcion=descripcion,
            imagenes_rutas=rutas_imagenes,
            cad_filename=cad_filename,
            cad_size_bytes=cad_size,
            cad_temporal_path=cad_temporal_path
        )
        
        filename_pdf = os.path.basename(ruta_pdf_generado)
        return {"mensaje": "Reporte generado con éxito en local.", "filename": filename_pdf}
        
    except Exception as e:
        # Si ocurre un error, logear y levantar HTTP Exception
        print(f"Error procesando reporte técnico: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# RUTAS ANTIGUAS Y COMPATIBILIDAD
# ==========================================

class DatosInformeBasico(BaseModel):
    titulo: str
    autor: str
    contenido: str

@app.post("/generar-pdf/")
def generar_pdf(datos: DatosInformeBasico):
    ruta = crear_pdf_basico(titulo=datos.titulo, autor=datos.autor, contenido=datos.contenido)
    return {"mensaje": "PDF básico generado", "ruta": ruta}

@app.post("/generar-pdf-fase3/")
def generar_pdf_fase3_api(payload: PayloadFase3):
    # La función crear_pdf_fase3 ya te hace el Word maravillosamente
    ruta_pdf_generado = crear_pdf_fase3(payload)
    
    return FileResponse(
        path=ruta_pdf_generado, 
        
        # CAMBIO 1: Dile que es un Word, no un PDF
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
        
        # CAMBIO 2: Ponle la extensión .docx en lugar de .pdf
        filename=f"Reporte_Orden_{payload.Metadatos.Orden}.docx"
    )

# ==========================================
# MONTAJE DE RECURSOS ESTÁTICOS
# ==========================================

# 1. Montar archivos_salida en '/static/archivos_salida' para descarga y previsualización local
app.mount("/static/archivos_salida", StaticFiles(directory="archivos_salida"), name="salidas")

# 2. Montar archivos estáticos del panel visual en '/static'
app.mount("/static", StaticFiles(directory="static"), name="static")

# Montar la carpeta de entrada para que las fotos sean públicas
app.mount("/archivos_entrada", StaticFiles(directory="archivos_entrada"), name="entradas")

# Las que ya tenías:
app.mount("/static/archivos_salida", StaticFiles(directory="archivos_salida"), name="salidas")
app.mount("/static", StaticFiles(directory="static"), name="static")