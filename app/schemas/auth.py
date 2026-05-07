from pydantic import BaseModel


class FirebaseTokenIn(BaseModel):
    firebase_token: str  # ID токен от Firebase Auth на клиенте


class RequestOtpIn(BaseModel):
    phone: str  # формат: +998901234567


class VerifyOtpIn(BaseModel):
    phone: str
    code: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_new_user: bool  # True — нужно заполнить профиль (имя, username)


class SetupProfileIn(BaseModel):
    name: str
    username: str | None = None  # опционально — пользователь может пропустить
