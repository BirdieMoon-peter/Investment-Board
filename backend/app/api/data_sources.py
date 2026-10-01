from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.dependencies import get_session
from app.schemas.data_sources import DataSourceUpdate
from app.services.data_source_management import DataSourceManagementService, SourceWriteError
from app.services.data_sources.registry import list_source_modules

router = APIRouter()


@router.get('')
def list_sources(limit: int = Query(20, ge=1, le=100), session: Session = Depends(get_session)):
    service = DataSourceManagementService(session)
    return {'sources': [service.detail(module.key, limit) for module in list_source_modules()]}


@router.get('/{vendor_key}')
def source_detail(vendor_key: str, limit: int = Query(20, ge=1, le=100), session: Session = Depends(get_session)):
    try:
        return DataSourceManagementService(session).detail(vendor_key, limit)
    except KeyError:
        raise HTTPException(404, 'source not found') from None


@router.put('/{vendor_key}')
def update_source(vendor_key: str, body: DataSourceUpdate, session: Session = Depends(get_session)):
    try:
        return DataSourceManagementService(session).update(vendor_key, body.enabled)
    except KeyError:
        raise HTTPException(404, 'source not found') from None
    except ValueError:
        raise HTTPException(422, 'source is not configurable') from None
    except SourceWriteError:
        raise HTTPException(503, 'source settings could not be saved') from None
