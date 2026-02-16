from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
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

# Static files directory
static_dir = Path(__file__).parent / "static"


@app.get("/")
async def serve_frontend():
    """Serve the frontend application."""
    return FileResponse(static_dir / "index.html")


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
