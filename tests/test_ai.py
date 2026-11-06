import json

import httpx

from chasse_logement.ai.dedup import make_ai_decider
from chasse_logement.ai.redact import redact
from chasse_logement.ai.signals import MistralClient, Signals, extract_signals
from chasse_logement.config import AiConfig
from chasse_logement.merge import cluster
from chasse_logement.models import Listing, SourceKind
from chasse_logement.store import ListingStore


def ai_cfg(**overrides) -> AiConfig:
    base = dict(provider="mistral", api_key="test-key", run_signals=True, run_dedup=True)
    base.update(overrides)
    return AiConfig(**base)


def make_listing(**overrides) -> Listing:
    base = dict(
        source_id="t",
        source_kind=SourceKind.RSS,
        external_id="1",
        url="https://x.fr/1",
        title="Appartement 3 pièces 60 m² 75011 - 1200 €",
        price=1200.0,
        surface_m2=60.0,
        rooms=3,
        postcode="75011",
    )
    base.update(overrides)
    return Listing(**base)


# ---------- redaction ----------


def test_redact_strips_pii():
    text = (
        "Contact : M. Dupont, 06 12 34 56 78, dupont@mail.fr\n"
        "Appelez au 06 12 34 56 78 ou écrivez à dupont@mail.fr"
    )
    out = redact(text)
    assert "06 12 34 56 78" not in out
    assert "dupont@mail.fr" not in out
    assert "[tél]" in out and "[email]" in out and "[contact]" in out


# ---------- IA-1 signaux ----------


def test_extract_signals_parses_json():
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "has_office": True,
                            "office_location": "cave",
                            "has_garden": True,
                            "garden_m2": 300,
                            "parking_places": 2,
                            "evidence": ["bureau aménagé à la cave", "jardin clos de 300 m²"],
                        }
                    )
                }
            }
        ]
    }
    http = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    )
    client = MistralClient(ai_cfg(), client=http)
    sig = extract_signals(
        "Maison T4 avec bureau aménagé à la cave, jardin 300 m², 2 parkings",
        ai_cfg(),
        client=client,
    )
    assert sig.has_office is True
    assert sig.office_location == "cave"
    assert sig.parking_places == 2
    assert sig.evidence


def test_extract_signals_off_returns_empty():
    sig = extract_signals("texte", ai_cfg(provider="off"))
    assert sig == Signals()


def test_extract_signals_uses_cache(tmp_path):
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps({"has_garden": True})}}]}
        )

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = MistralClient(ai_cfg(), client=http)
    store = ListingStore(tmp_path / "t.db")
    s1 = extract_signals("jardin privatif", ai_cfg(), client=client, cache=store)
    s2 = extract_signals("jardin privatif", ai_cfg(), client=client, cache=store)
    assert s1.has_garden is True and s2.has_garden is True
    assert len(calls) == 1  # 2e appel servi par le cache
    store.close()


# ---------- IA-2 dédup ----------


def test_decider_calls_ai_only_on_ambiguous_pairs():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": json.dumps({"same_property": True, "confidence": 0.9})}}
                ]
            },
        )

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = MistralClient(ai_cfg(), client=http)
    decider = make_ai_decider(ai_cfg(), client, cache=None, max_pairs=10)

    a = make_listing(url="https://x/1", title="Villa 5 pièces 120 m² jardin Aix 13100 - 2500 €")
    # même bien, formulation très différente -> paire ambiguë pour l'heuristique
    b = make_listing(
        url="https://y/2",
        title="Maison 5 pièces jardin Aix 13100 garage terrasse 2500 €",
    )
    c = make_listing(url="https://z/3", title="Studio 20 m² Paris 75011 - 800 €", postcode="75011")

    assert decider(a, b) is True  # paire ambiguë -> IA appelée
    assert len(calls) == 1
    assert decider(a, c) is None  # paire claire -> pas d'appel IA
    assert len(calls) == 1


def test_cluster_with_ai_decider_merges():
    a = make_listing(
        url="https://x/1",
        title="Maison 4 chambres Luynes terrasse 2500 €",
        price=2500.0,
        surface_m2=130.0,
        rooms=5,
    )
    # titre très différent mais même bien selon l'IA
    b = make_listing(
        url="https://y/2",
        source_id="seloger",
        price=2520.0,
        surface_m2=131.0,
        rooms=5,
        title="Belle demeure familiale proche centre Luynes avec grand jardin et garage",
    )

    def decider(x, y):
        return True

    groups = cluster([a, b], decider=decider)
    assert len(groups) == 1
    # sans décideur IA, l'heuristique seule les sépare (titres trop différents)
    assert len(cluster([a, b])) == 2
