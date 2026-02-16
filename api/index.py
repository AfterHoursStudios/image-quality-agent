"""Vercel serverless entry point for the FastAPI application."""
import sys
from pathlib import Path

# Add parent directory to path so 'app' module can be found
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app

# Vercel expects 'app' or 'handler' to be exported
handler = app
