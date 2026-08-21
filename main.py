import base64
from io import BytesIO
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from PIL import Image
import re
from docx import Document
from fastapi.staticfiles import StaticFiles
#from typing import List

app = FastAPI(title="Servidor Universal de Reportes - SEDEMI")

app.mount("/assets", StaticFiles(directory="assets"), name="assets") 

# ==========================================
# MODELO DE ENTRADA GENÉRICO
# ==========================================
class PayloadUniversal(BaseModel):
    template_name: str         
    data: Dict[str, Any]


# ==========================================
# MODELOS PARA COMPRESIÓN DE FOTOS
# ==========================================
class FotoItem(BaseModel):
    NombreArchivo: str
    NovedadFoto: str
    SubirNube: bool

class LoteFotos(BaseModel):
    fotos: List[FotoItem]


# ==========================================
# ENDPOINT DE COMPRESIÓN
# ==========================================
@app.post("/api/v1/comprimir-fotos/")
def comprimir_fotos(payload: LoteFotos):
    fotos_optimizadas = []
    
    for foto in payload.fotos:
        # Solo procesamos si realmente trae foto y hay que subirla
        if foto.SubirNube and foto.NovedadFoto:
            try:
                # 1. Separar la cabecera (data:image/jpeg;base64,) del contenido
                if "base64," in foto.NovedadFoto:
                    b64_data = foto.NovedadFoto.split("base64,")[-1]
                else:
                    b64_data = foto.NovedadFoto
                    
                img_bytes = base64.b64decode(b64_data)
                img = Image.open(BytesIO(img_bytes)).convert("RGB")
                
                # 2. Redimensionar si es gigante (ancho máximo 800px)
                max_width = 800
                if img.width > max_width:
                    wpercent = (max_width / float(img.width))
                    hsize = int((float(img.height) * float(wpercent)))
                    img = img.resize((max_width, hsize), Image.Resampling.LANCZOS)
                
                # 3. Comprimir la calidad
                buffer_optimizado = BytesIO()
                # Guardamos como JPEG con calidad al 60% (Suficiente para reportes)
                img.save(buffer_optimizado, format="JPEG", optimize=True, quality=70)
                
                # 4. Reconstruir el Base64
                nueva_b64 = f"data:image/jpeg;base64,{base64.b64encode(buffer_optimizado.getvalue()).decode()}"
                foto.NovedadFoto = nueva_b64
                
            except Exception as e:
                print(f"Error comprimiendo la foto {foto.NombreArchivo}: {e}")
                # Si falla, devolvemos la original para no romper el flujo
                pass 
                
        fotos_optimizadas.append(foto)
        
    return fotos_optimizadas

# ==========================================
# REPARACIÓN DE TAGS ROTOS (Con el Escudo)
# ==========================================
def reparar_tags_rotos(documento_docx):
    def fusionar_parrafo(p):
        texto_completo = "".join(run.text for run in p.runs)
        
        # EL ESCUDO: Solo entramos si el párrafo contiene "{%" y "tr"
        # Esto deja tranquilas a variables normales como {{ Metadatos.Fig }}
        if "{%" in texto_completo and "tr" in texto_completo:
            
            # TU SOLUCIÓN: Quitamos el espacio y forzamos el {%tr junto
            texto_corregido = texto_completo.replace("{% tr", "{%tr").replace("{%  tr", "{%tr")
            
            if len(p.runs) > 0:
                p.runs[0].text = texto_corregido
                for run in p.runs[1:]:
                    run.text = ""

    for p in documento_docx.paragraphs:
        fusionar_parrafo(p)
    for tabla in documento_docx.tables:
        for fila in tabla.rows:
            for celda in fila.cells:
                for p in celda.paragraphs:
                    fusionar_parrafo(p)

