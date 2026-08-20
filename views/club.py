"""클럽 개요 — 정체성, 연표, 라리가 33시즌 기록."""
import plotly.graph_objects as go
import streamlit as st

import numpy as np
import pandas as pd

from _lib import (BLAU, GOLD, GRANA, GRID, PHOTOS, PLOT, PROCESSED, b64,
                  credits_block, load_credits, load_parquet, load_seasons,
                  metric_cards, portrait_map, setup)

seasons = load_seasons()
credits = load_credits()
setup(seasons)

titles = int((seasons["rank"] == 1).sum())
total_goals = int(seasons["GF"].sum())
total_matches = int(seasons["P"].sum())
latest = seasons.iloc[-1]
best_ppg = seasons.loc[seasons["PPG"].idxmax()]
best_gf = seasons.loc[seasons["GF"].idxmax()]

# ---------------------------------------------------------------- 데이터 센터
# 첫 화면은 '지금 팀이 어떤 상태인가'가 먼저 보여야 한다. 클럽 소개와 연표는
# 아래로 내리고, 최신 시즌 실측치를 카드로 올린다.
mt = load_parquet(PROCESSED / "club_matches.parquet").copy()
mt["date"] = pd.to_datetime(mt["Date"], format="mixed", dayfirst=True)
mt = mt.sort_values("date")
home = mt["HomeTeam"] == "Barcelona"
mt["상대"] = mt["AwayTeam"].where(home, mt["HomeTeam"])
mt["득점"] = pd.to_numeric(mt["FTHG"].where(home, mt["FTAG"]), errors="coerce")
mt["실점"] = pd.to_numeric(mt["FTAG"].where(home, mt["FTHG"]), errors="coerce")
mt["장소"] = np.where(home, "홈", "원정")
mt["결과"] = np.where(mt["득점"] > mt["실점"], "W",
                    np.where(mt["득점"] == mt["실점"], "D", "L"))

last_season = mt[mt["Season"] == latest["Season"]].dropna(subset=["득점"])
recent = last_season.tail(10)
last_game = last_season.iloc[-1] if len(last_season) else None

hero_col, side_col = st.columns([1.95, 1], gap="medium")

with hero_col:
    if last_game is not None:
        lg = last_game
        who_l, who_r = (("바르셀로나", lg["상대"]) if lg["장소"] == "홈"
                        else (lg["상대"], "바르셀로나"))
        gl, gr = ((int(lg["득점"]), int(lg["실점"])) if lg["장소"] == "홈"
                  else (int(lg["실점"]), int(lg["득점"])))
        block = (f'<div class="dc-score">'
                 f'<div class="dc-team">{who_l}</div>'
                 f'<div class="dc-num">{gl}</div>'
                 f'<div class="dc-vs">VS</div>'
                 f'<div class="dc-num">{gr}</div>'
                 f'<div class="dc-team">{who_r}</div></div>'
                 f'<div class="dc-sub" style="margin:.75rem 0 0">'
                 f'{lg["date"]:%Y.%m.%d} · {lg["장소"]} · 시즌 최종전</div>')
    else:
        block = ""
    st.markdown(f"""
<div class="dc-hero">
  <div class="dc-kick">Més que un club · Des de 1899</div>
  <h2>FC BARCELONA</h2>
  <div class="dc-sub">{latest['Season']} 라리가 · {len(seasons)}시즌 누적 기록</div>
  {block}
</div>
""", unsafe_allow_html=True)

with side_col:
    wins = int(latest["W"])
    winrate = wins / int(latest["P"]) * 100
    dots = "".join(
        f'<span class="dc-dot dc-{r.lower()}">{r}</span>' for r in recent["결과"])
    st.markdown(f"""
<div class="dc-card">
  <div class="dc-head"><div class="dc-title">{latest['Season']} 시즌</div>
    <div class="dc-note">라리가</div></div>
  <div style="display:flex;align-items:flex-end;gap:1.4rem">
    <div><div class="dc-rank">{int(latest['rank'])}<small>위</small></div></div>
    <div style="flex:1">
      <div class="dc-wdl">{wins}<small>승</small> {int(latest['D'])}<small>무</small>
        {int(latest['L'])}<small>패</small></div>
      <div class="dc-bar"><i style="width:{winrate:.0f}%"></i></div>
      <div class="dc-note">승률 {winrate:.1f}% · 승점 {int(latest['Pts'])}점
        (경기당 {latest['PPG']:.2f})</div>
    </div>
  </div>
  <div class="dc-head" style="margin:1.05rem 0 .5rem">
    <div class="dc-title">최근 {len(recent)}경기</div>
    <div class="dc-note">{int((recent['결과'] == 'W').sum())}승
      {int((recent['결과'] == 'D').sum())}무
      {int((recent['결과'] == 'L').sum())}패</div></div>
  <div class="dc-dots">{dots}</div>
  <div class="dc-head" style="margin:1.05rem 0 .35rem">
    <div class="dc-title">득실</div><div class="dc-note">시즌 합계</div></div>
  <div class="dc-row"><div class="dc-rl"><b>득점 {int(latest['GF'])} · 실점
    {int(latest['GA'])}</b></div>
    <div class="dc-rr">{int(latest['GD']):+d}</div></div>
</div>
""", unsafe_allow_html=True)

