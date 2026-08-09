"""Deterministic publish slot planning."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from apscheduler.triggers.cron import CronTrigger

from app.config.schemas import ScheduleConfig


@dataclass(frozen=True, slots=True)
class SlotPlanningRequest:
    """Inputs for deterministic slot planning."""

    account_key: str
    channel: str
    schedule: ScheduleConfig
    now: datetime
    occupied_times: tuple[datetime, ...] = ()
    target_slot_count: int = 0


@dataclass(frozen=True, slots=True)
class PlannedSlot:
    """A planned publish slot derived from cron/window settings."""

    anchor_time: datetime
    window_start: datetime
    window_end: datetime
    scheduled_for: datetime
    jitter_minutes: int


@dataclass(frozen=True, slots=True)
class SlotPlanningResult:
    """Output of one slot-planning run."""

    slots: tuple[PlannedSlot, ...]
    anchors_considered: int


class SlotPlanner:
    """Plan deterministic future publish slots for one account/channel."""

    def plan(self, request: SlotPlanningRequest) -> SlotPlanningResult:
        if request.target_slot_count <= 0:
            return SlotPlanningResult(slots=(), anchors_considered=0)

        normalized_now = _normalize_datetime(request.now)
        occupied_times = tuple(sorted(_normalize_datetime(value) for value in request.occupied_times))
        schedule = request.schedule
        trigger = CronTrigger.from_crontab(schedule.cron, timezone=timezone.utc)

        slots: list[PlannedSlot] = []
        search_from = normalized_now - timedelta(minutes=schedule.window_minutes, seconds=1)
        previous_fire_time: datetime | None = None
        anchor = trigger.get_next_fire_time(previous_fire_time, search_from)
        anchors_considered = 0
        max_anchor_checks = max(366, request.target_slot_count * 500)

        while anchor is not None and len(slots) < request.target_slot_count and anchors_considered < max_anchor_checks:
            anchors_considered += 1
            window_start = _normalize_datetime(anchor)
            window_end = window_start + timedelta(minutes=schedule.window_minutes)
            jitter_minutes = _deterministic_jitter_minutes(
                account_key=request.account_key,
                channel=request.channel,
                anchor_time=window_start,
                max_jitter_minutes=min(schedule.jitter_minutes, schedule.window_minutes),
            )
            candidate = window_start + timedelta(minutes=jitter_minutes)
            candidate = max(candidate, _ceil_to_minute(normalized_now))
            candidate = _find_valid_candidate(
                candidate=candidate,
                window_end=window_end,
                min_gap_minutes=schedule.min_gap_minutes,
                occupied_times=occupied_times + tuple(slot.scheduled_for for slot in slots),
            )
            if candidate is not None:
                slots.append(
                    PlannedSlot(
                        anchor_time=window_start,
                        window_start=window_start,
                        window_end=window_end,
                        scheduled_for=candidate,
                        jitter_minutes=jitter_minutes,
                    )
                )

            previous_fire_time = window_start
            anchor = trigger.get_next_fire_time(previous_fire_time, previous_fire_time)

        return SlotPlanningResult(slots=tuple(slots), anchors_considered=anchors_considered)


def _deterministic_jitter_minutes(
    *,
    account_key: str,
    channel: str,
    anchor_time: datetime,
    max_jitter_minutes: int,
) -> int:
    if max_jitter_minutes <= 0:
        return 0

    raw_key = f"{account_key}:{channel}:{anchor_time.isoformat()}"
    digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % (max_jitter_minutes + 1)


def _find_valid_candidate(
    *,
    candidate: datetime,
    window_end: datetime,
    min_gap_minutes: int,
    occupied_times: tuple[datetime, ...],
) -> datetime | None:
    normalized_window_end = _normalize_datetime(window_end)
    if candidate > normalized_window_end:
        return None

    if min_gap_minutes <= 0:
        return candidate

    min_gap = timedelta(minutes=min_gap_minutes)
    current = candidate
    while current <= normalized_window_end:
        if all(abs(current - occupied_time) >= min_gap for occupied_time in occupied_times):
            return current
        current += timedelta(minutes=1)
    return None


def _ceil_to_minute(value: datetime) -> datetime:
    normalized = _normalize_datetime(value)
    if normalized.second == 0 and normalized.microsecond == 0:
        return normalized
    return (normalized + timedelta(minutes=1)).replace(second=0, microsecond=0)


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
