from sqlalchemy import (
    MetaData, Table, Column,
    Integer, String, Float, DateTime, Boolean, LargeBinary,
    ForeignKey, CheckConstraint,
)
from datetime import datetime

metadata = MetaData()

# ---------------------------------------------------------------------
# teachers — MVP: un solo registro, sin login
# ---------------------------------------------------------------------
teachers = Table(
    "teachers", metadata,
    Column("id", Integer, primary_key=True),
    Column("full_name", String, nullable=False),
)

# ---------------------------------------------------------------------
# subjects — materias (ej. "Visual Modeling for Information")
# ---------------------------------------------------------------------
subjects = Table(
    "subjects", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False, unique=True),
    Column("teacher_id", Integer, ForeignKey("teachers.id"), nullable=False),
)

# ---------------------------------------------------------------------
# groups — ej. "9A", "9B" — cada grupo pertenece a una materia
# ---------------------------------------------------------------------
groups = Table(
    "groups", metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, nullable=False),          # "9A"
    Column("subject_id", Integer, ForeignKey("subjects.id"), nullable=False),
)

# ---------------------------------------------------------------------
# students — matrícula como PK natural
# ---------------------------------------------------------------------
students = Table(
    "students", metadata,
    Column("id", String, primary_key=True),           # matrícula, ej. "2309192"
    Column("full_name", String, nullable=False),
    Column("group_id", Integer, ForeignKey("groups.id"), nullable=False),
)

# ---------------------------------------------------------------------
# face_embeddings — un estudiante puede tener varios (multi-foto enrollment)
# ---------------------------------------------------------------------
face_embeddings = Table(
    "face_embeddings", metadata,
    Column("id", Integer, primary_key=True),
    Column("student_id", String, ForeignKey("students.id"), nullable=False),
    Column("embedding", LargeBinary, nullable=False),  # vector serializado
    Column("source_photo", String, nullable=True),     # referencia, no la imagen en sí
    Column("created_at", DateTime, default=datetime.utcnow),
)

# ---------------------------------------------------------------------
# class_sessions — una clase específica en una fecha/hora
# ---------------------------------------------------------------------
class_sessions = Table(
    "class_sessions", metadata,
    Column("id", Integer, primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id"), nullable=False),
    Column("started_at", DateTime, nullable=False),
    Column("ended_at", DateTime, nullable=True),       # NULL mientras está activa
    Column("status", String, nullable=False, default="active"),
    CheckConstraint("status IN ('active', 'finished')", name="valid_status"),
)

# ---------------------------------------------------------------------
# attendance_events — eventos de entrada/salida (no cada detección cruda)
# ---------------------------------------------------------------------
attendance_events = Table(
    "attendance_events", metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", Integer, ForeignKey("class_sessions.id"), nullable=False),
    Column("student_id", String, ForeignKey("students.id"), nullable=False),
    Column("event_type", String, nullable=False),      # "entry" | "exit"
    Column("timestamp", DateTime, nullable=False),
    CheckConstraint("event_type IN ('entry', 'exit')", name="valid_event_type"),
)

# agregar a src/attendance/db/schema.py

session_snapshots = Table(
    "session_snapshots", metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", Integer, ForeignKey("class_sessions.id"), nullable=False),
    Column("timestamp", DateTime, nullable=False),
    Column("people_detected", Integer, nullable=False),   # de YOLO
    Column("people_identified", Integer, nullable=False), # de InsightFace (len de detected_ids)
)
