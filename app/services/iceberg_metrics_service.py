from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from statistics import median
from typing import Dict, List
from zoneinfo import ZoneInfo


@dataclass
class StudentMetricInput:
    username: str
    total_xp: int
    assigned_quests: int
    completed_assigned_quests: int
    untouched_assigned_quests: int
    in_progress_quests: int
    total_answers_14d: int
    correct_answers_14d: int
    recent_starts_14d: int
    recent_answers_14d: int
    recent_active_days: int
    baseline_answers_28d: int
    baseline_active_days: int
    days_since_last_activity_local: int
    median_response_seconds: int
    rapid_wrong_streak_max: int
    completed_short_quests_ratio: float
    xp_percentile: float


@dataclass
class QuestionMetricInput:
    question_id: str
    quest_id: str
    question_label: str
    attempt_count: int
    wrong_rate: float
    median_response_seconds: int
    top_wrong_option_share: float


@dataclass
class SurfaceDot:
    id: str
    label: str
    value: float | int | None


@dataclass
class AnalyzerStatus:
    analyzer: str
    state: str
    severity_score: int
    reason: str


@dataclass
class EvidenceCatalogEntry:
    evidence_id: str
    analyzer: str
    text: str


@dataclass
class IcebergDeterministicResult:
    surface_dots: List[SurfaceDot]
    analyzer_statuses: List[AnalyzerStatus]
    evidence_catalog: Dict[str, Dict[str, EvidenceCatalogEntry]]


