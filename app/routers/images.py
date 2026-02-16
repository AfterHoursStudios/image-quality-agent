import httpx
import re
import urllib.request
import urllib.error
import ssl
from urllib.parse import urljoin, urlparse
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from pydantic import BaseModel
from app.models.schemas import ImageResponse, ImageListResponse
from app.services import storage, database, vision

router = APIRouter(prefix="/api/images", tags=["images"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class UrlRequest(BaseModel):
    url: str


class UrlImagesResponse(BaseModel):
    images: list[str]
    count: int


class BatchAnalysisResponse(BaseModel):
    results: list[ImageResponse]
    failed: list[dict]


@router.post("/analyze", response_model=ImageResponse)
async def analyze_image(file: UploadFile = File(...)):
    """
    Upload and analyze an image for quality assessment.

    Returns scores for sharpness, lighting, composition, color, exposure,
    faces (if present), and an overall score.
    """
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_CONTENT_TYPES)}"
        )

    # Read and validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)} MB"
        )

    # Upload to Supabase Storage
    try:
        image_id, public_url = await storage.upload_image(
            file_content=content,
            filename=file.filename or "image.jpg",
            content_type=file.content_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")

    try:
        # Analyze with OpenAI Vision
        scores = await vision.analyze_image(public_url)

        # Save to database
        result = await database.save_image_analysis(
            image_id=image_id,
            url=public_url,
            filename=file.filename or "image.jpg",
            scores=scores
        )

        return result

    except Exception as e:
        # Clean up uploaded image on failure
        extension = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
        await storage.delete_image(image_id, extension)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(image_id: str):
    """Retrieve a previously analyzed image's details and scores."""
    result = await database.get_image_analysis(image_id)

    if not result:
        raise HTTPException(status_code=404, detail="Image not found")

    return result


@router.delete("/{image_id}")
async def delete_image(image_id: str):
    """Delete an image and its analysis from storage and database."""
    # Get image details first
    result = await database.get_image_analysis(image_id)

    if not result:
        raise HTTPException(status_code=404, detail="Image not found")

    # Extract extension from URL
    extension = result.url.rsplit(".", 1)[-1] if "." in result.url else "jpg"

    try:
        # Delete from storage
        await storage.delete_image(image_id, extension)
    except Exception:
        pass  # Continue even if storage delete fails

    # Delete from database
    await database.delete_image_analysis(image_id)

    return {"message": "Image deleted successfully", "id": image_id}


@router.post("/delete-batch")
async def delete_images_batch(image_ids: list[str]):
    """Delete multiple images at once."""
    deleted = []
    failed = []

    for image_id in image_ids:
        try:
            result = await database.get_image_analysis(image_id)
            if not result:
                failed.append({"id": image_id, "error": "Not found"})
                continue

            extension = result.url.rsplit(".", 1)[-1] if "." in result.url else "jpg"

            try:
                await storage.delete_image(image_id, extension)
            except Exception:
                pass

            await database.delete_image_analysis(image_id)
            deleted.append(image_id)

        except Exception as e:
            failed.append({"id": image_id, "error": str(e)})

    return {"deleted": deleted, "failed": failed, "count": len(deleted)}


@router.get("", response_model=ImageListResponse)
async def list_images(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page")
):
    """List all analyzed images with pagination."""
    items, total = await database.list_image_analyses(page=page, page_size=page_size)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return ImageListResponse(
        images=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.post("/analyze-batch", response_model=BatchAnalysisResponse)
async def analyze_batch(files: list[UploadFile] = File(...)):
    """
    Upload and analyze multiple images at once.
    Returns results for successful analyses and details of any failures.
    """
    results = []
    failed = []

    for file in files:
        try:
            # Validate content type
            if file.content_type not in ALLOWED_CONTENT_TYPES:
                failed.append({"filename": file.filename, "error": "Invalid file type"})
                continue

            content = await file.read()
            if len(content) > MAX_FILE_SIZE:
                failed.append({"filename": file.filename, "error": "File too large"})
                continue

            # Upload to storage
            image_id, public_url = await storage.upload_image(
                file_content=content,
                filename=file.filename or "image.jpg",
                content_type=file.content_type
            )

            # Analyze with OpenAI
            scores = await vision.analyze_image(public_url)

            # Save to database
            result = await database.save_image_analysis(
                image_id=image_id,
                url=public_url,
                filename=file.filename or "image.jpg",
                scores=scores
            )
            results.append(result)

        except Exception as e:
            failed.append({"filename": file.filename, "error": str(e)})

    return BatchAnalysisResponse(results=results, failed=failed)


def get_browser_headers(url: str = None, for_image: bool = False) -> dict:
    # Simple headers that work with most sites
    headers = {
        "User-Agent": "ImageQualityAnalyzer/1.0 (https://github.com; contact@example.com)",
        "Accept": "*/*",
    }

    if for_image:
        headers["Accept"] = "image/*,*/*"

    # Add referer for domains that require it
    if url:
        parsed = urlparse(url)
        if "wikimedia.org" in parsed.netloc:
            headers["Referer"] = "https://en.wikipedia.org/"
        elif "wikipedia.org" in parsed.netloc:
            headers["Referer"] = "https://en.wikipedia.org/"

    return headers


def get_page_headers() -> dict:
    # For fetching HTML pages
    return {
        "User-Agent": "Mozilla/5.0 (compatible; ImageQualityBot/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }


@router.post("/fetch-from-url", response_model=UrlImagesResponse)
async def fetch_images_from_url(request: UrlRequest):
    """
    Fetch all image URLs from a webpage.
    Returns a list of image URLs found on the page.
    """
    try:
        # Use urllib instead of httpx - more compatible with various sites
        req = urllib.request.Request(
            request.url,
            headers={"User-Agent": "curl/8.0", "Accept": "*/*"}
        )
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
            html = response.read().decode('utf-8', errors='ignore')

        # Find all image URLs
        img_patterns = [
            r'<img[^>]+src=["\']([^"\']+)["\']',
            r'<img[^>]+data-src=["\']([^"\']+)["\']',
            r'<source[^>]+srcset=["\']([^"\']+)["\']',
        ]

        image_urls = set()
        for pattern in img_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                # Handle srcset (take first URL)
                url = match.split(',')[0].split()[0]
                # Make absolute URL
                absolute_url = urljoin(request.url, url)
                # Filter by extension
                parsed = urlparse(absolute_url)
                ext = parsed.path.lower().split('.')[-1] if '.' in parsed.path else ''
                if f".{ext}" in ALLOWED_EXTENSIONS:
                    image_urls.add(absolute_url)

        return UrlImagesResponse(images=list(image_urls), count=len(image_urls))

    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e.reason)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")


def download_image(url: str) -> tuple[bytes, str]:
    """Download an image using urllib. Returns (content, content_type)."""
    parsed = urlparse(url)
    headers = {"User-Agent": "curl/8.0", "Accept": "*/*"}

    # Add referer for Wikimedia
    if "wikimedia.org" in parsed.netloc or "wikipedia.org" in parsed.netloc:
        headers["Referer"] = "https://en.wikipedia.org/"

    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()

    with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
        content = response.read()
        content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]
        return content, content_type


@router.post("/analyze-url", response_model=ImageResponse)
async def analyze_image_url(request: UrlRequest):
    """
    Analyze an image directly from a URL.
    Downloads the image, uploads to storage, and analyzes it.
    """
    try:
        content, content_type = download_image(request.url)

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Image too large")

        if content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid image type: {content_type}")

        parsed = urlparse(request.url)
        filename = parsed.path.split("/")[-1] or "image.jpg"

        # Upload to storage
        image_id, public_url = await storage.upload_image(
            file_content=content,
            filename=filename,
            content_type=content_type
        )

        # Analyze
        scores = await vision.analyze_image(public_url)

        # Save to database
        result = await database.save_image_analysis(
            image_id=image_id,
            url=public_url,
            filename=filename,
            scores=scores
        )

        return result

    except urllib.error.HTTPError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {str(e.reason)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {str(e)}")


@router.post("/analyze-urls", response_model=BatchAnalysisResponse)
async def analyze_multiple_urls(urls: list[str]):
    """
    Analyze multiple images from URLs.
    """
    results = []
    failed = []

    for url in urls:
        try:
            content, content_type = download_image(url)

            if len(content) > MAX_FILE_SIZE:
                failed.append({"url": url, "error": "Image too large"})
                continue

            if content_type not in ALLOWED_CONTENT_TYPES:
                failed.append({"url": url, "error": f"Invalid type: {content_type}"})
                continue

            parsed = urlparse(url)
            filename = parsed.path.split("/")[-1] or "image.jpg"

            image_id, public_url = await storage.upload_image(
                file_content=content,
                filename=filename,
                content_type=content_type
            )

            scores = await vision.analyze_image(public_url)

            result = await database.save_image_analysis(
                image_id=image_id,
                url=public_url,
                filename=filename,
                scores=scores
            )
            results.append(result)

        except Exception as e:
            failed.append({"url": url, "error": str(e)})

    return BatchAnalysisResponse(results=results, failed=failed)
