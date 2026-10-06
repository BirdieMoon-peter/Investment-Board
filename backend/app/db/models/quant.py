"""Additive, exact JSON snapshots and append-only forward simulation records."""
from datetime import datetime
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlmodel import SQLModel, Field
from app.db.models.timestamps import utc_now


class QuantDataset(SQLModel, table=True):
    __tablename__ = 'quant_datasets'
    id: int | None = Field(default=None, primary_key=True)
    fingerprint: str = Field(unique=True, index=True)
    payload_json: str
    created_at: datetime = Field(default_factory=utc_now)


class QuantStrategy(SQLModel, table=True):
    __tablename__ = 'quant_strategy_revisions'
    id: int | None = Field(default=None, primary_key=True)
    parent_id: int | None = Field(default=None, foreign_key='quant_strategy_revisions.id')
    fingerprint: str
    payload_json: str
    created_at: datetime = Field(default_factory=utc_now)


class QuantRun(SQLModel, table=True):
    __tablename__ = 'quant_runs'
    id: int | None = Field(default=None, primary_key=True)
    strategy_id: int = Field(foreign_key='quant_strategy_revisions.id', index=True)
    dataset_id: int = Field(foreign_key='quant_datasets.id', index=True)
    fingerprint: str
    payload_json: str
    created_at: datetime = Field(default_factory=utc_now)


class QuantAccount(SQLModel, table=True):
    __tablename__ = 'quant_accounts'
    __table_args__ = (CheckConstraint('version > 0'),)
    id: int | None = Field(default=None, primary_key=True)
    strategy_id: int = Field(foreign_key='quant_strategy_revisions.id')
    dataset_id: int = Field(foreign_key='quant_datasets.id')
    version: int = 1
    payload_json: str
    created_at: datetime = Field(default_factory=utc_now)


class QuantStep(SQLModel, table=True):
    __tablename__ = 'quant_account_steps'
    __table_args__ = (UniqueConstraint('account_id', 'session_date'),)
    id: int | None = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key='quant_accounts.id', index=True)
    session_date: str
    payload_json: str
    created_at: datetime = Field(default_factory=utc_now)


class QuantAnnotation(SQLModel, table=True):
    __tablename__ = 'quant_annotations'
    id: int | None = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key='quant_runs.id', index=True)
    research_project_id: int | None = Field(default=None, foreign_key='research_projects.id')
    kind: str
    payload_json: str
    created_at: datetime = Field(default_factory=utc_now)
