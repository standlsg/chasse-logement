from chasse_logement.sources.parsing import (
    extract_listing_urls,
    extract_postcode,
    extract_price,
    extract_rooms,
    extract_surface,
    strip_tags,
)


def test_extract_price():
    assert extract_price("Appartement - 1 250 €/mois") == 1250.0
    assert extract_price("Loyer 850€ CC") == 850.0
    assert extract_price("prix sur demande") is None


def test_extract_surface():
    assert extract_surface("45 m² lumineux") == 45.0
    assert extract_surface("surface 120m2") == 120.0
    assert extract_surface("sans surface") is None


def test_extract_rooms():
    assert extract_rooms("3 pièces") == 3
    assert extract_rooms("bel appartement T2") == 2
    assert extract_rooms("studio F1") == 1
    assert extract_rooms("rien") is None


def test_extract_postcode():
    assert extract_postcode("Paris 11e (75011)") == "75011"
    assert extract_postcode("Montreuil 93100") == "93100"
    assert extract_postcode("pas de code") is None


def test_extract_listing_urls():
    html = '<a href="https://www.leboncoin.fr/annonces/123.html">Voir</a>'
    urls = extract_listing_urls(html)
    assert urls == ["https://www.leboncoin.fr/annonces/123.html"]


def test_strip_tags():
    assert strip_tags("<p>Bonjour <b>ici</b></p>") == " Bonjour  ici  "
    assert strip_tags(None) == ""
