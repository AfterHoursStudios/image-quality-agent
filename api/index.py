"""Vercel serverless entry point for the FastAPI application."""
from app.main import app

# Export the FastAPI app for Vercel's Python runtime
# Vercel will automatically detect this as an ASGI application
