"""FC Barcelona 대시보드 진입점.

football-data.co.uk 라리가 경기 원본, FBref 선수 스탯과 전 대회 경기,
StatsBomb·Understat 이벤트 데이터에서 직접 집계한 수치만 표시한다.
공통 CSS·데이터 로더는 _lib.py, 페이지는 views/ 아래.
"""
import streamlit as st

st.set_page_config(page_title="FC Barcelona · Més que un club",
                   page_icon="🔵", layout="wide")

nav = st.navigation({
    "클럽": [
        st.Page("views/club.py", title="홈", icon="🔵", default=True),
        st.Page("views/eras.py", title="역사 · 시대 분석", icon="📜"),
        st.Page("views/legends.py", title="레전드 TOP 10", icon="🏆"),
        st.Page("views/managers.py", title="역대 감독", icon="🎓"),
    ],
    "라이벌": [
        st.Page("views/clasico.py", title="엘클라시코", icon="⚔️"),
    ],
    "선수": [
        st.Page("views/players.py", title="선수 아카이브", icon="👤"),
        st.Page("views/masia.py", title="라 마시아", icon="🌱"),
        st.Page("views/advanced.py", title="선수 고급 기록", icon="📈"),
    ],
    "전술": [
        st.Page("views/tikitaka.py", title="티키타카 지수", icon="🔄"),
        st.Page("views/network.py", title="연계 네트워크", icon="🔗"),
        st.Page("views/msn.py", title="MSN 삼각편대", icon="🔺"),
    ],
    "이벤트 데이터": [
        st.Page("views/shots.py", title="xG · 슈팅 맵", icon="🎯"),
        st.Page("views/passes.py", title="패스 맵", icon="🕸️"),
    ],
    "기록 · 모델": [
        st.Page("views/seasons.py", title="시즌 기록 검색", icon="🔎"),
        st.Page("views/model.py", title="AI 모델", icon="🤖"),
        st.Page("views/coverage.py", title="데이터 제공 범위", icon="🗂️"),
    ],
})
nav.run()
