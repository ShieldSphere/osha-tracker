"""Vercel serverless function entry point."""
import sys
import os

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the FastAPI app
from src.main import app

# Vercel expects 'app' or 'handler' at module level
handler = app
