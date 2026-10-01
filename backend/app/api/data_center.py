from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from app.api.dependencies import get_session
from app.api.stocks import get_stock_sync_service
from app.services.data_center import SecurityDataCenterService
from app.services.data_source_management import SourceWriteError
from app.services.data_sources import eastmoney
from app.services.data_center_sync import sync_security
from app.schemas.data_center import SecuritySyncRequest, SecurityMetadataUpdate, SecurityDataResponse, SecuritySyncResponse

router = APIRouter()


def get_fund_nav_source():
    return eastmoney.build_fund_nav_source()


def get_fund_profile_source():
    return eastmoney.build_fund_profile_source()


@router.get('/{security_id}', response_model=SecurityDataResponse)
def detail(security_id: int, limit: int = Query(20,ge=1,le=100),session: Session = Depends(get_session)):
    try:
        return SecurityDataCenterService(session).detail(security_id,limit)
    except KeyError:
        raise HTTPException(404,'security not found') from None


@router.put('/{security_id}/metadata', response_model=SecurityDataResponse)
def update_metadata(security_id: int,body: SecurityMetadataUpdate, session: Session = Depends(get_session)):
    try:
        return SecurityDataCenterService(session).update_metadata(security_id,body)
    except KeyError:
        raise HTTPException(404,'security not found') from None
    except SourceWriteError:
        raise HTTPException(503,'security metadata could not be saved') from None


@router.post('/{security_id}/sync', response_model=SecuritySyncResponse)
def sync(security_id:int,body:SecuritySyncRequest,session:Session=Depends(get_session),
         stock_service=Depends(get_stock_sync_service),nav_source=Depends(get_fund_nav_source),profile_source=Depends(get_fund_profile_source)):
    try:
        return sync_security(session,security_id,body,stock_service,nav_source,profile_source)
    except KeyError:
        raise HTTPException(404,'security not found') from None
