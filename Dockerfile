FROM python:3.13-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8080 PYTHONUNBUFFERED=1
ENV MARKMAP_DESK_MODEL=desk
ENV MARKMAP_DISABLE_BEDROCK=1
EXPOSE 8080
CMD ["python", "-m", "markmap"]

