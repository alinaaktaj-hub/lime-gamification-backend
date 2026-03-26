import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.iceberg_ai_service import AnalyzerWorkItem
from app.services.iceberg_metrics_service import (
    AnalyzerStatus,
    IcebergDeterministicResult,
    QuestionMetricInput,
    StudentMetricInput,
    SurfaceDot,
)
from app.services.iceberg_service import IcebergService


class FakeIcebergRepository:
    def __init__(self):
        self.audit_calls = []

    async def get_owned_group(self, group_id, teacher_id):
        return SimpleNamespace(
            id=group_id,
            name="Group A",
            teacher_id=teacher_id,
            timezone="UTC",
        )

    async def list_student_metric_inputs(self, group_id, timezone_name, now):
        return [
            StudentMetricInput(
                username="student01",
                total_xp=100,
                assigned_quests=4,
                completed_assigned_quests=1,
                untouched_assigned_quests=2,
                in_progress_quests=1,
                total_answers_14d=8,
                correct_answers_14d=2,
                recent_starts_14d=1,
                recent_answers_14d=8,
                recent_active_days=2,
                baseline_answers_28d=20,
                baseline_active_days=8,
                days_since_last_activity_local=1,
                median_response_seconds=7,
                rapid_wrong_streak_max=4,
                completed_short_quests_ratio=0.2,
                xp_percentile=0.4,
            )
        ]

    async def list_question_metric_inputs(self, group_id, timezone_name, now):
        return [
            QuestionMetricInput(
                question_id="q1",
                quest_id="quest-a",
                question_label="Q1",
                attempt_count=6,
                wrong_rate=0.8,
                median_response_seconds=20,
                top_wrong_option_share=0.6,
            )
        ]

    async def record_view_audit(self, **kwargs):
        self.audit_calls.append(kwargs)


class FakeMetricsService:
    def build_deterministic_layer(self, timezone_name, students, questions, now):
        return IcebergDeterministicResult(
            surface_dots=[SurfaceDot(id="xp", label="Total Class XP", value=100)],
            analyzer_statuses=[
                AnalyzerStatus(
                    analyzer="guessing",
                    state="emitted",
                    severity_score=70,
                    reason="Strong guessing pattern",
                ),
                AnalyzerStatus(
                    analyzer="task_design",
                    state="below_threshold",
                    severity_score=0,
                    reason="No design issue",
                ),
            ],
            evidence_catalog={
                "guessing": {"guessing_fast_wrong_streak": SimpleNamespace(text="fast wrong streak")},
                "task_design": {},
            },
        )


class FakeAIService:
    def __init__(self, fail=False):
        self.fail = fail

    async def run_analyzers(self, items):
        if self.fail:
            raise RuntimeError("provider down")
        assert len(items) == 1
        assert isinstance(items[0], AnalyzerWorkItem)
        return [
            {
                "analyzer": "guessing",
                "severity_score": 70,
                "title": "Likely superficial guessing",
                "insight": "Fast low-accuracy behavior is present.",
                "evidence_ids": ["guessing_fast_wrong_streak"],
                "evidence": ["fast wrong streak"],
                "risk_level": "medium",
                "recommendations": ["Slow the student down."],
                "flagged_usernames": ["student01"],
                "confidence": 0.8,
            }
        ]


def test_get_group_iceberg_uses_cache_and_audits_every_view():
    repo = FakeIcebergRepository()
    service = IcebergService(
        conn=None,
        repository=repo,
        metrics_service=FakeMetricsService(),
        ai_service=FakeAIService(),
    )
    group_id = uuid4()
    teacher_id = uuid4()

    first = asyncio.run(service.get_group_iceberg(group_id, teacher_id))
    second = asyncio.run(service.get_group_iceberg(group_id, teacher_id))

    assert first.analysisMeta.cache_state == "fresh"
    assert second.analysisMeta.cache_state == "cached"
    assert len(repo.audit_calls) == 2


def test_get_group_iceberg_returns_analysis_unavailable_when_ai_fails():
    repo = FakeIcebergRepository()
    service = IcebergService(
        conn=None,
        repository=repo,
        metrics_service=FakeMetricsService(),
        ai_service=FakeAIService(fail=True),
    )

    result = asyncio.run(service.get_group_iceberg(uuid4(), uuid4()))

    assert result.deepLayerState == "analysis_unavailable"
    assert result.deepDots == []
