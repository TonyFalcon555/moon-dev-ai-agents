# Moon Dev Alerts Service Dockerfile
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Minimal dependencies for alerts service (also used by www and docs)
RUN pip install --no-cache-dir \
    fastapi==0.115.5 \
    uvicorn==0.32.1 \
    apscheduler==3.10.4 \
    requests==2.32.3 \
    python-dotenv==1.0.0 \
    pandas==2.2.3 \
    numpy==2.1.3 \
    jinja2==3.1.4 \
    aiofiles==24.1.0

# Copy source code
COPY . /app

# Default runtime env
ENV ALERTS_PORT=8012

EXPOSE 8012

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8012/health', timeout=3).status==200 else 1)" || exit 1

CMD ["uvicorn", "src.services.alerts.main:app", "--host", "0.0.0.0", "--port", "8012"]
