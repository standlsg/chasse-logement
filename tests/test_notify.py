from chasse_logement.matching import MatchResult
from chasse_logement.merge import build_property
from chasse_logement.notify import build_digest_html, build_digest_text


def test_digest_property_lists_all_source_links(make_listing):
    a = make_listing(url="https://leboncoin.fr/a", source_id="leboncoin", price=900.0)
    b = make_listing(
        url="https://www.seloger.com/b",
        source_id="seloger",
        price=920.0,
        title="Appartement 2 pièces 40 m² 75011 - 920 €",
    )
    prop = build_property([a, b])
    res = MatchResult(listing=prop, score=80.0, reasons=[])
    text = build_digest_text([res])
    assert "https://leboncoin.fr/a" in text
    assert "https://www.seloger.com/b" in text
    assert "leboncoin" in text and "seloger" in text
    html = build_digest_html([res])
    assert "leboncoin" in html and "seloger" in html


def test_digest_property_shows_red_flags(make_listing):
    from chasse_logement.models import Property

    prop = build_property([make_listing()])
    prop.red_flags = ["formulation suspecte : « western union »"]
    res = MatchResult(listing=prop, score=60.0, reasons=[])
    assert "⚠" in build_digest_text([res])
    assert "western union" in build_digest_html([res])
    assert isinstance(prop, Property)
