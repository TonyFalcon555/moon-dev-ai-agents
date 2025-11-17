# Moon Dev Backtest Dashboard Dockerfile
FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Dependencies for backtest dashboard and RBI runs
RUN pip install --no-cache-dir \
    fastapi==0.115.5 \
    uvicorn==0.32.1 \
    requests==2.32.3 \
    python-dotenv==1.0.0 \
    pandas==2.2.3 \
    numpy==2.1.3 \
    apscheduler==3.10.4 \
    websockets==12.0 \
    jinja2==3.1.4 \
    python-multipart==0.0.9

# Copy source code
COPY . /app

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8002/', timeout=3).status==200 else 1)" || exit 1

CMD ["uvicorn", "src.scripts.backtestdashboard:app", "--host", "0.0.0.0", "--port", "8002"]
