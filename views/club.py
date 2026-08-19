"""클럽 개요 — 정체성, 연표, 라리가 33시즌 기록."""
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PHOTOS, PLOT, b64, credits_block,
                  load_credits, load_seasons, metric_cards, setup)

seasons = load_seasons()
credits = load_credits()
setup(seasons)

titles = int((seasons["rank"] == 1).sum())
total_goals = int(seasons["GF"].sum())
total_matches = int(seasons["P"].sum())
latest = seasons.iloc[-1]
best_ppg = seasons.loc[seasons["PPG"].idxmax()]
best_gf = seasons.loc[seasons["GF"].idxmax()]

# ---------------------------------------------------------------- 히어로
st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">Des de 1899 · Barcelona</div>
  <h1>FC BARCELONA</h1>
  <div class="hero-motto">"Més que un club" — 클럽 그 이상. 카탈루냐의 정체성을
  대변해 온 소시오 조합원 소유 구단의 {len(seasons)}시즌 기록.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- 클럽 정체성
st.markdown('<div class="section">클럽 정체성</div>', unsafe_allow_html=True)
st.markdown("""
<div class="lede">
1899년 스위스 출신 <b>한스 감퍼(주안 감페르)</b>가 신문 광고로 선수를 모아 창단했다.
프랑코 독재기에 카탈루냐어와 카탈루냐 깃발이 금지되자, 캄 노우는 카탈루냐 사람들이
모국어로 목소리를 낼 수 있는 몇 안 되는 공간이 됐다. "클럽 그 이상"이라는 표어는
여기서 나왔다.<br><br>
바르사는 주식회사가 아니라 <b>소시오</b>(조합원)가 소유하며, 회장을 직접 선출한다.
2006년까지 유니폼 가슴에 스폰서 대신 유니세프 로고를 <b>돈을 내고</b> 달았던 것도
이 구조 덕분이다. 유소년 아카데미 <b>라 마시아</b>는 메시·차비·이니에스타·푸욜을
한 세대에 배출하며, 2010년 발롱도르 최종 3인을 전원 자체 육성 선수로 채웠다.
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- 사진
st.markdown('<div class="section">기록 속의 바르사</div>', unsafe_allow_html=True)
cards = "".join(
    f'<div class="photo-card"><img src="{b64(k + ".jpg")}" alt="{t}">'
    f'<div class="photo-cap"><b>{t}</b><span>{d}</span></div></div>'
    for k, t, d in PHOTOS if b64(k + ".jpg")
)
st.markdown(f'<div class="photo-grid">{cards}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- 연표
st.markdown('<div class="section">클럽 연표</div>', unsafe_allow_html=True)
milestones = [
    ("1899", "창단", "한스 감퍼가 신문 광고로 선수를 모아 창단. 초대 회장은 발터 와일드."),
    ("1957", "캄 노우 개장", "레스 코르츠를 떠나 신구장으로. 이후 증축을 거쳐 99,354석."),
    ("1974", "크루이프 영입", "레알전 0-5 원정 승리. 14년 만의 리그 우승으로 상징적 전환점."),
    ("1992", "웸블리 유러피언컵", "크루이프의 드림팀이 삼프도리아를 꺾고 클럽 첫 유럽 정상."),
    ("2009", "6관왕", "과르디올라 부임 첫 시즌, 한 해 6개 대회 전관왕 — 축구사 최초."),
    ("2015", "두 번째 트레블", "MSN 삼각편대. 6년 만에 리그·코파·챔스 동시 석권."),
]
cards = "".join(
    f'<div class="timeline-card"><div class="timeline-year">{y}</div>'
    f'<div class="timeline-title">{t}</div><div class="timeline-body">{b}</div></div>'
    for y, t, b in milestones
)
st.markdown(f'<div class="timeline-grid">{cards}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- 데이터
st.markdown(f'<div class="section">데이터로 보는 {seasons["Season"].iloc[0][:4]}년 이후</div>',
            unsafe_allow_html=True)
st.markdown(metric_cards([
    ("분석 시즌", f"{len(seasons)}", f"{seasons['Season'].iloc[0]} ~ {latest['Season']}"),
    ("리그 경기", f"{total_matches:,}", "라리가 정규시즌 기준"),
    ("리그 우승", f"{titles}회", f"{titles / len(seasons) * 100:.0f}% 시즌에서 1위"),
    ("총 득점", f"{total_goals:,}", f"경기당 {total_goals / total_matches:.2f}골"),
    ("최고 승점률", f"{best_ppg['PPG']:.2f}", f"{best_ppg['Season']} · 승점 {int(best_ppg['Pts'])}"),
    ("최다 득점 시즌", f"{int(best_gf['GF'])}골", f"{best_gf['Season']}"),
    ("통산 승률", f"{seasons['W'].sum() / total_matches * 100:.1f}%",
     f"{int(seasons['W'].sum())}승 {int(seasons['D'].sum())}무 {int(seasons['L'].sum())}패"),
    ("평균 실점", f"{seasons['GA'].sum() / total_matches:.2f}", "경기당 · 전 시즌 평균"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------- 차트
st.markdown('<div class="section">시즌별 경기당 승점</div>', unsafe_allow_html=True)
fig = go.Figure(go.Bar(
    x=seasons["Season"], y=seasons["PPG"],
    marker_color=[GOLD if r == 1 else GRANA for r in seasons["rank"]],
    hovertemplate="<b>%{x}</b><br>경기당 승점 %{y:.2f}<extra></extra>"))
fig.add_hline(y=seasons["PPG"].mean(), line_dash="dot", line_color=BLAU,
              annotation_text=f"평균 {seasons['PPG'].mean():.2f}",
              annotation_font_color="#94a8c4")
fig.update_layout(height=340, yaxis_title="경기당 승점", **PLOT)
fig.update_xaxes(gridcolor=GRID, tickangle=-60)
fig.update_yaxes(gridcolor=GRID)
st.plotly_chart(fig, use_container_width=True)
st.caption("금색 = 해당 시즌 라리가 우승")

c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="section">10년 단위 리그 우승</div>', unsafe_allow_html=True)
    dec = (seasons[seasons["rank"] == 1].groupby("decade").size()
           .reindex(["1990s", "2000s", "2010s", "2020s"], fill_value=0))
    f2 = go.Figure(go.Bar(x=dec.index, y=dec.values, marker_color=BLAU, text=dec.values,
                          textposition="outside", textfont_color="#f2f6fc",
                          hovertemplate="<b>%{x}</b><br>우승 %{y}회<extra></extra>"))
    f2.update_layout(height=300, yaxis_title="우승 횟수", **PLOT)
    f2.update_xaxes(gridcolor=GRID)
    f2.update_yaxes(gridcolor=GRID, range=[0, int(dec.max()) + 2])
    st.plotly_chart(f2, use_container_width=True)

with c2:
    st.markdown('<div class="section">시즌별 득점 · 실점</div>', unsafe_allow_html=True)
    f3 = go.Figure()
    f3.add_trace(go.Scatter(x=seasons["Season"], y=seasons["GF"], name="득점",
                            line=dict(color=GRANA, width=2.4)))
    f3.add_trace(go.Scatter(x=seasons["Season"], y=seasons["GA"], name="실점",
                            line=dict(color=BLAU, width=2.4)))
    f3.update_layout(height=300, yaxis_title="골", legend=dict(orientation="h", y=1.12), **PLOT)
    f3.update_xaxes(gridcolor=GRID, tickangle=-60)
    f3.update_yaxes(gridcolor=GRID)
    st.plotly_chart(f3, use_container_width=True)

# ---------------------------------------------------------------- 최신 시즌
st.markdown(f'<div class="section">{latest["Season"]} 시즌 요약</div>', unsafe_allow_html=True)
st.markdown(metric_cards([
    ("최종 순위", f"{int(latest['rank'])}위", f"{int(latest['P'])}경기"),
    ("전적", f"{int(latest['W'])}-{int(latest['D'])}-{int(latest['L'])}",
     f"{int(latest['W'])}승 {int(latest['D'])}무 {int(latest['L'])}패"),
    ("승점", f"{int(latest['Pts'])}점", f"경기당 {latest['PPG']:.2f}"),
    ("골 득실", f"{int(latest['GD']):+d}", f"{int(latest['GF'])}득점 {int(latest['GA'])}실점"),
]), unsafe_allow_html=True)

with st.expander("시즌별 전체 기록 보기"):
    tbl = seasons[["Season", "P", "W", "D", "L", "GF", "GA", "GD", "Pts", "rank", "PPG"]].copy()
    tbl.columns = ["시즌", "경기", "승", "무", "패", "득점", "실점", "득실차", "승점", "순위", "경기당승점"]
    st.dataframe(tbl.set_index("시즌"), use_container_width=True, height=420)

st.markdown(credits_block(seasons, credits), unsafe_allow_html=True)
