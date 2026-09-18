"""Reports tab.

Provides two views built from the same underlying attendance dataset:
a group view for comparing all students against each other and
tracking the group's attendance trend over time, and an individual
view for a single student's attendance history compared against the
group average.
"""

import streamlit as st
import plotly.express as px
import pandas as pd

from attendance.db.connection import get_engine
from attendance.db.queries import get_students_by_group
from attendance.reports.calculations import build_attendance_dataframe
from app.theme import apply_theme

GROUPS = {"9A": 1, "9B": 2}


def render():
    """Render the Reports tab: group selector plus group/individual views."""
    st.header("Reports")

    engine = get_engine()
    group_name = st.selectbox("Group", options=list(GROUPS.keys()), key="reports_group")
    group_id = GROUPS[group_name]

    rows = build_attendance_dataframe(engine, group_id)

    if not rows:
        st.info("No finished sessions for this group yet.")
        return

    df = pd.DataFrame(rows)

    view = st.radio("View", ["Group", "Individual student"], horizontal=True)

    if view == "Group":
        _render_group_view(df)
    else:
        _render_student_view(df, engine, group_id)


def _render_group_view(df: pd.DataFrame):
    """Render the group comparison view: per-student averages and trend."""
    st.subheader("Comparison by student")

    avg_by_student = (
        df.groupby("full_name")["percentage"]
        .mean()
        .reset_index()
        .sort_values("percentage", ascending=True)
    )

    fig_bar = px.bar(
        avg_by_student, x="percentage", y="full_name", orientation="h",
        title="Average attendance % by student",
        labels={"percentage": "Average attendance %", "full_name": "Student"},
    )
    st.plotly_chart(apply_theme(fig_bar), width="stretch")

    st.subheader("Group trend over the course")

    avg_by_session = (
        df.groupby("session_date")["percentage"]
        .mean()
        .reset_index()
        .sort_values("session_date")
    )

    fig_line = px.line(
        avg_by_session, x="session_date", y="percentage", markers=True,
        title="Average group attendance % by session",
        labels={"percentage": "Average attendance %", "session_date": "Date"},
    )
    st.plotly_chart(apply_theme(fig_line), width="stretch")


def _render_student_view(df: pd.DataFrame, engine, group_id: int):
    """Render a single student's attendance history against the group average."""
    students = get_students_by_group(engine, group_id)
    student_options = {s.full_name: s.id for s in students}

    selected_name = st.selectbox("Select a student", options=list(student_options.keys()))
    selected_id = student_options[selected_name]

    student_df = df[df["student_id"] == selected_id].sort_values("session_date")
    group_avg_by_session = df.groupby("session_date")["percentage"].mean().reset_index()

    col1, col2 = st.columns(2)
    col1.metric("Average attendance %", f"{student_df['percentage'].mean():.0f}%")
    col2.metric("Average minutes per class", f"{student_df['minutes_present'].mean():.0f} min")

    fig = px.line(
        student_df, x="session_date", y="percentage", markers=True,
        title=f"{selected_name}'s attendance over the course",
        labels={"percentage": "Attendance %", "session_date": "Date"},
    )
    fig.add_scatter(
        x=group_avg_by_session["session_date"], y=group_avg_by_session["percentage"],
        mode="lines", name="Group average", line=dict(dash="dash", color="gray"),
    )
    st.plotly_chart(apply_theme(fig), width="stretch")

    st.subheader("Session detail")
    st.table(student_df[["session_date", "percentage", "minutes_present"]].rename(columns={
        "session_date": "Date", "percentage": "Attendance %", "minutes_present": "Minutes present"
    }))