from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.api.dependencies import get_session
from app.db.repositories import HoldingsRepository, SecurityRepository
from app.schemas import HoldingRemoveResponse, HoldingResponse, HoldingUpsertRequest, SecuritySearchResult

router = APIRouter()



def _row_to_response(row) -> HoldingResponse:
    return HoldingResponse(
        holding_id=row.holding_id,
        security_id=row.security_id,
        security=SecuritySearchResult(
            security_id=row.security_id,
            market=row.market,
            code=row.code,
            name=row.name,
            industry=row.industry,
            status=row.status,
        ),
        quantity=row.quantity,
        average_cost=row.average_cost,
        notes=row.notes,
        target_horizon=row.target_horizon,
    )


@router.get("", response_model=list[HoldingResponse])
def list_holdings(
    session: Session = Depends(get_session),
) -> list[HoldingResponse]:
    repository = HoldingsRepository(session)
    return [_row_to_response(row) for row in repository.list_rows()]


@router.post("", response_model=HoldingResponse)
def upsert_holding(
    payload: HoldingUpsertRequest,
    session: Session = Depends(get_session),
) -> HoldingResponse:
    security = SecurityRepository(session).get_by_id(payload.security_id)
    if security is None:
        raise HTTPException(status_code=404, detail="security not found")

    repository = HoldingsRepository(session)
    holding = repository.upsert_by_security_id(
        security_id=payload.security_id,
        quantity=payload.quantity,
        average_cost=payload.average_cost,
        notes=payload.notes,
        target_horizon=payload.target_horizon,
    )
    row = repository.get_row_by_id(holding.id)
    assert row is not None
    return _row_to_response(row)


@router.put("/{holding_id}", response_model=HoldingResponse)
def update_holding(
    holding_id: int,
    payload: HoldingUpsertRequest,
    session: Session = Depends(get_session),
) -> HoldingResponse:
    security = SecurityRepository(session).get_by_id(payload.security_id)
    if security is None:
        raise HTTPException(status_code=404, detail="security not found")

    repository = HoldingsRepository(session)
    existing = repository.get_by_id(holding_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="holding not found")
    if existing.security_id != payload.security_id:
        raise HTTPException(status_code=422, detail="security_id cannot be changed")

    updated = repository.update_by_id(
        holding_id,
        quantity=payload.quantity,
        average_cost=payload.average_cost,
        notes=payload.notes,
        target_horizon=payload.target_horizon,
    )
    assert updated is not None
    row = repository.get_row_by_id(updated.id)
    assert row is not None
    return _row_to_response(row)


@router.delete("/{holding_id}", response_model=HoldingRemoveResponse)
def remove_holding(
    holding_id: int,
    session: Session = Depends(get_session),
) -> HoldingRemoveResponse:
    repository = HoldingsRepository(session)
    removed = repository.remove_by_id(holding_id)
    if not removed:
        raise HTTPException(status_code=404, detail="holding not found")
    return HoldingRemoveResponse(removed=True, holding_id=holding_id)
