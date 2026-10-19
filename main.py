from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routers import reportes, vacunas, utils, pasaporte, pdf_formularios, matriz_ast, matriz_geritra

app = FastAPI(title="Servidor Universal de Reportes - SEDEMI")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

app.include_router(reportes.router)
app.include_router(vacunas.router)
app.include_router(utils.router)
app.include_router(pasaporte.router)
app.include_router(matriz_ast.router)
app.include_router(matriz_geritra.router)
app.include_router(pdf_formularios.router)
