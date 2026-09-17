# app/tabs/reports.py

import streamlit as st
import plotly.express as px
import pandas as pd

from attendance.db.connection import get_engine
from attendance.db.queries import get_students_by_group
from attendance.reports.calculations import build_attendance_dataframe

GROUPS = {"9A": 1, "9B": 2}


def render():
    st.header("Reportes")

    engine = get_engine()
    group_name = st.selectbox("Grupo", options=list(GROUPS.keys()), key="reports_group")
    group_id = GROUPS[group_name]

    rows = build_attendance_dataframe(engine, group_id)

    if not rows:
        st.info("Aún no hay sesiones finalizadas para este grupo.")
        return

    df = pd.DataFrame(rows)

    view = st.radio("Vista", ["Grupo", "Estudiante individual"], horizontal=True)

    if view == "Grupo":
        _render_group_view(df)
    else:
        _render_student_view(df, engine, group_id)


def _render_group_view(df: pd.DataFrame):
    st.subheader("Comparación por estudiante")

    avg_by_student = (
        df.groupby("full_name")["percentage"]
        .mean()
        .reset_index()
        .sort_values("percentage", ascending=True)
    )

    fig_bar = px.bar(
        avg_by_student, x="percentage", y="full_name", orientation="h",
        title="% de asistencia promedio por estudiante",
        labels={"percentage": "% Asistencia promedio", "full_name": "Estudiante"},
    )
    st.plotly_chart(fig_bar, width="stretch")

    st.subheader("Tendencia del grupo a lo largo del curso")

    avg_by_session = (
        df.groupby("session_date")["percentage"]
        .mean()
        .reset_index()
        .sort_values("session_date")
    )

    fig_line = px.line(
        avg_by_session, x="session_date", y="percentage", markers=True,
        title="% de asistencia promedio del grupo por sesión",
        labels={"percentage": "% Asistencia promedio", "session_date": "Fecha"},
    )
    st.plotly_chart(fig_line, width="stretch")


def _render_student_view(df: pd.DataFrame, engine, group_id: int):
    students = get_students_by_group(engine, group_id)
    student_options = {s.full_name: s.id for s in students}

    selected_name = st.selectbox("Selecciona un estudiante", options=list(student_options.keys()))
    selected_id = student_options[selected_name]

    student_df = df[df["student_id"] == selected_id].sort_values("session_date")
    group_avg_by_session = df.groupby("session_date")["percentage"].mean().reset_index()

    col1, col2 = st.columns(2)
    col1.metric("% Asistencia promedio", f"{student_df['percentage'].mean():.0f}%")
    col2.metric("Minutos promedio por clase", f"{student_df['minutes_present'].mean():.0f} min")

    fig = px.line(
        student_df, x="session_date", y="percentage", markers=True,
        title=f"Asistencia de {selected_name} a lo largo del curso",
        labels={"percentage": "% Asistencia", "session_date": "Fecha"},
    )
    fig.add_scatter(
        x=group_avg_by_session["session_date"], y=group_avg_by_session["percentage"],
        mode="lines", name="Promedio del grupo", line=dict(dash="dash", color="gray"),
    )
    st.plotly_chart(fig, width="stretch")

    st.subheader("Detalle por sesión")
    st.table(student_df[["session_date", "percentage", "minutes_present"]].rename(columns={
        "session_date": "Fecha", "percentage": "% Asistencia", "minutes_present": "Minutos presente"
    }))