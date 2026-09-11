import random
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

from app.models.matching import AvailabilityWindow, CommittedSession, PendingRequest, TutorCandidate
from app.services import matching

TUTOR_ID = uuid4()

STUDENT_ID = uuid4()
MICROTOPIC_ID = uuid4()


def _request(
    request_id=None,
    academic_average: float | None = None,
    funding_deficit_multiplier: float | None = None,
    created_at: datetime = datetime(2026, 1, 1, tzinfo=UTC),
) -> PendingRequest:
    return PendingRequest(
        request_id=request_id or uuid4(),
        student_id=STUDENT_ID,
        microtopic_id=MICROTOPIC_ID,
        starts_at=datetime(2026, 1, 5, 18, 0, tzinfo=UTC),
        duration_minutes=60,
        created_at=created_at,
        academic_average=academic_average,
        funding_deficit_multiplier=funding_deficit_multiplier,
    )


def test_urgency_score_uses_neutral_defaults_when_both_missing() -> None:
    request = _request(academic_average=None, funding_deficit_multiplier=None)
    assert matching.urgency_score(request) == 70.0


def test_urgency_score_uses_neutral_multiplier_when_region_missing() -> None:
    request = _request(academic_average=90.0, funding_deficit_multiplier=None)
    assert matching.urgency_score(request) == 90.0


def test_urgency_score_uses_neutral_average_when_academic_average_missing() -> None:
    request = _request(academic_average=None, funding_deficit_multiplier=2.0)
    assert matching.urgency_score(request) == 140.0


def test_urgency_score_multiplies_when_both_present() -> None:
    request = _request(academic_average=80.0, funding_deficit_multiplier=1.5)
    assert matching.urgency_score(request) == 120.0


def test_order_requests_sorts_by_urgency_descending() -> None:
    low = _request(request_id=uuid4(), academic_average=60.0, funding_deficit_multiplier=1.0)
    high = _request(request_id=uuid4(), academic_average=90.0, funding_deficit_multiplier=1.0)
    mid = _request(request_id=uuid4(), academic_average=75.0, funding_deficit_multiplier=1.0)

    ordered = matching.order_requests([low, high, mid])

    assert [r.request_id for r in ordered] == [high.request_id, mid.request_id, low.request_id]


