"""Détection de flux RSS sur un site d'agence (robots.txt respecté)."""

from __future__ import annotations

from .http import PoliteClient

RSS_PATHS = (
    "/rss.xml",
    "/feed",
    "/feed.xml",
    "/rss",
    "/atom.xml",
    "/index.xml",
    "/annonces/rss.xml",
    "/annonces/rss",
    "/annonces/feed",
    "/biens/rss.xml",
)


def looks_like_feed(text: str) -> bool:
    head = text[:600].lower()
    return "<rss" in head or "<feed" in head or "<atom" in head


def discover_rss(base_url: str, client: PoliteClient | None = None) -> list[str]:
    """Retourne les URLs de flux RSS trouvées sur le site (liste vide si aucun)."""
    client = client or PoliteClient()
    base = base_url.rstrip("/")
    found: list[str] = []
    for path in RSS_PATHS:
        url = base + path
        if not client.robots.allowed(url, client.user_agent):
            continue
        text = client.get_text(url)
        if text and looks_like_feed(text):
            found.append(url)
    return found
