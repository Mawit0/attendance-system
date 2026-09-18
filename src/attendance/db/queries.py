"""Database access layer.

Contains every read and write operation used across the system. Both
the camera worker (writer) and the Streamlit dashboard (reader) import
from this module exclusively, ensuring there is a single source of
truth for how data is accessed.

Write operations use ``engine.begin()`` (transactional, auto-commits
on success and rolls back on failure). Read operations use
``engine.connect()`` (no transaction needed, since nothing is being
modified).
"""

from datetime import datetime

from sqlalchemy import select, insert, update

from attendance.db.schema import (
    teachers, subjects, groups, students,
    face_embeddings, class_sessions, attendance_events,
    session_snapshots,
)


# ---------------------------------------------------------------------
# Teachers / Subjects / Groups — initial setup (seed data)
# ---------------------------------------------------------------------

def create_teacher(engine, full_name: str) -> int:
    """Insert a new teacher record.

    Args:
        engine: SQLAlchemy engine.
        full_name: Teacher's full name.

    Returns:
        The newly created teacher's primary key.
    """
    with engine.begin() as conn:
        result = conn.execute(insert(teachers).values(full_name=full_name))
        return result.inserted_primary_key[0]


def create_subject(engine, name: str, teacher_id: int) -> int:
    """Insert a new subject, associated with a teacher.

    Returns:
        The newly created subject's primary key.
    """
    with engine.begin() as conn:
        result = conn.execute(
            insert(subjects).values(name=name, teacher_id=teacher_id)
        )
        return result.inserted_primary_key[0]


def create_group(engine, name: str, subject_id: int) -> int:
    """Insert a new group (e.g. "9A"), associated with a subject.

    Returns:
        The newly created group's primary key.
    """
    with engine.begin() as conn:
        result = conn.execute(
            insert(groups).values(name=name, subject_id=subject_id)
        )
        return result.inserted_primary_key[0]


# ---------------------------------------------------------------------
# Students / Embeddings — enrollment
# ---------------------------------------------------------------------

def create_student(engine, student_id: str, full_name: str, group_id: int) -> None:
    """Insert a new student. The student ID (matrícula) is the primary key."""
    with engine.begin() as conn:
        conn.execute(
            insert(students).values(id=student_id, full_name=full_name, group_id=group_id)
        )


def get_student_by_id(engine, student_id: str):
    """Look up a single student by their ID.

    Returns:
        The student row, or None if no student with that ID exists.
    """
    with engine.connect() as conn:
        result = conn.execute(select(students).where(students.c.id == student_id))
        return result.first()


def add_face_embedding(engine, student_id: str, embedding_bytes: bytes, source_photo: str) -> None:
    """Store one face embedding for a student.

    A student typically has multiple embeddings (one per enrollment
    photo); matching compares a live embedding against all of them.
    """
    with engine.begin() as conn:
        conn.execute(
            insert(face_embeddings).values(
                student_id=student_id,
                embedding=embedding_bytes,
                source_photo=source_photo,
            )
        )


def get_all_embeddings(engine):
    """Fetch every stored (student_id, embedding) pair for matching.

    Returns:
        A list of rows with ``student_id`` and ``embedding`` columns.
    """
    with engine.connect() as conn:
        result = conn.execute(
            select(face_embeddings.c.student_id, face_embeddings.c.embedding)
        )
        return result.fetchall()


def get_students_by_group(engine, group_id: int):
    """Fetch all students belonging to a given group."""
    with engine.connect() as conn:
        result = conn.execute(
            select(students).where(students.c.group_id == group_id)
        )
        return result.fetchall()


def has_attendance_history(engine, student_id: str) -> bool:
    """Check whether a student has any recorded attendance events.

    Used to warn before deleting a student who has real historical
    data, as opposed to one added only for testing.
    """
    with engine.connect() as conn:
        result = conn.execute(
            select(attendance_events).where(attendance_events.c.student_id == student_id).limit(1)
        )
        return result.first() is not None


