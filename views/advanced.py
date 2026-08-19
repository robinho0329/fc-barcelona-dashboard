"""선수 고급 기록 — StatsBomb 이벤트로 만든 90분당 지표와 선수 비교."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, b64, load_sb, load_seasons,
                  metric_cards, setup)

seasons = load_seasons()
setup(seasons)

pm = load_sb("player_match")

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">StatsBomb Open Data · Per 90</div>
  <h1>선수 고급 기록</h1>
  <div class="hero-motto">골과 도움만으로는 보이지 않는 것들.
  패스·드리블·압박·수비 관여를 90분 기준으로 맞춰 비교한다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if pm.empty:
    st.warning("StatsBomb 이벤트 데이터가 없습니다. `python fetch_statsbomb.py`를 먼저 실행하세요.")
    st.stop()

barca = pm[pm["team"] == "Barcelona"].copy()

# minutes_seen은 그 선수가 마지막으로 등장한 분이라 출전 시간의 근사치다.
# 90분을 넘길 수 없도록 자르고, 경기당 최소 15분 이상 뛴 기록만 쓴다.
barca["minutes"] = barca["minutes_seen"].clip(upper=95)

METRICS = {
    "패스": "passes", "드리블 성공": "dribbles", "전진 운반": "carries",
    "압박": "pressures", "슛": "shots", "태클": "tackles",
    "인터셉트": "interceptions", "xG": "xg", "골": "goals",
}


@st.cache_data
def per90(df: pd.DataFrame, min_minutes: int) -> pd.DataFrame:
    """선수별 90분당 지표. 출전 시간이 짧은 선수는 표본이 흔들려 제외한다."""
    g = df.groupby("player").agg(
        경기=("match_id", "nunique"), 분=("minutes", "sum"),
        시즌=("season", "nunique"),
        **{k: (v, "sum") for k, v in METRICS.items()},
        패스성공=("passes_completed", "sum"))
    g = g[g["분"] >= min_minutes]
    nineties = g["분"] / 90
    out = g[["경기", "분", "시즌"]].copy()
    for k in METRICS:
        out[k] = (g[k] / nineties).round(2)
    out["패스 성공률"] = (g["패스성공"] / g["패스"].replace(0, np.nan) * 100).round(1)
    return out.sort_values("분", ascending=False)


# ---------------------------------------------------------------- 필터
c1, c2 = st.columns([1.2, 1.6])
season_opts = ["전체"] + sorted(barca["season"].unique())
season = c1.selectbox("시즌", season_opts)
scope = barca if season == "전체" else barca[barca["season"] == season]
min_min = c2.slider("최소 출전 시간(분)", 200, 4000, 900, step=100)

table = per90(scope, min_min)
if table.empty:
    st.info("조건을 만족하는 선수가 없습니다. 최소 출전 시간을 낮춰 보세요.")
    st.stop()

st.markdown('<div class="section">범위</div>', unsafe_allow_html=True)
st.markdown(metric_cards([
    ("대상 선수", f"{len(table)}명", f"최소 {min_min:,}분 이상"),
    ("합계 경기", f"{int(scope['match_id'].nunique()):,}", f"{scope['season'].nunique()}시즌"),
    ("최다 출전", f"{int(table['분'].max()):,}분", f"{table['분'].idxmax()}"),
    ("최고 패스 성공률", f"{table['패스 성공률'].max():.1f}%",
     f"{table['패스 성공률'].idxmax()}"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------- 90분당 순위
st.markdown('<div class="section">90분당 지표 순위</div>', unsafe_allow_html=True)
metric = st.selectbox("지표", list(METRICS) + ["패스 성공률"], index=0)
top = table.nlargest(15, metric).iloc[::-1]
f1 = go.Figure(go.Bar(
    y=top.index, x=top[metric], orientation="h", marker_color=GRANA,
    text=top[metric], textposition="outside", textfont_color="#f2f6fc",
    customdata=top[["경기", "분"]].values,
    hovertemplate="<b>%{y}</b><br>" + metric + " %{x}<br>"
                  "%{customdata[0]}경기 · %{customdata[1]:,.0f}분<extra></extra>"))
f1.update_layout(height=460, xaxis_title=f"90분당 {metric}", **PLOT)
f1.update_xaxes(gridcolor=GRID, range=[0, float(top[metric].max()) * 1.18])
f1.update_yaxes(gridcolor=GRID, type="category")
st.plotly_chart(f1, use_container_width=True)

# ---------------------------------------------------------------- 선수 비교
st.markdown('<div class="section">선수 비교 (레이더)</div>', unsafe_allow_html=True)
RADAR = ["패스", "드리블 성공", "전진 운반", "압박", "슛", "태클"]
pool = table.index.tolist()
picked = st.multiselect("선수 선택 (2~4명)", pool, default=pool[:2], max_selections=4)

if len(picked) < 2:
    st.info("두 명 이상 고르면 비교 그래프가 나옵니다.")
else:
    # 각 지표를 그 범위 안 최댓값으로 나눠 0~100으로 맞춘다. 절대값이 아니라
    # "이 집단 안에서 어느 위치인가"를 보는 그림이다.
    base = table[RADAR]
    norm = (base / base.max()).fillna(0) * 100
    f2 = go.Figure()
    for color, name in zip([GRANA, BLAU, GOLD, "#7ab8ff"], picked):
        vals = norm.loc[name, RADAR].tolist()
        raw = base.loc[name, RADAR].tolist()
        f2.add_trace(go.Scatterpolar(
            r=vals + vals[:1], theta=RADAR + RADAR[:1], name=name,
            fill="toself", opacity=.42, line=dict(color=color, width=2.2),
            customdata=[[v] for v in raw + raw[:1]],
            hovertemplate="<b>" + name + "</b><br>%{theta}: %{customdata[0]}"
                          " (상대 %{r:.0f})<extra></extra>"))
    f2.update_layout(
        height=470,
        polar=dict(bgcolor="rgba(0,0,0,0)",
                   radialaxis=dict(range=[0, 100], gridcolor=GRID, tickfont=dict(size=10)),
                   angularaxis=dict(gridcolor=GRID)),
        legend=dict(orientation="h", y=1.1),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a8c4", size=12),
        margin=dict(l=40, r=40, t=50, b=20))
    st.plotly_chart(f2, use_container_width=True)
    st.caption("각 축은 이 필터 안 최댓값을 100으로 놓은 상대값이다. "
               "숫자에 마우스를 올리면 실제 90분당 값이 나온다.")

# ---------------------------------------------------------------- 관계
st.markdown('<div class="section">지표 사이 관계</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
xm = c1.selectbox("가로축", list(METRICS) + ["패스 성공률"], index=0)
ym = c2.selectbox("세로축", list(METRICS) + ["패스 성공률"], index=3)
f3 = go.Figure(go.Scatter(
    x=table[xm], y=table[ym], mode="markers+text",
    text=[n.split()[-1] if len(table) <= 25 else "" for n in table.index],
    textposition="top center", textfont=dict(size=9, color="#94a8c4"),
    marker=dict(size=np.clip(table["분"] / 260, 7, 24), color=GRANA, opacity=.72,
                line=dict(width=.8, color="#0b1b2f")),
    customdata=np.stack([table.index, table["경기"], table["분"]], axis=-1),
    hovertemplate="<b>%{customdata[0]}</b><br>" + xm + " %{x}<br>" + ym + " %{y}<br>"
                  "%{customdata[1]}경기 · %{customdata[2]:,.0f}분<extra></extra>"))
f3.update_layout(height=460, xaxis_title=f"90분당 {xm}", yaxis_title=f"90분당 {ym}", **PLOT)
f3.update_xaxes(gridcolor=GRID)
f3.update_yaxes(gridcolor=GRID)
st.plotly_chart(f3, use_container_width=True)
st.caption("점 크기 = 출전 시간")

with st.expander("전체 수치 표"):
    st.dataframe(table.round(2), use_container_width=True, height=430)

st.markdown("""
<div class="credits">
<b>데이터</b> StatsBomb Open Data 라리가 2004/05~2020/21 바르셀로나 경기의
이벤트를 선수-경기 단위로 집계한 뒤 90분당으로 환산했다.<br>
<b>출전 시간</b> 원본에 교체 시각이 없어, 그 선수가 이벤트에 마지막으로 등장한
분을 출전 시간의 근사치로 썼다(95분 상한). 실제 출전 시간과 다를 수 있어
90분당 값은 대략적인 비교용으로만 봐야 한다.<br>
<b>압박·전진 운반</b> StatsBomb이 2015/16 무렵부터 기록하기 시작한 이벤트라,
그 이전 시즌 선수는 값이 낮게 잡힌다. 시즌을 좁혀 비교하는 편이 안전하다.
</div>
""", unsafe_allow_html=True)
