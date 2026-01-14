"""Vercel serverless function entry point."""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "message": "FastAPI on Vercel"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}
