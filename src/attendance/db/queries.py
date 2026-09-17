# src/attendance/db/queries.py

from datetime import datetime
from sqlalchemy import select, insert
from sqlalchemy.engine import Engine

from attendance.db.schema import (
    teachers, subjects, groups, students,
    face_embeddings, class_sessions, attendance_events,
    session_snapshots,
)


# ---------------------------------------------------------------------
# Teachers / Subjects / Groups — setup inicial (seed)
# ---------------------------------------------------------------------

def create_teacher(engine: Engine, full_name: str) -> int:
    with engine.begin() as conn:
        result = conn.execute(insert(teachers).values(full_name=full_name))
        return result.inserted_primary_key[0]


def create_subject(engine: Engine, name: str, teacher_id: int) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            insert(subjects).values(name=name, teacher_id=teacher_id)
        )
        return result.inserted_primary_key[0]


def create_group(engine: Engine, name: str, subject_id: int) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            insert(groups).values(name=name, subject_id=subject_id)
        )
        return result.inserted_primary_key[0]


# ---------------------------------------------------------------------
# Students / Embeddings — enrollment
# ---------------------------------------------------------------------

def create_student(engine: Engine, student_id: str, full_name: str, group_id: int) -> None:
    with engine.begin() as conn:
        conn.execute(
            insert(students).values(id=student_id, full_name=full_name, group_id=group_id)
        )


def add_face_embedding(engine: Engine, student_id: str, embedding_bytes: bytes, source_photo: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            insert(face_embeddings).values(
                student_id=student_id,
                embedding=embedding_bytes,
                source_photo=source_photo,
            )
        )


def get_all_embeddings(engine: Engine):
    """Regresa todas las filas (student_id, embedding) para matching."""
    with engine.connect() as conn:
        result = conn.execute(
            select(face_embeddings.c.student_id, face_embeddings.c.embedding)
        )
        return result.fetchall()


def get_students_by_group(engine: Engine, group_id: int):
    with engine.connect() as conn:
        result = conn.execute(
            select(students).where(students.c.group_id == group_id)
        )
        return result.fetchall()


# ---------------------------------------------------------------------
# Class sessions
# ---------------------------------------------------------------------

def start_session(engine: Engine, group_id: int) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            insert(class_sessions).values(
                group_id=group_id,
                started_at=datetime.utcnow(),
                status="active",
            )
        )
        return result.inserted_primary_key[0]


def end_session(engine: Engine, session_id: int) -> None:
    from sqlalchemy import update
    with engine.begin() as conn:
        conn.execute(
            update(class_sessions)
            .where(class_sessions.c.id == session_id)
            .values(ended_at=datetime.utcnow(), status="finished")
        )


# ---------------------------------------------------------------------
# Attendance events
# ---------------------------------------------------------------------

def log_event(engine: Engine, session_id: int, student_id: str, event_type: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            insert(attendance_events).values(
                session_id=session_id,
                student_id=student_id,
                event_type=event_type,
                timestamp=datetime.utcnow(),
            )
        )


def get_events_for_session(engine: Engine, session_id: int):
    with engine.connect() as conn:
        result = conn.execute(
            select(attendance_events).where(attendance_events.c.session_id == session_id)
        )
        return result.fetchall()

def get_active_session(engine, group_id: int):
    with engine.connect() as conn:
        result = conn.execute(
            select(class_sessions)
            .where(class_sessions.c.group_id == group_id)
            .where(class_sessions.c.status == "active")
            .order_by(class_sessions.c.started_at.desc())
        )
        rows = result.fetchall()
        if len(rows) > 1:
            print(f"ADVERTENCIA: {len(rows)} sesiones activas simultáneas para group_id={group_id}")
        return rows[0] if rows else None

def log_snapshot(engine, session_id: int, people_detected: int, people_identified: int) -> None:
    with engine.begin() as conn:
        conn.execute(
            insert(session_snapshots).values(
                session_id=session_id,
                timestamp=datetime.utcnow(),
                people_detected=people_detected,
                people_identified=people_identified,
            )
        )