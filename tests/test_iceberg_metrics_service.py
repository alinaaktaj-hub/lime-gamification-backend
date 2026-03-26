from datetime import datetime, timezone

from app.services.iceberg_metrics_service import (
    IcebergMetricsService,
    QuestionMetricInput,
    StudentMetricInput,
)


def test_surface_dots_compute_weighted_metrics():
    service = IcebergMetricsService()
    result = service.build_deterministic_layer(
        timezone_name="Asia/Qyzylorda",
        students=[
            StudentMetricInput(
                username="student01",
                total_xp=120,
                assigned_quests=4,
                completed_assigned_quests=2,
                untouched_assigned_quests=1,
                in_progress_quests=1,
                total_answers_14d=10,
                correct_answers_14d=8,
                recent_starts_14d=0,
                recent_answers_14d=10,
                recent_active_days=6,
                baseline_answers_28d=28,
                baseline_active_days=14,
                days_since_last_activity_local=1,
                median_response_seconds=14,
                rapid_wrong_streak_max=1,
                completed_short_quests_ratio=0.25,
                xp_percentile=0.6,
            ),
            StudentMetricInput(
                username="student02",
                total_xp=80,
                assigned_quests=4,
                completed_assigned_quests=1,
                untouched_assigned_quests=2,
                in_progress_quests=1,
                total_answers_14d=5,
                correct_answers_14d=3,
                recent_starts_14d=1,
                recent_answers_14d=0,
                recent_active_days=1,
                baseline_answers_28d=12,
                baseline_active_days=5,
                days_since_last_activity_local=2,
                median_response_seconds=18,
                rapid_wrong_streak_max=1,
                completed_short_quests_ratio=0.4,
                xp_percentile=0.4,
            ),
        ],
        questions=[],
        now=datetime(2026, 3, 26, 7, 0, tzinfo=timezone.utc),
    )

    dots = {dot.id: dot for dot in result.surface_dots}

    assert dots["xp"].value == 200
    assert dots["completion"].value == 0.375
    assert dots["accuracy"].value == 11 / 15
    assert dots["retention"].value == 1.0


def test_recent_window_uses_class_timezone_boundaries():
    service = IcebergMetricsService()

    start_utc = service.local_window_start(
        now=datetime(2026, 3, 26, 1, 0, tzinfo=timezone.utc),
        timezone_name="Asia/Qyzylorda",
        days=14,
    )

    assert start_utc == datetime(2026, 3, 12, 19, 0, tzinfo=timezone.utc)


def test_burnout_emits_against_longer_baseline():
    service = IcebergMetricsService()
    result = service.build_deterministic_layer(
        timezone_name="UTC",
        students=[
            StudentMetricInput(
                username="student01",
                total_xp=100,
                assigned_quests=5,
                completed_assigned_quests=2,
                untouched_assigned_quests=2,
                in_progress_quests=1,
                total_answers_14d=14,
                correct_answers_14d=10,
                recent_starts_14d=0,
                recent_answers_14d=14,
                recent_active_days=4,
                baseline_answers_28d=56,
                baseline_active_days=20,
                days_since_last_activity_local=6,
                median_response_seconds=13,
                rapid_wrong_streak_max=1,
                completed_short_quests_ratio=0.4,
                xp_percentile=0.5,
            ),
            StudentMetricInput(
                username="student02",
                total_xp=90,
                assigned_quests=5,
                completed_assigned_quests=1,
                untouched_assigned_quests=3,
                in_progress_quests=1,
                total_answers_14d=0,
                correct_answers_14d=0,
                recent_starts_14d=0,
                recent_answers_14d=0,
                recent_active_days=0,
                baseline_answers_28d=40,
                baseline_active_days=12,
                days_since_last_activity_local=7,
                median_response_seconds=0,
                rapid_wrong_streak_max=0,
                completed_short_quests_ratio=0.2,
                xp_percentile=0.4,
            ),
        ],
        questions=[],
        now=datetime(2026, 3, 26, 7, 0, tzinfo=timezone.utc),
    )

    status = {item.analyzer: item for item in result.analyzer_statuses}["burnout"]

    assert status.state == "emitted"
    assert status.severity_score > 0
    assert "burnout_recent_drop_rate" in result.evidence_catalog["burnout"]


def test_burnout_reports_insufficient_data_without_baseline():
    service = IcebergMetricsService()
    result = service.build_deterministic_layer(
        timezone_name="UTC",
        students=[
            StudentMetricInput(
                username="student01",
                total_xp=50,
                assigned_quests=2,
                completed_assigned_quests=1,
                untouched_assigned_quests=1,
                in_progress_quests=0,
                total_answers_14d=2,
                correct_answers_14d=1,
                recent_starts_14d=0,
                recent_answers_14d=2,
                recent_active_days=2,
                baseline_answers_28d=6,
                baseline_active_days=2,
                days_since_last_activity_local=1,
                median_response_seconds=10,
                rapid_wrong_streak_max=0,
                completed_short_quests_ratio=0.4,
                xp_percentile=0.5,
            )
        ],
        questions=[],
        now=datetime(2026, 3, 26, 7, 0, tzinfo=timezone.utc),
    )

    status = {item.analyzer: item for item in result.analyzer_statuses}["burnout"]

    assert status.state == "insufficient_data"


