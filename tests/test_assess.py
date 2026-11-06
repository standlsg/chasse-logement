import json

import httpx

from chasse_logement.ai.assess import RiskAssessment, assess_property
from chasse_logement.ai.signals import MistralClient
from chasse_logement.config import AiConfig
from chasse_logement.store import ListingStore


def ai_cfg() -> AiConfig:
    return AiConfig(provider="mistral", api_key="k", run_risk=True)


def test_assess_parses_and_clamps_risk():
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "scam_risk": 1.4,
                            "reasons": ["paiement avant visite demandé"],
                            "summary": "arnaque probable",
                        }
                    )
                }
            }
        ]
    }
    http = httpx.Client(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
    )
    risk = assess_property(
        "loyer à payer par western union avant visite",
        "leboncoin: prix=500",
        ai_cfg(),
        MistralClient(ai_cfg(), client=http),
    )
    assert risk.scam_risk == 1.0  # clampé
    assert risk.reasons == ["paiement avant visite demandé"]


def test_assess_uses_cache(tmp_path):
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps({"scam_risk": 0.1, "reasons": []})}}]
            },
        )

    http = httpx.Client(transport=httpx.MockTransport(handler))
    client = MistralClient(ai_cfg(), client=http)
    store = ListingStore(tmp_path / "t.db")
    r1 = assess_property("texte", "src: prix=900", ai_cfg(), client, cache=store)
    r2 = assess_property("texte", "src: prix=900", ai_cfg(), client, cache=store)
    assert r1.scam_risk == r2.scam_risk == 0.1
    assert len(calls) == 1
    store.close()


def test_pipeline_adds_ia_redflag(tmp_path, monkeypatch, make_listing):
    from chasse_logement.config import (
        AiConfig,
        AppConfig,
        CommuteConfig,
        Criteria,
        EnrichmentConfig,
        NotifyConfig,
        NotifyEmailConfig,
        SourcesConfig,
    )
    from chasse_logement.models import SourceKind
    from chasse_logement.pipeline import run_once

    class FakeSource:
        name = "fake"
        kind = SourceKind.RSS

        def collect(self):
            return iter([make_listing()])

    class FakeNotifier:
        def __init__(self):
            self.digests = []

        def send_digest(self, subject, results):
            self.digests.append(results)

    cfg = AppConfig(
        database_path=str(tmp_path / "t.db"),
        criteria=Criteria(budget_max=3000, postcodes=["75011"], min_score=0),
        sources=SourcesConfig(),
        notify=NotifyConfig(email=NotifyEmailConfig(enabled=False)),
        enrichment=EnrichmentConfig(geocode=False, poi=False),
        commute=CommuteConfig(enabled=False),
        ai=AiConfig(
            provider="mistral", api_key="k", run_signals=False, run_dedup=False, run_risk=True
        ),
    )
    monkeypatch.setattr("chasse_logement.pipeline.build_sources", lambda c, client: [FakeSource()])
    monkeypatch.setattr(
        "chasse_logement.pipeline.assess_property",
        lambda *a, **k: RiskAssessment(scam_risk=0.9, reasons=["paiement avant visite"]),
    )
    notifier = FakeNotifier()
    run_once(cfg, notifier=notifier, client=object())
    prop = notifier.digests[0][0].listing
    assert any(f.startswith("IA:") for f in prop.red_flags)
