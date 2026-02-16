from datetime import datetime
from typing import Optional
from supabase import create_client, Client
from app.config import get_settings
from app.models.schemas import ImageScores, ImageResponse, ImageListItem


def get_supabase_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)


async def save_image_analysis(
    image_id: str,
    url: str,
    filename: str,
    scores: ImageScores
) -> ImageResponse:
    """Save image analysis results to the database."""
    client = get_supabase_client()

    now = datetime.utcnow()

    record = {
        "id": image_id,
        "url": url,
        "filename": filename,
        "scores": scores.model_dump(),
        "created_at": now.isoformat()
    }

    client.table("image_analyses").insert(record).execute()

    return ImageResponse(
        id=image_id,
        url=url,
        filename=filename,
        scores=scores,
        created_at=now
    )


async def get_image_analysis(image_id: str) -> Optional[ImageResponse]:
    """Retrieve an image analysis by ID."""
    client = get_supabase_client()

    result = client.table("image_analyses").select("*").eq("id", image_id).execute()

    if not result.data:
        return None

    record = result.data[0]
    return ImageResponse(
        id=record["id"],
        url=record["url"],
        filename=record["filename"],
        scores=ImageScores(**record["scores"]),
        created_at=datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))
    )


async def list_image_analyses(page: int = 1, page_size: int = 10) -> tuple[list[ImageListItem], int]:
    """List image analyses with pagination."""
    client = get_supabase_client()

    # Get total count
    count_result = client.table("image_analyses").select("id", count="exact").execute()
    total = count_result.count or 0

    # Get paginated results
    offset = (page - 1) * page_size
    result = (
        client.table("image_analyses")
        .select("id, url, filename, scores, created_at")
        .order("created_at", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )

    items = []
    for record in result.data:
        scores = ImageScores(**record["scores"])
        items.append(ImageListItem(
            id=record["id"],
            url=record["url"],
            filename=record["filename"],
            overall_score=scores.overall.score,
            created_at=datetime.fromisoformat(record["created_at"].replace("Z", "+00:00"))
        ))

    return items, total


async def delete_image_analysis(image_id: str) -> None:
    """Delete an image analysis from the database."""
    client = get_supabase_client()
    client.table("image_analyses").delete().eq("id", image_id).execute()
