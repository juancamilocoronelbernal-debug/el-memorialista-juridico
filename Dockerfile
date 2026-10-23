FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000 PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
ARG WITH_LOCAL_BROWSER=0
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng poppler-utils \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-browser.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements-browser.txt -c constraints.txt
# Browserbase usa la biblioteca de Playwright sin descargar Chromium local.
# Para navegación local: docker build --build-arg WITH_LOCAL_BROWSER=1 ...
RUN if [ "$WITH_LOCAL_BROWSER" = "1" ]; then \
      python -m playwright install --with-deps chromium && chmod -R a+rX /opt/playwright; \
    fi
COPY . .
RUN useradd --create-home --uid 10001 memorialista && chown -R memorialista:memorialista /app
USER memorialista
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --no-proxy-headers --host 0.0.0.0 --port ${PORT:-8000}"]
