"""Attendance metric calculations.

Derives attendance percentages and presence durations from raw
entry/exit events. Nothing here is pre-aggregated or cached: every
metric is recomputed from ``attendance_events`` on demand, which keeps
the derived numbers always consistent with the source data at the cost
of recalculating on every call. At the current scale (dozens of
sessions, a few dozen students) this is effectively instantaneous;
should the dataset grow much larger, this would be the first place to
consider caching or pre-aggregation.
"""

from attendance.db.queries import get_sessions_by_group, get_events_for_session, get_students_by_group


def calculate_presence_seconds(events: list, session_start, session_end) -> float:
    """Sum the total seconds a student was present, from their events.

    Pairs each "entry" event with the next "exit" event to compute
    presence intervals. Assumes events are well-formed (every entry is
    eventually followed by an exit), which is guaranteed by
    ``PresenceTracker.finalize_session`` closing out any session in
    progress.

    Args:
        events: A list of a single student's attendance events within
            one session, in any order.
        session_start: The session's start time (currently unused, but
            kept in the signature for clarity about scope).
        session_end: The session's end time (currently unused, same as
            above).

    Returns:
        Total seconds of recorded presence.
    """
    total_seconds = 0.0
    entry_time = None

    for event in sorted(events, key=lambda e: e.timestamp):
        if event.event_type == "entry":
            entry_time = event.timestamp
        elif event.event_type == "exit" and entry_time is not None:
            total_seconds += (event.timestamp - entry_time).total_seconds()
            entry_time = None

    return total_seconds


def calculate_attendance_percentage(engine, session_id: int, student_id: str) -> float:
    """Calculate one student's attendance percentage for one session.

    Args:
        engine: SQLAlchemy engine.
        session_id: ID of the session to evaluate.
        student_id: The student's ID.

    Returns:
        A percentage between 0 and 100. Returns 0.0 if the session
        hasn't ended yet or has no recorded duration.
    """
    from sqlalchemy import select
    from attendance.db.schema import class_sessions

    with engine.connect() as conn:
        session = conn.execute(
            select(class_sessions).where(class_sessions.c.id == session_id)
        ).first()

    if session is None or session.ended_at is None:
        return 0.0

    session_duration = (session.ended_at - session.started_at).total_seconds()
    if session_duration <= 0:
        return 0.0

    all_events = get_events_for_session(engine, session_id)
    student_events = [e for e in all_events if e.student_id == student_id]

    presence_seconds = calculate_presence_seconds(student_events, session.started_at, session.ended_at)
    return min(presence_seconds / session_duration * 100, 100.0)


def build_attendance_dataframe(engine, group_id: int) -> list[dict]:
    """Build a flat list of per-student, per-session attendance records.

    Computes attendance percentage and minutes present for every
    combination of student and finished session in a group, ready to
    be loaded into a pandas DataFrame for charting.

    Args:
        engine: SQLAlchemy engine.
        group_id: ID of the group to build the dataset for.

    Returns:
        A list of dicts, each with: student_id, full_name, session_id,
        session_date, percentage, and minutes_present.
    """
    sessions = get_sessions_by_group(engine, group_id)
    students = get_students_by_group(engine, group_id)
    student_lookup = {s.id: s.full_name for s in students}

    rows = []
    for session in sessions:
        if session.ended_at is None:
            continue
        session_duration = (session.ended_at - session.started_at).total_seconds()
        if session_duration <= 0:
            continue

        events = get_events_for_session(engine, session.id)

        for student in students:
            student_events = [e for e in events if e.student_id == student.id]
            presence_seconds = calculate_presence_seconds(student_events, session.started_at, session.ended_at)
            percentage = min(presence_seconds / session_duration * 100, 100.0)

            rows.append({
                "student_id": student.id,
                "full_name": student_lookup[student.id],
                "session_id": session.id,
                "session_date": session.started_at,
                "percentage": round(percentage, 1),
                "minutes_present": round(presence_seconds / 60, 1),
            })

    return rows