"""대회별 성적 — 라리가만 보던 이벤트 데이터의 사각지대를 FBref 전 대회 집계로 메운다.

슛맵·패스맵·티키타카·연계·삼각편대는 전부 라리가 한정이다(StatsBomb·Understat이
라리가 경기만 공개한다). 그래서 2015년 챔피언스리그 결승 골 같은 장면은 이
대시보드 어디에도 안 보인다. 이 페이지는 FBref 전 대회 경기 기록·선수 기록으로
그 빈틈 — 대회마다 팀이 얼마나 다르게 싸웠고 누가 어디서 강했는지 — 만이라도
채운다.
"""
import pathlib

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, WHITE, b64, load_dir,
                  load_seasons, metric_cards, setup)

seasons = load_seasons()
setup(seasons)

# FBref 원본 대회명(영문) → 표시명. Europa Lg/UEFA Cup은 같은 대회의 옛/새 이름이라
# 하나로 묶는다. Round == 'UEFA Super Cup'인 한 경기만 진짜 UEFA 슈퍼컵이다.
COMP_MAP = {
    "La Liga": "라리가",
    "Champions Lg": "챔피언스리그",
    "Copa del Rey": "코파 델 레이",
    "Supercopa de España": "수페르코파",
    "Europa Lg": "UEFA 유로파(구 UEFA컵)",
    "UEFA Cup": "UEFA 유로파(구 UEFA컵)",
    "Super Cup": "UEFA 슈퍼컵",
}
COMP_ORDER = ["라리가", "챔피언스리그", "코파 델 레이", "수페르코파",
              "UEFA 유로파(구 UEFA컵)", "UEFA 슈퍼컵"]
COMP_COLOR = {"라리가": GRANA, "챔피언스리그": BLAU, "코파 델 레이": GOLD,
              "수페르코파": "#7ab8ff", "UEFA 유로파(구 UEFA컵)": "#4fb0a5",
              "UEFA 슈퍼컵": "#e0748f"}
# 선수 기록의 '대회' 열은 한때 UEFA컵·유로파리그·UEFA 슈퍼컵을 전부
# 'UEFA 슈퍼컵' 하나로 묶어 놓았었다(crawl_allcomps.py 의 comp id 19 를
# 슈퍼컵으로 잘못 적어 둔 탓). 지금은 원본에서 바로잡혀 있으므로 여기서
# 다시 이름을 바꿀 필요가 없다. 표시명만 팀 기록 쪽과 맞춰 준다.
PLAYER_COMP_RENAME = {"UEFA컵/유로파": "UEFA 유로파(구 UEFA컵)"}


@st.cache_data
def load_club(stamp: str) -> pd.DataFrame:
    df = load_dir("fbref_allcomps")
    if df.empty:
        return df
    df = df.copy()
    df["comp"] = df["Comp"].map(COMP_MAP)
    df = df.dropna(subset=["comp"])
    df["GF"] = pd.to_numeric(df["GF"], errors="coerce")
    df["GA"] = pd.to_numeric(df["GA"], errors="coerce")
    df["Poss"] = pd.to_numeric(df["Poss"], errors="coerce")
    df["pts"] = df["Result"].map({"W": 3, "D": 1, "L": 0})
    return df


