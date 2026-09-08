"""
SM-2 spaced repetition scheduling.

Deliberately free of any database or FastAPI import: the whole algorithm is a
pure function over the four numbers a topic carries (`repetitions`,
`interval_days`, `ease_factor`, `lapses`) plus the grade the user pressed, so
it can be unit tested without a Supabase connection. See
backend/tests/test_spaced_repetition.py.

The UI offers four buttons — Zor / Orta / Kolay / Cok Kolay — rather than
SM-2's raw 0..5 quality scale. Only the top half of that scale is reachable,
because a topic the user cannot answer at all is not a "grade" in this app; it
is a topic they open and study again. So "Zor" is the failing grade (q=2): it
resets the repetition count and sends the topic back to tomorrow.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

# -- Tunables ---------------------------------------------------

#: Ease factor a topic starts life with, straight from SM-2.
DEFAULT_EASE_FACTOR = 2.5
#: SM-2's floor. Below this the intervals stop growing meaningfully and the
#: topic would be shown almost daily forever.
MIN_EASE_FACTOR = 1.3
#: Not part of SM-2 - a ceiling that keeps a long streak of "Cok Kolay" from
#: pushing a topic years into the future.
MAX_EASE_FACTOR = 5.0
#: First two intervals are fixed by SM-2; only from the third review on does
#: the ease factor drive the spacing.
FIRST_INTERVAL_DAYS = 1
SECOND_INTERVAL_DAYS = 6
#: Cap on a single interval. An exam-prep tool that schedules a topic 5 years
#: out is not useful; item 7 (exam countdown) will tighten this further.
MAX_INTERVAL_DAYS = 365

#: The four buttons, and the SM-2 quality each maps to.
GRADE_QUALITY: dict[str, int] = {
    "hard": 2,       # Zor       - failed, reschedule for tomorrow
    "medium": 3,     # Orta      - recalled with effort
    "easy": 4,       # Kolay     - recalled comfortably
    "very_easy": 5,  # Cok Kolay - instant recall
}

#: Below this quality the review counts as a lapse and the streak resets.
PASSING_QUALITY = 3

VALID_GRADES = tuple(GRADE_QUALITY)


@dataclass(frozen=True)
class ReviewState:
    """A topic's scheduling state - the columns added by the SR migration."""

    repetitions: int = 0
    interval_days: int = 0
    ease_factor: float = DEFAULT_EASE_FACTOR
    lapses: int = 0
    last_reviewed_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: dict) -> "ReviewState":
        """Build from a `topics` row, tolerating rows written before the
        migration (every column falls back to its default)."""
        return cls(
            repetitions=int(row.get("repetitions") or 0),
            interval_days=int(row.get("interval_days") or 0),
            ease_factor=float(row.get("ease_factor") or DEFAULT_EASE_FACTOR),
            lapses=int(row.get("lapses") or 0),
            last_reviewed_at=parse_timestamp(row.get("last_reviewed_at")),
            next_review_at=parse_timestamp(row.get("next_review_at")),
        )

    def to_update(self) -> dict:
        """Serialise back into the column payload the repository writes."""
        return {
            "repetitions": self.repetitions,
            "interval_days": self.interval_days,
            "ease_factor": round(self.ease_factor, 4),
            "lapses": self.lapses,
            "last_reviewed_at": _iso(self.last_reviewed_at),
            "next_review_at": _iso(self.next_review_at),
        }


def parse_timestamp(value) -> Optional[datetime]:
    """Postgres timestamptz as supabase-py returns it - a string - into an
    aware datetime. Already-parsed datetimes pass through."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).replace("Z", "+00:00")
    # Postgres emits fractional seconds at whatever precision it has; a stray
    # parse failure here should not take down a review submission.
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.astimezone(timezone.utc).isoformat() if value else None


def quality_for_grade(grade: str) -> int:
    """Map a button to its SM-2 quality, rejecting anything unknown."""
    try:
        return GRADE_QUALITY[grade]
    except KeyError:
        raise ValueError(
            "Unknown grade " + repr(grade) + "; expected one of " + ", ".join(VALID_GRADES)
        ) from None


def next_ease_factor(ease_factor: float, quality: int) -> float:
    """
    SM-2's ease update, clamped to [MIN, MAX].

    At q=4 the term is exactly zero, so "Kolay" holds the ease steady; "Cok
    Kolay" adds 0.10, "Orta" subtracts 0.14 and "Zor" subtracts 0.32. Unlike
    textbook SM-2 this is applied on failure too, which is what makes a
    repeatedly-failed topic drift towards the 1.3 floor - the signal
    weak-topic detection (item 2) reads.
    """
    delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    return max(MIN_EASE_FACTOR, min(MAX_EASE_FACTOR, ease_factor + delta))


def review(
    state: ReviewState,
    grade: str,
    *,
    now: Optional[datetime] = None,
) -> ReviewState:
    """
    Apply one graded review and return the new state.

    Pure: `state` is untouched, and `now` is injectable so tests do not depend
    on the wall clock.
    """
    quality = quality_for_grade(grade)
    reviewed_at = now or datetime.now(timezone.utc)

    ease_factor = next_ease_factor(state.ease_factor, quality)

    if quality < PASSING_QUALITY:
        # Failed: the streak is gone and the topic comes back tomorrow. The
        # lowered ease factor is kept, so the topic climbs back more slowly
        # than a fresh one would.
        repetitions = 0
        interval_days = FIRST_INTERVAL_DAYS
        lapses = state.lapses + 1
    else:
        repetitions = state.repetitions + 1
        lapses = state.lapses
        if repetitions == 1:
            interval_days = FIRST_INTERVAL_DAYS
        elif repetitions == 2:
            interval_days = SECOND_INTERVAL_DAYS
        else:
            # From the third review on, the previous interval is stretched by
            # the ease factor. `max(1, ...)` guards a state that somehow
            # arrives with interval_days = 0 while repetitions > 2.
            interval_days = round(max(1, state.interval_days) * ease_factor)
        interval_days = min(interval_days, MAX_INTERVAL_DAYS)

    return ReviewState(
        repetitions=repetitions,
        interval_days=interval_days,
        ease_factor=ease_factor,
        lapses=lapses,
        last_reviewed_at=reviewed_at,
        next_review_at=reviewed_at + timedelta(days=interval_days),
    )


def preview_intervals(
    state: ReviewState,
    *,
    now: Optional[datetime] = None,
) -> dict[str, int]:
    """
    What each button would schedule, in days - so the review screen can label
    them ("Kolay - 12 gun") before the user commits to one.
    """
    return {grade: review(state, grade, now=now).interval_days for grade in VALID_GRADES}


def is_due(state: ReviewState, *, now: Optional[datetime] = None) -> bool:
    """A topic with no schedule at all counts as due - that is the state every
    topic starts in."""
    if state.next_review_at is None:
        return True
    return state.next_review_at <= (now or datetime.now(timezone.utc))


def days_until_due(state: ReviewState, *, now: Optional[datetime] = None) -> int:
    """
    Whole days until the next review; negative when overdue.

    Rounded towards the user: a topic due in 30 hours reads as "1 gun", and
    one 18 hours overdue reads as "-1 gun" rather than 0, so an overdue topic
    never displays as if it were due exactly now.
    """
    if state.next_review_at is None:
        return 0
    seconds = (state.next_review_at - (now or datetime.now(timezone.utc))).total_seconds()
    days = seconds / 86400
    return int(days) if seconds >= 0 else -int(-days + 0.999999)
