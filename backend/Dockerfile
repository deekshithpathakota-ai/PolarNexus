FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# ffmpeg/ffprobe: video metadata, thumbnails, key frames and audio. tesseract-ocr: OCR for scanned PDFs.
# Both are optional — without them the pipelines mark those steps as skipped with the reason.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-visual.txt requirements-s3.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Visual semantic search (CLIP via ONNX Runtime). Build with --build-arg WITH_VISUAL=0 to leave it out.
ARG WITH_VISUAL=1
RUN if [ "$WITH_VISUAL" = "1" ]; then pip install --no-cache-dir -r requirements-visual.txt; fi
ENV VISUAL_MODEL_CACHE=/app/.model_cache
COPY app ./app
RUN useradd -m polar && mkdir -p /app/storage /app/.model_cache && chown -R polar /app
USER polar
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
