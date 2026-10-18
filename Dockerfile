FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=10000

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente y recursos estáticos
COPY . .

EXPOSE 10000

CMD sh -c "uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"
