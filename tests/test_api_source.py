import httpx

from chasse_logement.config import ApiAggregatorConfig, Criteria
from chasse_logement.pipeline import build_sources
from chasse_logement.sources.api import ApiAggregatorSource, listing_from_api_item

RealClient = httpx.Client


def api_cfg(**overrides) -> ApiAggregatorConfig:
    base = dict(
        enabled=True,
        base_url="https://api.moteurimmo.fr",
        api_key="cle-test",
        path="/api/v1/annonces",
        items_path="annonces",
    )
    base.update(overrides)
    return ApiAggregatorConfig(**base)


def criteria() -> Criteria:
    return Criteria(budget_max=2800, min_surface_m2=80, min_rooms=4, postcodes=["13100", "13008"])


def test_listing_from_api_item_tolerant_mapping():
    item = {
        "titre": "Villa T6 Les Milles jardin 300 m² 2500 €",
        "prix": "2500",
        "surfaceM2": 123,
        "nb_pieces": 6,
        "code_postal": "13290",
        "ville": "Aix-en-Provence",
        "lien": "https://moteurimmo.fr/annonce/42",
        "reference": "MIM-42",
        "date_publication": "2026-11-05T10:00:00Z",
        "photos": [{"url": "https://cdn.example/p1.jpg"}, "https://cdn.example/p2.jpg"],
    }
    lst = listing_from_api_item(item, "api.moteurimmo.fr")
    assert lst.title.startswith("Villa T6")
    assert lst.price == 2500.0
    assert lst.surface_m2 == 123.0
    assert lst.rooms == 6
    assert lst.postcode == "13290"
    assert lst.city == "Aix-en-Provence"
    assert lst.url == "https://moteurimmo.fr/annonce/42"
    assert lst.external_id == "MIM-42"
    assert lst.published_at is not None and lst.published_at.year == 2026
    assert lst.photos == ["https://cdn.example/p1.jpg", "https://cdn.example/p2.jpg"]
    assert lst.source_id == "api.moteurimmo.fr"


def test_source_builds_params_and_sends_auth(monkeypatch):
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured["url"] = str(req.url)
        captured["headers"] = dict(req.headers)
        return httpx.Response(
            200,
            json={
                "annonces": [
                    {
                        "id": "1",
                        "titre": "Maison 5 pièces 13100 - 2500 €",
                        "prix": 2500,
                        "surface_m2": 120,
                        "nb_pieces": 5,
                        "code_postal": "13100",
                        "lien": "https://x/1",
                    }
                ]
            },
        )

    import chasse_logement.sources.api as api_mod

    monkeypatch.setattr(
        api_mod.httpx,
        "Client",
        lambda **kw: RealClient(transport=httpx.MockTransport(handler), **kw),
    )

    src = ApiAggregatorSource(api_cfg(), criteria())
    listings = list(src.collect())
    assert len(listings) == 1
    assert listings[0].price == 2500.0
    assert captured["headers"].get("x-api-key") == "cle-test"
    assert "prix_max=2800" in captured["url"]
    assert "nb_pieces_min=4" in captured["url"]
    assert "surface_min=80" in captured["url"]
    assert "code_postal=13100%2C13008" in captured["url"] or "13100,13008" in captured["url"]
    assert "type=location" in captured["url"]


def test_source_disabled_or_http_error_yields_nothing(monkeypatch):
    import chasse_logement.sources.api as api_mod

    monkeypatch.setattr(
        api_mod.httpx,
        "Client",
        lambda **kw: RealClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(403)), **kw
        ),
    )
    src = ApiAggregatorSource(api_cfg(), criteria())
    assert list(src.collect()) == []
    src_off = ApiAggregatorSource(api_cfg(enabled=False), criteria())
    assert list(src_off.collect()) == []


def test_build_sources_includes_api_when_enabled():
    from chasse_logement.config import AppConfig, SourcesConfig

    cfg = AppConfig(sources=SourcesConfig(api=api_cfg()))
    sources = build_sources(cfg, client=object())
    assert any(getattr(s, "kind", None) == "api" for s in sources)

    cfg_off = AppConfig(sources=SourcesConfig(api=api_cfg(enabled=False)))
    assert not any(
        getattr(s, "kind", None) == "api" for s in build_sources(cfg_off, client=object())
    )
