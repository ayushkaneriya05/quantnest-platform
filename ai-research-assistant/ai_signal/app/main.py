# ai-research-assistant/ai_signal/app/main.py
"""Entrypoint for the FastAPI app."""
from fastapi import FastAPI
from .api import router
import uvicorn
import os

app = FastAPI()
app.include_router(router)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("ai_signal.app.main:app", host="127.0.0.1", port=port, reload=True)
