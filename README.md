# Image Quality Assessment Agent

AI-powered image quality analysis service using OpenAI Vision API.

## Features

- Upload images for automatic quality assessment
- Scores on multiple criteria (sharpness, lighting, composition, color, exposure, faces)
- Stores images in Supabase Storage
- Persists analysis results in Supabase PostgreSQL
- RESTful API with FastAPI

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase anon/service key
- `SUPABASE_BUCKET`: Storage bucket name (default: "images")

### 3. Supabase Setup

Create a storage bucket named "images" (or your chosen name) with public access.

Create the database table:

```sql
CREATE TABLE image_analyses (
    id UUID PRIMARY KEY,
    url TEXT NOT NULL,
    filename TEXT NOT NULL,
    scores JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4. Run the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Endpoints

### POST /api/images/analyze

Upload and analyze an image.

```bash
curl -X POST -F "file=@image.jpg" http://localhost:8000/api/images/analyze
```

### GET /api/images/{id}

Retrieve analysis results for a specific image.

```bash
curl http://localhost:8000/api/images/{image_id}
```

### GET /api/images

List all analyzed images with pagination.

```bash
curl "http://localhost:8000/api/images?page=1&page_size=10"
```

### GET /health

Health check endpoint.

## Scoring Criteria

| Criterion | Description |
|-----------|-------------|
| sharpness | Focus and clarity of the image |
| lighting | Quality and balance of lighting |
| composition | Framing, rule of thirds, balance |
| color | Color accuracy, white balance, saturation |
| exposure | Proper exposure, no blown highlights/crushed blacks |
| faces | Face quality if present (null if no faces) |
| overall | Weighted average of all applicable scores |

Each score is on a 1-10 scale with a brief explanation.

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
