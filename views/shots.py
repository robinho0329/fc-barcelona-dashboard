"""xG · 슈팅 맵 — StatsBomb 이벤트 기반.

라리가 2004/05~2020/21 바르사 524경기의 모든 슛을 좌표·xG와 함께 표시한다.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, WHITE, b64, load_sb,
                  load_seasons, metric_cards, pitch_layout, setup)

seasons = load_seasons()
setup(seasons)

shots = load_sb("shots")

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">StatsBomb Open Data · Event Level</div>
  <h1>xG · 슈팅 맵</h1>
  <div class="hero-motto">슛이 어디서 나왔고 그 자리가 얼마나 좋은 자리였는지를
  좌표와 기대득점(xG)으로 본다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if shots.empty:
    st.warning("StatsBomb 이벤트 데이터가 아직 없습니다. `python fetch_statsbomb.py`를 먼저 실행하세요.")
    st.stop()

barca = shots[shots["is_barca"]].copy()

# ---------------------------------------------------------------- 필터
c1, c2, c3 = st.columns([1.1, 1.4, 1])
season_opts = ["전체"] + sorted(barca["season"].unique())
season = c1.selectbox("시즌", season_opts)
view = barca if season == "전체" else barca[barca["season"] == season]

top_players = (view.groupby("player")["xg"].agg(["sum", "count"])
               .sort_values("sum", ascending=False))
player_opts = ["전체"] + [p for p in top_players.index if isinstance(p, str)]
player = c2.selectbox("선수", player_opts)
if player != "전체":
    view = view[view["player"] == player]

only_goals = c3.checkbox("골만 보기", value=False)
plot_df = view[view["goal"]] if only_goals else view

# ---------------------------------------------------------------- 요약
if view.empty:
    st.info("조건에 맞는 슛이 없습니다.")
    st.stop()

goals = int(view["goal"].sum())
xg_sum = view["xg"].sum()
st.markdown('<div class="section">요약</div>', unsafe_allow_html=True)
st.markdown(metric_cards([
    ("슛", f"{len(view):,}", f"{view['match_id'].nunique()}경기"),
    ("골", f"{goals:,}", f"결정률 {goals / len(view) * 100:.1f}%"),
    ("누적 xG", f"{xg_sum:.1f}", f"슛당 {view['xg'].mean():.3f}"),
    ("xG 대비", f"{goals - xg_sum:+.1f}", "실제 골 − 기대 득점"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------- 슈팅 맵
st.markdown('<div class="section">슈팅 위치</div>', unsafe_allow_html=True)
fig = go.Figure()
for is_goal, color, name in [(False, BLAU, "무득점"), (True, GRANA, "골")]:
    part = plot_df[plot_df["goal"] == is_goal]
    if part.empty:
        continue
    fig.add_trace(go.Scattergl(
        x=part["x"], y=part["y"], mode="markers", name=name,
        marker=dict(size=6 + part["xg"] * 34, color=color, opacity=.72,
                    line=dict(width=.6, color="#0b1b2f")),
        customdata=part[["player", "season", "xg", "outcome", "body_part"]].values,
        hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}<br>"
                      "xG %{customdata[2]:.3f} · %{customdata[3]}<br>"
                      "%{customdata[4]}<extra></extra>"))
fig.update_layout(**pitch_layout(height=490, showlegend=True,
                                 legend=dict(orientation="h", y=1.06)))
st.plotly_chart(fig, use_container_width=True)
st.caption("점 크기 = xG. 공격 방향은 오른쪽, 골대는 오른쪽 끝. "
           "StatsBomb 좌표계(가로 120 × 세로 80).")

# ---------------------------------------------------------------- 거리·부위
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="section">골대와의 거리별</div>', unsafe_allow_html=True)
    d = view.assign(dist=((120 - view["x"]) ** 2 + (40 - view["y"]) ** 2) ** .5)
    bins = pd.cut(d["dist"], [0, 6, 12, 18, 24, 30, 100],
                  labels=["~6", "6~12", "12~18", "18~24", "24~30", "30+"])
    agg = d.groupby(bins, observed=True).agg(shots=("goal", "size"),
                                             goals=("goal", "sum"),
                                             xg=("xg", "mean"))
    f2 = go.Figure()
    f2.add_trace(go.Bar(x=agg.index.astype(str), y=agg["shots"], name="슛",
                        marker_color=BLAU))
    f2.add_trace(go.Bar(x=agg.index.astype(str), y=agg["goals"], name="골",
                        marker_color=GRANA))
    f2.update_layout(height=300, barmode="overlay", yaxis_title="횟수",
                     legend=dict(orientation="h", y=1.14), **PLOT)
    f2.update_xaxes(gridcolor=GRID, title="거리 (야드)")
    f2.update_yaxes(gridcolor=GRID)
    st.plotly_chart(f2, use_container_width=True)

with c2:
    st.markdown('<div class="section">슈팅 부위</div>', unsafe_allow_html=True)
    bp = (view[view["body_part"] != ""].groupby("body_part")
          .agg(shots=("goal", "size"), goals=("goal", "sum"))
          .sort_values("shots", ascending=True).tail(6))
    f3 = go.Figure()
    f3.add_trace(go.Bar(y=bp.index, x=bp["shots"], orientation="h", name="슛",
                        marker_color=BLAU))
    f3.add_trace(go.Bar(y=bp.index, x=bp["goals"], orientation="h", name="골",
                        marker_color=GRANA))
    f3.update_layout(height=300, barmode="overlay", xaxis_title="횟수",
                     legend=dict(orientation="h", y=1.14), **PLOT)
    f3.update_xaxes(gridcolor=GRID)
    f3.update_yaxes(gridcolor=GRID, type="category")
    st.plotly_chart(f3, use_container_width=True)

# ---------------------------------------------------------------- 선수 순위
st.markdown('<div class="section">선수별 xG · 득점</div>', unsafe_allow_html=True)
scope = barca if season == "전체" else barca[barca["season"] == season]
rank = (scope.groupby("player")
        .agg(슛=("goal", "size"), 골=("goal", "sum"), xG=("xg", "sum"))
        .sort_values("골", ascending=False).head(15))
rank["xG 대비"] = (rank["골"] - rank["xG"]).round(1)
rank["xG"] = rank["xG"].round(1)
rank["결정률"] = (rank["골"] / rank["슛"] * 100).round(1)

f4 = go.Figure()
f4.add_trace(go.Bar(x=rank.index, y=rank["xG"], name="누적 xG", marker_color=BLAU,
                    hovertemplate="<b>%{x}</b><br>xG %{y:.1f}<extra></extra>"))
f4.add_trace(go.Scatter(x=rank.index, y=rank["골"], name="실제 골", mode="markers",
                        marker=dict(size=11, color=GOLD, line=dict(width=1, color="#0b1b2f")),
                        hovertemplate="<b>%{x}</b><br>골 %{y}<extra></extra>"))
f4.update_layout(height=380, yaxis_title="골 / xG",
                 legend=dict(orientation="h", y=1.1), **PLOT)
f4.update_xaxes(gridcolor=GRID, tickangle=-40)
f4.update_yaxes(gridcolor=GRID)
st.plotly_chart(f4, use_container_width=True)
st.caption("노란 점이 파란 막대보다 위면 기대치보다 많이 넣었다는 뜻이다.")

with st.expander("선수별 수치 표"):
    st.dataframe(rank[["슛", "골", "xG", "xG 대비", "결정률"]],
                 use_container_width=True, height=420)

st.markdown("""
<div class="credits">
<b>데이터</b> StatsBomb Open Data — 라리가 2004/05~2020/21 바르셀로나 경기의
이벤트 기록. xG는 StatsBomb 모델 값(<code>statsbomb_xg</code>)을 그대로 쓴다.
공개 범위가 시즌마다 달라 한 시즌 38경기가 모두 들어 있지 않은 시즌이 있다.<br>
<b>라이선스</b> StatsBomb Open Data (비상업적 이용 허용).
</div>
""", unsafe_allow_html=True)
