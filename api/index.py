"""Vercel serverless function entry point."""
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set serverless environment before any app imports
os.environ["VERCEL"] = "1"

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "message": "FastAPI on Vercel - with path setup"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

@app.get("/test-config")
async def test_config():
    """Test importing config."""
    try:
        from src.config import settings
        return {
            "success": True,
            "db_url_exists": bool(settings.DATABASE_URL),
            "db_url_preview": settings.DATABASE_URL[:30] + "..." if settings.DATABASE_URL else None
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.get("/test-db")
async def test_db():
    """Test database connection."""
    try:
        from src.database.connection import engine, get_db_session
        from sqlalchemy import text

        with get_db_session() as db:
            result = db.execute(text("SELECT 1")).scalar()
            return {"success": True, "db_test": result}
    except Exception as e:
        import traceback
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })
