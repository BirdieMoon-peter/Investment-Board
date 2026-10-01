"""Research actions: only explicit POST runs can invoke AI."""
import json
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlmodel import Session
from app.api.dependencies import get_session
from app.db.repositories.research_repository import ResearchRepository,ResearchConflict
from app.db.models.research import ResearchReviewEvent
from app.schemas.research import ProjectCreate,ProjectUpdate,VersionRequest,GenerateRequest
from app.services.research_service import ResearchService
from app.services.research_evidence import plain

router=APIRouter()


def view(row):
    result=plain(row.model_dump())
    for field in ('input_snapshot_json','output_json','details_json'):
        if field in result:
            result[field.removesuffix('_json')]=json.loads(result.pop(field)) if result[field] is not None else None
    return result


def apply(action):
    try: return action()
    except ResearchConflict: raise HTTPException(409,'project version conflict') from None
    except KeyError: raise HTTPException(404,'research object not found') from None
    except ValueError: raise HTTPException(422,'invalid research action') from None


@router.get('/projects')
def projects(security_id: int | None=None,limit: int=Query(20,ge=1,le=100),session: Session=Depends(get_session)):
    return [view(r) for r in ResearchRepository(session).list_projects(security_id=security_id,limit=limit)]


@router.post('/projects',status_code=201)
def create(body: ProjectCreate,session: Session=Depends(get_session)):
    repo=ResearchRepository(session)
    from app.db.models import Security
    if session.get(Security,body.security_id) is None: raise HTTPException(404,'security not found')
    return apply(lambda:view(repo.create_project(**body.model_dump())))


@router.get('/projects/{project_id}')
def project(project_id: int,session: Session=Depends(get_session)):
    return apply(lambda:view(ResearchService(session).project(project_id)))


@router.put('/projects/{project_id}')
def update(project_id: int,body: ProjectUpdate,session: Session=Depends(get_session)):
    service=ResearchService(session); apply(lambda:service.project(project_id))
    return apply(lambda:view(service.repo.update_project(project_id,**body.model_dump(exclude_unset=True))))


@router.post('/projects/{project_id}/archive')
def archive(project_id: int,body: VersionRequest,session: Session=Depends(get_session)):
    service=ResearchService(session); apply(lambda:service.project(project_id))
    return apply(lambda:view(service.repo.archive_project(project_id,expected_version=body.expected_version)))


@router.get('/projects/{project_id}/runs')
def runs(project_id: int,limit: int=Query(20,ge=1,le=100),session: Session=Depends(get_session)):
    service=ResearchService(session); apply(lambda:service.project(project_id))
    return [view(r) for r in service.repo.list_runs(project_id,limit=limit)]


@router.get('/projects/{project_id}/runs/{run_id}')
def run(project_id: int,run_id: int,session: Session=Depends(get_session)):
    row=ResearchRepository(session).get_run(run_id)
    if row is None or row.project_id!=project_id: raise HTTPException(404,'run not found')
    return view(row)


@router.post('/projects/{project_id}/runs',status_code=201)
def generate(project_id: int,body: GenerateRequest,session: Session=Depends(get_session)):
    return apply(lambda:view(ResearchService(session).generate(project_id,critique=body.critique)))


@router.post('/projects/{project_id}/check')
def check(project_id: int,session: Session=Depends(get_session)):
    result=apply(lambda:ResearchService(session).check(project_id))
    result['events']=[view(e) for e in result['events']]
    return result


@router.get('/projects/{project_id}/events')
def events(project_id: int,limit: int=Query(20,ge=1,le=100),session: Session=Depends(get_session)):
    service=ResearchService(session); apply(lambda:service.project(project_id))
    return [view(e) for e in service.repo.list_events(project_id,limit=limit)]


@router.post('/events/{event_id}/resolve')
def resolve(event_id: int,session: Session=Depends(get_session)):
    row=ResearchRepository(session).resolve_event(event_id)
    if row is None: raise HTTPException(404,'event not found')
    return view(row)
