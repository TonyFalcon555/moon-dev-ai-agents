# Moon Dev API Gateway Dockerfile
FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install minimal deps
RUN pip install --no-cache-dir fastapi==0.115.5 uvicorn==0.32.1 requests==2.32.3 python-dotenv==1.0.0

# Copy source
COPY . /app

# Default runtime env
ENV USE_KEYSTORE=1 \
    PORT=8010

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8010/health', timeout=3).status==200 else 1)" || exit 1

# Note: mount a volume to persist keystore.sqlite3 if desired
# VOLUME ["/data"]

CMD ["uvicorn", "src.services.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8010"]
