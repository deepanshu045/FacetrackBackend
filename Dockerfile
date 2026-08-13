FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir dlib-bin==20.0.1 \
    && pip install --no-cache-dir -r requirements.txt

# Install face-recognition without allowing pip to install dlib
RUN pip install --no-cache-dir --no-deps face-recognition==1.3.0

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:${PORT:-8000}"]