# ==========================================
# MAGIA: ESCANER DE IMÁGENES Y LIMPIEZA DE NULOS
# ==========================================
def procesar_datos_rec(sub_contexto, doc):
    if isinstance(sub_contexto, dict):
        for k, v in list(sub_contexto.items()):
            # 1. Limpiar Nulos 
            if v is None:
                sub_contexto[k] = ""
            
            # 2. Procesar Imágenes
            elif isinstance(v, str) and ("base64," in v or v.startswith("data:image")):
                try:
                    foto_str = v.split("base64,")[-1]
                    img_bytes_raw = base64.b64decode(foto_str)

                    pil_img = Image.open(BytesIO(img_bytes_raw)).convert("RGB")
                    buffer_corregido = BytesIO()
                    pil_img.save(buffer_corregido, format="JPEG", dpi=(96, 96))
                    buffer_corregido.seek(0)

                    # 🚀 AQUÍ ESTÁ EL CAMBIO
                    if k == "FotoPerfil":
                        # Le damos 30mm (3cm) de ancho y 40mm (4cm) de alto
                        # Nota: Si la foto original es muy cuadrada, forzar el alto a 40mm podría deformarla un poco. 
                        # Si se ve estirada, quítale el parámetro height=Mm(40) y deja que Word calcule el alto solo.
                        sub_contexto[k] = InlineImage(doc, buffer_corregido, width=Mm(30), height=Mm(40))
                    else:
                        # Para el resto de imágenes del servidor (como las de inspección) se mantiene 5cm
                        sub_contexto[k] = InlineImage(doc, buffer_corregido, width=Mm(50))
                        
                except Exception as e:
                    print(f"No se pudo procesar la imagen en '{k}': {e}")
                    sub_contexto[k] = ""
            else:
                procesar_datos_rec(v, doc)
                
    elif isinstance(sub_contexto, list):
        for i in range(len(sub_contexto)):
            if sub_contexto[i] is None:
                sub_contexto[i] = ""
            else:
                procesar_datos_rec(sub_contexto[i], doc)

