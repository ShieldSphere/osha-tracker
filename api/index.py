"""Vercel serverless function entry point - minimal test."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "message": "Minimal Vercel test working"}

@app.get("/api/health")
async def health():
    return {"status": "healthy"}

@app.get("/test-import")
async def test_import():
    """Test importing the main app step by step."""
    import sys
    import os
    results = {"steps": []}

    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, project_root)
        results["steps"].append({"step": "path_setup", "success": True, "project_root": project_root})
    except Exception as e:
        results["steps"].append({"step": "path_setup", "success": False, "error": str(e)})
        return JSONResponse(status_code=500, content=results)

    try:
        from src.config import settings
        results["steps"].append({"step": "import_config", "success": True})
    except Exception as e:
        results["steps"].append({"step": "import_config", "success": False, "error": str(e)})
        return JSONResponse(status_code=500, content=results)

    try:
        from src.database.models import Base
        results["steps"].append({"step": "import_models", "success": True})
    except Exception as e:
        results["steps"].append({"step": "import_models", "success": False, "error": str(e)})
        return JSONResponse(status_code=500, content=results)

    try:
        from src.database.connection import engine
        results["steps"].append({"step": "import_connection", "success": True})
    except Exception as e:
        results["steps"].append({"step": "import_connection", "success": False, "error": str(e)})
        return JSONResponse(status_code=500, content=results)

    try:
        from src.main import app as main_app
        results["steps"].append({"step": "import_main", "success": True})
    except Exception as e:
        results["steps"].append({"step": "import_main", "success": False, "error": str(e)})
        return JSONResponse(status_code=500, content=results)

    results["all_imports_successful"] = True
    return results

handler = app