class IcebergMetricsService:
    def local_window_start(
        self, now: datetime, timezone_name: str, days: int
    ) -> datetime:
        local_now = now.astimezone(ZoneInfo(timezone_name))
        start_local_date = local_now.date() - timedelta(days=days - 1)
        start_local = datetime.combine(
            start_local_date,
            time.min,
            tzinfo=ZoneInfo(timezone_name),
        )
        return start_local.astimezone(timezone.utc)

    def build_deterministic_layer(
        self,
        timezone_name: str,
        students: List[StudentMetricInput],
        questions: List[QuestionMetricInput],
        now: datetime,
    ) -> IcebergDeterministicResult:
        _ = self.local_window_start(now, timezone_name, 14)
        surface_dots = self._build_surface_dots(students)

        evidence_catalog: Dict[str, Dict[str, EvidenceCatalogEntry]] = {
            "burnout": {},
            "guessing": {},
            "progress_imbalance": {},
            "task_design": {},
        }
        analyzer_statuses = [
            self._burnout_status(students, evidence_catalog["burnout"]),
            self._guessing_status(students, evidence_catalog["guessing"]),
            self._progress_status(students, evidence_catalog["progress_imbalance"]),
            self._task_design_status(questions, evidence_catalog["task_design"]),
        ]
        return IcebergDeterministicResult(
            surface_dots=surface_dots,
            analyzer_statuses=analyzer_statuses,
            evidence_catalog=evidence_catalog,
        )

    def _build_surface_dots(self, students: List[StudentMetricInput]) -> List[SurfaceDot]:
        total_xp = sum(s.total_xp for s in students)
        assigned_slots = sum(s.assigned_quests for s in students)
        completed_slots = sum(s.completed_assigned_quests for s in students)
        total_answers = sum(s.total_answers_14d for s in students)
        correct_answers = sum(s.correct_answers_14d for s in students)
        retained_students = sum(
            1 for s in students if s.recent_answers_14d > 0 or s.recent_starts_14d > 0
        )

        return [
            SurfaceDot(id="xp", label="Total Class XP", value=total_xp),
            SurfaceDot(
                id="completion",
                label="Quest Completion Rate",
                value=(completed_slots / assigned_slots) if assigned_slots else None,
            ),
            SurfaceDot(
                id="accuracy",
                label="Average Accuracy",
                value=(correct_answers / total_answers) if total_answers else None,
            ),
            SurfaceDot(
                id="retention",
                label="Retention Rate",
                value=(retained_students / len(students)) if students else None,
            ),
        ]

    def _burnout_status(
        self,
        students: List[StudentMetricInput],
        evidence: Dict[str, EvidenceCatalogEntry],
    ) -> AnalyzerStatus:
        eligible = [
            s for s in students if s.baseline_answers_28d >= 12 or s.baseline_active_days >= 4
        ]
        if not eligible:
            return AnalyzerStatus("burnout", "insufficient_data", 0, "Not enough baseline history")

        flagged = []
        for student in eligible:
            recent_per_day = student.recent_answers_14d / 14
            baseline_per_day = student.baseline_answers_28d / 28
            if baseline_per_day > 0 and recent_per_day <= baseline_per_day * 0.5:
                evidence.setdefault(
                    "burnout_recent_drop_rate",
                    EvidenceCatalogEntry(
                        evidence_id="burnout_recent_drop_rate",
                        analyzer="burnout",
                        text=(
                            f"{student.username} activity fell from {baseline_per_day:.1f} "
                            f"answers/day over the prior 28 days to {recent_per_day:.1f} "
                            f"answers/day in the last 14 days."
                        ),
                    ),
                )
                flagged.append(student)
            elif (
                student.days_since_last_activity_local >= 6
                and student.in_progress_quests >= 1
            ):
                evidence.setdefault(
                    "burnout_inactive_6d",
                    EvidenceCatalogEntry(
                        evidence_id="burnout_inactive_6d",
                        analyzer="burnout",
                        text=(
                            f"{student.username} has been inactive for "
                            f"{student.days_since_last_activity_local} days with "
                            f"{student.in_progress_quests} in-progress quest(s)."
                        ),
                    ),
                )
                flagged.append(student)

        if not flagged:
            return AnalyzerStatus("burnout", "below_threshold", 0, "No burnout pattern crossed the class trigger")

        class_ratio = len(flagged) / max(len(students), 1)
        if len(flagged) >= 2 or class_ratio >= 0.2:
            severity = 40
            if class_ratio >= 0.35:
                severity += 20
            if median([s.days_since_last_activity_local for s in flagged]) >= 6:
                severity += 20
            if any(s.in_progress_quests >= 1 for s in flagged):
                severity += 20
            return AnalyzerStatus("burnout", "emitted", severity, "Recent activity dropped against the trailing baseline")

        return AnalyzerStatus("burnout", "below_threshold", 0, "Burnout pattern did not cross the class threshold")

    def _guessing_status(
        self,
        students: List[StudentMetricInput],
        evidence: Dict[str, EvidenceCatalogEntry],
    ) -> AnalyzerStatus:
        candidates = []
        for student in students:
            accuracy = (
                student.correct_answers_14d / student.total_answers_14d
                if student.total_answers_14d
                else 0
            )
            if (
                student.total_answers_14d >= 6
                and accuracy <= 0.4
                and student.median_response_seconds <= 10
                and student.rapid_wrong_streak_max >= 3
            ):
                candidates.append(student)

        if not candidates:
            return AnalyzerStatus("guessing", "below_threshold", 0, "No superficial guessing pattern crossed the threshold")

        sample = candidates[0]
        evidence["guessing_fast_wrong_streak"] = EvidenceCatalogEntry(
            evidence_id="guessing_fast_wrong_streak",
            analyzer="guessing",
            text=(
                f"{sample.username} answered {sample.rapid_wrong_streak_max} questions "
                f"wrong in a rapid streak with a median response time of "
                f"{sample.median_response_seconds} seconds."
            ),
        )
        evidence["guessing_low_accuracy_14d"] = EvidenceCatalogEntry(
            evidence_id="guessing_low_accuracy_14d",
            analyzer="guessing",
            text=(
                f"{sample.username} answered only "
                f"{sample.correct_answers_14d} of {sample.total_answers_14d} "
                f"questions correctly over the last 14 days."
            ),
        )
        severity = 50 + (20 if len(candidates) >= 2 else 0)
        if (
            sample.total_answers_14d
            and sample.correct_answers_14d / sample.total_answers_14d <= 0.25
        ):
            severity += 15
        if sample.rapid_wrong_streak_max >= 4:
            severity += 15
        return AnalyzerStatus("guessing", "emitted", severity, "Fast low-accuracy answer behavior suggests superficial guessing")

    def _progress_status(
        self,
        students: List[StudentMetricInput],
        evidence: Dict[str, EvidenceCatalogEntry],
    ) -> AnalyzerStatus:
        candidates = []
        for student in students:
            completion_ratio = (
                student.completed_assigned_quests / student.assigned_quests
                if student.assigned_quests
                else 0
            )
            if (
                completion_ratio <= 0.35
                and student.xp_percentile >= 0.7
                and student.completed_short_quests_ratio >= 0.6
                and student.untouched_assigned_quests >= 2
            ):
                candidates.append((student, completion_ratio))

        if not candidates:
            return AnalyzerStatus("progress_imbalance", "below_threshold", 0, "No progress imbalance pattern crossed the threshold")

        sample, completion_ratio = candidates[0]
        evidence["progress_high_xp_low_coverage"] = EvidenceCatalogEntry(
            evidence_id="progress_high_xp_low_coverage",
            analyzer="progress_imbalance",
            text=(
                f"{sample.username} is in the top {int((1 - sample.xp_percentile) * 100)}% "
                f"of class XP but has completed only "
                f"{sample.completed_assigned_quests} of {sample.assigned_quests} assigned quests."
            ),
        )
        evidence["progress_untouched_assigned_quests"] = EvidenceCatalogEntry(
            evidence_id="progress_untouched_assigned_quests",
            analyzer="progress_imbalance",
            text=(
                f"{sample.username} still has {sample.untouched_assigned_quests} "
                f"untouched assigned quest(s)."
            ),
        )
        severity = 45 + (20 if len(candidates) >= 2 else 0)
        if sample.untouched_assigned_quests >= 3:
            severity += 20
        if sample.xp_percentile >= 0.8:
            severity += 15
        return AnalyzerStatus("progress_imbalance", "emitted", severity, "XP concentration and low coverage suggest uneven progress")

    def _task_design_status(
        self,
        questions: List[QuestionMetricInput],
        evidence: Dict[str, EvidenceCatalogEntry],
    ) -> AnalyzerStatus:
        candidates = [
            question
            for question in questions
            if question.attempt_count >= 5
            and (
                question.wrong_rate >= 0.7
                or (
                    question.wrong_rate >= 0.6
                    and question.median_response_seconds >= 45
                )
                or question.top_wrong_option_share >= 0.55
            )
        ]

        if not candidates:
            return AnalyzerStatus("task_design", "insufficient_data" if not questions else "below_threshold", 0, "No question-level design issue crossed the threshold")

        sample = candidates[0]
        evidence["task_question_wrong_rate"] = EvidenceCatalogEntry(
            evidence_id="task_question_wrong_rate",
            analyzer="task_design",
            text=(
                f"Question {sample.question_label} was answered incorrectly by "
                f"{sample.wrong_rate:.0%} of students over the last 14 days."
            ),
        )
        evidence["task_distractor_concentration"] = EvidenceCatalogEntry(
            evidence_id="task_distractor_concentration",
            analyzer="task_design",
            text=(
                f"Question {sample.question_label} had a top wrong-option concentration "
                f"of {sample.top_wrong_option_share:.0%}."
            ),
        )
        severity = 55 + (20 if len(candidates) >= 2 else 0)
        if sample.wrong_rate >= 0.85:
            severity += 15
        if sample.top_wrong_option_share >= 0.55:
            severity += 10
        return AnalyzerStatus("task_design", "emitted", severity, "Question-level evidence suggests a task design problem")