# ==========================================
# ENDPOINT UNIVERSAL
# ==========================================
@app.post("/api/v1/generar-reporte/")
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

        nombre_descarga = f"Reporte_{payload.template_name}.docx"
        return StreamingResponse(
            file_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{nombre_descarga}"'}
        )

    except Exception as e:
        print(f"Error crítico en el servidor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# ENDPOINT PARA MANTENER DESPIERTO (PING)
# ==========================================
@app.get("/api/v1/ping/")
def ping_server():
    return {"status": "ok", "message": "Servidor de reportes despierto y listo."}




# ==========================================
# MODELOS PARA EL PDF DE VACUNACIÓN
# ==========================================
class PacienteInfo(BaseModel):
    institucion: str = ""
    ruc: str = ""
    ciiu: str = ""
    establecimiento_salud: str = ""
    historia_clinica: str = ""
    numero_archivo: str = ""
    primer_apellido: str = ""
    segundo_apellido: str = ""
    primer_nombre: str = ""
    segundo_nombre: str = ""
    sexo: str = ""
    cargo: str = ""

class PayloadVacunacion(BaseModel):
    paciente: PacienteInfo
    vacunas: List[Dict[str, Any]] # Aquí recibiremos el array JSON que me mostraste

# ==========================================
# ENDPOINT PARA PDF DE VACUNACIÓN (HTML a PDF)
# ==========================================
@app.post("/api/v1/generar-pdf-vacunas/")
def generar_pdf_vacunas(payload: PayloadVacunacion):
    try:
        html_rows = ""
        # Recorremos el JSON de vacunas
        for vac in payload.vacunas:
            doses = []
            
            # Validamos si existe la primera dosis general (La del padre)
            if vac.get('FechaPrimeraDosis'):
                doses.append({
                    'dosis': '1°',
                    'fecha': vac.get('FechaPrimeraDosis', ''),
                    'lote': vac.get('lote1', ''),
                    'responsable': vac.get('Responsable1', ''),
                    'establecimiento': vac.get('Establecimiento1', ''),
                    'observacion': vac.get('Observacion1', '')
                })
            
            # Recorremos la Lista de Actividades (Dosis hijas/Refuerzos)
            for act in vac.get('ListaActividades', []):
                # Limpiamos el texto "Dosis X" para que solo quede "X°"
                num_dosis = act.get('NumeroDosis', '')
                if 'Dosis' in num_dosis:
                    num_dosis = num_dosis.replace('Dosis ', '') + '°'
                
                # Determinamos la fecha a usar
                fecha = act.get('FechaReal') or act.get('FechaTentativa') or ''
                
                doses.append({
                    'dosis': num_dosis,
                    'fecha': fecha,
                    'lote': act.get('Lote', ''),
                    'responsable': act.get('ResponsableVacuna', ''),
                    'establecimiento': act.get('Establecimiento', ''),
                    'observacion': act.get('Observacion', '')
                })
            
            # Si por algún motivo la vacuna no tiene dosis, ponemos una fila vacía
            if not doses:
                doses.append({'dosis': '1°', 'fecha': '', 'lote': '', 'responsable': '', 'establecimiento': '', 'observacion': ''})

            rowspan = len(doses)
            
            # Generamos las filas de la tabla combinando la primera columna con rowspan
            for i, dose in enumerate(doses):
                html_rows += "<tr>\n"
                if i == 0:
                    html_rows += f'<td rowspan="{rowspan}" class="vacuna-col">{vac.get("NombreVacuna", "")}</td>\n'
                
                html_rows += f'<td>{dose["dosis"]}</td>\n'
                html_rows += f'<td>{dose["fecha"].replace("-", "/")}</td>\n'
                html_rows += f'<td>{dose["lote"]}</td>\n'
                html_rows += f'<td></td>\n' # Columna Esquema Completo vacía para marcar a mano
                html_rows += f'<td>{dose["responsable"]}</td>\n'
                html_rows += f'<td>{dose["establecimiento"]}</td>\n'
                html_rows += f'<td>{dose["observacion"]}</td>\n'
                html_rows += "</tr>\n"

        # Armamos el HTML completo inyectando los datos del paciente y las filas
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 landscape; margin: 15mm; background-color: #ffffff; }}
            body {{ font-family: 'Open Sans', 'Arial', sans-serif; font-size: 10px; margin: 0; padding: 0; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 2px; }}
            th, td {{ border: 1px solid #7a8a8f; padding: 6px; text-align: center; vertical-align: middle; }}
            th {{ background-color: #d9ead3; font-weight: bold; color: #000; }}
            .section-title {{ 
                background-color: #ccccff; text-align: left; font-size: 13px; 
                font-weight: bold; padding: 4px; border: 1px solid #7a8a8f; 
                border-bottom: none; margin-top: 15px;
            }}
            .vacuna-col {{ background-color: #e0ffff; font-weight: normal; }}
            .blank-row td {{ height: 18px; }}
        </style>
        </head>
        <body>
        <table>
            <tr>
                <th>INSTITUCIÓN DEL SISTEMA O NOMBRE DE LA EMPRESA</th>
                <th>RUC</th>
                <th>CIIU</th>
                <th>ESTABLECIMIENTO DE SALUD</th>
                <th>NÚMERO DE HISTORIA CLÍNICA</th>
                <th>NÚMERO DE ARCHIVO</th>
            </tr>
            <tr class="blank-row">
                <td>{payload.paciente.institucion}</td>
                <td>{payload.paciente.ruc}</td>
                <td>{payload.paciente.ciiu}</td>
                <td>{payload.paciente.establecimiento_salud}</td>
                <td>{payload.paciente.historia_clinica}</td>
                <td>{payload.paciente.numero_archivo}</td>
            </tr>
        </table>
        <table>
            <tr>
                <th>PRIMER APELLIDO</th>
                <th>SEGUNDO APELLIDO</th>
                <th>PRIMER NOMBRE</th>
                <th>SEGUNDO NOMBRE</th>
                <th>SEXO</th>
                <th>CARGO / OCUPACIÓN</th>
            </tr>
            <tr class="blank-row">
                <td>{payload.paciente.primer_apellido}</td>
                <td>{payload.paciente.segundo_apellido}</td>
                <td>{payload.paciente.primer_nombre}</td>
                <td>{payload.paciente.segundo_nombre}</td>
                <td>{payload.paciente.sexo}</td>
                <td>{payload.paciente.cargo}</td>
            </tr>
        </table>
        <div class="section-title">B. INMUNIZACIONES</div>
        <table>
            <tr>
                <th style="width: 15%;">VACUNAS</th>
                <th style="width: 5%;">DOSIS</th>
                <th style="width: 10%;">FECHA<br><span style="font-size:8px; font-weight:normal;">( aaaa / mm / dd )</span></th>
                <th style="width: 10%;">LOTE</th>
                <th style="width: 10%;">ESQUEMA<br>COMPLETO<br><span style="font-size:8px; font-weight:normal;">(marcar X)</span></th>
                <th style="width: 20%;">NOMBRES COMPLETOS DEL<br>RESPONSABLE DE LA<br>VACUNACIÓN</th>
                <th style="width: 15%;">ESTABLECIMIENTO DE<br>SALUD DONDE SE<br>COLOCÓ LA VACUNA.</th>
                <th style="width: 15%;">OBSERVACIONES</th>
            </tr>
            {html_rows}
        </table>
        </body>
        </html>
        """

        # Generamos el PDF directamente en memoria
        pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()
        
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