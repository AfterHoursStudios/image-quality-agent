from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pathlib import Path
from app.routers import images
import os

app = FastAPI(
    title="Image Quality Assessment Agent",
    description="AI-powered image quality analysis service using OpenAI Vision",
    version="1.0.0"
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return JSON errors instead of HTML error pages."""
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__}
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(images.router)

# Static files directory - check public/ first (Vercel), then app/static/ (local)
project_root = Path(__file__).parent.parent
public_dir = project_root / "public"
static_dir = Path(__file__).parent / "static"


@app.get("/")
async def serve_frontend():
    """Serve the frontend application."""
    # Check public/ first (Vercel deployment)
    if (public_dir / "index.html").exists():
        return FileResponse(public_dir / "index.html")
    # Fall back to app/static/ (local development)
    if (static_dir / "index.html").exists():
        return FileResponse(static_dir / "index.html")
    # If neither exists, redirect to static path
    return RedirectResponse("/index.html", status_code=307)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check if required env vars are set
    env_status = {
        "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
        "SUPABASE_URL": bool(os.environ.get("SUPABASE_URL")),
        "SUPABASE_KEY": bool(os.environ.get("SUPABASE_KEY")),
    }
    all_configured = all(env_status.values())
    return {
        "status": "healthy" if all_configured else "missing_config",
        "env_vars": env_status
    }
