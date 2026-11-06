from chasse_logement.merge import build_property, cluster, same_property, title_similarity


def test_title_similarity():
    assert (
        title_similarity("Appartement 2 pièces 40 m² 75011", "appartement 2 PIÈCES 40 m² 75011")
        == 1.0
    )
    assert title_similarity("Studio 20m2 centre", "Maison 5 pièces jardin") < 0.3


def test_same_property(make_listing):
    a = make_listing(url="https://a/1", price=900.0)
    b = make_listing(
        url="https://b/2", price=920.0, title="Appartement 2 pièces 40 m² 75011 - 920 €"
    )
    assert same_property(a, b)
    c = make_listing(url="https://c/3", postcode="13001", price=900.0)
    assert not same_property(a, c)


def test_same_property_price_gap_too_big(make_listing):
    a = make_listing(url="https://a/1", price=900.0)
    b = make_listing(url="https://b/2", price=1500.0, title=a.title)
    assert not same_property(a, b)


def test_cluster_and_build_property(make_listing):
    a = make_listing(url="https://a/1", source_id="leboncoin", price=900.0)
    b = make_listing(
        url="https://b/2",
        source_id="seloger",
        price=920.0,
        title="Appartement 2 pièces 40 m² 75011 - 920 €",
    )
    c = make_listing(
        url="https://c/3",
        postcode="13001",
        title="Studio 25 m² 13001 - 700 €",
        price=700.0,
        surface_m2=25.0,
        rooms=1,
    )
    groups = cluster([a, b, c])
    assert len(groups) == 2
    props = [build_property(g) for g in groups]
    merged = next(p for p in props if len(p.sources) == 2)
    assert merged.price == 910.0
    assert {s.source_id for s in merged.sources} == {"leboncoin", "seloger"}
    assert any("prix" in i for i in merged.inconsistencies)
    assert len({p.prop_id for p in props}) == 2
    # stabilité de l'id : rebuild identique
    assert build_property(cluster([a, b, c])[0]).prop_id in {p.prop_id for p in props}
