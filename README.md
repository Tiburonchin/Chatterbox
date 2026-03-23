# Chatterbox Upstream API (Production)

Endpoint externo para TTS con Chatterbox usado por Supabase media-gateway.

## Endpoints
- GET /health
- POST /generate

## Deploy rápido (Render)
- Root Directory: .
- Build Command: pip install -r requirements.txt
- Start Command: uvicorn upstream_api:app --host 0.0.0.0 --port $PORT
- Python Version: 3.11.9

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

## Si falla el deploy en Render
- Revisa que esté usando Python 3.11.9.
- Verifica que el Build Command sea exactamente `pip install -r requirements.txt`.
- Si falla por memoria/tiempo en build, usa plan con más RAM para la fase de instalación de Torch.
