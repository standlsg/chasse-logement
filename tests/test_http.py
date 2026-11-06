"""Tests de la couche récolte HTTP : client « poli » (robots.txt, rate-limit, pas de retry)."""

import httpx

from chasse_logement.http import PoliteClient
from chasse_logement.robots import RobotsChecker

ROBOTS = "User-agent: *\nDisallow: /prive\n"


def make_client(handler, robots_text=ROBOTS, **kwargs):
    kwargs.setdefault("min_interval_s", 0.0)
    robots = RobotsChecker(fetch=lambda url: robots_text if url.endswith("robots.txt") else None)
    client = PoliteClient(robots=robots, **kwargs)
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_get_respects_robots_and_skips_http():
    calls = []

    def handler(req):
        calls.append(str(req.url))
        return httpx.Response(200, text="ok")

    client = make_client(handler)
    assert client.get("https://example.com/prive/x") is None
    assert calls == []  # aucun appel HTTP si robots.txt interdit
    assert client.get_text("https://example.com/public") == "ok"
    assert calls == ["https://example.com/public"]


def test_get_returns_none_on_http_error():
    client = make_client(lambda req: httpx.Response(404), robots_text=None)
    assert client.get("https://example.com/404") is None


def test_get_returns_none_on_exception():
    def handler(req):
        raise httpx.ConnectError("boom")

    client = make_client(handler, robots_text=None)
    assert client.get("https://down.example/") is None


def test_rate_limit_per_host(monkeypatch):
    sleeps = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))
    client = make_client(lambda req: httpx.Response(200, text="ok"), min_interval_s=5.0)
    client.get("https://a.example/1")
    client.get("https://a.example/2")  # même hôte -> attend
    client.get("https://b.example/1")  # autre hôte -> pas d'attente
    assert len(sleeps) == 1 and sleeps[0] > 0


def test_no_robots_txt_allows_all():
    client = make_client(lambda req: httpx.Response(200, text="ok"), robots_text=None)
    assert client.get_text("https://no-robots.example/anything") == "ok"
