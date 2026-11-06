"""IA-1 : extraction de signaux depuis le texte libre des annonces (provider Mistral).

Exemple : « bureau aménagé à la cave » -> Signals(has_office=True, office_location="cave"),
bien que le champ structuré `rooms` ne le compte pas.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
from pydantic import BaseModel, Field

from .redact import redact

SYSTEM_PROMPT = (
    "Tu es un extracteur de signaux pour des annonces immobilières françaises (location). "
    "Retourne UNIQUEMENT un objet JSON conforme au schéma demandé. Mets null quand l'info "
    "n'est pas mentionnée. Le champ 'evidence' contient les extraits exacts du texte qui "
    "justifient les champs renseignés."
)

SIGNALS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "has_office": {"type": ["boolean", "null"]},
        "office_location": {"type": ["string", "null"]},
        "has_garden": {"type": ["boolean", "null"]},
        "garden_m2": {"type": ["number", "null"]},
        "terrace_m2": {"type": ["number", "null"]},
        "parking_places": {"type": ["integer", "null"]},
        "furnished": {"type": ["boolean", "null"]},
        "charges_included": {"type": ["boolean", "null"]},
        "available_from": {"type": ["string", "null"]},
        "dpe": {"type": ["string", "null"]},
        "pets_allowed": {"type": ["boolean", "null"]},
        "evidence": {"type": "array", "items": {"type": "string"}},
    },
}


class Signals(BaseModel):
    has_office: bool | None = None
    office_location: str | None = None
    has_garden: bool | None = None
    garden_m2: float | None = None
    terrace_m2: float | None = None
    parking_places: int | None = None
    furnished: bool | None = None
    charges_included: bool | None = None
    available_from: str | None = None
    dpe: str | None = None
    pets_allowed: bool | None = None
    evidence: list[str] = Field(default_factory=list)


class MistralClient:
    """Client API Mistral (chat completions, réponse JSON)."""

    def __init__(self, cfg: Any, client: httpx.Client | None = None) -> None:
        self.cfg = cfg
        self._client = client or httpx.Client(timeout=cfg.timeout_s)

    def complete_json(self, system: str, user: str) -> dict:
        resp = self._client.post(
            f"{self.cfg.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.cfg.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.cfg.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)


def extract_signals(
    text: str,
    cfg: Any,
    client: MistralClient | None = None,
    cache: Any = None,
) -> Signals:
    """Extrait les signaux d'un texte d'annonce. provider=off -> Signals vide."""
    if getattr(cfg, "provider", "off") == "off" or not getattr(cfg, "run_signals", True):
        return Signals()
    cleaned = redact(text or "")[:6000]
    if not cleaned.strip():
        return Signals()
    cache_key = "signals:" + hashlib.sha256(cleaned.encode()).hexdigest()
    if cache is not None:
        hit = cache.get_cached("ai_cache", cache_key)
        if hit:
            return Signals.model_validate(json.loads(hit))
    client = client or MistralClient(cfg)
    user = (
        "Texte de l'annonce (données perso déjà redactées) :\n"
        f"{cleaned}\n\nSchéma JSON attendu : {json.dumps(SIGNALS_SCHEMA)}"
    )
    raw = client.complete_json(SYSTEM_PROMPT, user)
    signals = Signals.model_validate(raw)
    if cache is not None:
        cache.set_cached("ai_cache", cache_key, signals.model_dump_json())
    return signals
