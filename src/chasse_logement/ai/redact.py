"""Redaction des données personnelles avant tout appel à une API externe (IA).

On ne envoie jamais de téléphone/email d'annonceur à l'API Mistral.
"""

from __future__ import annotations

import re

PHONE_RE = re.compile(r"(?:\+33|0)\s?[1-9](?:[\s.\-]?\d{2}){4}")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
CONTACT_LINE_RE = re.compile(
    r"(?im)^\s*(contact|t[ée]l\.?phone|t[ée]l|tel|email|e-?mail|mail|appel[ez]?-?moi)\s*[:.]?\s*.*$"
)


def redact(text: str) -> str:
    text = EMAIL_RE.sub("[email]", text)
    text = PHONE_RE.sub("[tél]", text)
    text = CONTACT_LINE_RE.sub("[contact]", text)
    return text
