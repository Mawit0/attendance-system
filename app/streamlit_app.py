"""Application entrypoint.

Sets up the three-tab layout (Dashboard, Live Class, Reports) that
maps to the three decision-making audiences the system was designed
for: the teacher during class, the teacher after class, and the
program coordinator assessing overall attendance.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from app.tabs import dashboard, live_class, reports

st.set_page_config(page_title="Attendance System", layout="wide")
st.title("Attendance System — Visual Modeling for Information")

tab1, tab2, tab3 = st.tabs(["Dashboard", "Live Class", "Reports"])

with tab1:
    dashboard.render()

with tab2:
    live_class.render()

with tab3:
    reports.render()