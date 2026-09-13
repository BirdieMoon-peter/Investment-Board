from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.models import Holding, InvestmentAdviceCache, Security
from app.db.repositories.holdings_repository import HoldingsRepository
from app.db.repositories.investment_advice_cache_repository import InvestmentAdviceCacheRepository


def add_holding(session, security):
    return HoldingsRepository(session).upsert_by_security_id(
        security_id=security.id,
        quantity=Decimal("100"),
        average_cost=Decimal("10"),
        notes="Original position",
        target_horizon="long_term",
    )


def add_advice(session, security, *, holding_id=None, target_id=None, target_type="holding"):
    return InvestmentAdviceCacheRepository(session).create(
        InvestmentAdviceCache(
            target_type=target_type,
            target_id=target_id if target_id is not None else holding_id,
            security_id=security.id,
            holding_id=holding_id,
            target_market=security.market,
            target_code=security.code,
            target_name=security.name,
            recommendation="hold",
            confidence="medium",
            summary="Original summary",
            thesis_points_json='["Original thesis"]',
            risk_points_json='["Original risk"]',
            position_notes_json='["Original position note"]',
            recent_catalysts_json='["Original catalyst"]',
            warnings_json="[]",
            full_analysis="Original full analysis",
            disclaimer="Model-generated content",
            generated_at=datetime(2026, 9, 12, 10, 0),
        )
    )


def test_remove_holding_preserves_all_advice_history_fields_except_holding_link(session, seeded_security):
    holding = add_holding(session, seeded_security)
    holding_id = holding.id
    advice = [add_advice(session, seeded_security, holding_id=holding_id) for _ in range(2)]
    original = {entry.id: entry.model_dump() for entry in advice}

    assert HoldingsRepository(session).remove_by_id(holding_id) is True

    assert session.get(Holding, holding_id) is None
    history = InvestmentAdviceCacheRepository(session).list_recent()
    assert len(history) == 2
    for entry in history:
        assert entry.model_dump() == {**original[entry.id], "holding_id": None}


def test_recycled_holding_id_does_not_reuse_deleted_security_advice(session, seeded_security):
    repository = HoldingsRepository(session)
    cache = InvestmentAdviceCacheRepository(session)
    holding_id = add_holding(session, seeded_security).id
    old_advice = add_advice(session, seeded_security, holding_id=holding_id)
    old_advice_id = old_advice.id
    assert repository.remove_by_id(holding_id) is True

    other_security = Security(market="SH", code="600000", name="Other Bank", status="active")
    session.add(other_security)
    session.commit()
    new_holding = add_holding(session, other_security)

    assert new_holding.id == holding_id  # SQLite reuses the deleted highest row ID.
    assert cache.get_latest_for_target("holding", new_holding.id) is None
    new_advice = add_advice(session, other_security, holding_id=new_holding.id)
    assert cache.get_latest_for_target("holding", new_holding.id).id == new_advice.id
    assert session.get(InvestmentAdviceCache, old_advice_id).security_id == seeded_security.id


def test_current_holding_cache_ignores_newer_detached_history(session, seeded_security):
    holding = add_holding(session, seeded_security)
    cache = InvestmentAdviceCacheRepository(session)
    current = add_advice(session, seeded_security, holding_id=holding.id)
    detached = add_advice(session, seeded_security, target_id=holding.id)
    assert detached.id > current.id

    assert cache.get_latest_for_target("holding", holding.id).id == current.id
    assert cache.list_recent()[0].id == detached.id


def test_remove_holding_leaves_stock_cache_and_other_holding_links_unchanged(session, seeded_security):
    holding = add_holding(session, seeded_security)
    stock_advice = add_advice(session, seeded_security, target_type="stock", target_id=seeded_security.id)
    stock_original = stock_advice.model_dump()
    other_security = Security(market="SH", code="600000", name="Other Bank", status="active")
    session.add(other_security)
    session.commit()
    other_holding = add_holding(session, other_security)
    other_advice = add_advice(session, other_security, holding_id=other_holding.id)
    other_original = other_advice.model_dump()

    assert HoldingsRepository(session).remove_by_id(holding.id) is True

    cache = InvestmentAdviceCacheRepository(session)
    assert cache.get_latest_for_target("stock", seeded_security.id).model_dump() == stock_original
    assert cache.get_latest_for_target("holding", other_holding.id).model_dump() == other_original


def test_failed_holding_delete_rolls_back_advice_detachment(session, seeded_security):
    holding_id = add_holding(session, seeded_security).id
    advice_id = add_advice(session, seeded_security, holding_id=holding_id).id
    session.execute(text(
        "CREATE TRIGGER reject_holding_delete BEFORE DELETE ON holdings "
        "BEGIN SELECT RAISE(ABORT, 'test delete rejected'); END"
    ))
    session.commit()

    with pytest.raises(IntegrityError, match="test delete rejected"):
        HoldingsRepository(session).remove_by_id(holding_id)

    # The repository must restore a usable session and both original records.
    assert session.get(Holding, holding_id) is not None
    assert session.get(InvestmentAdviceCache, advice_id).holding_id == holding_id
