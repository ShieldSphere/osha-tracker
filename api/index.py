"""Vercel serverless function entry point."""
import sys
import os

# Ensure the project root is in the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set VERCEL env var if not already set (Vercel should set this automatically)
os.environ.setdefault("VERCEL", "1")

try:
    # Import the FastAPI app
    from src.main import app
    handler = app
except Exception as e:
    # If import fails, create a minimal app that shows the error
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import traceback

    error_app = FastAPI()
    error_msg = f"{type(e).__name__}: {str(e)}"
    error_tb = traceback.format_exc()

    @error_app.get("/{path:path}")
    async def catch_all(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": error_msg,
                "traceback": error_tb,
                "python_path": sys.path,
                "project_root": project_root,
                "cwd": os.getcwd(),
            }
        )

    app = error_app
    handler = error_app
