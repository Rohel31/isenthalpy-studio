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

# Descarga directa del libro de Çengel desde Google Drive
RUN python -c "import urllib.request, os; os.makedirs('Libros', exist_ok=True); print('Descargando Cengel...'); urllib.request.urlretrieve('https://drive.google.com/uc?export=download&id=1Jh0_EANQT-1Ini689YV4uppXuvuLjtAs', 'Libros/Cengel Yunus, Boles Michael - TERMODINAMICA (Spanish Edition)-McGraw-Hill Interamericana de España S.L. (2015).pdf'); print('Descarga completa!')"

EXPOSE 10000

CMD sh -c "uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"
