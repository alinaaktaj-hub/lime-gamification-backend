from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class IcebergSurfaceDotResponse(BaseModel):
    id: str
    label: str
    value: Optional[float]


class IcebergDeepDotResponse(BaseModel):
    analyzer: str
    severity_score: int
    title: str
    insight: str
    evidence_ids: List[str]
    evidence: List[str]
    risk_level: str
    recommendations: List[str]
    flagged_usernames: List[str]
    confidence: float


class IcebergAnalyzerStatusResponse(BaseModel):
    analyzer: str
    state: str
    severity_score: int
    reason: str


class IcebergAnalysisMetaResponse(BaseModel):
    generated_at: datetime
    expires_at: datetime
    cache_state: str
    model: str


class IcebergGroupResponse(BaseModel):
    id: UUID
    name: str
    student_count: int
    timezone: str


class IcebergResponse(BaseModel):
    group: IcebergGroupResponse
    surfaceDots: List[IcebergSurfaceDotResponse]
    deepDots: List[IcebergDeepDotResponse]
    deepLayerState: str
    analyzerStatuses: List[IcebergAnalyzerStatusResponse]
    analysisMeta: IcebergAnalysisMetaResponse
