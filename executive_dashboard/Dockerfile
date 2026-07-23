# --- Build stage ---
FROM python:3.11-slim AS builder

WORKDIR /app

COPY executive_dashboard/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Runtime stage ---
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy application code
COPY executive_dashboard/app/ ./app/
COPY executive_dashboard/tools/ ./tools/
COPY mcp_server/ ./mcp_server/

# Create data directory for SQLite
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
