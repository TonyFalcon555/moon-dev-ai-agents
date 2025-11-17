# Moon Dev Billing Service Dockerfile
FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Minimal dependencies for billing
RUN pip install --no-cache-dir fastapi==0.115.5 uvicorn==0.32.1 stripe==13.1.0

# Copy source code
COPY . /app

# Default runtime env
ENV PORT=8011

EXPOSE 8011

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8011/health', timeout=3).status==200 else 1)" || exit 1

CMD ["uvicorn", "src.services.billing.main:app", "--host", "0.0.0.0", "--port", "8011"]
