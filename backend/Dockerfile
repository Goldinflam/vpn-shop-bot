FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install shared packages first for better layer caching.
COPY shared/ /app/shared/
COPY xui_client/ /app/xui_client/
COPY backend/ /app/backend/

RUN pip install --no-cache-dir \
        /app/shared \
        /app/xui_client \
        /app/backend

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
