"""FastAPI entrypoint — STUB.

This file will be fleshed out by the backend agent. The stub exists so
that `uvicorn backend.main:app` can start and return a 200 on /health
even before full implementation.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="vpn-shop-backend", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
