from __future__ import annotations

import time
from urllib.parse import urlsplit

import httpx

from .robots import RobotsChecker


class PoliteClient:
    """Client HTTP poli : UA honnête, robots.txt respecté, rate limit par hôte.

    Ne contourne jamais aucune protection technique (CAPTCHA, auth, blocage IP) :
    une réponse >= 400 ou un robots.txt défavorable = on ne fetch pas.
    """

    def __init__(
        self,
        user_agent: str = "chasse-logement/0.1 (+https://github.com/standlsg/chasse-logement)",
        min_interval_s: float = 2.0,
        respect_robots: bool = True,
        timeout_s: float = 20.0,
        robots: RobotsChecker | None = None,
    ) -> None:
        self.user_agent = user_agent
        self.min_interval_s = min_interval_s
        self.respect_robots = respect_robots
        self.robots = robots or RobotsChecker()
        self._client = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=timeout_s,
            follow_redirects=True,
        )
        self._last_fetch: dict[str, float] = {}

    def get(self, url: str) -> httpx.Response | None:
        host = urlsplit(url).netloc
        if self.respect_robots and not self.robots.allowed(url, self.user_agent):
            return None
        now = time.monotonic()
        wait = self.min_interval_s - (now - self._last_fetch.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        self._last_fetch[host] = time.monotonic()
        try:
            resp = self._client.get(url)
        except httpx.HTTPError:
            return None
        if resp.status_code >= 400:
            return None
        return resp

    def get_text(self, url: str) -> str | None:
        resp = self.get(url)
        return resp.text if resp is not None else None

    def close(self) -> None:
        self._client.close()
