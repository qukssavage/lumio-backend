from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.deps import get_current_user
from app.models.user import User
from app.services.storage import upload_photo

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic"}
MAX_SIZE = 10 * 1024 * 1024  # 10 МБ


@router.post("/photo")
async def upload_photo_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Поддерживаются только изображения (jpg, png, webp, heic)")

    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(400, "Файл слишком большой (макс. 10 МБ)")

    url = await upload_photo(data, file.content_type)
    return {"url": url}
