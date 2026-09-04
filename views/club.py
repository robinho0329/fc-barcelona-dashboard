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
# 진행 중 시즌은 역대 기록 비교에서 뺀다. 3경기 만에 경기당 승점 3.00 이면
# 38경기를 치른 2012/13(2.63)을 제치고 '역대 최고'로 올라와 버린다.
# build_data.py 의 league_table() 이 complete 열을 채운다.
done = seasons[seasons["complete"]] if "complete" in seasons.columns else seasons
if done.empty:
    done = seasons
best_ppg = done.loc[done["PPG"].idxmax()]
best_gf = done.loc[done["GF"].idxmax()]

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

played = mt.dropna(subset=["득점"])
last_season = played[played["Season"] == latest["Season"]]
# 폼은 시즌 경계를 넘어서 본다. 시즌 초에는 최신 시즌 안에 경기가 몇 개
# 없어서, 시즌 안에서만 뽑으면 점이 서너 개뿐이라 흐름이 안 보인다.
recent = played.tail(10)
last_game = played.iloc[-1] if len(played) else None

# 최근 경기 묶음이 몇 시즌에 걸쳐 있는지. 시즌 초에는 지난 시즌이 섞인다.
_spans = list(dict.fromkeys(recent["Season"]))
recent_span = _spans[0] if len(_spans) == 1 else f"{_spans[0]}~{_spans[-1]}"
recent_note = "" if len(_spans) == 1 else " (시즌 걸침)"

hero_col, side_col = st.columns([1.95, 1], gap="medium")

with hero_col:
    # 시즌이 끝나야 최종전이다. 진행 중이면 그냥 가장 최근 경기다.
    _fin = bool(latest["complete"]) if "complete" in latest.index else True
    last_label = "시즌 최종전" if _fin else f"{int(latest['P'])}라운드 · 최근 경기"
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
                 f'{lg["date"]:%Y.%m.%d} · {lg["장소"]} · {last_label}</div>')
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
    <div class="dc-title">최근 {len(recent)}경기{recent_note}</div>
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
# 선수 기록(FBref)은 경기 기록(football-data)보다 늦게 채워진다. 최신 시즌으로
# 그대로 거르면 시즌 초에 0행이 나와 카드가 '데이터 없음' 이 된다.
# 있는 시즌 중 가장 최근으로 물러나되, 어느 시즌인지 화면에 밝힌다.
if pl.empty:
    season_pl, leader_season = pd.DataFrame(), None
else:
    leader_season = (latest["Season"] if (pl["season"] == latest["Season"]).any()
                     else pl["season"].max())
    season_pl = pl[pl["season"] == leader_season]
faces = portrait_map(season_pl["Player"].tolist()) if not season_pl.empty else {}
# 경기 기록과 선수 기록의 최신 시즌이 다르면 그 사실을 부제에 적는다
leader_note = ("라리가" if leader_season == latest["Season"]
               else f"라리가 · {leader_season}")

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
                 f'<b>{r.상대}</b>'
                 f'<span class="dc-note">{r.date:%y.%m.%d}</span></div>'
                 f'<div class="dc-rr">'
                 f'{int(r.득점)} : {int(r.실점)} '
                 f'<span class="dc-pill" style="background:{RESULT_BG[r.결과]};'
                 f'color:{"#fff" if r.결과 == "L" else "#04101f"}">{r.결과}</span>'
                 f'</div></div>')
    st.markdown(f'<div class="dc-card"><div class="dc-head">'
                f'<div class="dc-title">최근 6경기 결과</div>'
                f'<div class="dc-note">{recent_span}</div></div>{rows}</div>',
                unsafe_allow_html=True)

with k2:
    body = (leader_rows(season_pl, "골", "골") if not season_pl.empty
            else '<div class="dc-note">선수 기록이 아직 없다</div>')
    st.markdown(f'<div class="dc-card"><div class="dc-head">'
                f'<div class="dc-title">득점 리더</div>'
                f'<div class="dc-note">{leader_note}</div></div>{body}</div>',
                unsafe_allow_html=True)

with k3:
    body = (leader_rows(season_pl, "도움", "도움") if not season_pl.empty
            else '<div class="dc-note">선수 기록이 아직 없다</div>')
    st.markdown(f'<div class="dc-card"><div class="dc-head">'
                f'<div class="dc-title">도움 리더</div>'
                f'<div class="dc-note">{leader_note}</div></div>{body}</div>',
                unsafe_allow_html=True)

st.caption(f"모두 실제 경기 기록에서 집계한 값이다. 최근 폼은 시즌 경계를 "
           f"넘어 마지막 {len(recent)}경기로 본다 — 시즌 초에 현재 시즌만 보면 "
           f"경기가 몇 개 없어 흐름이 보이지 않는다.")

