# API image. Build:  docker build -t doc-intel-api .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt .
# build-essential is only needed while installing; removed afterwards to keep the image small
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && pip install --no-cache-dir -r requirements.txt \
 && apt-get purge -y build-essential \
 && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

COPY app ./app
COPY scripts ./scripts
COPY data/pdfs ./data/pdfs

# run as a normal user, not root
RUN useradd -m appuser \
 && mkdir -p /code/data/chroma /code/logs \
 && chown -R appuser /code
USER appuser

EXPOSE 8000

# Render / Railway give the port in $PORT; locally it defaults to 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
  CMD python -c "import os,urllib.request; urllib.request.urlopen('http://localhost:%s/health' % os.getenv('PORT','8000'))" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
