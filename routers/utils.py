from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["utils"])

@router.get("/ping/")
def ping_server():
    return {"status": "ok", "message": "Servidor de reportes despierto y listo."}