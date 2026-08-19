"""FC Barcelona 대시보드 진입점.

football-data.co.uk 라리가(SP1) 원본과 FBref 선수 스탯에서 직접 집계한
수치만 표시한다. 공통 CSS·데이터 로더는 _lib.py, 페이지는 views/ 아래.
"""
import streamlit as st

st.set_page_config(page_title="FC Barcelona · Més que un club",
                   page_icon="🔵", layout="wide")

nav = st.navigation([
    st.Page("views/club.py", title="클럽 개요", icon="🔵", default=True),
    st.Page("views/clasico.py", title="엘클라시코", icon="⚔️"),
])
nav.run()
