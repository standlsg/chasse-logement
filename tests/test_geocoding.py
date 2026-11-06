from chasse_logement.geocoding import Geocoder, address_query
from chasse_logement.store import ListingStore

GEOJSON = {
    "features": [
        {
            "geometry": {"coordinates": [4.835, 43.296]},
            "properties": {
                "label": "12 rue de la République, 13001 Marseille",
                "score": 0.92,
                "type": "housenumber",
            },
        }
    ]
}


def test_geocode_parse_and_cache(tmp_path):
    store = ListingStore(tmp_path / "t.db")
    calls = []

    def fetch(query):
        calls.append(query)
        return GEOJSON

    geocoder = Geocoder(fetch=fetch, cache=store)
    r = geocoder.geocode("12 rue de la République, 13001 Marseille")
    assert r is not None
    assert r.latitude == 43.296 and r.longitude == 4.835
    assert r.precision == "housenumber"
    assert r.label.startswith("12 rue de la République")
    geocoder.geocode("12 rue de la République, 13001 Marseille")
    assert len(calls) == 1  # deuxième appel servi par le cache
    store.close()


def test_geocode_no_result():
    geocoder = Geocoder(fetch=lambda q: {"features": []})
    assert geocoder.geocode("nulle part") is None
    assert geocoder.geocode("") is None


def test_address_query_prefers_street_address(make_listing):
    listing = make_listing(description="Situé au 12 rue de la République, 13001 Marseille")
    assert "rue de la République" in address_query(listing)


def test_address_query_fallback_postcode(make_listing):
    listing = make_listing(description="", title="")
    assert address_query(listing) == "75011"
