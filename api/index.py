"""Vercel serverless function entry point."""
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Set serverless environment before any app imports
os.environ["VERCEL"] = "1"

# Import the main FastAPI app
from src.main import app
