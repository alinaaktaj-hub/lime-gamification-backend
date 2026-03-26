from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID

import asyncpg
from fastapi import HTTPException

from app.config import OPENAI_MODEL
from app.dtos.iceberg_dtos import (
    IcebergAnalysisMetaResponse,
    IcebergAnalyzerStatusResponse,
    IcebergDeepDotResponse,
    IcebergGroupResponse,
    IcebergResponse,
    IcebergSurfaceDotResponse,
)
from app.repositories.iceberg_repository import IcebergRepository
from app.services.iceberg_ai_service import AnalyzerWorkItem, IcebergAIService
from app.services.iceberg_metrics_service import IcebergMetricsService


@dataclass
class _CacheEntry:
    expires_at: datetime
    response: IcebergResponse


class IcebergService:
    def __init__(
        self,
        conn: Optional[asyncpg.Connection],
        *,
        repository=None,
        metrics_service=None,
        ai_service=None,
    ):
        self.conn = conn
        self.repository = repository or IcebergRepository(conn)
        self.metrics_service = metrics_service or IcebergMetricsService()
        self.ai_service = ai_service or IcebergAIService()
        self._cache: Dict[UUID, _CacheEntry] = {}

    async def get_group_iceberg(self, group_id: UUID, teacher_id: UUID) -> IcebergResponse:
        group = await self.repository.get_owned_group(group_id, teacher_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        now = datetime.now(timezone.utc)
        cache_entry = self._cache.get(group_id)
        if cache_entry and cache_entry.expires_at > now:
            cached_response = cache_entry.response.model_copy(deep=True)
            cached_response.analysisMeta.cache_state = "cached"
            await self._record_audit(group_id, teacher_id, cached_response)
            return cached_response

        students = await self.repository.list_student_metric_inputs(group_id, group.timezone, now)
        questions = await self.repository.list_question_metric_inputs(group_id, group.timezone, now)
        deterministic = self.metrics_service.build_deterministic_layer(
            timezone_name=group.timezone,
            students=students,
            questions=questions,
            now=now,
        )

        analyzer_statuses = list(deterministic.analyzer_statuses)
        work_items = [
            AnalyzerWorkItem(
                analyzer=status.analyzer,
                severity_score=status.severity_score,
                evidence_catalog={
                    evidence_id: entry.text
                    for evidence_id, entry in deterministic.evidence_catalog[status.analyzer].items()
                },
                payload={
                    "analyzer": status.analyzer,
                    "group": {"id": str(group.id), "name": group.name, "timezone": group.timezone},
                    "evidence_catalog": {
                        evidence_id: entry.text
                        for evidence_id, entry in deterministic.evidence_catalog[status.analyzer].items()
                    },
                },
            )
            for status in analyzer_statuses
            if status.state == "emitted"
        ]

        cache_state = "fresh"
        deep_dots: List[IcebergDeepDotResponse] = []
        deep_layer_state = "below_threshold"
        try:
            ai_results = await self.ai_service.run_analyzers(work_items) if work_items else []
            deep_dots = [IcebergDeepDotResponse(**item) for item in ai_results]
            if deep_dots:
                deep_layer_state = "has_findings"
            elif work_items:
                deep_layer_state = "healthy_no_findings"
            elif analyzer_statuses and all(status.state == "insufficient_data" for status in analyzer_statuses):
                deep_layer_state = "insufficient_data"
            elif analyzer_statuses and any(status.state == "below_threshold" for status in analyzer_statuses):
                deep_layer_state = "below_threshold"
            else:
                deep_layer_state = "insufficient_data"
        except Exception:
            deep_dots = []
            deep_layer_state = "analysis_unavailable"

        response = IcebergResponse(
            group=IcebergGroupResponse(
                id=group.id,
                name=group.name,
                student_count=len(students),
                timezone=group.timezone,
            ),
            surfaceDots=[
                IcebergSurfaceDotResponse(id=dot.id, label=dot.label, value=dot.value)
                for dot in deterministic.surface_dots
            ],
            deepDots=deep_dots,
            deepLayerState=deep_layer_state,
            analyzerStatuses=[
                IcebergAnalyzerStatusResponse(
                    analyzer=status.analyzer,
                    state=status.state,
                    severity_score=status.severity_score,
                    reason=status.reason,
                )
                for status in analyzer_statuses
            ],
            analysisMeta=IcebergAnalysisMetaResponse(
                generated_at=now,
                expires_at=now + timedelta(minutes=15),
                cache_state=cache_state,
                model=OPENAI_MODEL,
            ),
        )
        self._cache[group_id] = _CacheEntry(
            expires_at=response.analysisMeta.expires_at,
            response=response.model_copy(deep=True),
        )
        await self._record_audit(group_id, teacher_id, response)
        return response

    async def _record_audit(self, group_id: UUID, teacher_id: UUID, response: IcebergResponse) -> None:
        await self.repository.record_view_audit(
            group_id=group_id,
            teacher_id=teacher_id,
            deep_layer_state=response.deepLayerState,
            deep_dot_count=len(response.deepDots),
            cache_state=response.analysisMeta.cache_state,
            model_snapshot=response.analysisMeta.model,
            flagged_username_count=sum(len(dot.flagged_usernames) for dot in response.deepDots),
        )
