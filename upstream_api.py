#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from chatterbox_service import ChatterboxTTSService


app = FastAPI(title="Chatterbox Upstream API", version="1.0.0")

API_TOKEN = (os.getenv("UPSTREAM_API_TOKEN") or "").strip()
DEFAULT_MODEL = (os.getenv("CHATTERBOX_MODEL") or "turbo").strip()
DEFAULT_DEVICE = (os.getenv("CHATTERBOX_DEVICE") or "cpu").strip()
DEFAULT_LANGUAGE = (os.getenv("CHATTERBOX_LANGUAGE") or "es").strip()


class GenerateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    language_id: str = Field(default=DEFAULT_LANGUAGE)
    voice_id: Optional[str] = None
    model: Optional[str] = None
    display_name: Optional[str] = None


def _ensure_auth(authorization: Optional[str]) -> None:
    if not API_TOKEN:
        return

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = authorization.split(" ", 1)[1].strip()
    if token != API_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _read_as_data_uri(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Audio no encontrado: {path}")

    data = p.read_bytes()
    mime = "audio/wav"
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{b64}"


@app.get("/health")
def health():
    return {"ok": True, "service": "chatterbox-upstream", "status": "up"}


@app.post("/generate")
def generate(payload: GenerateRequest, authorization: Optional[str] = Header(default=None)):
    _ensure_auth(authorization)

    model_name = (payload.model or DEFAULT_MODEL).strip() or DEFAULT_MODEL

    try:
        service = ChatterboxTTSService(model=model_name, device=DEFAULT_DEVICE)
        result = service.synthesize(
            text=payload.text,
            language_id=(payload.language_id or DEFAULT_LANGUAGE).strip() or DEFAULT_LANGUAGE,
            reference_audio=None,
            exaggeration=0.5,
            cfg_weight=0.5,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error") or "TTS failed")

        audio_b64 = _read_as_data_uri(result["file_path"])

        return {
            "ok": True,
            "provider": "chatterbox_upstream",
            "audio_b64": audio_b64,
            "meta": {
                "model": result.get("model"),
                "language": result.get("language"),
                "duration": result.get("duration"),
                "hash": result.get("hash"),
            },
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
