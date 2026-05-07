#!/bin/bash
set -e

echo "=== Checking Python imports ==="
python -c "
import sys
print('Python:', sys.version)

print('Testing config...')
from app.config import settings
print('DATABASE_URL prefix:', settings.DATABASE_URL[:40])
print('SECRET_KEY set:', bool(settings.SECRET_KEY))
print('REDIS_URL prefix:', settings.REDIS_URL[:30])
print('Config OK')

print('Testing database engine...')
from app.database import engine
print('Engine OK')

print('Testing routers import...')
from app.routers import auth, chats, users, websocket
print('Routers OK')

print('All imports OK — starting uvicorn')
"

exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
