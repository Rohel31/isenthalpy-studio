FROM python:3.11-slim

# Crear usuario seguro UID 1000 requerido por las políticas de Hugging Face Spaces
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Instalar dependencias
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copiar el código fuente y recursos estáticos
COPY --chown=user . .

# Hugging Face Spaces expone el puerto 7860 por defecto
EXPOSE 7860

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "2"]
