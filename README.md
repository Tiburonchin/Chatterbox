# Chatterbox Upstream API (Production)

Endpoint externo para TTS con Chatterbox usado por Supabase media-gateway.

## Endpoints
- GET /health
- POST /generate

## Deploy rápido (Render)
- Root Directory: .
- Build Command: pip install -r requirements.txt
- Start Command: uvicorn upstream_api:app --host 0.0.0.0 --port 

## Variables de entorno
- UPSTREAM_API_TOKEN
- CHATTERBOX_MODEL=turbo
- CHATTERBOX_DEVICE=cpu
- CHATTERBOX_LANGUAGE=es

## Prueba local
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
set UPSTREAM_API_TOKEN=CHANGE_ME
python -m uvicorn upstream_api:app --host 0.0.0.0 --port 8000