# ---- 3열 카드: 최근 경기 · 득점 리더 · 도움 리더
pl = load_parquet(PROCESSED / "players.parquet")
season_pl = pl[pl["season"] == latest["Season"]] if not pl.empty else pd.DataFrame()
faces = portrait_map(season_pl["Player"].tolist()) if not season_pl.empty else {}

RESULT_BG = {"W": "var(--gold)", "D": "#7d92ad", "L": "#8d2440"}


def leader_rows(df: pd.DataFrame, col: str, unit: str) -> str:
    """상위 5명을 사진·이름·수치 한 줄로."""
    out = ""
    for i, r in enumerate(df.nlargest(5, col).itertuples(), 1):
        uri = faces.get(r.Player, "")
        face = (f'<img class="dc-face" src="{uri}" alt="">' if uri
                else '<span class="dc-face"></span>')
        out += (f'<div class="dc-row"><div class="dc-rl">'
                f'<span class="dc-idx">{i}</span>{face}<b>{r.Player}</b></div>'
                f'<div class="dc-rr">{int(getattr(r, col))}{unit}</div></div>')
    return out


k1, k2, k3 = st.columns(3, gap="medium")

with k1:
    rows = ""
    for r in recent.iloc[::-1].head(6).itertuples():
        rows += (f'<div class="dc-row"><div class="dc-rl">'
                 f'<span class="dc-idx">{r.장소[0]}</span>'
                 f'<b>{r.상대}</b></div><div class="dc-rr">'
                 f'{int(r.득점)} : {int(r.실점)} '
                 f'<span class="dc-pill" style="background:{RESULT_BG[r.결과]};'
                 f'color:{"#fff" if r.결과 == "L" else "#04101f"}">{r.결과}</span>'
                 f'</div></div>')
    st.markdown(f'<div class="dc-card"><div class="dc-head">'
                f'<div class="dc-title">최근 6경기 결과</div>'
                f'<div class="dc-note">{latest["Season"]}</div></div>{rows}</div>',
                unsafe_allow_html=True)

with k2:
    body = (leader_rows(season_pl, "골", "골") if not season_pl.empty
            else '<div class="dc-note">데이터 없음</div>')
    st.markdown(f'<div class="dc-card"><div class="dc-head">'
                f'<div class="dc-title">득점 리더</div>'
                f'<div class="dc-note">라리가</div></div>{body}</div>',
                unsafe_allow_html=True)

with k3:
    body = (leader_rows(season_pl, "도움", "도움") if not season_pl.empty
            else '<div class="dc-note">데이터 없음</div>')
    st.markdown(f'<div class="dc-card"><div class="dc-head">'
                f'<div class="dc-title">도움 리더</div>'
                f'<div class="dc-note">라리가</div></div>{body}</div>',
                unsafe_allow_html=True)

st.caption("모두 실제 경기 기록에서 집계한 값이다. 라리가 전체 순위표는 원본에 "
           "바르사 경기만 있어 만들 수 없어, 팀 성적과 최근 폼으로 대신했다.")

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

with st.expander("시즌별 전체 기록 보기"):
    tbl = seasons[["Season", "P", "W", "D", "L", "GF", "GA", "GD", "Pts", "rank", "PPG"]].copy()
    tbl.columns = ["시즌", "경기", "승", "무", "패", "득점", "실점", "득실차", "승점", "순위", "경기당승점"]
    st.dataframe(tbl.set_index("시즌"), use_container_width=True, height=420)

st.markdown(credits_block(seasons, credits), unsafe_allow_html=True)
