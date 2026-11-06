from chasse_logement.models import SourceKind
from chasse_logement.sources.imap_alerts import detect_portal, parse_alert_email, portal_allowed


def test_detect_portal():
    assert detect_portal("alertes@leboncoin.fr", "Nouvelle annonce") == "leboncoin"
    assert detect_portal("noreply@seloger.com", "x") == "seloger"
    assert detect_portal("noreply@gensdeconfiance.com", "x") == "gensdeconfiance"
    assert detect_portal("noreply@appartager.com", "x") == "appartager"
    assert detect_portal("alerts@studapart.com", "x") == "studapart"
    assert detect_portal("contact@agence-x.fr", "x") == "portail"


def test_parse_alert_email(sample_email):
    listing = parse_alert_email(sample_email)
    assert listing is not None
    assert listing.source_kind == SourceKind.IMAP_ALERT
    assert listing.source_id == "leboncoin"
    assert "2 pièces 45 m²" in listing.title
    assert listing.price == 950.0
    assert listing.surface_m2 == 45.0
    assert listing.rooms == 2
    assert listing.url == "https://www.leboncoin.fr/annonces/123456789.html?utm_source=alert"
    assert listing.external_id == "<abc123@leboncoin.fr>"


def test_parse_alert_email_empty():
    raw = b"From: x@y.fr\nSubject:\n\n"
    assert parse_alert_email(raw) is None


def test_portal_allowed():
    assert portal_allowed([], "leboncoin")
    assert portal_allowed(None, "pap")
    assert portal_allowed(["leboncoin"], "leboncoin")
    assert not portal_allowed(["leboncoin"], "seloger")
