# app/pages/2_live_class.py

import subprocess
import streamlit as st

from attendance.db.connection import get_engine
from attendance.db.queries import (
    get_students_by_group,
    get_active_session,
    get_events_for_session,
)
from attendance.config import DATA_DIR

STOP_SIGNAL_PATH = DATA_DIR / ".stop_signal"
GROUPS = {"9A": 1, "9B": 2}  # simplificación intencional por ahora

st.title("Clase en vivo")

engine = get_engine()

if "worker_process" not in st.session_state:
    st.session_state.worker_process = None
if "group_id" not in st.session_state:
    st.session_state.group_id = None


@st.fragment(run_every=3)
def live_status(group_id: int):
    session = get_active_session(engine, group_id)
    if session is None:
        st.warning("No hay sesión activa.")
        return

    all_students = get_students_by_group(engine, group_id)
    events = get_events_for_session(engine, session.id)

    # Reconstruir quién está presente AHORA mismo a partir de los eventos
    present_ids = set()
    for e in sorted(events, key=lambda x: x.timestamp):
        if e.event_type == "entry":
            present_ids.add(e.student_id)
        elif e.event_type == "exit":
            present_ids.discard(e.student_id)

    total = len(all_students)
    present_count = len(present_ids)

    col1, col2, col3 = st.columns(3)
    col1.metric("Total", total)
    col2.metric("Presentes", present_count)
    col3.metric("% Asistencia", f"{(present_count/total*100 if total else 0):.0f}%")

    st.subheader("Presentes")
    present_students = [s for s in all_students if s.id in present_ids]
    st.table([{"Matrícula": s.id, "Nombre": s.full_name} for s in present_students])

    st.subheader("Ausentes")
    absent_students = [s for s in all_students if s.id not in present_ids]
    st.table([{"Matrícula": s.id, "Nombre": s.full_name} for s in absent_students])


# --- Controles de inicio/fin de clase ---
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
    st.success(f"Clase activa")

    if st.button("Terminar clase"):
        STOP_SIGNAL_PATH.touch()
        st.session_state.worker_process.wait(timeout=30)
        st.session_state.worker_process = None
        st.session_state.group_id = None
        st.rerun()

    live_status(st.session_state.group_id)
