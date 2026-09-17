# src/attendance/reports/calculations.py

from datetime import datetime


def calculate_presence_seconds(events: list, session_start, session_end) -> float:
    """
    Dado los eventos entry/exit de UN estudiante en UNA sesión (ya filtrados y ordenados),
    regresa los segundos totales que estuvo presente.
    """
    total_seconds = 0.0
    entry_time = None

    for event in events:
        if event.event_type == "entry":
            entry_time = event.timestamp
        elif event.event_type == "exit" and entry_time is not None:
            total_seconds += (event.timestamp - entry_time).total_seconds()
            entry_time = None

    return total_seconds


def calculate_attendance_percentage(engine, session_id: int, student_id: str) -> float:
    """% de asistencia de un estudiante en una sesión específica."""
    from attendance.db.queries import get_events_for_session
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
