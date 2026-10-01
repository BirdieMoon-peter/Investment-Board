"""Additive research objects; historical runs are append-only via the repository."""
from datetime import datetime
from sqlalchemy import UniqueConstraint, CheckConstraint, ForeignKeyConstraint
from sqlmodel import Field, SQLModel
from app.db.models.timestamps import utc_now


class ResearchProject(SQLModel, table=True):
    __tablename__ = 'research_projects'
    __table_args__ = (CheckConstraint("status IN ('active','archived')"), CheckConstraint('version > 0'),)
    id: int | None = Field(default=None, primary_key=True)
    security_id: int = Field(foreign_key='securities.id', index=True)
    question: str
    hypothesis: str | None = None
    horizon: str | None = None
    status: str = 'active'
    version: int = 1
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ResearchRun(SQLModel, table=True):
    __tablename__ = 'research_runs'
    __table_args__ = (UniqueConstraint('id','project_id'),CheckConstraint("status IN ('completed','failed')"),CheckConstraint('project_version > 0'),)
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key='research_projects.id', index=True)
    project_version: int
    status: str
    input_snapshot_json: str
    input_fingerprint: str
    output_json: str | None = None
    model_name: str
    prompt_version: str
    error_code: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ResearchReviewEvent(SQLModel, table=True):
    __tablename__ = 'research_review_events'
    __table_args__ = (UniqueConstraint('project_id','run_id','input_fingerprint','reason_code'),
        ForeignKeyConstraint(['run_id','project_id'],['research_runs.id','research_runs.project_id']),
        CheckConstraint("status IN ('open','resolved')"),
        CheckConstraint("reason_code IN ('data_changed','condition_triggered','data_unavailable')"),)
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(foreign_key='research_projects.id', index=True)
    run_id: int = Field(foreign_key='research_runs.id', index=True)
    input_fingerprint: str
    reason_code: str
    status: str = 'open'
    details_json: str
    created_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None
