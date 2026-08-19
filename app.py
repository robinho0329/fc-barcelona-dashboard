"""FC Barcelona 대시보드 진입점.

football-data.co.uk 라리가(SP1) 경기 원본, FBref 선수 시즌 스탯,
StatsBomb 이벤트 데이터에서 직접 집계한 수치만 표시한다.
공통 CSS·데이터 로더는 _lib.py, 페이지는 views/ 아래.
"""
import streamlit as st

st.set_page_config(page_title="FC Barcelona · Més que un club",
                   page_icon="🔵", layout="wide")

nav = st.navigation({
    "클럽": [
        st.Page("views/club.py", title="홈", icon="🔵", default=True),
        st.Page("views/legends.py", title="레전드 TOP 10", icon="🏆"),
    ],
    "라이벌": [
        st.Page("views/clasico.py", title="엘클라시코", icon="⚔️"),
    ],
    "선수": [
        st.Page("views/players.py", title="선수 아카이브", icon="👤"),
    ],
    "이벤트 데이터": [
        st.Page("views/shots.py", title="xG · 슈팅 맵", icon="🎯"),
    ],
})
nav.run()
