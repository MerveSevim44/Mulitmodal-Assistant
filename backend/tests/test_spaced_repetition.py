"""
Unit tests for the SM-2 scheduler.

pytest is not in requirements.txt, so these are written as plain assert
functions with a __main__ runner:

    python backend/tests/test_spaced_repetition.py

They are still ordinary pytest test functions, so `pytest backend/tests` works
unchanged once pytest is installed.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import spaced_repetition as sr  # noqa: E402

NOW = datetime(2026, 9, 8, 9, 0, tzinfo=timezone.utc)


def fresh() -> sr.ReviewState:
    return sr.ReviewState()


def test_new_topic_is_due_immediately():
    assert sr.is_due(fresh(), now=NOW)
    assert sr.days_until_due(fresh(), now=NOW) == 0


def test_first_successful_review_schedules_one_day():
    state = sr.review(fresh(), "medium", now=NOW)
    assert state.repetitions == 1
    assert state.interval_days == sr.FIRST_INTERVAL_DAYS
    assert state.next_review_at == NOW + timedelta(days=1)
    assert state.last_reviewed_at == NOW


def test_second_successful_review_schedules_six_days():
    state = sr.review(fresh(), "easy", now=NOW)
    state = sr.review(state, "easy", now=NOW + timedelta(days=1))
    assert state.repetitions == 2
    assert state.interval_days == sr.SECOND_INTERVAL_DAYS


def test_third_review_multiplies_by_ease_factor():
    state = sr.review(fresh(), "easy", now=NOW)
    state = sr.review(state, "easy", now=NOW)
    # "Kolay" (q=4) leaves the ease factor at its 2.5 default, so the third
    # interval is exactly 6 * 2.5 = 15 days.
    state = sr.review(state, "easy", now=NOW)
    assert state.ease_factor == sr.DEFAULT_EASE_FACTOR
    assert state.interval_days == 15


def test_ease_factor_moves_in_the_right_direction():
    assert sr.next_ease_factor(2.5, 5) > 2.5           # cok kolay
    assert sr.next_ease_factor(2.5, 4) == 2.5          # kolay - unchanged
    assert sr.next_ease_factor(2.5, 3) < 2.5           # orta
    assert sr.next_ease_factor(2.5, 2) < sr.next_ease_factor(2.5, 3)  # zor


def test_ease_factor_is_floored():
    ease = 2.5
    for _ in range(20):
        ease = sr.next_ease_factor(ease, 2)
    assert ease == sr.MIN_EASE_FACTOR


def test_ease_factor_is_capped():
    ease = 2.5
    for _ in range(100):
        ease = sr.next_ease_factor(ease, 5)
    assert ease == sr.MAX_EASE_FACTOR


def test_hard_grade_resets_streak_and_counts_a_lapse():
    state = fresh()
    for _ in range(4):
        state = sr.review(state, "easy", now=NOW)
    assert state.repetitions == 4
    assert state.interval_days > 6

    lapsed = sr.review(state, "hard", now=NOW)
    assert lapsed.repetitions == 0
    assert lapsed.interval_days == sr.FIRST_INTERVAL_DAYS
    assert lapsed.lapses == 1
    assert lapsed.ease_factor < state.ease_factor


def test_recovery_after_a_lapse_is_slower_than_a_fresh_topic():
    """A lapsed topic keeps its lowered ease, so it re-expands more slowly."""
    lapsed = fresh()
    for _ in range(3):
        lapsed = sr.review(lapsed, "hard", now=NOW)
    for _ in range(3):
        lapsed = sr.review(lapsed, "easy", now=NOW)

    clean = fresh()
    for _ in range(3):
        clean = sr.review(clean, "easy", now=NOW)

    assert lapsed.interval_days < clean.interval_days


def test_interval_is_capped():
    state = fresh()
    for _ in range(30):
        state = sr.review(state, "very_easy", now=NOW)
    assert state.interval_days == sr.MAX_INTERVAL_DAYS


def test_preview_intervals_are_ordered_and_do_not_mutate():
    state = fresh()
    for _ in range(3):
        state = sr.review(state, "easy", now=NOW)

    before = state
    preview = sr.preview_intervals(state, now=NOW)

    assert state == before, "preview must not mutate the state it is given"
    assert set(preview) == set(sr.VALID_GRADES)
    assert preview["hard"] == sr.FIRST_INTERVAL_DAYS
    assert preview["medium"] < preview["easy"] < preview["very_easy"]
    # And the preview matches what actually happens when the button is pressed.
    for grade, days in preview.items():
        assert sr.review(state, grade, now=NOW).interval_days == days


def test_unknown_grade_is_rejected():
    try:
        sr.review(fresh(), "again", now=NOW)
    except ValueError as exc:
        assert "again" in str(exc)
    else:
        raise AssertionError("an unknown grade should raise ValueError")


def test_days_until_due_rounds_towards_the_user():
    soon = sr.ReviewState(next_review_at=NOW + timedelta(hours=30))
    assert sr.days_until_due(soon, now=NOW) == 1

    overdue = sr.ReviewState(next_review_at=NOW - timedelta(hours=18))
    assert sr.days_until_due(overdue, now=NOW) == -1
    assert sr.is_due(overdue, now=NOW)

    later = sr.ReviewState(next_review_at=NOW + timedelta(hours=1))
    assert sr.days_until_due(later, now=NOW) == 0
    assert not sr.is_due(later, now=NOW)


def test_round_trips_through_a_database_row():
    state = sr.review(fresh(), "medium", now=NOW)
    payload = state.to_update()

    # Naive strings and a missing column are both what real rows look like.
    row = dict(payload)
    restored = sr.ReviewState.from_row(row)
    assert restored.repetitions == state.repetitions
    assert restored.interval_days == state.interval_days
    assert abs(restored.ease_factor - state.ease_factor) < 1e-4
    assert restored.next_review_at == state.next_review_at

    legacy = sr.ReviewState.from_row({"name": "pre-migration topic"})
    assert legacy.ease_factor == sr.DEFAULT_EASE_FACTOR
    assert legacy.next_review_at is None
    assert sr.is_due(legacy, now=NOW)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for test in tests:
        try:
            test()
            print("  PASS  " + test.__name__)
        except Exception as exc:  # noqa: BLE001 - a test runner reports everything
            failed += 1
            print("  FAIL  " + test.__name__ + ": " + repr(exc))
    print("\n" + str(len(tests) - failed) + "/" + str(len(tests)) + " passed")
    sys.exit(1 if failed else 0)
