from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.routers import images

app = FastAPI(
    title="Image Quality Assessment Agent",
    description="AI-powered image quality analysis service using OpenAI Vision",
    version="1.0.0"
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
    return {"status": "healthy"}
