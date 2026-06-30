winget install -e --id Python.Python.3.14

1. Crear el Entorno
python -m venv .venv
python3 -m venv .venv

2. Activa el entorno virtual:
venv\Scripts\activate
source .venv/bin/activate

3. Instalar las librerías
pip install -r requirements.txt

4. Enciende el servidor FastAPI:
uvicorn main:app --reload
fastapi dev main.py
fastapi run main.py --host 0.0.0.0 --port 7052
uvicorn main:app --reload --host 0.0.0.0 --port 7052

5. Desactivar entorno
deactivate