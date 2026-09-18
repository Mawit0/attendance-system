# app/tabs/live_class.py

import subprocess
from datetime import datetime

import streamlit as st
import plotly.express as px
import pandas as pd

from attendance.db.connection import get_engine
from attendance.db.queries import (
    get_students_by_group,
    get_active_session,
    get_events_for_session,
    get_latest_snapshot,
)
from attendance.config import DATA_DIR

STOP_SIGNAL_PATH = DATA_DIR / ".stop_signal"
GROUPS = {"9A": 1, "9B": 2}


def _compute_presence_intervals(events, session_end_fallback):
    """
    Regresa una lista de dicts {student_id, start, end} por cada intervalo
    entry->exit (o entry->ahora si sigue presente), para la timeline.
    """
    intervals = []
    open_entries = {}

    for e in sorted(events, key=lambda x: x.timestamp):
        if e.event_type == "entry":
            open_entries[e.student_id] = e.timestamp
        elif e.event_type == "exit" and e.student_id in open_entries:
            intervals.append({
                "student_id": e.student_id,
                "start": open_entries.pop(e.student_id),
                "end": e.timestamp,
            })


    return intervals


@st.fragment(run_every=3)
def _live_status(engine, group_id: int):
    session = get_active_session(engine, group_id)
    if session is None:
        st.warning("No hay sesión activa.")
        return



    all_students = get_students_by_group(engine, group_id)
    events = get_events_for_session(engine, session.id)
    snapshot = get_latest_snapshot(engine, session.id)

    present_ids = set()
    for e in sorted(events, key=lambda x: x.timestamp):
        if e.event_type == "entry":
            present_ids.add(e.student_id)
        elif e.event_type == "exit":
            present_ids.discard(e.student_id)

    total = len(all_students)
    present_count = len(present_ids)
    absent_count = total - present_count

    # --- Métricas rápidas ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", total)
    col2.metric("Presentes", present_count)
    col3.metric("% Asistencia", f"{(present_count/total*100 if total else 0):.0f}%")
    if snapshot:
        col4.metric("Personas visibles (YOLO)", snapshot.people_detected)

    # --- Donut: presente / ausente / detectado-no-identificado ---
    unidentified = 0
    if snapshot:
        unidentified = max(snapshot.people_detected - snapshot.people_identified, 0)

    donut_data = pd.DataFrame({
        "categoria": ["Presentes (identificados)", "Ausentes", "Detectados sin identificar"],
        "cantidad": [present_count, max(absent_count - unidentified, 0), unidentified],
    })
    fig_donut = px.pie(donut_data, names="categoria", values="cantidad", hole=0.5,
                        title="Estado actual de la clase")
    st.plotly_chart(fig_donut, width="stretch")

    # --- Bar chart: tiempo de permanencia por estudiante ---
    intervals = _compute_presence_intervals(events, datetime.utcnow())
    time_by_student = {}
    for interval in intervals:
        duration = (interval["end"] - interval["start"]).total_seconds()
        time_by_student[interval["student_id"]] = time_by_student.get(interval["student_id"], 0) + duration

    student_lookup = {s.id: s.full_name for s in all_students}
    bar_data = pd.DataFrame([
        {"Estudiante": student_lookup.get(sid, sid), "Minutos presente": round(secs / 60, 1)}
        for sid, secs in time_by_student.items()
    ])

    if not bar_data.empty:
        bar_data = bar_data.sort_values("Minutos presente", ascending=True)
        fig_bar = px.bar(bar_data, x="Minutos presente", y="Estudiante", orientation="h",
                          title="Tiempo de permanencia (minutos)")
        st.plotly_chart(fig_bar, width="stretch")

    # --- Timeline de entradas/salidas ---
    if intervals:
        timeline_data = pd.DataFrame([
            {
                "Estudiante": student_lookup.get(i["student_id"], i["student_id"]),
                "Inicio": i["start"],
                "Fin": i["end"],
            }
            for i in intervals
        ])
        fig_timeline = px.timeline(timeline_data, x_start="Inicio", x_end="Fin", y="Estudiante",
                                    title="Línea de tiempo de presencia")
        st.plotly_chart(fig_timeline, width="stretch")

    # --- Tablas de respaldo (detalle) ---
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Presentes")
        present_students = [s for s in all_students if s.id in present_ids]
        st.table([{"Matrícula": s.id, "Nombre": s.full_name} for s in present_students])
    with col_b:
        st.subheader("Ausentes")
        absent_students = [s for s in all_students if s.id not in present_ids]
        st.table([{"Matrícula": s.id, "Nombre": s.full_name} for s in absent_students])


def render():
    st.header("Clase en vivo")
    engine = get_engine()

    if "worker_process" not in st.session_state:
        st.session_state.worker_process = None
    if "group_id" not in st.session_state:
        st.session_state.group_id = None

    if st.session_state.worker_process is None:
        group_name = st.selectbox("Selecciona el grupo", options=list(GROUPS.keys()))

        if st.button("Iniciar clase", disabled=st.session_state.get("starting", False)):
            st.session_state.starting = True
            group_id = GROUPS[group_name]
            process = subprocess.Popen(
                ["uv", "run", "python", "-m", "attendance.capture.worker", "--group-id", str(group_id)]
            )
            st.session_state.worker_process = process
            st.session_state.group_id = group_id
            st.session_state.starting = False
            st.rerun()
    else:
        st.success("Clase activa")

        if st.button("Terminar clase"):
            STOP_SIGNAL_PATH.touch()
            st.session_state.worker_process.wait(timeout=30)
            st.session_state.worker_process = None
            st.session_state.group_id = None
            st.rerun()

        _live_status(engine, st.session_state.group_id)