"""라 마시아 — 바르사 B 출신 선수의 1군 출전 시간 비중."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, PROCESSED, _name_key, b64,
                  load_json, load_parquet, load_seasons, metric_cards,
                  portrait_map, setup)


seasons = load_seasons()
setup(seasons)

players = load_parquet(PROCESSED / "players.parquet").copy()
masia = load_json(PROCESSED / "masia.json")

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">BARÇA B · 1993/94–2025/26</div>
  <h1>라 마시아</h1>
  <div class="hero-motto">유스 시스템을 거친 선수들이 1군의 시간을 얼마나
  책임졌는지, 33시즌의 흐름으로 본다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if players.empty or not masia:
    st.warning("라 마시아 데이터가 없습니다. `python crawl_masia.py`와 "
               "`python build_players.py`를 먼저 실행하세요.")
    st.stop()

# crawl_masia.py가 수집한 바르사 B 시즌 명단에 등장한 선수를 유스 출신으로 본다.
# 이름은 악센트와 구두점을 제거한 키로만 정확히 대조한다. 성만 맞추면 Arturo
# Vidal/Marc Vidal처럼 전혀 다른 선수를 붙일 수 있어 느슨한 매칭은 하지 않는다.
players["masia_key"] = players["Player"].map(_name_key)
players["유스출신"] = players["masia_key"].isin(masia)
players["출전분"] = pd.to_numeric(players["출전분"], errors="coerce").fillna(0)
players["유스출전분"] = players["출전분"].where(players["유스출신"], 0)

trend = (players.groupby("season", as_index=False)
         .agg(전체출전분=("출전분", "sum"), 유스출전분=("유스출전분", "sum"),
              전체선수=("Player", "nunique")))
youth_counts = (players[players["유스출신"] & players["출전분"].gt(0)]
                .groupby("season")["Player"]
                .nunique().rename("유스선수"))
trend = trend.join(youth_counts, on="season").fillna({"유스선수": 0})
trend["유스비중"] = trend["유스출전분"].div(trend["전체출전분"]).mul(100)
trend = trend.sort_values("season").reset_index(drop=True)

matched = players.loc[players["유스출신"], "Player"].nunique()
peak = trend.loc[trend["유스비중"].idxmax()]
latest = trend.iloc[-1]
overall = players["유스출전분"].sum() / players["출전분"].sum() * 100

st.markdown('<div class="section">33시즌 한눈에 보기</div>',
            unsafe_allow_html=True)
st.markdown(metric_cards([
    ("B팀 명단", f"{len(masia):,}명", "Transfermarkt 시즌 스쿼드 수집"),
    ("1군 기록 매칭", f"{matched}명", "FBref 라리가 기록과 정확히 대조"),
    ("최고 비중", f"{peak['유스비중']:.1f}%", f"{peak['season']} · {int(peak['유스선수'])}명"),
    ("최근 시즌", f"{latest['유스비중']:.1f}%", f"{latest['season']} · 33시즌 전체 {overall:.1f}%"),
]), unsafe_allow_html=True)

st.info("여기서 ‘라 마시아 출신’은 수집 가능한 **바르사 B 시즌 명단에 등장한 선수**를 "
        "뜻합니다. 유스팀에서 바로 해외로 떠났거나 B팀을 거치지 않은 선수는 빠질 수 "
        "있으므로, 공식 아카데미 전체 명단이 아니라 일관된 하한선 지표로 보세요.")

st.markdown('<div class="section">시즌별 유스 출전 시간 비중</div>',
            unsafe_allow_html=True)
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=trend["season"], y=trend["유스비중"], mode="lines+markers",
    name="유스 출전 비중", line=dict(color=GRANA, width=3),
    marker=dict(color=GOLD, size=7, line=dict(color=GRANA, width=1.5)),
    fill="tozeroy", fillcolor="rgba(165,0,68,.14)",
    customdata=trend[["유스출전분", "전체출전분", "유스선수"]],
    hovertemplate=("<b>%{x}</b><br>유스 비중 %{y:.1f}%"
                   "<br>유스 출전 %{customdata[0]:,.0f}분 / %{customdata[1]:,.0f}분"
                   "<br>유스 선수 %{customdata[2]:.0f}명<extra></extra>")))
fig.add_hline(y=overall, line_dash="dot", line_color=BLAU,
              annotation_text=f"33시즌 평균 {overall:.1f}%",
              annotation_font_color="#94a8c4")
fig.add_annotation(x=peak["season"], y=peak["유스비중"],
                   text=f"정점 {peak['season']} · {peak['유스비중']:.1f}%",
                   showarrow=True, arrowcolor=GOLD, arrowhead=2, ay=-45,
                   font=dict(color=GOLD))
fig.update_layout(height=430, yaxis_title="팀 전체 출전 시간 중 비중(%)",
                  showlegend=False, **PLOT)
fig.update_xaxes(gridcolor=GRID, tickangle=-45)
fig.update_yaxes(gridcolor=GRID, range=[0, max(65, peak["유스비중"] + 6)],
                 ticksuffix="%")
st.plotly_chart(fig, width="stretch")
st.caption("라리가 선수별 출전분 합계를 분모로 계산. 골키퍼를 포함한 팀 전체 출전 시간 "
           "중 바르사 B 경유 선수의 몫이다.")

st.markdown('<div class="section">누가 그 시간을 만들었나</div>',
            unsafe_allow_html=True)
c1, c2 = st.columns([1.05, 1.35])

with c1:
    career = (players[players["유스출신"]].groupby("Player")
              .agg(출전분=("출전분", "sum"), 경기=("경기", "sum"),
                   골=("골", "sum"), 시즌=("season", "nunique"))
              .nlargest(12, "출전분").sort_values("출전분"))
    f2 = go.Figure(go.Bar(
        y=career.index, x=career["출전분"], orientation="h",
        marker_color=BLAU,
        customdata=career[["경기", "골", "시즌"]],
        hovertemplate=("<b>%{y}</b><br>%{x:,.0f}분 · %{customdata[0]:.0f}경기"
                       "<br>%{customdata[1]:.0f}골 · %{customdata[2]:.0f}시즌"
                       "<extra></extra>")))
    f2.update_layout(height=475, xaxis_title="라리가 출전 시간(분)", **PLOT)
    f2.update_xaxes(gridcolor=GRID)
    f2.update_yaxes(gridcolor=GRID)
    st.plotly_chart(f2, width="stretch")
    st.caption("33시즌 누적 라리가 출전 시간 상위 12명")

with c2:
    selected = st.selectbox("시즌 상세", trend["season"].tolist(),
                            index=len(trend) - 1)
    one = players[(players["season"] == selected) & players["유스출신"] &
                  players["출전분"].gt(0)].copy()
    one = one.sort_values("출전분", ascending=False)
    selected_summary = trend[trend["season"] == selected].iloc[0]
    st.markdown(metric_cards([
        ("유스 비중", f"{selected_summary['유스비중']:.1f}%", selected),
        ("유스 선수", f"{int(selected_summary['유스선수'])}명", "1분 이상 기록 포함"),
    ]), unsafe_allow_html=True)
    table = one[["Player", "Pos", "경기", "선발", "출전분", "골", "도움"]].copy()
    table.columns = ["선수", "포지션", "경기", "선발", "출전분", "골", "도움"]
    photos = portrait_map(table["선수"].unique())
    table.insert(0, "사진", table["선수"].map(photos))
    st.dataframe(table.set_index("선수"), width="stretch", height=360,
                 column_config={"사진": st.column_config.ImageColumn("사진", width="small")})

st.markdown("""
<div class="credits">
<b>데이터</b> Transfermarkt 바르셀로나 B 시즌 스쿼드(유스 판별) + FBref 라리가
선수 기록 1993/94~2025/26(출전 시간). 이름은 악센트와 구두점을 정규화한 뒤
정확히 일치할 때만 연결했다.<br>
<b>해석 한계</b> 바르사 B 명단을 기준으로 하므로 B팀을 거치지 않은 아카데미 출신은
누락될 수 있다. 반대로 B팀 명단에 있었던 선수는 유스 체류 기간과 관계없이 포함된다.
출전분은 FBref가 기록한 선수별 합계이며 라리가만 포함한다.
</div>
""", unsafe_allow_html=True)
