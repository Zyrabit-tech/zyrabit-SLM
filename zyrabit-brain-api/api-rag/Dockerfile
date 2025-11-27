# Usa una imagen oficial de Python ligera
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /

# Instala las dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código de tu API
COPY ./app /app

# Comando para correr el servidor
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]