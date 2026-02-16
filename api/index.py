"""Vercel serverless entry point for the FastAPI application."""
import sys
from pathlib import Path

# Add parent directory to path so 'app' module can be found
sys.path.insert(0, str(Path(__file__).parent.parent))

from mangum import Mangum
from app.main import app

# Wrap FastAPI with Mangum for serverless compatibility
handler = Mangum(app, lifespan="off")
