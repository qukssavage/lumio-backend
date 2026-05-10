import asyncio
import uuid

from supabase import create_client

from app.config import settings

_client = None


def _get_client():
    global _client
    if not _client:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return _client


def _do_upload(file_bytes: bytes, content_type: str) -> str:
    ext = content_type.split("/")[-1].replace("jpeg", "jpg")
    filename = f"photos/{uuid.uuid4()}.{ext}"
    client = _get_client()
    client.storage.from_(settings.SUPABASE_BUCKET).upload(
        path=filename,
        file=file_bytes,
        file_options={"content-type": content_type},
    )
    return client.storage.from_(settings.SUPABASE_BUCKET).get_public_url(filename)


async def upload_photo(file_bytes: bytes, content_type: str) -> str:
    return await asyncio.to_thread(_do_upload, file_bytes, content_type)
