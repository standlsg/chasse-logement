from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from chasse_logement.web.app import create_app


def write_config(tmp_path: Path, imap_enabled: bool = True) -> str:
    cfg = {
        "database_path": str(tmp_path / "data" / "test.db"),
        "sources": {
            "imap": {
                "enabled": imap_enabled,
                "host": "imap.example.com",
                "user": "u",
                "password": "secret",
                "portals": ["leboncoin"],
            },
            "rss_feeds": [
                {"name": "agence-x", "url": "https://agence-x.fr/rss.xml", "enabled": True}
            ],
            "api": {"enabled": False},
        },
        "criteria": {
            "budget_max": 1000,
            "min_surface_m2": 30,
            "min_rooms": 2,
            "postcodes": ["75011"],
            "min_score": 50,
        },
        "notify": {
            "mode": "digest",
            "email": {"enabled": True, "to_addrs": ["old@example.com"]},
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return str(path)


@pytest.fixture
def client(tmp_path):
    path = write_config(tmp_path)
    app = create_app(path, run_scheduler=False)
    return TestClient(app), path


def test_index(client):
    c, _ = client
    r = c.get("/")
    assert r.status_code == 200
    assert "annonces vues" in r.text


def test_parametres_get(client):
    c, _ = client
    r = c.get("/parametres")
    assert r.status_code == 200
    assert "budget_max" in r.text
    assert "leboncoin" in r.text
    assert "agence-x" in r.text
    assert "old@example.com" in r.text
    assert "secret" not in r.text  # jamais de secret affiché


def test_parametres_post_updates_config_and_preserves_secret(client):
    c, path = client
    r = c.post(
        "/parametres",
        data={
            "budget_max": "1500",
            "min_surface_m2": "35",
            "min_rooms": "2",
            "postcodes": "75011 75020",
            "cities": "",
            "furnished": "any",
            "exclude_keywords": "",
            "min_score": "60",
            "portals": ["leboncoin", "seloger"],
            "api_enabled": "1",
            "email_to": "a@b.fr\nc@d.fr",
            "notify_mode": "instant",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    assert raw["criteria"]["budget_max"] == 1500
    assert raw["criteria"]["postcodes"] == ["75011", "75020"]
    assert raw["sources"]["imap"]["portals"] == ["leboncoin", "seloger"]
    assert raw["sources"]["imap"]["password"] == "secret"
    assert raw["sources"]["api"]["enabled"] is True
    assert raw["notify"]["email"]["to_addrs"] == ["a@b.fr", "c@d.fr"]
    assert raw["notify"]["mode"] == "instant"


def test_feed_add_update_delete(client):
    c, path = client
    r = c.post(
        "/parametres/feed/add",
        data={"name": "agence-y", "url": "https://y.fr/rss"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    assert len(raw["sources"]["rss_feeds"]) == 2

    c.post(
        "/parametres/feed/update",
        data={"idx": "1", "name": "agence-y", "url": "https://y.fr/rss", "enabled": ["0"]},
        follow_redirects=False,
    )
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    assert raw["sources"]["rss_feeds"][1]["enabled"] is False

    c.post("/parametres/feed/delete", data={"idx": "0"}, follow_redirects=False)
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    assert len(raw["sources"]["rss_feeds"]) == 1
    assert raw["sources"]["rss_feeds"][0]["name"] == "agence-y"


def test_run_button(tmp_path):
    path = write_config(tmp_path, imap_enabled=False)
    app = create_app(path, run_scheduler=False)
    c = TestClient(app)
    r = c.post("/run", follow_redirects=False)
    assert r.status_code == 303
