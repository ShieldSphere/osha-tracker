"""Vercel serverless function entry point."""
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set serverless environment
os.environ["VERCEL"] = "1"

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from mangum import Mangum

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "message": "FastAPI working on Vercel"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

@app.get("/test-imports")
async def test_imports():
    """Test importing the main app components."""
    results = []

    # Test 1: Config
    try:
        from src.config import settings
        results.append({"step": "config", "success": True, "db_url_set": bool(settings.DATABASE_URL)})
    except Exception as e:
        results.append({"step": "config", "success": False, "error": str(e)})
        return JSONResponse(status_code=500, content={"results": results})

    # Test 2: Models
    try:
        from src.database.models import Base, Inspection
        results.append({"step": "models", "success": True})
    except Exception as e:
        results.append({"step": "models", "success": False, "error": str(e)})
        return JSONResponse(status_code=500, content={"results": results})

    # Test 3: Database connection
    try:
        from src.database.connection import engine
        results.append({"step": "connection", "success": True})
    except Exception as e:
        results.append({"step": "connection", "success": False, "error": str(e)})
        return JSONResponse(status_code=500, content={"results": results})

    # Test 4: Main app
    try:
        from src.main import app as main_app
        results.append({"step": "main_app", "success": True})
    except Exception as e:
        results.append({"step": "main_app", "success": False, "error": str(e)})
        return JSONResponse(status_code=500, content={"results": results})

    return {"all_passed": True, "results": results}

# Mangum handler for AWS Lambda/Vercel serverless
handler = Mangum(app, lifespan="off")