def test_order_requests_breaks_urgency_ties_by_created_at_ascending() -> None:
    later = _request(
        request_id=uuid4(),
        academic_average=80.0,
        funding_deficit_multiplier=1.0,
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    earlier = _request(
        request_id=uuid4(),
        academic_average=80.0,
        funding_deficit_multiplier=1.0,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )

    ordered = matching.order_requests([later, earlier])

    assert [r.request_id for r in ordered] == [earlier.request_id, later.request_id]


def test_to_request_window_converts_winter_est_to_local_minutes() -> None:
    # 2026-01-05 18:00 UTC = 13:00 EST (America/Toronto, no DST in January).
    starts_at = datetime(2026, 1, 5, 18, 0, tzinfo=UTC)

    window = matching.to_request_window(starts_at, duration_minutes=60)

    assert window.day_of_week == 0  # Monday
    assert window.start_minute == 13 * 60
    assert window.end_minute == 14 * 60
    assert window.local_date == date(2026, 1, 5)
    assert window.week_start == date(2026, 1, 5)
    assert window.duration_minutes == 60
    assert window.is_schedulable is True


def test_to_request_window_spans_spring_forward_gap_in_wall_clock() -> None:
    # 2026-03-08 06:30 UTC = 01:30 EST, the last moment before clocks jump to
    # 03:00 EDT. Real elapsed time is 60 minutes; wall-clock span is 90->210.
    starts_at = datetime(2026, 3, 8, 6, 30, tzinfo=UTC)

    window = matching.to_request_window(starts_at, duration_minutes=60)

    assert window.day_of_week == 6  # Sunday
    assert window.start_minute == 90
    assert window.end_minute == 210
    assert window.is_schedulable is True


def test_to_request_window_collapses_on_fall_back_hour() -> None:
    # 2026-11-01 05:30 UTC = 01:30 EDT, before clocks fall back to 01:00 EST.
    # 60 real minutes later lands back on the same wall-clock 01:30.
    starts_at = datetime(2026, 11, 1, 5, 30, tzinfo=UTC)

    window = matching.to_request_window(starts_at, duration_minutes=60)

    assert window.start_minute == window.end_minute == 90
    assert window.is_schedulable is False


def test_to_request_window_is_unschedulable_when_crossing_local_midnight() -> None:
    # 2026-01-05 23:30 EST (Monday) + 60 minutes = 00:30 EST Tuesday.
    starts_at = datetime(2026, 1, 6, 4, 30, tzinfo=UTC)

    window = matching.to_request_window(starts_at, duration_minutes=60)

    assert window.is_schedulable is False


def test_to_request_window_buckets_sunday_into_prior_mondays_week() -> None:
    # 2026-01-04 is a Sunday; its week runs Dec 29 2025 (Mon) - Jan 4 2026 (Sun).
    starts_at = datetime(2026, 1, 4, 17, 0, tzinfo=UTC)

    window = matching.to_request_window(starts_at, duration_minutes=60)

    assert window.day_of_week == 6
    assert window.local_date == date(2026, 1, 4)
    assert window.week_start == date(2025, 12, 29)


def _candidate(
    availability: tuple[AvailabilityWindow, ...] = (),
    daily_cap_minutes: int = 300,
    weekly_cap_minutes: int = 300,
    commitments: tuple = (),
) -> TutorCandidate:
    return TutorCandidate(
        tutor_id=TUTOR_ID,
        daily_cap_minutes=daily_cap_minutes,
        weekly_cap_minutes=weekly_cap_minutes,
        availability=availability,
        commitments=commitments,
    )


# Monday 13:00-14:00, matching test_to_request_window_converts_winter_est_to_local_minutes.
_MONDAY_WINDOW = matching.to_request_window(datetime(2026, 1, 5, 18, 0, tzinfo=UTC), 60)


def test_covers_window_true_for_exact_fit_availability() -> None:
    candidate = _candidate(
        availability=(AvailabilityWindow(day_of_week=0, start_minute=13 * 60, end_minute=14 * 60),)
    )
    assert matching.covers_window(candidate, _MONDAY_WINDOW) is True


def test_covers_window_false_when_availability_starts_one_minute_late() -> None:
    candidate = _candidate(
        availability=(
            AvailabilityWindow(day_of_week=0, start_minute=13 * 60 + 1, end_minute=14 * 60),
        )
    )
    assert matching.covers_window(candidate, _MONDAY_WINDOW) is False


def test_covers_window_false_when_availability_ends_one_minute_early() -> None:
    candidate = _candidate(
        availability=(
            AvailabilityWindow(day_of_week=0, start_minute=13 * 60, end_minute=14 * 60 - 1),
        )
    )
    assert matching.covers_window(candidate, _MONDAY_WINDOW) is False


def test_covers_window_false_for_wrong_day_of_week() -> None:
    candidate = _candidate(
        availability=(AvailabilityWindow(day_of_week=1, start_minute=13 * 60, end_minute=14 * 60),)
    )
    assert matching.covers_window(candidate, _MONDAY_WINDOW) is False


def _committed(starts_at: datetime, ends_at: datetime) -> CommittedSession:
    local_date = starts_at.astimezone(matching.TORONTO).date()
    return CommittedSession(
        starts_at=starts_at,
        ends_at=ends_at,
        local_date=local_date,
        week_start=local_date - timedelta(days=local_date.weekday()),
        duration_minutes=int((ends_at - starts_at).total_seconds() // 60),
    )


def test_has_conflict_false_when_existing_session_ends_exactly_at_window_start() -> None:
    existing = _committed(
        starts_at=datetime(2026, 1, 5, 17, 0, tzinfo=UTC),
        ends_at=_MONDAY_WINDOW.starts_at,
    )
    candidate = _candidate(commitments=(existing,))
    assert matching.has_conflict(candidate, _MONDAY_WINDOW) is False


def test_has_conflict_false_when_existing_session_starts_exactly_at_window_end() -> None:
    existing = _committed(
        starts_at=_MONDAY_WINDOW.ends_at,
        ends_at=datetime(2026, 1, 5, 20, 0, tzinfo=UTC),
    )
    candidate = _candidate(commitments=(existing,))
    assert matching.has_conflict(candidate, _MONDAY_WINDOW) is False


def test_has_conflict_true_when_existing_session_overlaps_window() -> None:
    existing = _committed(
        starts_at=datetime(2026, 1, 5, 18, 30, tzinfo=UTC),
        ends_at=datetime(2026, 1, 5, 19, 30, tzinfo=UTC),
    )
    candidate = _candidate(commitments=(existing,))
    assert matching.has_conflict(candidate, _MONDAY_WINDOW) is True


def _same_day_committed(minutes: int) -> CommittedSession:
    # A same-local-day, same-local-week commitment distinct from the request window.
    starts_at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    return CommittedSession(
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=minutes),
        local_date=_MONDAY_WINDOW.local_date,
        week_start=_MONDAY_WINDOW.week_start,
        duration_minutes=minutes,
    )


def test_within_caps_false_when_daily_cap_would_be_exceeded() -> None:
    # 240 existing + 60 requested = 300, one minute over a 299 daily cap.
    candidate = _candidate(
        daily_cap_minutes=299, weekly_cap_minutes=1000, commitments=(_same_day_committed(240),)
    )
    assert matching.within_caps(candidate, _MONDAY_WINDOW) is False


def test_within_caps_true_when_exactly_at_daily_cap() -> None:
    candidate = _candidate(
        daily_cap_minutes=300, weekly_cap_minutes=1000, commitments=(_same_day_committed(240),)
    )
    assert matching.within_caps(candidate, _MONDAY_WINDOW) is True


def test_within_caps_false_when_weekly_cap_binds_even_though_daily_does_not() -> None:
    candidate = _candidate(
        daily_cap_minutes=1000, weekly_cap_minutes=299, commitments=(_same_day_committed(240),)
    )
    assert matching.within_caps(candidate, _MONDAY_WINDOW) is False


def _eligible_candidate(tutor_id=None) -> TutorCandidate:
    return TutorCandidate(
        tutor_id=tutor_id or uuid4(),
        daily_cap_minutes=300,
        weekly_cap_minutes=300,
        availability=(AvailabilityWindow(day_of_week=0, start_minute=13 * 60, end_minute=14 * 60),),
        commitments=(),
    )


def test_build_domain_includes_a_fully_eligible_candidate() -> None:
    candidate = _eligible_candidate()
    assert matching.build_domain([candidate], _MONDAY_WINDOW) == [candidate]


def test_build_domain_excludes_candidate_without_matching_availability() -> None:
    candidate = _candidate(availability=())
    assert matching.build_domain([candidate], _MONDAY_WINDOW) == []


def test_build_domain_excludes_candidate_with_conflicting_session() -> None:
    conflicting = _committed(
        starts_at=datetime(2026, 1, 5, 18, 30, tzinfo=UTC),
        ends_at=datetime(2026, 1, 5, 19, 30, tzinfo=UTC),
    )
    eligible = _eligible_candidate()
    candidate = TutorCandidate(
        tutor_id=eligible.tutor_id,
        daily_cap_minutes=eligible.daily_cap_minutes,
        weekly_cap_minutes=eligible.weekly_cap_minutes,
        availability=eligible.availability,
        commitments=(conflicting,),
    )
    assert matching.build_domain([candidate], _MONDAY_WINDOW) == []


def test_build_domain_excludes_candidate_over_cap() -> None:
    eligible = _eligible_candidate()
    candidate = TutorCandidate(
        tutor_id=eligible.tutor_id,
        daily_cap_minutes=59,
        weekly_cap_minutes=eligible.weekly_cap_minutes,
        availability=eligible.availability,
        commitments=(),
    )
    assert matching.build_domain([candidate], _MONDAY_WINDOW) == []


def test_select_match_returns_none_for_empty_domain() -> None:
    assert matching.select_match([], _MONDAY_WINDOW, random.Random(1)) is None


def test_select_match_is_deterministic_for_a_given_seed() -> None:
    candidates = [_eligible_candidate(tutor_id=uuid4()) for _ in range(5)]
    first = matching.select_match(candidates, _MONDAY_WINDOW, random.Random(42))
    second = matching.select_match(candidates, _MONDAY_WINDOW, random.Random(42))
    assert first == second


def test_select_match_is_independent_of_input_order() -> None:
    candidates = [_eligible_candidate(tutor_id=uuid4()) for _ in range(5)]
    shuffled = list(reversed(candidates))
    original_pick = matching.select_match(candidates, _MONDAY_WINDOW, random.Random(7))
    shuffled_pick = matching.select_match(shuffled, _MONDAY_WINDOW, random.Random(7))
    assert original_pick == shuffled_pick


def test_to_committed_session_derives_local_date_and_week_start() -> None:
    # Same Monday 13:00-14:00 EST session used throughout this file.
    session = matching.to_committed_session(_MONDAY_WINDOW.starts_at, _MONDAY_WINDOW.ends_at)

    assert session.local_date == date(2026, 1, 5)
    assert session.week_start == date(2026, 1, 5)
    assert session.duration_minutes == 60


def test_pending_request_from_row_parses_nested_urgency_inputs() -> None:
    row = {
        "id": str(REQUEST_ID_FOR_ROW := uuid4()),
        "student_id": str(STUDENT_ID),
        "microtopic_id": str(MICROTOPIC_ID),
        "starts_at": "2026-01-05T18:00:00+00:00",
        "duration_minutes": 60,
        "created_at": "2026-01-01T00:00:00+00:00",
        "student_profiles": {
            "academic_average": 85.0,
            "regions": {"funding_deficit_multiplier": 1.5},
        },
    }

    request = PendingRequest.from_row(row)

    assert request.request_id == REQUEST_ID_FOR_ROW
    assert request.academic_average == 85.0
    assert request.funding_deficit_multiplier == 1.5


def test_pending_request_from_row_handles_missing_student_or_region() -> None:
    row = {
        "id": str(uuid4()),
        "student_id": str(STUDENT_ID),
        "microtopic_id": str(MICROTOPIC_ID),
        "starts_at": "2026-01-05T18:00:00+00:00",
        "duration_minutes": 60,
        "created_at": "2026-01-01T00:00:00+00:00",
        "student_profiles": {"academic_average": None, "regions": None},
    }

    request = PendingRequest.from_row(row)

    assert request.academic_average is None
    assert request.funding_deficit_multiplier is None
