from chasse_logement.sources.catalog import CATALOGS, apply_catalog


def test_catalog_aix_marseille_contents():
    reg = CATALOGS["aix-marseille"]
    assert "13001" in reg["postcodes"] and "13100" in reg["postcodes"]
    assert "gensdeconfiance" in reg["portals"]
    assert any("CROUS" in m["name"] for m in reg["manual"])
    assert any("Orpi" in a["name"] for a in reg["agencies"])


def test_apply_catalog_merges_without_duplicates():
    raw = {
        "sources": {"imap": {"portals": ["leboncoin"]}, "rss_feeds": []},
        "criteria": {"postcodes": ["75011"]},
    }
    out = apply_catalog(raw, "aix-marseille", apply_postcodes=True)
    portals = out["sources"]["imap"]["portals"]
    assert "leboncoin" in portals and "studapart" in portals
    assert portals.count("leboncoin") == 1
    cps = out["criteria"]["postcodes"]
    assert "75011" in cps and "13100" in cps and cps.count("13100") == 1


def test_apply_catalog_without_postcodes():
    raw = {"criteria": {"postcodes": ["75011"]}}
    out = apply_catalog(raw, "aix-marseille", apply_postcodes=False)
    assert out["criteria"]["postcodes"] == ["75011"]
    assert "gensdeconfiance" in out["sources"]["imap"]["portals"]
