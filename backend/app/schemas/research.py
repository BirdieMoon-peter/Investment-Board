"""Bounded research input/output contracts; predicates are data, never code."""
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

Text = Annotated[str, Field(min_length=1,max_length=4000)]
Items = Annotated[list[Text], Field(max_length=30)]
Refs = Annotated[list[Annotated[str,Field(min_length=1,max_length=100)]],Field(max_length=30)]


class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)


class ProjectCreate(Strict):
    security_id: Annotated[int,Field(gt=0)]
    question: Annotated[str,Field(min_length=1,max_length=2000)]
    hypothesis: Annotated[str,Field(max_length=4000)] | None = None
    horizon: Annotated[str,Field(max_length=200)] | None = None


class ProjectUpdate(Strict):
    expected_version: Annotated[int,Field(gt=0)]
    question: Annotated[str,Field(min_length=1,max_length=2000)] | None = None
    hypothesis: Annotated[str,Field(max_length=4000)] | None = None
    horizon: Annotated[str,Field(max_length=200)] | None = None


class VersionRequest(Strict):
    expected_version: Annotated[int,Field(gt=0)]


class GenerateRequest(Strict):
    critique: bool = False


class MetricReference(Strict):
    metric_key: Annotated[str,Field(min_length=1,max_length=100)]
    reported_value: Annotated[str,Field(max_length=100)] | None = None


class Claim(Strict):
    kind: Literal['fact','inference','hypothesis']
    statement: Text
    evidence_ids: Refs
    counter_evidence_ids: Refs
    metric_refs: Annotated[list[MetricReference],Field(max_length=30)]


class InvalidationCondition(Strict):
    description: Text
    metric_key: Annotated[str,Field(max_length=100)] | None = None
    operator: Annotated[str,Field(max_length=20)] | None = None
    threshold: Annotated[str,Field(max_length=100)] | None = None


class ResearchOutput(Strict):
    executive_summary: Text
    claims: Annotated[list[Claim],Field(max_length=30)]
    risks: Items
    data_gaps: Items
    invalidation_conditions: Annotated[list[InvalidationCondition],Field(max_length=20)]
    next_checks: Items


class CritiqueItem(Strict):
    claim_index: Annotated[int,Field(ge=0,lt=30)]
    support: Literal['supported','unsupported','uncertain']
    explanation: Text


class CritiqueOutput(Strict):
    claims: Annotated[list[CritiqueItem],Field(max_length=30)]