def test_guessing_emits_with_fast_low_accuracy_pattern():
    service = IcebergMetricsService()
    result = service.build_deterministic_layer(
        timezone_name="UTC",
        students=[
            StudentMetricInput(
                username="student01",
                total_xp=40,
                assigned_quests=2,
                completed_assigned_quests=0,
                untouched_assigned_quests=1,
                in_progress_quests=1,
                total_answers_14d=8,
                correct_answers_14d=2,
                recent_starts_14d=1,
                recent_answers_14d=8,
                recent_active_days=2,
                baseline_answers_28d=16,
                baseline_active_days=7,
                days_since_last_activity_local=0,
                median_response_seconds=7,
                rapid_wrong_streak_max=4,
                completed_short_quests_ratio=0.0,
                xp_percentile=0.2,
            )
        ],
        questions=[],
        now=datetime(2026, 3, 26, 7, 0, tzinfo=timezone.utc),
    )

    status = {item.analyzer: item for item in result.analyzer_statuses}["guessing"]

    assert status.state == "emitted"
    assert "guessing_fast_wrong_streak" in result.evidence_catalog["guessing"]


def test_progress_imbalance_emits_for_high_xp_low_coverage():
    service = IcebergMetricsService()
    result = service.build_deterministic_layer(
        timezone_name="UTC",
        students=[
            StudentMetricInput(
                username="student01",
                total_xp=300,
                assigned_quests=8,
                completed_assigned_quests=2,
                untouched_assigned_quests=3,
                in_progress_quests=1,
                total_answers_14d=12,
                correct_answers_14d=9,
                recent_starts_14d=1,
                recent_answers_14d=12,
                recent_active_days=5,
                baseline_answers_28d=20,
                baseline_active_days=10,
                days_since_last_activity_local=0,
                median_response_seconds=12,
                rapid_wrong_streak_max=1,
                completed_short_quests_ratio=0.75,
                xp_percentile=0.8,
            )
        ],
        questions=[],
        now=datetime(2026, 3, 26, 7, 0, tzinfo=timezone.utc),
    )

    status = {item.analyzer: item for item in result.analyzer_statuses}[
        "progress_imbalance"
    ]

    assert status.state == "emitted"
    assert "progress_high_xp_low_coverage" in result.evidence_catalog[
        "progress_imbalance"
    ]


def test_task_design_emits_for_high_wrong_rate_question():
    service = IcebergMetricsService()
    result = service.build_deterministic_layer(
        timezone_name="UTC",
        students=[],
        questions=[
            QuestionMetricInput(
                question_id="q1",
                quest_id="quest-a",
                question_label="Q1",
                attempt_count=6,
                wrong_rate=0.82,
                median_response_seconds=19,
                top_wrong_option_share=0.58,
            )
        ],
        now=datetime(2026, 3, 26, 7, 0, tzinfo=timezone.utc),
    )

    status = {item.analyzer: item for item in result.analyzer_statuses}["task_design"]

    assert status.state == "emitted"
    assert "task_question_wrong_rate" in result.evidence_catalog["task_design"]


def test_evidence_catalog_uses_backend_authored_text():
    service = IcebergMetricsService()
    result = service.build_deterministic_layer(
        timezone_name="UTC",
        students=[
            StudentMetricInput(
                username="student01",
                total_xp=100,
                assigned_quests=5,
                completed_assigned_quests=2,
                untouched_assigned_quests=2,
                in_progress_quests=1,
                total_answers_14d=14,
                correct_answers_14d=10,
                recent_starts_14d=0,
                recent_answers_14d=14,
                recent_active_days=4,
                baseline_answers_28d=56,
                baseline_active_days=20,
                days_since_last_activity_local=6,
                median_response_seconds=13,
                rapid_wrong_streak_max=1,
                completed_short_quests_ratio=0.4,
                xp_percentile=0.5,
            ),
            StudentMetricInput(
                username="student02",
                total_xp=90,
                assigned_quests=5,
                completed_assigned_quests=1,
                untouched_assigned_quests=3,
                in_progress_quests=1,
                total_answers_14d=0,
                correct_answers_14d=0,
                recent_starts_14d=0,
                recent_answers_14d=0,
                recent_active_days=0,
                baseline_answers_28d=40,
                baseline_active_days=12,
                days_since_last_activity_local=7,
                median_response_seconds=0,
                rapid_wrong_streak_max=0,
                completed_short_quests_ratio=0.2,
                xp_percentile=0.4,
            ),
        ],
        questions=[],
        now=datetime(2026, 3, 26, 7, 0, tzinfo=timezone.utc),
    )

    evidence = result.evidence_catalog["burnout"]["burnout_recent_drop_rate"]

    assert evidence.evidence_id == "burnout_recent_drop_rate"
    assert "student01" in evidence.text
    assert "answers/day" in evidence.text