# ---- 라리가 순위표
# 원본(football-data SP1)에는 20개 팀 전 경기가 들어 있어 전체 순위표를
# 만들 수 있다. build_data.py 의 league_table() 이 라리가 규정대로
# 승점 → 동률 팀 간 상대전적 → 골득실 → 다득점 순으로 세운다.
standings = load_parquet(PROCESSED / "standings.parquet")
if not standings.empty:
    _done = bool(latest["complete"]) if "complete" in latest.index else True
    st.markdown(f'<div class="section">{latest["Season"]} 라리가 순위'
                f'{"" if _done else " (진행 중)"}</div>', unsafe_allow_html=True)
    tbl = (standings[standings["season"] == latest["Season"]]
           .sort_values("rank"))
    if not tbl.empty:
        # 바르사 앞뒤만 보여준다. 20팀을 다 세우면 첫 화면이 표로 덮인다.
        pos = int(tbl[tbl["team"] == "Barcelona"]["rank"].iloc[0])
        lo, hi = max(1, pos - 3), min(len(tbl), pos + 3)
        near = tbl[(tbl["rank"] >= lo) & (tbl["rank"] <= hi)]
        rows = ""
        for r in near.itertuples():
            me = r.team == "Barcelona"
            rows += (
                f'<div class="dc-row"'
                + (' style="background:rgba(165,0,68,.18);border-radius:7px;'
                   'padding-left:.4rem;padding-right:.4rem"' if me else "")
                + f'><div class="dc-rl"><span class="dc-idx">{r.rank}</span>'
                f'<b>{r.team}</b>'
                f'<span class="dc-note">{r.W}승 {r.D}무 {r.L}패 · '
                f'{r.GD:+d}</span></div>'
                f'<div class="dc-rr">{r.Pts}점</div></div>')
        s1, s2 = st.columns([1, 1], gap="medium")
        with s1:
            st.markdown(
                f'<div class="dc-card"><div class="dc-head">'
                f'<div class="dc-title">순위표 (바르사 주변)</div>'
                f'<div class="dc-note">{len(tbl)}팀 중 {pos}위</div></div>'
                f'{rows}</div>', unsafe_allow_html=True)
        with s2:
            champ = tbl.iloc[0]
            gap = int(champ["Pts"]) - int(tbl[tbl["team"] == "Barcelona"]["Pts"].iloc[0])
            # 시즌 도중이면 1위여도 '우승' 이 아니다. 아직 안 끝났다.
            season_done = bool(tbl["complete"].iloc[0]) if "complete" in tbl.columns else True
            gap_txt = ("우승" if season_done else "선두") if gap == 0 else f"{gap}점"
            rival = tbl[tbl["team"] == "Real Madrid"]
            rival_txt = (f'{int(rival["rank"].iloc[0])}위 · {int(rival["Pts"].iloc[0])}점'
                         if not rival.empty else "기록 없음")
            st.markdown(
                f'<div class="dc-card"><div class="dc-head">'
                f'<div class="dc-title">이 시즌 한눈에</div>'
                f'<div class="dc-note">라리가</div></div>'
                f'<div class="dc-row"><div class="dc-rl">'
                f'<b>{"우승" if season_done else "현재 1위"}</b></div>'
                f'<div class="dc-rr">{champ["team"]} {int(champ["Pts"])}점</div></div>'
                f'<div class="dc-row"><div class="dc-rl"><b>1위와 승점 차</b></div>'
                f'<div class="dc-rr">{gap_txt}</div></div>'
                f'<div class="dc-row"><div class="dc-rl"><b>레알 마드리드</b></div>'
                f'<div class="dc-rr">{rival_txt}</div></div>'
                f'<div class="dc-row"><div class="dc-rl"><b>최다 득점</b></div>'
                f'<div class="dc-rr">{tbl.nlargest(1, "GF")["team"].iloc[0]} '
                f'{int(tbl["GF"].max())}골</div></div>'
                f'<div class="dc-row"><div class="dc-rl"><b>최소 실점</b></div>'
                f'<div class="dc-rr">{tbl.nsmallest(1, "GA")["team"].iloc[0]} '
                f'{int(tbl["GA"].min())}골</div></div>'
                f'</div>', unsafe_allow_html=True)

        with st.expander(f'{latest["Season"]} 전체 순위표'):
            show = tbl[["rank", "team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]]
            show.columns = ["순위", "팀", "경기", "승", "무", "패",
                            "득점", "실점", "득실차", "승점"]
            st.dataframe(show, width="stretch", hide_index=True)
    _note = ("" if _done else
             f" **아직 {int(tbl['P'].max())}라운드까지만 치른 진행 중인 시즌**이라"
             " 순위는 얼마든지 바뀐다.")
    st.caption("라리가 규정대로 승점 → 동률 팀 간 상대전적 → 골득실 → 다득점 "
               "순으로 세웠다. 원본에 20개 팀 전 경기가 들어 있어 전체 순위를 "
               "그대로 계산할 수 있다." + _note)

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
    ("최고 경기당 승점", f"{best_ppg['PPG']:.2f}점", f"{best_ppg['Season']} · 승점 {int(best_ppg['Pts'])}"),
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
st.plotly_chart(fig, width="stretch")
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
    st.plotly_chart(f2, width="stretch")

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
    st.plotly_chart(f3, width="stretch")

with st.expander("시즌별 전체 기록 보기"):
    tbl = seasons[["Season", "P", "W", "D", "L", "GF", "GA", "GD", "Pts", "rank", "PPG"]].copy()
    tbl.columns = ["시즌", "경기", "승", "무", "패", "득점", "실점", "득실차", "승점", "순위", "경기당승점"]
    st.dataframe(tbl.set_index("시즌"), width="stretch", height=420)

st.markdown(credits_block(seasons, credits), unsafe_allow_html=True)
