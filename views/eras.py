"""역사·시대 분석 — 감독 시대별로 33시즌을 끊어 본다."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, b64, load_seasons,
                  metric_cards, setup)

seasons = load_seasons().copy()
setup(seasons)

# 시대 구분은 감독 재임을 기준으로 한 편집 판단이다. 시즌 중 교체가 있던 해는
# 그 시즌을 더 오래 이끈 쪽에 넣었다.
# 각 시대의 얼굴 한 명. 이미 받아 둔 감독·레전드 사진을 쓴다.
ERAS = [
    ("크루이프 드림팀", "1993/94", "1995/96", GOLD, "eras/era_dreamteam.jpg",
     "1992년 유러피언컵 우승 세리머니",
     "요한 크루이프 감독 마지막 3년. 리그 4연패의 끝자락과 세대 교체기."),
    ("과도기", "1996/97", "2002/03", "#6b7d99", "eras/era_transition.jpg",
     "캄 노우",
     "로브손·판 할·레샥이 차례로 지휘. 리그 2회 우승했지만 흐름이 끊겼다."),
    ("레이카르트 부활", "2003/04", "2007/08", BLAU, "eras/era_rijkaard.jpg",
     "캄 노우 경기 전",
     "호나우지뉴 영입으로 반등. 리그 2연패와 2006년 챔피언스리그 우승."),
    ("과르디올라", "2008/09", "2011/12", GRANA, "eras/era_pep.jpg",
     "2010년 클라시코 5-0",
     "부임 첫해 6관왕. 리그 3연패, 클럽 역사상 가장 압도적인 4년."),
    ("MSN", "2012/13", "2016/17", "#e0748f", "eras/era_msn.jpg",
     "2015년 베를린 우승 축제",
     "티토·마르티노를 거쳐 루이스 엔리케 체제. 2015년 두 번째 트레블."),
    ("포스트 과르디올라", "2017/18", "2020/21", "#7ab8ff", "eras/era_transition.jpg",
     "캄 노우",
     "발베르데·세티엔·쿠만. 리그는 지켰지만 유럽에서 무너졌다."),
    ("재건", "2021/22", "2025/26", "#4fb0a5", "camp_nou.jpg",
     "캄 노우",
     "메시 이적 이후. 차비에 이어 플릭 체제로 리그를 되찾았다."),
]

ORDER = seasons["Season"].tolist()


def era_of(s: str) -> str:
    i = ORDER.index(s)
    for name, a, b, *_ in ERAS:
        if ORDER.index(a) <= i <= ORDER.index(b):
            return name
    return "기타"


seasons["시대"] = seasons["Season"].map(era_of)
COLOR = {e[0]: e[3] for e in ERAS}

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">1993/94 – {seasons['Season'].iloc[-1]}</div>
  <h1>역사 · 시대 분석</h1>
  <div class="hero-motto">감독이 바뀌면 팀도 바뀐다. 33시즌을 일곱 시대로 끊어
  성적이 어떻게 달라졌는지 본다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- 시대 카드
st.markdown('<div class="section">일곱 시대</div>', unsafe_allow_html=True)
cards = ""
for name, a, b, color, photo, caption, desc in ERAS:
    part = seasons[seasons["시대"] == name]
    titles = int((part["rank"] == 1).sum())
    src = b64(photo)
    img = (f'<img class="era-photo" src="{src}" alt="{caption}">' if src else "")
    cards += (
        f'<div class="era-card" style="border-left:5px solid {color}">{img}'
        f'<div class="era-body">'
        f'<div class="timeline-year">{a} ~ {b}</div>'
        f'<div class="timeline-title">{name}</div>'
        f'<div class="timeline-score" style="font-size:1.02rem">'
        f'{len(part)}시즌 · 우승 {titles}회 · 경기당 {part["PPG"].mean():.2f}점</div>'
        f'<div class="timeline-body">{desc}</div>'
        f'<div class="era-caption">{caption}</div>'
        f'</div></div>')
st.markdown(f'<div class="era-grid">{cards}</div>', unsafe_allow_html=True)
st.caption("시대 구분은 감독 재임 기준의 편집 판단이며, 수치는 라리가 경기 원본 집계다.")

# ---------------------------------------------------------------- 시대별 비교
st.markdown('<div class="section">시대별 성적</div>', unsafe_allow_html=True)
agg = (seasons.groupby("시대")
       .agg(시즌=("Season", "size"), 우승=("rank", lambda s: int((s == 1).sum())),
            평균순위=("rank", "mean"), 경기당승점=("PPG", "mean"),
            경기당득점=("GF", lambda s: s.sum() / seasons.loc[s.index, "P"].sum()),
            경기당실점=("GA", lambda s: s.sum() / seasons.loc[s.index, "P"].sum()))
       .reindex([n for n, *_ in ERAS]))
agg["우승률"] = (agg["우승"] / agg["시즌"] * 100).round(0)

st.markdown(metric_cards([
    ("최고 시대", f"{agg['경기당승점'].idxmax()}",
     f"경기당 {agg['경기당승점'].max():.2f}점"),
    ("최다 우승 시대", f"{agg['우승'].idxmax()}",
     f"{int(agg['우승'].max())}회 / {int(agg.loc[agg['우승'].idxmax(), '시즌'])}시즌"),
    ("최강 수비", f"{agg['경기당실점'].idxmin()}",
     f"경기당 {agg['경기당실점'].min():.2f}실점"),
    ("최강 공격", f"{agg['경기당득점'].idxmax()}",
     f"경기당 {agg['경기당득점'].max():.2f}득점"),
]), unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    f1 = go.Figure(go.Bar(
        x=agg.index, y=agg["경기당승점"],
        marker_color=[COLOR[n] for n in agg.index],
        text=agg["경기당승점"].round(2), textposition="outside",
        textfont_color="#f2f6fc",
        customdata=agg[["시즌", "우승"]].values,
        hovertemplate="<b>%{x}</b><br>경기당 %{y:.2f}점<br>"
                      "%{customdata[0]}시즌 · 우승 %{customdata[1]}회<extra></extra>"))
    f1.add_hline(y=seasons["PPG"].mean(), line_dash="dot", line_color="#94a8c4",
                 annotation_text=f"33시즌 평균 {seasons['PPG'].mean():.2f}",
                 annotation_font_color="#94a8c4")
    f1.update_layout(height=380, yaxis_title="경기당 승점", **PLOT)
    f1.update_xaxes(gridcolor=GRID, tickangle=-30)
    f1.update_yaxes(gridcolor=GRID, range=[0, float(agg["경기당승점"].max()) * 1.2])
    st.plotly_chart(f1, use_container_width=True)
    st.caption("시대별 경기당 승점")

with c2:
    f2 = go.Figure()
    f2.add_trace(go.Bar(x=agg.index, y=agg["경기당득점"], name="득점",
                        marker_color=GRANA))
    f2.add_trace(go.Bar(x=agg.index, y=agg["경기당실점"], name="실점",
                        marker_color=BLAU))
    f2.update_layout(height=380, barmode="group", yaxis_title="경기당 골",
                     legend=dict(orientation="h", y=1.1), **PLOT)
    f2.update_xaxes(gridcolor=GRID, tickangle=-30)
    f2.update_yaxes(gridcolor=GRID)
    st.plotly_chart(f2, use_container_width=True)
    st.caption("시대별 경기당 득점 · 실점")

# ---------------------------------------------------------------- 시즌 흐름
st.markdown('<div class="section">33시즌 흐름</div>', unsafe_allow_html=True)
f3 = go.Figure()
for name, *_ in [(n, ) for n, *_ in ERAS]:
    part = seasons[seasons["시대"] == name]
    if part.empty:
        continue
    f3.add_trace(go.Scatter(
        x=part["Season"], y=part["PPG"], name=name, mode="lines+markers",
        line=dict(color=COLOR[name], width=3),
        marker=dict(size=[13 if r == 1 else 7 for r in part["rank"]],
                    symbol=["star" if r == 1 else "circle" for r in part["rank"]]),
        customdata=part[["rank", "Pts"]].values,
        hovertemplate="<b>%{x}</b><br>경기당 %{y:.2f}점<br>"
                      "%{customdata[0]}위 · 승점 %{customdata[1]:.0f}<extra></extra>"))
f3.update_layout(height=420, yaxis_title="경기당 승점",
                 legend=dict(orientation="h", y=1.16), **PLOT)
f3.update_xaxes(gridcolor=GRID, tickangle=-60, categoryorder="array", categoryarray=ORDER)
f3.update_yaxes(gridcolor=GRID)
st.plotly_chart(f3, use_container_width=True)
st.caption("별 표시 = 그 시즌 라리가 우승")

# ---------------------------------------------------------------- 순위 분포
st.markdown('<div class="section">시대별 최종 순위 분포</div>', unsafe_allow_html=True)
f4 = go.Figure()
for name, *_ in [(n, ) for n, *_ in ERAS]:
    part = seasons[seasons["시대"] == name]
    if part.empty:
        continue
    f4.add_trace(go.Box(y=part["rank"], name=name, marker_color=COLOR[name],
                        boxpoints="all", jitter=.4, pointpos=0,
                        hovertemplate="<b>" + name + "</b><br>%{y}위<extra></extra>"))
f4.update_layout(height=380, yaxis_title="최종 순위", showlegend=False, **PLOT)
f4.update_xaxes(gridcolor=GRID, tickangle=-30)
f4.update_yaxes(gridcolor=GRID, autorange="reversed", dtick=1)
st.plotly_chart(f4, use_container_width=True)
st.caption("위쪽일수록 좋은 순위. 점 하나가 한 시즌이다.")

with st.expander("시대별 시즌 목록"):
    tb = seasons[["Season", "시대", "P", "W", "D", "L", "GF", "GA", "Pts", "rank", "PPG"]].copy()
    tb.columns = ["시즌", "시대", "경기", "승", "무", "패", "득점", "실점", "승점", "순위", "경기당승점"]
    st.dataframe(tb.set_index("시즌"), use_container_width=True, height=430)

st.markdown("""
<div class="credits">
<b>데이터</b> football-data.co.uk 라리가(SP1) 1993/94~2025/26 전 경기 결과에서
직접 집계. 순위는 승점 → 골득실 → 다득점 순으로 산출한 값이다.<br>
<b>시대 구분</b> 감독 재임을 기준으로 나눈 편집 판단이며 공식 구분이 아니다.
시즌 중 감독이 바뀐 해는 더 오래 지휘한 쪽에 넣었다.<br>
<b>범위</b> 리그 경기만 담아 컵대회·챔피언스리그 성적은 반영되지 않는다.
</div>
""", unsafe_allow_html=True)
