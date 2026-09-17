# app/tabs/dashboard.py

import streamlit as st
import plotly.express as px
import pandas as pd

from attendance.db.connection import get_engine
from attendance.db.queries import get_students_by_group, get_sessions_by_group
from attendance.reports.calculations import build_attendance_dataframe

GROUPS = {"9A": 1, "9B": 2}
LOW_ATTENDANCE_THRESHOLD = 70  # % — configurable


def render():
    st.header("Dashboard")

    engine = get_engine()

    for group_name, group_id in GROUPS.items():
        students = get_students_by_group(engine, group_id)
        if not students:
            continue  # grupo sin estudiantes enrollados (ej. 9B por ahora)

        sessions = get_sessions_by_group(engine, group_id)
        rows = build_attendance_dataframe(engine, group_id)

        st.subheader(f"Grupo {group_name}")

        col1, col2, col3 = st.columns(3)
        col1.metric("Estudiantes", len(students))
        col2.metric("Sesiones registradas", len(sessions))

        if rows:
            df = pd.DataFrame(rows)
            overall_avg = df["percentage"].mean()
            col3.metric("% Asistencia promedio", f"{overall_avg:.0f}%")

            # --- Tendencia rápida ---
            avg_by_session = (
                df.groupby("session_date")["percentage"]
                .mean()
                .reset_index()
                .sort_values("session_date")
            )
            fig = px.line(
                avg_by_session, x="session_date", y="percentage", markers=True,
                title=f"Tendencia de asistencia — {group_name}",
                labels={"percentage": "% Asistencia promedio", "session_date": "Fecha"},
            )
            st.plotly_chart(fig, width="stretch")

            # --- Alertas ---
            avg_by_student = df.groupby("full_name")["percentage"].mean().reset_index()
            low_attendance = avg_by_student[avg_by_student["percentage"] < LOW_ATTENDANCE_THRESHOLD]

            if not low_attendance.empty:
                st.warning(
                    f"⚠️ {len(low_attendance)} estudiante(s) con asistencia menor a {LOW_ATTENDANCE_THRESHOLD}%: "
                    + ", ".join(low_attendance["full_name"].tolist())
                )
            else:
                st.success("✅ Todos los estudiantes tienen buena asistencia.")
        else:
            col3.metric("% Asistencia promedio", "—")
            st.info("Aún no hay sesiones finalizadas para este grupo.")

        st.divider()