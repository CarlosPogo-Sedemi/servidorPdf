Paso 1: Encender el Servidor Local
1. Abre tu terminal y navega hasta la carpeta del proyecto:
cd D:\SERVIDOR\servidorPdf

2. Activa el entorno virtual:
venv\Scripts\activate

3. Enciende el servidor FastAPI:
uvicorn main:app --reload

deactivate

Paso 2: Encender el Túnel Público
1. Abre una nueva ventana de terminal. Ejecuta el comando de ngrok apuntando al puerto de tu servidor:
ngrok http 8000