@st.cache_data
def load_players(stamp: str) -> pd.DataFrame:
    df = load_dir("fbref_allcomps_players")
    if df.empty:
        return df
    df = df.copy()
    # '전 대회' 행은 나머지 대회의 합이라 개별 대회와 같이 더하면 중복 집계된다
    df = df[df["대회"] != "전 대회"].copy()
    df["대회"] = df["대회"].replace(PLAYER_COMP_RENAME)
    for c in ["골", "도움", "90분수", "경기"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


_club_dir = pathlib.Path("data/fbref_allcomps")
_club_stamp = "|".join(sorted(f"{f.name}:{f.stat().st_mtime}" for f in _club_dir.glob("*.parquet"))) \
    if _club_dir.exists() else ""
_pl_dir = pathlib.Path("data/fbref_allcomps_players")
_pl_stamp = "|".join(sorted(f"{f.name}:{f.stat().st_mtime}" for f in _pl_dir.glob("*.parquet"))) \
    if _pl_dir.exists() else ""

club = load_club(_club_stamp)
players = load_players(_pl_stamp)

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">FBref All Competitions · 1993/94~</div>
  <h1>대회별 성적</h1>
  <div class="hero-motto">이 대시보드의 이벤트 데이터는 전부 라리가 한정이다.
  챔피언스리그·코파 델 레이 같은 컵대회에서 바르사가 어떻게 달랐는지는
  FBref의 전 대회 집계로만 볼 수 있다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if club.empty or players.empty:
    st.warning("FBref 전 대회 데이터가 없습니다.")
    st.stop()

st.warning(
    "**슛맵·패스맵·티키타카·연계·삼각편대 페이지는 전부 라리가 경기만 다룬다.** "
    "StatsBomb·Understat 이벤트 데이터가 라리가만 공개하기 때문이다. 그래서 "
    "2015년 챔피언스리그 결승 골 같은 장면은 이 대시보드 어디에도 좌표로 남아있지 "
    "않는다. 이 페이지는 좌표 없이 결과·득점·출전 기록만으로 그 빈틈을 채운다.")

# ---------------------------------------------------------------- 요약
st.markdown('<div class="section">대회별 전적 (1993/94~ 통산)</div>', unsafe_allow_html=True)
summ = club.groupby("comp").agg(
    경기=("Result", "size"),
    승=("Result", lambda s: (s == "W").sum()),
    무=("Result", lambda s: (s == "D").sum()),
    패=("Result", lambda s: (s == "L").sum()),
    경기당득점=("GF", "mean"), 경기당실점=("GA", "mean"),
    평균점유율=("Poss", "mean"), 경기당승점=("pts", "mean"),
).reindex(COMP_ORDER).dropna(subset=["경기"])
summ["승률"] = summ["승"] / summ["경기"] * 100

liga = summ.loc["라리가"]
cl = summ.loc["챔피언스리그"] if "챔피언스리그" in summ.index else None
st.markdown(metric_cards([
    ("집계 대회", f"{len(summ)}개", "1993/94~2025/26"),
    ("라리가 승률", f"{liga['승률']:.1f}%", f"경기당 득점 {liga['경기당득점']:.2f}"),
    ("챔스 승률", f"{cl['승률']:.1f}%" if cl is not None else "-",
     f"경기당 득점 {cl['경기당득점']:.2f}" if cl is not None else ""),
    ("승률 최고 대회", f"{summ['승률'].idxmax()}",
     f"{summ['승률'].max():.1f}% ({int(summ.loc[summ['승률'].idxmax(), '경기'])}경기)"),
]), unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    f1 = go.Figure(go.Bar(
        x=summ.index, y=summ["경기당득점"], marker_color=[COMP_COLOR[c] for c in summ.index],
        text=summ["경기당득점"].round(2), textposition="outside", textfont_color="#f2f6fc",
        customdata=summ[["경기", "경기당실점", "평균점유율"]].values,
        hovertemplate="<b>%{x}</b><br>경기당 득점 %{y:.2f}<br>경기당 실점 %{customdata[1]:.2f}<br>"
                      "평균 점유율 %{customdata[2]:.1f}%<br>%{customdata[0]}경기<extra></extra>"))
    f1.update_layout(height=340, yaxis_title="경기당 득점", **PLOT)
    f1.update_xaxes(gridcolor=GRID, tickangle=-20)
    f1.update_yaxes(gridcolor=GRID)
    st.plotly_chart(f1, width="stretch")
    st.caption("경기당 득점 = 총 득점 / 경기 수. 대회별 표본 수가 크게 달라"
               "(라리가 1,262경기 vs UEFA 슈퍼컵 1경기) 표본이 적은 대회는 참고만.")

with c2:
    f2 = go.Figure(go.Bar(
        x=summ.index, y=summ["승률"], marker_color=[COMP_COLOR[c] for c in summ.index],
        text=summ["승률"].round(1), textposition="outside", textfont_color="#f2f6fc",
        customdata=summ[["승", "무", "패"]].values,
        hovertemplate="<b>%{x}</b><br>승률 %{y:.1f}%<br>%{customdata[0]}승 %{customdata[1]}무 "
                      "%{customdata[2]}패<extra></extra>"))
    f2.update_layout(height=340, yaxis_title="승률(%)", **PLOT)
    f2.update_xaxes(gridcolor=GRID, tickangle=-20)
    f2.update_yaxes(gridcolor=GRID, range=[0, 105])
    st.plotly_chart(f2, width="stretch")
    st.caption("UEFA 슈퍼컵은 통산 1경기(2015/16 세비야전 승)뿐이라 승률 100%가 표본 부족의 결과다.")

with st.expander("대회별 전적 표"):
    tb = summ[["경기", "승", "무", "패", "승률", "경기당득점", "경기당실점", "평균점유율"]].copy()
    tb.columns = ["경기", "승", "무", "패", "승률(%)", "경기당 득점", "경기당 실점", "평균 점유율(%)"]
    st.dataframe(tb.round(2), width="stretch")

# ---------------------------------------------------------------- 시즌별 비중
st.markdown('<div class="section">시즌별 대회 비중</div>', unsafe_allow_html=True)
piv = club.groupby(["season", "comp"]).size().unstack(fill_value=0)
piv = piv.reindex(columns=[c for c in COMP_ORDER if c in piv.columns], fill_value=0)
piv = piv.reindex(sorted(piv.index, key=lambda s: seasons["Season"].tolist().index(s)
                          if s in seasons["Season"].tolist() else -1))
f3 = go.Figure()
for c in piv.columns:
    f3.add_trace(go.Bar(x=piv.index, y=piv[c], name=c, marker_color=COMP_COLOR[c]))
f3.update_layout(height=420, barmode="stack", yaxis_title="경기 수",
                 legend=dict(orientation="h", y=1.1), **PLOT)
f3.update_xaxes(gridcolor=GRID, tickangle=-60)
f3.update_yaxes(gridcolor=GRID)
st.plotly_chart(f3, width="stretch")
cl_seasons = club[club["comp"] == "챔피언스리그"].groupby("season").size()
best_cl = cl_seasons.idxmax()
st.caption(f"챔피언스리그 최다 경기 시즌 {best_cl}({int(cl_seasons.max())}경기) — "
           "결승까지 갔거나 조별리그가 길었던 시즌일수록 막대가 두껍다. "
           "코파 델 레이·수페르코파는 토너먼트 방식이라 탈락 라운드에 따라 경기 수가 크게 출렁인다.")

# ---------------------------------------------------------------- 대회별 득점왕
st.markdown('<div class="section">대회별 득점·도움 상위</div>', unsafe_allow_html=True)
comp_opts = [c for c in players["대회"].unique() if pd.notna(c)]
comp_opts = sorted(comp_opts, key=lambda c: (c not in COMP_ORDER, COMP_ORDER.index(c) if c in COMP_ORDER else 0))
sel_comp = st.selectbox("대회", comp_opts, index=0)
psub = players[players["대회"] == sel_comp]
agg = psub.groupby("Player").agg(골=("골", "sum"), 도움=("도움", "sum"),
                                  출전분=("90분수", "sum"), 경기=("경기", "sum")).reset_index()
agg = agg[agg["골"] + agg["도움"] > 0].sort_values("골", ascending=False)

c3, c4 = st.columns(2)
with c3:
    top_g = agg.sort_values("골", ascending=False).head(10)
    fg = go.Figure(go.Bar(
        y=top_g["Player"][::-1], x=top_g["골"][::-1], orientation="h",
        marker_color=GRANA, text=top_g["골"][::-1].astype(int), textposition="outside",
        textfont_color="#f2f6fc"))
    fg.update_layout(height=380, xaxis_title="통산 골", **PLOT)
    fg.update_xaxes(gridcolor=GRID)
    fg.update_yaxes(gridcolor=GRID)
    st.plotly_chart(fg, width="stretch")
    st.caption(f"{sel_comp} 통산 득점 TOP 10")

with c4:
    top_a = agg.sort_values("도움", ascending=False).head(10)
    fa = go.Figure(go.Bar(
        y=top_a["Player"][::-1], x=top_a["도움"][::-1], orientation="h",
        marker_color=BLAU, text=top_a["도움"][::-1].astype(int), textposition="outside",
        textfont_color="#f2f6fc"))
    fa.update_layout(height=380, xaxis_title="통산 도움", **PLOT)
    fa.update_xaxes(gridcolor=GRID)
    fa.update_yaxes(gridcolor=GRID)
    st.plotly_chart(fa, width="stretch")
    st.caption(f"{sel_comp} 통산 도움 TOP 10 · 도움은 FBref가 기록을 남긴 경기만 반영한다")

with st.expander("대회별 선수 기록 표"):
    tb2 = agg.copy()
    tb2.columns = ["선수", "골", "도움", "출전 분", "경기"]
    st.dataframe(tb2.round(0).set_index("선수"), width="stretch", height=400)

st.markdown(f"""
<div class="credits">
<b>데이터</b> FBref 전 대회 경기 기록({club['season'].min()}~{club['season'].max()},
{len(club):,}경기)과 선수 기록({players['season'].min()}~{players['season'].max()}).<br>
<b>대회 통합</b> Europa Lg·UEFA Cup은 같은 대회의 신·구 명칭이라 하나로 묶었다.
UEFA 슈퍼컵은 단판이라 따로 둔다(바르사는 2015/16 1경기).<br>
<b>주의</b> 이 페이지는 결과·득점·출전 기록만 다룬다. 좌표 기반 슛맵·패스맵·
xG는 라리가에만 있는 StatsBomb/Understat 이벤트 데이터가 필요해 여기서는
만들 수 없다.
</div>
""", unsafe_allow_html=True)
