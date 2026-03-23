#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import os
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request

app = Flask(__name__)

API_TOKEN = (os.getenv("UPSTREAM_API_TOKEN") or "").strip()
DEFAULT_MODEL = (os.getenv("CHATTERBOX_MODEL") or "turbo").strip()
DEFAULT_DEVICE = (os.getenv("CHATTERBOX_DEVICE") or "cpu").strip()
DEFAULT_LANGUAGE = (os.getenv("CHATTERBOX_LANGUAGE") or "es").strip()

def _ensure_auth(authorization: Optional[str]) -> tuple[bool, Optional[tuple[dict, int]]]:
    if not API_TOKEN:
        return True, None

    if not authorization or not authorization.lower().startswith("bearer "):
        return False, ({"ok": False, "error": "Unauthorized"}, 401)

    token = authorization.split(" ", 1)[1].strip()
    if token != API_TOKEN:
        return False, ({"ok": False, "error": "Unauthorized"}, 401)

    return True, None


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
    return jsonify({"ok": True, "service": "chatterbox-upstream", "status": "up"})


@app.post("/generate")
def generate():
    authorized, error_response = _ensure_auth(request.headers.get("Authorization"))
    if not authorized and error_response:
        payload, status = error_response
        return jsonify(payload), status

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "text es requerido"}), 422
    if len(text) > 5000:
        text = text[:5000]

    language_id = str(payload.get("language_id") or DEFAULT_LANGUAGE).strip() or DEFAULT_LANGUAGE
    model_name = str(payload.get("model") or DEFAULT_MODEL).strip() or DEFAULT_MODEL

    try:
        from chatterbox_service import ChatterboxTTSService

        service = ChatterboxTTSService(model=model_name, device=DEFAULT_DEVICE)
        result = service.synthesize(
            text=text,
            language_id=language_id,
            reference_audio=None,
            exaggeration=0.5,
            cfg_weight=0.5,
        )

        if not result.get("success"):
            return jsonify({"ok": False, "error": result.get("error") or "TTS failed"}), 400

        audio_b64 = _read_as_data_uri(result["file_path"])

        return jsonify({
            "ok": True,
            "provider": "chatterbox_upstream",
            "audio_b64": audio_b64,
            "meta": {
                "model": result.get("model"),
                "language": result.get("language"),
                "duration": result.get("duration"),
                "hash": result.get("hash"),
            },
        })

    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
