"""Shared visual theming utilities for the Streamlit app.

Provides a consistent dark/purple theme across all three tabs: a
function to apply matching colors to Plotly charts (Streamlit's own
theme config doesn't reach into Plotly figures), and a function to
render a student photo card with a colored border indicating presence.
"""

import base64

import streamlit as st
import plotly.graph_objects as go

from attendance.config import (
    COLOR_CARD, COLOR_TEXT, PLOTLY_COLOR_SEQUENCE,
    INSTITUTIONAL_PHOTOS_DIR,
)

PRESENT_COLOR = "#22C55E"
ABSENT_COLOR = "#EF4444"


def apply_theme(fig: go.Figure) -> go.Figure:
    """Apply the app's dark/purple color scheme to a Plotly figure.

    Args:
        fig: A Plotly figure to restyle in place.

    Returns:
        The same figure, with theme colors applied.
    """
    fig.update_layout(
        paper_bgcolor=COLOR_CARD,
        plot_bgcolor=COLOR_CARD,
        font=dict(color=COLOR_TEXT),
        colorway=PLOTLY_COLOR_SEQUENCE,
        title_font=dict(size=16, color=COLOR_TEXT),
        margin=dict(t=50, b=30, l=30, r=30),
    )
    fig.update_xaxes(gridcolor="#2A2745", zerolinecolor="#2A2745")
    fig.update_yaxes(gridcolor="#2A2745", zerolinecolor="#2A2745")
    return fig


def render_student_card(student_id: str, full_name: str, is_present: bool):
    """Render one student's photo card with a presence-colored border.

    Shows the student's institutional photo (if available) inside a
    fixed-size card, bordered green if currently present and red if
    absent. All cards share the same fixed height regardless of name
    length, so the grid stays visually aligned.

    Args:
        student_id: The student's ID, used to locate their
            institutional photo file.
        full_name: Displayed under the photo.
        is_present: Whether the student is currently marked present,
            determining the border color.
    """
    photo_path = INSTITUTIONAL_PHOTOS_DIR / f"{student_id}.jpg"
    border_color = PRESENT_COLOR if is_present else ABSENT_COLOR

    if photo_path.exists():
        img_bytes = photo_path.read_bytes()
        img_b64 = base64.b64encode(img_bytes).decode()
        img_html = (
            f'<img src="data:image/jpeg;base64,{img_b64}" '
            f'style="width:100%; height:140px; object-fit:cover; border-radius:8px; display:block;">'
        )
    else:
        img_html = (
            '<div style="width:100%; height:140px; background:#2A2745; border-radius:8px; '
            'display:flex; align-items:center; justify-content:center; color:#A1A1AA;">'
            "No photo</div>"
        )

    st.markdown(
        f"""
        <div style="border: 3px solid {border_color}; border-radius: 10px; padding: 8px;
                    background: {COLOR_CARD}; margin-bottom: 10px; height: 210px;
                    display: flex; flex-direction: column;">
            {img_html}
            <div style="height: 44px; display: flex; align-items: center; justify-content: center; overflow: hidden;">
                <p style="text-align:center; margin:0; font-size:0.8em; color:{COLOR_TEXT}; line-height:1.2;">{full_name}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )