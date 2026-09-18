"""Live class tab.

Lets the teacher start and stop a class session (launching/stopping
the camera worker subprocess) and shows real-time attendance status
while a session is active: a donut chart of presence categories, a bar
chart of time present per student, a timeline of entry/exit events,
and a photo grid of all students with a presence-colored border.
"""

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
from app.theme import apply_theme, render_student_card

STOP_SIGNAL_PATH = DATA_DIR / ".stop_signal"
GROUPS = {"9A": 1, "9B": 2}


def _compute_presence_intervals(events: list, session_end_fallback: datetime) -> list[dict]:
    """Pair entry/exit events into presence intervals for the timeline.

    Args:
        events: A session's attendance events, any order.
        session_end_fallback: Used as the interval's end time for a
            student who is still present (has an "entry" with no
            matching "exit" yet).

    Returns:
        A list of dicts with student_id, start, and end.
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

    # Any entry without a matching exit means the student is still present.
    for student_id, start in open_entries.items():
        intervals.append({"student_id": student_id, "start": start, "end": session_end_fallback})

    return intervals


@st.fragment(run_every=3)
def _live_status(engine, group_id: int):
    """Render the live status panel for the active session.

    Wrapped as a fragment so it refreshes independently every 3
    seconds without re-running the rest of the page (e.g. the
    start/stop controls), reading fresh data from the database each
    time the camera worker writes a new detection cycle.
    """
    session = get_active_session(engine, group_id)
    if session is None:
        st.warning("No active session.")
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

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total", total)
    col2.metric("Present", present_count)
    col3.metric("Attendance %", f"{(present_count/total*100 if total else 0):.0f}%")
    if snapshot:
        col4.metric("People visible (YOLO)", snapshot.people_detected)

    # People YOLO saw but InsightFace couldn't confidently identify.
    unidentified = 0
    if snapshot:
        unidentified = max(snapshot.people_detected - snapshot.people_identified, 0)

    donut_data = pd.DataFrame({
        "category": ["Present (identified)", "Absent", "Detected but unidentified"],
        "count": [present_count, max(absent_count - unidentified, 0), unidentified],
    })

    intervals = _compute_presence_intervals(events, datetime.utcnow())
    time_by_student = {}
    for interval in intervals:
        duration = (interval["end"] - interval["start"]).total_seconds()
        time_by_student[interval["student_id"]] = time_by_student.get(interval["student_id"], 0) + duration

    student_lookup = {s.id: s.full_name for s in all_students}
    bar_data = pd.DataFrame([
        {"Student": student_lookup.get(sid, sid), "Minutes present": round(secs / 60, 1)}
        for sid, secs in time_by_student.items()
    ])

    col_donut, col_bar = st.columns(2)

    with col_donut:
        fig_donut = px.pie(donut_data, names="category", values="count", hole=0.5,
                            title="Current class status")
        fig_donut.update_layout(height=320)
        st.plotly_chart(apply_theme(fig_donut), width="stretch")

    with col_bar:
        if not bar_data.empty:
            bar_data = bar_data.sort_values("Minutes present", ascending=True)
            fig_bar = px.bar(bar_data, x="Minutes present", y="Student", orientation="h",
                              title="Time present (minutes)")
            fig_bar.update_layout(height=320)
            st.plotly_chart(apply_theme(fig_bar), width="stretch")

    if intervals:
        timeline_data = pd.DataFrame([
            {
                "Student": student_lookup.get(i["student_id"], i["student_id"]),
                "Start": i["start"],
                "End": i["end"],
            }
            for i in intervals
        ])
        fig_timeline = px.timeline(timeline_data, x_start="Start", x_end="End", y="Student",
                                    title="Presence timeline")
        fig_timeline.update_layout(height=280)
        st.plotly_chart(apply_theme(fig_timeline), width="stretch")

    st.subheader("Students")

    # Present students are shown first.
    sorted_students = sorted(all_students, key=lambda s: s.id not in present_ids)
    cols = st.columns(7)
    for idx, student in enumerate(sorted_students):
        with cols[idx % 7]:
            render_student_card(student.id, student.full_name, student.id in present_ids)


def render():
    """Render the Live Class tab: session controls plus live status."""
    st.header("Live Class")
    engine = get_engine()

    if "worker_process" not in st.session_state:
        st.session_state.worker_process = None
    if "group_id" not in st.session_state:
        st.session_state.group_id = None

    if st.session_state.worker_process is None:
        group_name = st.selectbox("Select the group", options=list(GROUPS.keys()), key="live_class_group")

        if st.button("Start class", disabled=st.session_state.get("starting", False)):
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
        st.success("Class in progress")

        if st.button("End class"):
            STOP_SIGNAL_PATH.touch()
            st.session_state.worker_process.wait(timeout=30)
            st.session_state.worker_process = None
            st.session_state.group_id = None
            st.rerun()

        _live_status(engine, st.session_state.group_id)