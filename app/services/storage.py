import uuid
from supabase import create_client, Client
from app.config import get_settings


def get_supabase_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)


async def upload_image(file_content: bytes, filename: str, content_type: str) -> tuple[str, str]:
    """
    Upload an image to Supabase Storage.

    Returns:
        tuple[str, str]: (image_id, public_url)
    """
    settings = get_settings()
    client = get_supabase_client()

    image_id = str(uuid.uuid4())
    extension = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    storage_path = f"{image_id}.{extension}"

    client.storage.from_(settings.supabase_bucket).upload(
        path=storage_path,
        file=file_content,
        file_options={"content-type": content_type}
    )

    public_url = client.storage.from_(settings.supabase_bucket).get_public_url(storage_path)

    return image_id, public_url


async def delete_image(image_id: str, extension: str = "jpg") -> None:
    """Delete an image from Supabase Storage."""
    settings = get_settings()
    client = get_supabase_client()
    storage_path = f"{image_id}.{extension}"

    client.storage.from_(settings.supabase_bucket).remove([storage_path])
