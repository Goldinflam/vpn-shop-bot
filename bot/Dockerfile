FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY shared/ /app/shared/
COPY bot/ /app/bot/

RUN pip install --no-cache-dir \
        /app/shared \
        /app/bot

CMD ["python", "-m", "bot"]