def delete_student(engine, student_id: str) -> None:
    """Permanently delete a student, their embeddings, and their
    attendance history.

    Deletes in dependency order (events and embeddings first) to
    satisfy the foreign key constraints enforced by SQLite.
    """
    with engine.begin() as conn:
        conn.execute(attendance_events.delete().where(attendance_events.c.student_id == student_id))
        conn.execute(face_embeddings.delete().where(face_embeddings.c.student_id == student_id))
        conn.execute(students.delete().where(students.c.id == student_id))


# ---------------------------------------------------------------------
# Class sessions
# ---------------------------------------------------------------------

def start_session(engine, group_id: int) -> int:
    """Create a new active class session for a group.

    Returns:
        The newly created session's primary key.
    """
    with engine.begin() as conn:
        result = conn.execute(
            insert(class_sessions).values(
                group_id=group_id,
                started_at=datetime.utcnow(),
                status="active",
            )
        )
        return result.inserted_primary_key[0]


def end_session(engine, session_id: int) -> None:
    """Mark a session as finished and record its end time."""
    with engine.begin() as conn:
        conn.execute(
            update(class_sessions)
            .where(class_sessions.c.id == session_id)
            .values(ended_at=datetime.utcnow(), status="finished")
        )


def get_active_session(engine, group_id: int):
    """Fetch the currently active session for a group, if any.

    If more than one active session exists for the group (which should
    not normally happen), the most recently started one is returned
    and a warning is printed, since this indicates a bug elsewhere
    (e.g. the worker being launched twice).

    Returns:
        The active session row, or None if there isn't one.
    """
    with engine.connect() as conn:
        result = conn.execute(
            select(class_sessions)
            .where(class_sessions.c.group_id == group_id)
            .where(class_sessions.c.status == "active")
            .order_by(class_sessions.c.started_at.desc())
        )
        rows = result.fetchall()
        if len(rows) > 1:
            print(f"WARNING: {len(rows)} simultaneous active sessions for group_id={group_id}")
        return rows[0] if rows else None


def get_sessions_by_group(engine, group_id: int):
    """Fetch all finished sessions for a group, ordered chronologically."""
    with engine.connect() as conn:
        result = conn.execute(
            select(class_sessions)
            .where(class_sessions.c.group_id == group_id)
            .where(class_sessions.c.status == "finished")
            .order_by(class_sessions.c.started_at)
        )
        return result.fetchall()


# ---------------------------------------------------------------------
# Attendance events
# ---------------------------------------------------------------------

def log_event(engine, session_id: int, student_id: str, event_type: str) -> None:
    """Record an entry or exit event for a student in a session.

    Args:
        event_type: Either "entry" or "exit".
    """
    with engine.begin() as conn:
        conn.execute(
            insert(attendance_events).values(
                session_id=session_id,
                student_id=student_id,
                event_type=event_type,
                timestamp=datetime.utcnow(),
            )
        )


def get_events_for_session(engine, session_id: int):
    """Fetch all attendance events recorded for a session."""
    with engine.connect() as conn:
        result = conn.execute(
            select(attendance_events).where(attendance_events.c.session_id == session_id)
        )
        return result.fetchall()


def get_events_for_student(engine, student_id: str):
    """Fetch all attendance events for a student across every session
    they have participated in, ordered chronologically.
    """
    with engine.connect() as conn:
        result = conn.execute(
            select(attendance_events)
            .where(attendance_events.c.student_id == student_id)
            .order_by(attendance_events.c.timestamp)
        )
        return result.fetchall()


# ---------------------------------------------------------------------
# Session snapshots (YOLO person count vs. InsightFace identification)
# ---------------------------------------------------------------------

def log_snapshot(engine, session_id: int, people_detected: int, people_identified: int) -> None:
    """Record one detection cycle's counts from both ML models."""
    with engine.begin() as conn:
        conn.execute(
            insert(session_snapshots).values(
                session_id=session_id,
                timestamp=datetime.utcnow(),
                people_detected=people_detected,
                people_identified=people_identified,
            )
        )


def get_latest_snapshot(engine, session_id: int):
    """Fetch the most recent snapshot for a session, used to show the
    current YOLO/InsightFace detection gap in the live dashboard.
    """
    with engine.connect() as conn:
        result = conn.execute(
            select(session_snapshots)
            .where(session_snapshots.c.session_id == session_id)
            .order_by(session_snapshots.c.timestamp.desc())
        )
        return result.first()