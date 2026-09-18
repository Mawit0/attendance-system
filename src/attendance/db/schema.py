"""Database schema definitions using SQLAlchemy Core.

Defines all tables for the attendance system: teachers, subjects, groups,
students, face embeddings, class sessions, attendance events, and
per-cycle detection snapshots. Uses SQLAlchemy Core (not the ORM) to
keep the data layer lightweight and to make a future migration to
PostgreSQL straightforward if the system needs to scale beyond a
single local instance.
"""

from datetime import datetime

from sqlalchemy import (
    MetaData, Table, Column,
    Integer, String, DateTime, LargeBinary,
    ForeignKey, CheckConstraint,
)

metadata = MetaData()

# ---------------------------------------------------------------------
# teachers — MVP: a single record, no login/authentication yet
# ---------------------------------------------------------------------
teachers = Table(
    "teachers", metadata,
    Column("id", Integer, primary_key=True),
    Column("full_name", String, nullable=False),
)

# ---------------------------------------------------------------------
# subjects — e.g. "Visual Modeling for Information"
# ---------------------------------------------------------------------
subjects = Table(
    "subjects", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False, unique=True),
    Column("teacher_id", Integer, ForeignKey("teachers.id"), nullable=False),
)

# ---------------------------------------------------------------------
# groups — e.g. "9A", "9B" — each group belongs to one subject
# ---------------------------------------------------------------------
groups = Table(
    "groups", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),
    Column("subject_id", Integer, ForeignKey("subjects.id"), nullable=False),
)

# ---------------------------------------------------------------------
# students — the student ID (matrícula) is used directly as the
# primary key, since it is a stable, unique identifier that never
# changes at the institution.
# ---------------------------------------------------------------------
students = Table(
    "students", metadata,
    Column("id", String, primary_key=True),
    Column("full_name", String, nullable=False),
    Column("group_id", Integer, ForeignKey("groups.id"), nullable=False),
)

# ---------------------------------------------------------------------
# face_embeddings — a student can have multiple embeddings (one per
# enrollment photo). Matching compares a live embedding against all
# stored embeddings for a student and keeps the best match, improving
# tolerance to lighting and angle variation.
# ---------------------------------------------------------------------
face_embeddings = Table(
    "face_embeddings", metadata,
    Column("id", Integer, primary_key=True),
    Column("student_id", String, ForeignKey("students.id"), nullable=False),
    Column("embedding", LargeBinary, nullable=False),  # serialized numpy array (float32)
    Column("source_photo", String, nullable=True),
    Column("created_at", DateTime, default=datetime.utcnow),
)

# ---------------------------------------------------------------------
# class_sessions — a single class occurrence on a given date/time
# ---------------------------------------------------------------------
class_sessions = Table(
    "class_sessions", metadata,
    Column("id", Integer, primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id"), nullable=False),
    Column("started_at", DateTime, nullable=False),
    Column("ended_at", DateTime, nullable=True),  # NULL while the session is active
    Column("status", String, nullable=False, default="active"),
    CheckConstraint("status IN ('active', 'finished')", name="valid_status"),
)

# ---------------------------------------------------------------------
# attendance_events — entry/exit events only (not raw per-frame
# detections). A student may have multiple entry/exit pairs within a
# single session if they leave and return, which allows precise
# calculation of total presence time rather than a simple boolean.
# ---------------------------------------------------------------------
attendance_events = Table(
    "attendance_events", metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", Integer, ForeignKey("class_sessions.id"), nullable=False),
    Column("student_id", String, ForeignKey("students.id"), nullable=False),
    Column("event_type", String, nullable=False),  # "entry" | "exit"
    Column("timestamp", DateTime, nullable=False),
    CheckConstraint("event_type IN ('entry', 'exit')", name="valid_event_type"),
)

# ---------------------------------------------------------------------
# session_snapshots — per-cycle detection counts from both ML models:
# people_detected comes from the YOLO person detector, and
# people_identified comes from the InsightFace recognition pipeline.
# The gap between the two surfaces detections that YOLO saw but
# InsightFace could not confidently match to a known student.
# ---------------------------------------------------------------------
session_snapshots = Table(
    "session_snapshots", metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", Integer, ForeignKey("class_sessions.id"), nullable=False),
    Column("timestamp", DateTime, nullable=False),
    Column("people_detected", Integer, nullable=False),
    Column("people_identified", Integer, nullable=False),
)