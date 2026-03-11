from sqlmodel import select

from app.db.models import WatchlistItem
from app.db.repositories.watchlist_repository import WatchlistRepository


def test_add_returns_existing_item_for_duplicate_security(session, seeded_security):
    repository = WatchlistRepository(session)

    first_item = repository.add(seeded_security.id)
    second_item = repository.add(seeded_security.id)

    assert second_item.id == first_item.id
    assert second_item.security_id == seeded_security.id

    rows = session.exec(select(WatchlistItem)).all()
    assert len(rows) == 1
    assert repository.list_ids() == [seeded_security.id]


def test_remove_by_security_id_deletes_item_and_list_ids_becomes_empty(session, seeded_security):
    repository = WatchlistRepository(session)

    repository.add(seeded_security.id)

    removed = repository.remove_by_security_id(seeded_security.id)

    assert removed is True
    assert repository.list_ids() == []
    assert session.exec(select(WatchlistItem)).all() == []
