"""Local read-only financial indicator endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.api.dependencies import get_session
from app.schemas.indicators import HoldingsIndicatorsResponse, SecurityIndicatorsResponse
from app.services.security_indicators import SecurityIndicatorsService

router = APIRouter()


@router.get('/securities/{security_id}', response_model=SecurityIndicatorsResponse)
def security_indicators(security_id: int, session: Session = Depends(get_session)):
    try:
        return SecurityIndicatorsService(session).security(security_id)
    except KeyError:
        raise HTTPException(404, 'security not found') from None


@router.get('/holdings', response_model=HoldingsIndicatorsResponse)
def holdings_indicators(session: Session = Depends(get_session)):
    return SecurityIndicatorsService(session).holdings()
