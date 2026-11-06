from chasse_logement.models import Property, SourceRef
from chasse_logement.redflags import red_flags


def make_prop(**overrides) -> Property:
    base = dict(
        prop_id="p1",
        title="Appartement 2 pièces 75011",
        price=900.0,
        surface_m2=40.0,
        postcode="75011",
        sources=[SourceRef(source_id="leboncoin", url="https://x/1")],
    )
    base.update(overrides)
    return Property(**base)


def test_scam_keyword_flagged():
    p = make_prop(description="Paiement avant la visite par western union svp")
    flags = red_flags(p, [25.0])
    assert any("western union" in f for f in flags)


def test_price_way_below_market_flagged():
    p = make_prop(price=400.0, surface_m2=40.0)  # 10 €/m² vs marché ~25 €/m²
    flags = red_flags(p, [25.0, 26.0, 24.0])
    assert any("arnaque" in f for f in flags)


def test_inconsistency_flagged():
    p = make_prop(inconsistencies=["prix : de 900 € à 1200 € selon les sources"])
    flags = red_flags(p, [])
    assert any("incohérence" in f for f in flags)


def test_clean_property_no_flags():
    p = make_prop()
    assert red_flags(p, [22.5]) == []
