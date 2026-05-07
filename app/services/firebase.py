import json
import os

import firebase_admin
from firebase_admin import auth, credentials

from app.config import settings

_app = None


def init_firebase():
    global _app
    if _app:
        return
    raw = settings.FIREBASE_CREDENTIALS_JSON
    if not raw:
        return
    # поддерживаем и JSON-строку (Render), и путь к файлу (локально)
    try:
        cred_dict = json.loads(raw)
        cred = credentials.Certificate(cred_dict)
    except (json.JSONDecodeError, ValueError):
        if os.path.exists(raw):
            cred = credentials.Certificate(raw)
        else:
            return
    _app = firebase_admin.initialize_app(cred)


def verify_firebase_token(id_token: str) -> dict:
    """Верифицирует Firebase ID токен, возвращает decoded token."""
    try:
        decoded = auth.verify_id_token(id_token)
        return decoded
    except Exception as e:
        raise ValueError(f"Невалидный Firebase токен: {e}")
