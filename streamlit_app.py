"""Streamlit entry point: shows the static mock-test site (index.html + questions.js)."""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT = Path(__file__).parent

st.set_page_config(page_title="Vexy Mock Tests – NISM Series VIII", layout="wide")
st.markdown(
    "<style>#MainMenu,header,footer{visibility:hidden}"
    ".block-container{padding:0!important;max-width:100%!important}</style>",
    unsafe_allow_html=True,
)

html = (ROOT / "index.html").read_text(encoding="utf-8")
questions = (ROOT / "questions.js").read_text(encoding="utf-8")
# Inline the question bank so the page works inside Streamlit's iframe
html = html.replace('<script src="questions.js"></script>', f"<script>{questions}</script>")

components.html(html, height=1000, scrolling=True)
