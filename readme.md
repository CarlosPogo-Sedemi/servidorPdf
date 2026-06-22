Paso 1: Encender el Servidor Local
python -m venv .venv

winget install -e --id Python.Python.3.14

pip install -r requirements.txt

1. Activa el entorno virtual:
venv\Scripts\activate

2. Enciende el servidor FastAPI:
uvicorn main:app --reload

fastapi dev main.py