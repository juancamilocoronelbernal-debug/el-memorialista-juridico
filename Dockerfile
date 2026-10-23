FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt
COPY . .
RUN useradd --create-home --uid 10001 memorialista && chown -R memorialista:memorialista /app
USER memorialista
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --no-proxy-headers --host 0.0.0.0 --port ${PORT:-8000}"]
