from app.db.repositories.stock_detail_repository import StockDetailRepository



def test_get_by_security_id_returns_empty_sections_when_detail_data_is_missing(session, seeded_security):
    repository = StockDetailRepository(session)

    detail = repository.get_by_security_id(seeded_security.id)

    assert detail is not None
    assert detail.security.id == seeded_security.id
    assert detail.security.code == "000001"
    assert detail.security.name == "Ping An Bank"
    assert detail.price_context == []
    assert detail.announcements == []
    assert detail.news == []
