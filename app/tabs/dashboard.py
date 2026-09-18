"""Dashboard tab.

Gives the teacher a quick overview of each group: student count,
session count, average attendance, a trend chart, and low-attendance
alerts. Also hosts student management: adding a new student (via
photo upload or webcam capture) and deleting one.
"""

import streamlit as st
import plotly.express as px
import pandas as pd

from attendance.db.connection import get_engine
from attendance.db.queries import (
    get_students_by_group,
    get_sessions_by_group,
    has_attendance_history,
    delete_student,
)
from attendance.reports.calculations import build_attendance_dataframe
from attendance.enrollment.register import enroll_student_from_uploads
from app.theme import apply_theme

GROUPS = {"9A": 1, "9B": 2}
LOW_ATTENDANCE_THRESHOLD = 70


def _render_enrollment_section(engine):
    """Render the collapsible 'Add new student' form.

    Supports two photo sources: uploading existing files, or capturing
    photos one at a time with the browser's camera (accumulated in
    session state, since Streamlit's camera widget only captures one
    photo per call and cannot be used inside a form).
    """
    with st.expander("Add new student"):
        st.caption(
            "Note: the institutional photo for the live class view must be added "
            "manually in data/institutional_photos/ named {student_id}.jpg"
        )

        photo_source = st.radio(
            "Photo source", ["Upload files", "Take with camera"], horizontal=True, key="photo_source"
        )

        if "captured_photos" not in st.session_state:
            st.session_state.captured_photos = []

        uploaded_files = None

        if photo_source == "Upload files":
            uploaded_files = st.file_uploader(
                "Student photos (minimum 1, recommended 5-10)",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
            )
        else:
            captured = st.camera_input("Take a photo")
            if captured is not None:
                if st.button("Add this photo to the list"):
                    st.session_state.captured_photos.append(captured)
                    st.rerun()

            st.write(f"Captured photos: {len(st.session_state.captured_photos)}")
            if st.session_state.captured_photos and st.button("Clear captured photos"):
                st.session_state.captured_photos = []
                st.rerun()

            uploaded_files = st.session_state.captured_photos

        with st.form("enrollment_form", clear_on_submit=True):
            full_name = st.text_input("Full name")
            student_id = st.text_input("Student ID")
            group_name = st.selectbox("Group", options=list(GROUPS.keys()), key="enroll_group")
            submitted = st.form_submit_button("Register student")

        if submitted:
            if not full_name or not student_id or not uploaded_files:
                st.error("Fill in the name, student ID, and upload or take at least one photo.")
            else:
                try:
                    with st.spinner("Processing photos and generating embeddings..."):
                        group_id = GROUPS[group_name]
                        count = enroll_student_from_uploads(
                            engine, student_id, full_name, group_id, uploaded_files
                        )
                    if count > 0:
                        st.success(f"Student registered with {count} photo(s) processed successfully.")
                        st.session_state.captured_photos = []
                    else:
                        st.error("No face could be detected in the uploaded photos. Try different photos.")
                except ValueError as e:
                    st.error(str(e))


def _render_delete_section(engine):
    """Render the collapsible 'Delete student' form.

    Warns if the selected student has recorded attendance history,
    since deleting them also permanently deletes that history (SQLite
    enforces the foreign key constraint, so the history cannot be left
    orphaned).
    """
    with st.expander("Delete student"):
        group_name = st.selectbox("Group", options=list(GROUPS.keys()), key="delete_group")
        group_id = GROUPS[group_name]
        students_list = get_students_by_group(engine, group_id)

        if not students_list:
            st.info("No students in this group.")
            return

        student_options = {f"{s.full_name} ({s.id})": s.id for s in students_list}
        selected = st.selectbox("Student to delete", options=list(student_options.keys()))
        selected_id = student_options[selected]

        if has_attendance_history(engine, selected_id):
            st.warning(
                "This student has attendance history recorded. "
                "Deleting them will also permanently delete that history."
            )

        confirm = st.checkbox("I confirm I want to permanently delete this student")

        if st.button("Delete student", disabled=not confirm):
            delete_student(engine, selected_id)
            st.success("Student deleted.")
            st.rerun()


def render():
    """Render the Dashboard tab: enrollment/deletion tools plus per-group summaries."""
    st.header("Dashboard")

    engine = get_engine()

    _render_enrollment_section(engine)
    _render_delete_section(engine)

    for group_name, group_id in GROUPS.items():
        students = get_students_by_group(engine, group_id)
        if not students:
            continue

        sessions = get_sessions_by_group(engine, group_id)
        rows = build_attendance_dataframe(engine, group_id)

        st.subheader(f"Group {group_name}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Students", len(students))
        col2.metric("Recorded sessions", len(sessions))

        if rows:
            df = pd.DataFrame(rows)
            overall_avg = df["percentage"].mean()
            col3.metric("Average attendance %", f"{overall_avg:.0f}%")

            avg_by_session = (
                df.groupby("session_date")["percentage"]
                .mean()
                .reset_index()
                .sort_values("session_date")
            )
            fig = px.line(
                avg_by_session, x="session_date", y="percentage", markers=True,
                title=f"Attendance trend — {group_name}",
                labels={"percentage": "Average attendance %", "session_date": "Date"},
            )
            st.plotly_chart(apply_theme(fig), width="stretch")

            avg_by_student = df.groupby("full_name")["percentage"].mean().reset_index()
            low_attendance = avg_by_student[avg_by_student["percentage"] < LOW_ATTENDANCE_THRESHOLD]

            if not low_attendance.empty:
                st.warning(
                    f"{len(low_attendance)} student(s) with attendance below {LOW_ATTENDANCE_THRESHOLD}%: "
                    + ", ".join(low_attendance["full_name"].tolist())
                )
            else:
                st.success("All students have good attendance.")
        else:
            col3.metric("Average attendance %", "—")
            st.info("No finished sessions for this group yet.")

        st.divider()