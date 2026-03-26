from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from statistics import median
from typing import Dict, List, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

import asyncpg

from app.entities.group import GroupEntity
from app.services.iceberg_metrics_service import QuestionMetricInput, StudentMetricInput


@dataclass
class _StudentQuestRow:
    student_id: UUID
    username: str
    quest_id: UUID
    status: str
    started_at: Optional[datetime]


@dataclass
class _AnswerEventRow:
    student_id: UUID
    username: str
    quest_id: UUID
    question_id: UUID
    student_quest_id: UUID
    question_index: int
    submitted_answer: str
    is_correct: bool
    answered_at: datetime
    question_label: str


class IcebergRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def get_owned_group(self, group_id: UUID, teacher_id: UUID) -> Optional[GroupEntity]:
        row = await self.conn.fetchrow(
            "SELECT * FROM groups WHERE id = $1 AND teacher_id = $2",
            group_id,
            teacher_id,
        )
        return GroupEntity(**dict(row)) if row else None

    async def list_student_metric_inputs(
        self,
        group_id: UUID,
        timezone_name: str,
        now: datetime,
    ) -> List[StudentMetricInput]:
        student_rows = await self.conn.fetch(
            """SELECT u.id, u.username, COALESCE(sd.total_xp, 0) AS total_xp
               FROM group_students gs
               JOIN users u ON u.id = gs.student_id
               LEFT JOIN student_data sd ON sd.user_id = u.id
               WHERE gs.group_id = $1
               ORDER BY u.username""",
            group_id,
        )
        assigned_rows = await self.conn.fetch(
            """SELECT gq.quest_id, COUNT(q.id) AS question_count
               FROM group_quests gq
               LEFT JOIN questions q ON q.quest_id = gq.quest_id
               WHERE gq.group_id = $1
               GROUP BY gq.quest_id""",
            group_id,
        )
        assigned_quests = {row["quest_id"]: int(row["question_count"]) for row in assigned_rows}

        student_quest_rows = [
            _StudentQuestRow(
                student_id=row["student_id"],
                username=row["username"],
                quest_id=row["quest_id"],
                status=row["status"],
                started_at=row["started_at"],
            )
            for row in await self.conn.fetch(
                """SELECT gs.student_id, u.username, sq.quest_id, sq.status, sq.started_at
                   FROM group_students gs
                   JOIN users u ON u.id = gs.student_id
                   LEFT JOIN student_quests sq
                     ON sq.student_id = gs.student_id
                    AND sq.quest_id IN (
                        SELECT quest_id FROM group_quests WHERE group_id = $1
                    )
                   WHERE gs.group_id = $1""",
                group_id,
            )
            if row["quest_id"] is not None
        ]

        answer_rows = [
            _AnswerEventRow(
                student_id=row["student_id"],
                username=row["username"],
                quest_id=row["quest_id"],
                question_id=row["question_id"],
                student_quest_id=row["student_quest_id"],
                question_index=row["question_index"],
                submitted_answer=row["submitted_answer"],
                is_correct=row["is_correct"],
                answered_at=row["answered_at"],
                question_label=row["question_label"],
            )
            for row in await self.conn.fetch(
                """SELECT gs.student_id,
                          u.username,
                          ae.quest_id,
                          ae.question_id,
                          ae.student_quest_id,
                          ae.question_index,
                          ae.submitted_answer,
                          ae.is_correct,
                          ae.answered_at,
                          CONCAT('Q', q.sort_order + 1) AS question_label
                   FROM group_students gs
                   JOIN users u ON u.id = gs.student_id
                   JOIN student_answer_events ae ON ae.student_id = gs.student_id
                   JOIN questions q ON q.id = ae.question_id
                   WHERE gs.group_id = $1
                     AND ae.quest_id IN (
                        SELECT quest_id FROM group_quests WHERE group_id = $1
                     )
                   ORDER BY ae.student_id, ae.student_quest_id, ae.answered_at""",
                group_id,
            )
        ]

        recent_start = self._local_window_start(now, timezone_name, 14)
        baseline_start = self._local_window_start(now, timezone_name, 42)

        student_events: Dict[UUID, List[_AnswerEventRow]] = defaultdict(list)
        for row in answer_rows:
            student_events[row.student_id].append(row)

        student_quests_by_student: Dict[UUID, List[_StudentQuestRow]] = defaultdict(list)
        for row in student_quest_rows:
            student_quests_by_student[row.student_id].append(row)

        xp_rank = self._xp_percentiles(student_rows)
        short_threshold = median(assigned_quests.values()) if assigned_quests else 0

        inputs = []
        for row in student_rows:
            student_id = row["id"]
            events = student_events.get(student_id, [])
            recent_events = [event for event in events if event.answered_at >= recent_start]
            baseline_events = [
                event
                for event in events
                if baseline_start <= event.answered_at < recent_start
            ]
            student_quests = student_quests_by_student.get(student_id, [])
            completed_quests = [item for item in student_quests if item.status == "completed"]
            in_progress = [item for item in student_quests if item.status == "in_progress"]
            started_recent = [
                item for item in student_quests
                if item.started_at is not None and item.started_at >= recent_start
            ]
            completed_short = [
                item for item in completed_quests
                if assigned_quests.get(item.quest_id, 0) <= short_threshold
            ]
            seen_quest_ids = {item.quest_id for item in student_quests}
            activity_timestamps = [
                *(event.answered_at for event in events),
                *(item.started_at for item in student_quests if item.started_at is not None),
            ]
            last_activity = max(activity_timestamps) if activity_timestamps else None
            days_since_last = (
                (now.astimezone(ZoneInfo(timezone_name)).date()
                 - last_activity.astimezone(ZoneInfo(timezone_name)).date()).days
                if last_activity is not None
                else 999
            )

            inputs.append(
                StudentMetricInput(
                    username=row["username"],
                    total_xp=row["total_xp"],
                    assigned_quests=len(assigned_quests),
                    completed_assigned_quests=len(completed_quests),
                    untouched_assigned_quests=len(set(assigned_quests) - seen_quest_ids),
                    in_progress_quests=len(in_progress),
                    total_answers_14d=len(recent_events),
                    correct_answers_14d=sum(1 for event in recent_events if event.is_correct),
                    recent_starts_14d=len(started_recent),
                    recent_answers_14d=len(recent_events),
                    recent_active_days=len(self._local_days(recent_events, timezone_name)),
                    baseline_answers_28d=len(baseline_events),
                    baseline_active_days=len(self._local_days(baseline_events, timezone_name)),
                    days_since_last_activity_local=days_since_last,
                    median_response_seconds=self._median_response_seconds(
                        recent_events,
                        student_quests,
                    ),
                    rapid_wrong_streak_max=self._rapid_wrong_streak_max(
                        recent_events,
                        student_quests,
                    ),
                    completed_short_quests_ratio=(
                        len(completed_short) / len(completed_quests)
                        if completed_quests else 0.0
                    ),
                    xp_percentile=xp_rank.get(student_id, 0.0),
                )
            )
        return inputs

    async def list_question_metric_inputs(
        self,
        group_id: UUID,
        timezone_name: str,
        now: datetime,
    ) -> List[QuestionMetricInput]:
        recent_start = self._local_window_start(now, timezone_name, 14)
        rows = await self.conn.fetch(
            """SELECT ae.question_id,
                      ae.quest_id,
                      CONCAT('Q', q.sort_order + 1) AS question_label,
                      ae.submitted_answer,
                      ae.is_correct,
                      ae.answered_at
               FROM student_answer_events ae
               JOIN group_students gs ON gs.student_id = ae.student_id
               JOIN questions q ON q.id = ae.question_id
               WHERE gs.group_id = $1
                 AND ae.quest_id IN (
                    SELECT quest_id FROM group_quests WHERE group_id = $1
                 )
                 AND ae.answered_at >= $2
               ORDER BY ae.question_id, ae.answered_at""",
            group_id,
            recent_start,
        )
        grouped: Dict[UUID, List[asyncpg.Record]] = defaultdict(list)
        for row in rows:
            grouped[row["question_id"]].append(row)

        result = []
        for question_id, question_rows in grouped.items():
            attempts = len(question_rows)
            wrong_rows = [row for row in question_rows if not row["is_correct"]]
            wrong_counts: Dict[str, int] = defaultdict(int)
            for row in wrong_rows:
                wrong_counts[row["submitted_answer"]] += 1
            result.append(
                QuestionMetricInput(
                    question_id=str(question_id),
                    quest_id=str(question_rows[0]["quest_id"]),
                    question_label=question_rows[0]["question_label"],
                    attempt_count=attempts,
                    wrong_rate=(len(wrong_rows) / attempts) if attempts else 0.0,
                    median_response_seconds=0,
                    top_wrong_option_share=(
                        max(wrong_counts.values()) / len(wrong_rows)
                        if wrong_rows else 0.0
                    ),
                )
            )
        return result

    async def record_view_audit(self, **kwargs) -> None:
        await self.conn.execute(
            """INSERT INTO iceberg_view_audit
               (group_id, teacher_id, deep_layer_state, deep_dot_count,
                cache_state, model_snapshot, flagged_username_count)
               VALUES ($1, $2, $3, $4, $5, $6, $7)""",
            kwargs["group_id"],
            kwargs["teacher_id"],
            kwargs["deep_layer_state"],
            kwargs["deep_dot_count"],
            kwargs["cache_state"],
            kwargs["model_snapshot"],
            kwargs["flagged_username_count"],
        )

    def _local_window_start(self, now: datetime, timezone_name: str, days: int) -> datetime:
        zone = ZoneInfo(timezone_name)
        local_now = now.astimezone(zone)
        start_local = datetime.combine(local_now.date() - timedelta(days=days - 1), time.min, tzinfo=zone)
        return start_local.astimezone(timezone.utc)

    def _local_days(self, events: List[_AnswerEventRow], timezone_name: str) -> set:
        zone = ZoneInfo(timezone_name)
        return {event.answered_at.astimezone(zone).date() for event in events}

    def _median_response_seconds(
        self,
        events: List[_AnswerEventRow],
        student_quests: List[_StudentQuestRow],
    ) -> int:
        starts = {item.quest_id: item.started_at for item in student_quests if item.started_at is not None}
        by_sq: Dict[UUID, List[_AnswerEventRow]] = defaultdict(list)
        for event in events:
            by_sq[event.student_quest_id].append(event)
        deltas: List[int] = []
        for sq_events in by_sq.values():
            sq_events.sort(key=lambda item: item.answered_at)
            previous_time = starts.get(sq_events[0].quest_id, sq_events[0].answered_at)
            for event in sq_events:
                delta = max(int((event.answered_at - previous_time).total_seconds()), 0)
                deltas.append(delta)
                previous_time = event.answered_at
        return int(median(deltas)) if deltas else 0

    def _rapid_wrong_streak_max(
        self,
        events: List[_AnswerEventRow],
        student_quests: List[_StudentQuestRow],
    ) -> int:
        starts = {item.quest_id: item.started_at for item in student_quests if item.started_at is not None}
        by_sq: Dict[UUID, List[_AnswerEventRow]] = defaultdict(list)
        for event in events:
            by_sq[event.student_quest_id].append(event)

        best = 0
        for sq_events in by_sq.values():
            sq_events.sort(key=lambda item: item.answered_at)
            previous_time = starts.get(sq_events[0].quest_id, sq_events[0].answered_at)
            current = 0
            for event in sq_events:
                delta = max(int((event.answered_at - previous_time).total_seconds()), 0)
                if not event.is_correct and delta <= 10:
                    current += 1
                    best = max(best, current)
                else:
                    current = 0
                previous_time = event.answered_at
        return best

    def _xp_percentiles(self, student_rows: List[asyncpg.Record]) -> Dict[UUID, float]:
        ordered = sorted(student_rows, key=lambda row: row["total_xp"])
        total = len(ordered) or 1
        return {
            row["id"]: (index + 1) / total
            for index, row in enumerate(ordered)
        }
