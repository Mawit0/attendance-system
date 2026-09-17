# app/streamlit_app.py

import sys
from pathlib import Path

# Asegura que 'app/' sea encontrable como paquete al correr streamlit
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from app.tabs import dashboard, live_class, reports

st.set_page_config(page_title="Attendance System", layout="wide")
st.title("Sistema de Asistencia — Visual Modeling for Information")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🎥 Clase en vivo", "📈 Reportes"])

with tab1:
    dashboard.render()

with tab2:
    live_class.render()

with tab3:
    reports.render()