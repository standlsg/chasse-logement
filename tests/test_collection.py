"""Tests de la couche récolte : parsing (cas limites), RSS (flux cassés, entrées partielles),
IMAP (multipart, texte seul, sans lien)."""

from chasse_logement.sources.parsing import (
    extract_listing_urls,
    extract_postcode,
    extract_price,
    extract_rooms,
    extract_surface,
)
from chasse_logement.sources.rss import RssSource, listing_from_entry

# ---------- parsing : cas limites ----------


def test_price_formats():
    assert extract_price("1 250,50 €/mois") == 1250.50
    assert extract_price("1250€") == 1250.0
    assert extract_price("Loyer : 980 € CC") == 980.0
    assert extract_price("sans prix") is None


def test_surface_formats():
    assert extract_surface("42,5 m2") == 42.5
    assert extract_surface("120 m²") == 120.0
    assert extract_surface("rien") is None


def test_rooms_formats():
    assert extract_rooms("T3") == 3
    assert extract_rooms("appartement F2") == 2
    assert extract_rooms("4 pièces + bureau") == 4
    assert extract_rooms("rien ici") is None


def test_postcode_ignores_phone_numbers():
    assert extract_postcode("Appel 0612345678, Paris 75011") == "75011"
    assert extract_postcode("13008 Marseille 8e") == "13008"


def test_listing_urls_strip_trailing_punctuation():
    urls = extract_listing_urls('<a href="https://x.fr/a/1?utm=mail">lien</a>, fin.')
    assert urls == ["https://x.fr/a/1?utm=mail"]


# ---------- RSS ----------


class FakeHttpClient:
    def __init__(self, text_by_url):
        self._texts = text_by_url
        self.robots = type("R", (), {"allowed": lambda self, url, ua="*": True})()
        self.user_agent = "test"

    def get_text(self, url):
        return self._texts.get(url)


def test_rss_source_collect_parses_entries(sample_rss):
    client = FakeHttpClient({"https://agence-test.fr/rss.xml": sample_rss})
    src = RssSource("Agence Test", "https://agence-test.fr/rss.xml", client=client)
    listings = list(src.collect())
    assert len(listings) == 1
    lst = listings[0]
    assert lst.price == 950.0 and lst.surface_m2 == 45.0 and lst.rooms == 2
    assert lst.postcode == "75011"
    assert lst.source_id == "agence-test.fr"


def test_rss_source_broken_feed_yields_nothing():
    client = FakeHttpClient({"https://bad.fr/rss.xml": "<html>404 page</html>"})
    src = RssSource("Bad", "https://bad.fr/rss.xml", client=client)
    assert list(src.collect()) == []


def test_rss_source_missing_feed_yields_nothing():
    client = FakeHttpClient({})
    src = RssSource("None", "https://none.fr/rss.xml", client=client)
    assert list(src.collect()) == []


def test_listing_from_entry_without_link():
    entry = {"title": "Studio 25 m² 13008 - 700 €", "description": "proche métro"}
    lst = listing_from_entry(entry, source_id="x.fr", feed_name="X")
    assert lst.url == ""
    assert lst.external_id == lst.title  # repli sur le titre
    assert lst.postcode == "13008" and lst.price == 700.0


# ---------- IMAP ----------


def test_parse_alert_email_multipart():
    body = "Bonjour, une annonce : 2 pièces 50 m² Marseille 13008, 1100 €".encode()
    raw = (
        b"From: alertes@seloger.com\r\n"
        b"Subject: =?UTF-8?Q?Nouvelle_annonce_-_2_pi=C3=A8ces_13008_-_1100_=E2=82=AC?=\r\n"
        b"Message-ID: <m1@seloger>\r\n"
        b'Content-Type: multipart/alternative; boundary="BB"\r\n'
        b'\r\n--BB\r\nContent-Type: text/plain; charset="utf-8"\r\n\r\n'
        + body
        + b'\r\n--BB\r\nContent-Type: text/html; charset="utf-8"\r\n\r\n'
        + b'<a href="https://www.seloger.com/annonces/99.html">Voir</a>'
        + b"\r\n--BB--\r\n"
    )
    from chasse_logement.sources.imap_alerts import parse_alert_email

    listing = parse_alert_email(raw)
    assert listing is not None
    assert listing.source_id == "seloger"
    assert listing.price == 1100.0
    assert listing.surface_m2 == 50.0
    assert listing.url == "https://www.seloger.com/annonces/99.html"


def test_parse_alert_email_plain_text_without_link():
    raw = (
        b"From: noreply@pap.fr\nSubject: Nouvelle annonce PAP - Studio 13001 - 750 EUR\n"
        b"Content-Type: text/plain\n\nStudio 28 m2 centre Aix, 750 euros, dispo janvier.\n"
    )
    from chasse_logement.sources.imap_alerts import parse_alert_email

    listing = parse_alert_email(raw)
    assert listing is not None
    assert listing.source_id == "pap"
    assert listing.url == ""
    assert listing.postcode == "13001"
    assert listing.rooms is None or listing.rooms >= 1
