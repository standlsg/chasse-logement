"""Extraction d'attributs depuis le texte libre des annonces (titres, emails, RSS).

Heuristiques simples (regex) : suffisantes pour le MVP, à affiner avec des exemples
réels de tes zones.
"""

from __future__ import annotations

import re

PRICE_RE = re.compile(r"(\d[\d\s ]*)\s*€", re.IGNORECASE)
SURFACE_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*m[²2]", re.IGNORECASE)
ROOMS_PIECES_RE = re.compile(r"(\d+)\s*pi[èe]ces", re.IGNORECASE)
ROOMS_TF_RE = re.compile(r"\b[TF](\d+)\b")
POSTCODE_RE = re.compile(r"(?<![\d])(\d{5})(?![\d])")
URL_RE = re.compile(r"https?://[^\s<>\"'()\]]+", re.IGNORECASE)


def _to_float(digits: str) -> float:
    return float(digits.replace(" ", "").replace(" ", "").replace(",", "."))


def extract_price(text: str | None) -> float | None:
    m = PRICE_RE.search(text or "")
    return _to_float(m.group(1)) if m else None


def extract_surface(text: str | None) -> float | None:
    m = SURFACE_RE.search(text or "")
    return _to_float(m.group(1)) if m else None


def extract_rooms(text: str | None) -> int | None:
    text = text or ""
    m = ROOMS_PIECES_RE.search(text)
    if m:
        return int(m.group(1))
    m = ROOMS_TF_RE.search(text)
    if m:
        return int(m.group(1))
    return None


def extract_postcode(text: str | None) -> str | None:
    m = POSTCODE_RE.search(text or "")
    return m.group(1) if m else None


def extract_listing_urls(text: str | None) -> list[str]:
    return URL_RE.findall(text or "")


def strip_tags(html: str | None) -> str:
    if not html:
        return ""
    return re.sub(r"<[^>]+>", " ", html)
