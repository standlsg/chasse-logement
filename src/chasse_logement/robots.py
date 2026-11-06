from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser


def _default_fetch(url: str) -> str | None:
    import httpx

    try:
        r = httpx.get(url, timeout=10.0, follow_redirects=True)
    except httpx.HTTPError:
        return None
    if r.status_code >= 400:
        return None
    return r.text


class RobotsChecker:
    """Vérifie robots.txt par hôte (avec cache). Un robots.txt absent = tout autorisé."""

    def __init__(self, fetch: Callable[[str], str | None] | None = None) -> None:
        self._fetch = fetch or _default_fetch
        self._cache: dict[str, RobotFileParser] = {}

    def _parser_for(self, url: str) -> RobotFileParser:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self._cache:
            rp = RobotFileParser()
            rp.set_url(f"{origin}/robots.txt")
            content = self._fetch(rp.url)
            rp.parse(content.splitlines() if content else [])
            self._cache[origin] = rp
        return self._cache[origin]

    def allowed(self, url: str, user_agent: str = "*") -> bool:
        return bool(self._parser_for(url).can_fetch(user_agent, url))


def robots_summary(
    url: str, user_agent: str = "*", fetch: Callable[[str], str | None] | None = None
) -> dict[str, Any]:
    checker = RobotsChecker(fetch=fetch)
    return {"url": url, "user_agent": user_agent, "allowed": checker.allowed(url, user_agent)}
