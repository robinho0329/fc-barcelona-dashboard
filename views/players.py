"""선수 아카이브 — FBref 33시즌 바르셀로나 선수 시즌 기록."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, PROCESSED, b64, load_seasons,
                  metric_cards, setup)

seasons = load_seasons()
setup(seasons)


@st.cache_data
def load_players() -> pd.DataFrame:
    p = PROCESSED / "players.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


df = load_players()

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">FBref · La Liga 1993/94–2025/26</div>
  <h1>선수 아카이브</h1>
  <div class="hero-motto">33시즌 동안 바르사 유니폼을 입고 라리가를 뛴 선수들의
  시즌 기록. 리그 경기만 집계한 값이다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if df.empty:
    st.warning("선수 데이터가 없습니다. `python crawl_fbref.py` 후 `python build_players.py`를 실행하세요.")
    st.stop()

# ---------------------------------------------------------------- 총괄
st.markdown('<div class="section">아카이브 규모</div>', unsafe_allow_html=True)
career = df.groupby("Player").agg(
    시즌=("season", "nunique"), 경기=("경기", "sum"), 출전분=("출전분", "sum"),
    골=("골", "sum"), 도움=("도움", "sum"))
most = career.nlargest(1, "경기").iloc[0]
top_scorer = career.nlargest(1, "골").iloc[0]

st.markdown(metric_cards([
    ("선수", f"{df['Player'].nunique()}명", f"{df['season'].nunique()}시즌 누적"),
    ("선수-시즌", f"{len(df):,}", "한 선수의 한 시즌이 한 행"),
    ("최다 출전", f"{int(most['경기'])}경기", f"{career['경기'].idxmax()} · {int(most['시즌'])}시즌"),
    ("최다 득점", f"{int(top_scorer['골'])}골", f"{career['골'].idxmax()}"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------- 필터
st.markdown('<div class="section">찾아보기</div>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.2, 1.4])
season_opts = ["전체"] + sorted(df["season"].unique(), reverse=True)
season = c1.selectbox("시즌", season_opts)
pos_opts = ["전체"] + [p for p in ["골키퍼", "수비수", "미드필더", "공격수"]
                     if p in set(df["포지션군"])]
pos = c2.selectbox("포지션", pos_opts)
min_games = c3.slider("최소 출전 경기", 0, 38, 5)
name_q = c4.text_input("선수 이름 검색", placeholder="예: Messi, Xavi")

view = df.copy()
if season != "전체":
    view = view[view["season"] == season]
if pos != "전체":
    view = view[view["포지션군"] == pos]
view = view[view["경기"].fillna(0) >= min_games]
if name_q.strip():
    view = view[view["Player"].str.contains(name_q.strip(), case=False, na=False)]

if view.empty:
    st.info("조건에 맞는 선수가 없습니다.")
    st.stop()

st.caption(f"{len(view)}건 · 선수 {view['Player'].nunique()}명 · "
           f"시즌 {view['season'].nunique()}개")

SHOW = ["Player", "season", "Pos", "Age", "경기", "선발", "출전분", "골", "도움",
        "골p90", "슛", "유효슛", "유효슛%", "경고", "퇴장"]
tbl = view[[c for c in SHOW if c in view.columns]].copy()
tbl.columns = ["선수", "시즌", "포지션", "나이", "경기", "선발", "출전분", "골", "도움",
               "골p90", "슛", "유효슛", "유효슛%", "경고", "퇴장"][:len(tbl.columns)]
st.dataframe(tbl.sort_values("출전분", ascending=False).set_index("선수"),
             use_container_width=True, height=430)

# ---------------------------------------------------------------- 랭킹
st.markdown('<div class="section">통산 순위 (필터 적용)</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
rank = (view.groupby("Player")
        .agg(경기=("경기", "sum"), 골=("골", "sum"), 도움=("도움", "sum"),
             출전분=("출전분", "sum"))
        .assign(공격P=lambda d: d["골"].fillna(0) + d["도움"].fillna(0)))

with c1:
    top = rank.nlargest(12, "골").iloc[::-1]
    f1 = go.Figure()
    f1.add_trace(go.Bar(y=top.index, x=top["골"], orientation="h", name="골",
                        marker_color=GRANA))
    f1.add_trace(go.Bar(y=top.index, x=top["도움"], orientation="h", name="도움",
                        marker_color=BLAU))
    f1.update_layout(height=420, barmode="stack", xaxis_title="횟수",
                     legend=dict(orientation="h", y=1.08), **PLOT)
    f1.update_xaxes(gridcolor=GRID)
    f1.update_yaxes(gridcolor=GRID, type="category")
    st.plotly_chart(f1, use_container_width=True)
    st.caption("골 기준 상위 12명 · 도움을 쌓아 표시")

with c2:
    tm = rank.nlargest(12, "출전분").iloc[::-1]
    f2 = go.Figure(go.Bar(y=tm.index, x=tm["출전분"], orientation="h",
                          marker_color=GOLD,
                          hovertemplate="<b>%{y}</b><br>%{x:,}분<extra></extra>"))
    f2.update_layout(height=420, xaxis_title="출전 시간(분)", **PLOT)
    f2.update_xaxes(gridcolor=GRID)
    f2.update_yaxes(gridcolor=GRID, type="category")
    st.plotly_chart(f2, use_container_width=True)
    st.caption("출전 시간 기준 상위 12명")

# ---------------------------------------------------------------- 선수 궤적
st.markdown('<div class="section">선수 시즌별 궤적</div>', unsafe_allow_html=True)
pool = career.nlargest(60, "출전분").index.tolist()
picked = st.multiselect("선수 선택 (최대 5명)", pool,
                        default=pool[:2], max_selections=5)
if picked:
    f3 = go.Figure()
    palette = [GRANA, BLAU, GOLD, "#7ab8ff", "#e0748f"]
    for color, name in zip(palette, picked):
        one = df[df["Player"] == name].sort_values("season")
        f3.add_trace(go.Scatter(x=one["season"], y=one["골"], name=name,
                                mode="lines+markers", line=dict(color=color, width=2.4),
                                hovertemplate="<b>" + name + "</b><br>%{x} · %{y}골<extra></extra>"))
    f3.update_layout(height=360, yaxis_title="시즌 득점",
                     legend=dict(orientation="h", y=1.1), **PLOT)
    f3.update_xaxes(gridcolor=GRID, tickangle=-45)
    f3.update_yaxes(gridcolor=GRID)
    st.plotly_chart(f3, use_container_width=True)
else:
    st.info("선수를 한 명 이상 고르세요.")

st.markdown("""
<div class="credits">
<b>데이터</b> FBref 라리가 선수 시즌 스탯 1993/94~2025/26. 리그 경기만 집계하며
컵대회·챔피언스리그는 빠져 있어 클럽 공식 통산 기록과 다르다.<br>
<b>결측</b> FBref가 라리가 페이지에서 세부 패스·수비·점유 지표를 빈 값으로 내려주어
해당 열은 아예 제외했다. 슛·유효슛은 2014/15 이후, 도움은 1999/00 이후만 제공된다.
패스·드리블·압박 같은 세부 지표는 <b>xG·슈팅 맵</b>과 <b>레전드</b> 페이지의
StatsBomb 이벤트 데이터에서 볼 수 있다(2004/05~2020/21).
</div>
""", unsafe_allow_html=True)
