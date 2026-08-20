"""MSN — 메시·수아레스·네이마르, 2014/15~2016/17."""
import pathlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, b64, load_dir, load_seasons,
                  load_understat, metric_cards, portrait_map, setup)

seasons = load_seasons()
setup(seasons)

TRIO = ["Lionel Messi", "Luis Suárez", "Neymar"]
SEASONS = ["2014/15", "2015/16", "2016/17"]
COLOR = {"Lionel Messi": GRANA, "Luis Suárez": GOLD, "Neymar": BLAU}
KOR = {"Lionel Messi": "메시", "Luis Suárez": "수아레스", "Neymar": "네이마르"}


@st.cache_data
def trio_stats(stamp: str) -> pd.DataFrame:
    """FBref 전 대회 합산에서 세 명의 시즌 기록만."""
    ac = load_dir("fbref_allcomps_players")
    if ac.empty:
        return pd.DataFrame()
    d = ac[(ac["Player"].isin(TRIO)) & (ac["season"].isin(SEASONS))
           & (ac["대회"] == "전 대회")]
    return d.copy()


@st.cache_data
def team_goals(stamp: str) -> pd.Series:
    ac = load_dir("fbref_allcomps_players")
    if ac.empty:
        return pd.Series(dtype=float)
    d = ac[(ac["season"].isin(SEASONS)) & (ac["대회"] == "전 대회")]
    return d.groupby("season")["골"].sum()


@st.cache_data
def trio_links(stamp: float) -> pd.DataFrame:
    """세 명 사이에서 나온 골. Understat의 도움-득점 짝을 쓴다."""
    u = load_understat()
    if u.empty:
        return pd.DataFrame()
    g = u[u["is_barca"] & u["goal"] & u["season"].isin(SEASONS)
          & u["player_name"].isin(TRIO) & u["player_assisted"].isin(TRIO)]
    return g.groupby(["player_assisted", "player_name"]).size().reset_index(name="골")


_d = pathlib.Path("data/fbref_allcomps_players")
_stamp = "|".join(sorted(f"{f.name}:{f.stat().st_mtime}" for f in _d.glob("*.parquet"))) \
    if _d.exists() else ""
_u = pathlib.Path("data/understat/shots.parquet")

trio = trio_stats(_stamp)
team = team_goals(_stamp)
links = trio_links(_u.stat().st_mtime if _u.exists() else 0.0)

photos = portrait_map(TRIO)

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">MSN · 2014/15 – 2016/17</div>
  <h1>메시 · 수아레스 · 네이마르</h1>
  <div class="hero-motto">세 시즌 동안 세 명이 넣은 골이 팀 득점의 3분의 2를
  넘었다. 축구사에서 손꼽히는 삼각편대의 기록.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if trio.empty:
    st.warning("선수 데이터가 없습니다. `python crawl_allcomps.py`를 먼저 실행하세요.")
    st.stop()

# ---------------------------------------------------------------- 세 사람
st.markdown('<div class="section">세 사람</div>', unsafe_allow_html=True)
cards = ""
for name in TRIO:
    part = trio[trio["Player"] == name]
    g = int(part["골"].sum())
    a = int(part["도움"].sum())
    mp = int(part["경기"].sum())
    src = photos.get(name, "")
    img = (f'<img class="msn-photo" src="{src}" alt="{name}">' if src else "")
    cards += (
        f'<div class="msn-card" style="border-top:4px solid {COLOR[name]}">{img}'
        f'<div class="msn-body"><div class="msn-name">{KOR[name]}</div>'
        f'<div class="msn-full">{name}</div>'
        f'<div class="msn-line"><b>{g}</b>골 · <b>{a}</b>도움</div>'
        f'<div class="msn-sub">{mp}경기 · 경기당 {g / max(mp, 1):.2f}골</div>'
        f'</div></div>')
st.markdown(f'<div class="msn-grid">{cards}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- 연혁
st.markdown('<div class="section">연혁</div>', unsafe_allow_html=True)
HISTORY = [
    ("2013.06", "네이마르 합류", "산투스에서 21세에 도착. 메시 옆자리를 맡을 "
                             "재목으로 기대를 받았지만 첫 시즌은 적응기였다."),
    ("2014.07", "수아레스 합류", "리버풀에서 왔다. 월드컵 징계로 10월에야 데뷔했고, "
                             "그때부터 셋이 함께 뛰기 시작했다."),
    ("2015.01", "삼각편대 완성", "루이스 엔리케가 메시를 오른쪽으로 옮기고 수아레스를 "
                             "중앙에 세우면서 세 명의 자리가 맞아떨어졌다."),
    ("2015.06", "트레블", "베를린에서 유벤투스를 3-1로 꺾고 리그·코파·챔스 석권. "
                       "그 시즌 셋이 122골을 합작했다."),
    ("2016.05", "리그·코파 더블", "수아레스가 40골로 득점왕. 세 명 중 메시가 아닌 "
                              "선수가 피치치를 차지한 드문 해였다."),
    ("2017.08", "네이마르 이적", "PSG가 2억 2천만 유로 바이아웃을 지불했다. "
                             "축구 이적료 기록을 두 배 이상 갈아치운 금액이었다."),
]
cards = "".join(
    f'<div class="timeline-card"><div class="timeline-year">{y}</div>'
    f'<div class="timeline-title">{t}</div><div class="timeline-body">{b}</div></div>'
    for y, t, b in HISTORY
)
st.markdown(f'<div class="timeline-grid">{cards}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- 주요 성과
st.markdown('<div class="section">함께 든 트로피</div>', unsafe_allow_html=True)
st.markdown("""
<div class="lede">
셋이 함께 뛴 세 시즌 동안 바르사는 <b>9개 대회에서 우승</b>했다. 2015년에는
한 해에 리그·코파 델 레이·챔피언스리그를 모두 가져가며 클럽 역사상 두 번째
트레블을 이뤘고, 그해 UEFA 슈퍼컵과 클럽월드컵까지 더해 5관왕으로 마무리했다.
</div>
""", unsafe_allow_html=True)
TROPHIES = [
    ("2014/15", "리그 · 코파 · 챔피언스리그", "트레블. 이어 슈퍼컵·클럽월드컵까지 5관왕"),
    ("2015/16", "리그 · 코파 델 레이", "더블. 챔스는 8강에서 아틀레티코에 탈락"),
    ("2016/17", "코파 델 레이", "리그는 레알에 3점 차로 내줬다"),
]
cards = "".join(
    f'<div class="timeline-card tl-win"><div class="timeline-year">{y}</div>'
    f'<div class="timeline-title">{t}</div><div class="timeline-body">{b}</div></div>'
    for y, t, b in TROPHIES
)
st.markdown(f'<div class="timeline-grid">{cards}</div>', unsafe_allow_html=True)

tot_g = int(trio["골"].sum())
tot_a = int(trio["도움"].sum())
share = {s: trio[trio["season"] == s]["골"].sum() / team.get(s, np.nan) * 100
         for s in SEASONS}
best_season = max(share, key=lambda s: share[s])

st.markdown('<div class="section">세 시즌 합계</div>', unsafe_allow_html=True)
st.markdown(metric_cards([
    ("합계 골", f"{tot_g}", f"3시즌 · 도움 {tot_a}"),
    ("팀 득점 비중", f"{np.mean(list(share.values())):.0f}%",
     f"최고 {share[best_season]:.0f}% ({best_season})"),
    ("최다 득점 시즌", f"{int(trio.groupby('season')['골'].sum().max())}골",
     f"{trio.groupby('season')['골'].sum().idxmax()}"),
    ("서로 만든 골", f"{int(links['골'].sum()) if not links.empty else 0}",
     "셋 사이의 도움 → 득점 (라리가)"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------- 시즌별
st.markdown('<div class="section">시즌별 득점</div>', unsafe_allow_html=True)
c1, c2 = st.columns([1.4, 1])
with c1:
    f1 = go.Figure()
    for name in TRIO:
        part = trio[trio["Player"] == name].set_index("season").reindex(SEASONS)
        f1.add_trace(go.Bar(x=SEASONS, y=part["골"], name=KOR[name],
                            marker_color=COLOR[name],
                            customdata=part[["도움", "경기"]].values,
                            hovertemplate="<b>" + KOR[name] + "</b> %{x}<br>"
                                          "%{y:.0f}골 · 도움 %{customdata[0]:.0f}<br>"
                                          "%{customdata[1]:.0f}경기<extra></extra>"))
    f1.update_layout(height=380, barmode="stack", yaxis_title="골",
                     legend=dict(orientation="h", y=1.12), **PLOT)
    f1.update_xaxes(gridcolor=GRID)
    f1.update_yaxes(gridcolor=GRID)
    st.plotly_chart(f1, use_container_width=True)
    st.caption("전 대회 합산 — 라리가·챔피언스리그·코파 델 레이·수페르코파")

with c2:
    f2 = go.Figure(go.Bar(
        x=SEASONS, y=[share[s] for s in SEASONS], marker_color=GRANA,
        text=[f"{share[s]:.0f}%" for s in SEASONS], textposition="outside",
        textfont_color="#f2f6fc",
        customdata=[[int(trio[trio["season"] == s]["골"].sum()), int(team.get(s, 0))]
                    for s in SEASONS],
        hovertemplate="<b>%{x}</b><br>MSN %{customdata[0]}골 / 팀 %{customdata[1]}골"
                      "<br>%{y:.1f}%<extra></extra>"))
    f2.update_layout(height=380, yaxis_title="팀 득점 중 MSN 비중(%)", **PLOT)
    f2.update_xaxes(gridcolor=GRID)
    f2.update_yaxes(gridcolor=GRID, range=[0, 100])
    st.plotly_chart(f2, use_container_width=True)
    st.caption("나머지 스쿼드 전원이 나눠 넣은 몫이 3분의 1도 안 됐다")

# ---------------------------------------------------------------- 삼각형
if not links.empty:
    st.markdown('<div class="section">셋 사이의 삼각형</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="lede">
셋이 서로 건네 넣은 골만 따로 뽑았다. 화살표는 <b>도움 → 득점</b> 방향이고
숫자는 그렇게 나온 골 수다. 한 방향으로 치우치지 않고 세 변이 모두 굵은 것이
이 조합의 특징이었다.
</div>
""", unsafe_allow_html=True)

    ang = {"Lionel Messi": np.pi / 2,
           "Luis Suárez": np.pi / 2 + 2 * np.pi / 3,
           "Neymar": np.pi / 2 - 2 * np.pi / 3}
    pos = {n: (np.cos(a), np.sin(a)) for n, a in ang.items()}

    fig = go.Figure()
    for r in links.itertuples():
        a, b = r.player_assisted, r.player_name
        if a not in pos or b not in pos:
            continue
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        # 양방향이 겹치지 않게 살짝 휘어 보이도록 중간점을 옆으로 민다
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        off = 0.10
        nx, ny = -(y1 - y0), (x1 - x0)
        norm = (nx ** 2 + ny ** 2) ** .5 or 1
        cx, cy = mx + nx / norm * off, my + ny / norm * off
        t = np.linspace(0, 1, 30)
        bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
        by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
        fig.add_trace(go.Scatter(
            x=bx, y=by, mode="lines",
            line=dict(color=COLOR[a], width=2 + r.골 * 0.55), opacity=.75,
            hovertemplate=f"<b>{KOR[a]} → {KOR[b]}</b><br>{r.골}골<extra></extra>",
            showlegend=False))
        fig.add_annotation(x=cx, y=cy, text=f"<b>{r.골}</b>", showarrow=False,
                           font=dict(size=13, color=COLOR[a]),
                           bgcolor="rgba(4,16,31,.75)")

    imgs = []
    for name, (x, y) in pos.items():
        if photos.get(name):
            imgs.append(dict(source=photos[name], x=x, y=y, sizex=.52, sizey=.52,
                             xref="x", yref="y", xanchor="center",
                             yanchor="middle", sizing="contain", layer="above"))
    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in TRIO], y=[pos[n][1] - 0.36 for n in TRIO],
        mode="text", text=[KOR[n] for n in TRIO], textposition="middle center",
        textfont=dict(size=13, color="#f2f6fc"), showlegend=False,
        hoverinfo="skip"))

    fig.update_layout(
        height=520, images=imgs,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(range=[-1.7, 1.7], visible=False, constrain="domain"),
        yaxis=dict(range=[-1.5, 1.6], visible=False, scaleanchor="x", scaleratio=1))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"라리가 경기만 집계. 셋 사이에서만 {int(links['골'].sum())}골이 나왔다. "
               "선 색은 도움을 준 쪽이다.")

# ---------------------------------------------------------------- 공격 루트
@st.cache_data
def route_stats(stamp: float) -> pd.DataFrame:
    """세 명의 골이 어떤 상황에서, 어느 부위로 나왔는지."""
    u = load_understat()
    if u.empty:
        return pd.DataFrame()
    return u[u["is_barca"] & u["goal"] & u["season"].isin(SEASONS)
             & u["player_name"].isin(TRIO)].copy()


routes = route_stats(_u.stat().st_mtime if _u.exists() else 0.0)

if not routes.empty:
    st.markdown('<div class="section">주 공격 루트</div>', unsafe_allow_html=True)
    PATTERN_KO = {"OpenPlay": "오픈 플레이", "Penalty": "페널티킥",
                  "DirectFreekick": "직접 프리킥", "FromCorner": "코너",
                  "SetPiece": "세트피스"}
    BODY_KO = {"LeftFoot": "왼발", "RightFoot": "오른발", "Head": "헤더",
               "OtherBodyPart": "기타"}

    c1, c2 = st.columns(2)
    with c1:
        pat = (routes.assign(상황=routes["pattern"].map(PATTERN_KO).fillna("기타"))
               .groupby(["player_name", "상황"]).size().unstack(fill_value=0))
        fr = go.Figure()
        for col in pat.columns:
            fr.add_trace(go.Bar(x=[KOR[i] for i in pat.index], y=pat[col], name=col))
        fr.update_layout(height=340, barmode="stack", yaxis_title="골",
                         legend=dict(orientation="h", y=1.14), **PLOT)
        fr.update_xaxes(gridcolor=GRID)
        fr.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fr, use_container_width=True)
        st.caption("상황별 득점. 셋 다 오픈 플레이 비중이 압도적이다")

    with c2:
        bod = (routes.assign(부위=routes["body_part"].map(BODY_KO).fillna("기타"))
               .groupby(["player_name", "부위"]).size().unstack(fill_value=0))
        fb = go.Figure()
        for col in bod.columns:
            fb.add_trace(go.Bar(x=[KOR[i] for i in bod.index], y=bod[col], name=col))
        fb.update_layout(height=340, barmode="stack", yaxis_title="골",
                         legend=dict(orientation="h", y=1.14), **PLOT)
        fb.update_xaxes(gridcolor=GRID)
        fb.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fb, use_container_width=True)
        st.caption("메시는 왼발, 수아레스·네이마르는 오른발이 주무기였다")

    st.markdown('<div class="section">골 직전에 무슨 일이 있었나</div>',
                unsafe_allow_html=True)
    ACT_KO = {"Pass": "패스", "Standard": "세트피스 상황", "Throughball": "스루패스",
              "TakeOn": "제치고 나서", "Cross": "크로스", "Rebound": "세컨드볼",
              "Chipped": "칩 패스", "HeadPass": "헤더 패스", "None": "직접"}
    act = (routes["lastAction"].map(lambda v: ACT_KO.get(v, "기타"))
           .value_counts().head(9).iloc[::-1])
    fa = go.Figure(go.Bar(y=act.index, x=act.values, orientation="h",
                          marker_color=GRANA, text=act.values,
                          textposition="outside", textfont_color="#f2f6fc",
                          hovertemplate="<b>%{y}</b><br>%{x}골<extra></extra>"))
    fa.update_layout(height=340, xaxis_title="골", **PLOT)
    fa.update_xaxes(gridcolor=GRID, range=[0, int(act.max()) * 1.2])
    fa.update_yaxes(gridcolor=GRID, type="category")
    st.plotly_chart(fa, use_container_width=True)

    feeders = (routes[routes["player_assisted"].notna()
                      & ~routes["player_assisted"].isin(TRIO)]
               ["player_assisted"].value_counts().head(8).iloc[::-1])
    if not feeders.empty:
        st.markdown('<div class="section">셋에게 공을 대준 사람들</div>',
                    unsafe_allow_html=True)
        ff = go.Figure(go.Bar(y=feeders.index, x=feeders.values, orientation="h",
                              marker_color=BLAU, text=feeders.values,
                              textposition="outside", textfont_color="#f2f6fc",
                              hovertemplate="<b>%{y}</b><br>%{x}도움<extra></extra>"))
        ff.update_layout(height=320, xaxis_title="MSN에게 준 도움", **PLOT)
        ff.update_xaxes(gridcolor=GRID, range=[0, int(feeders.max()) * 1.25])
        ff.update_yaxes(gridcolor=GRID, type="category")
        st.plotly_chart(ff, use_container_width=True)
        st.caption("셋을 뺀 나머지 선수들의 도움. 알바·알베스 같은 풀백이 위에 있다")

# ---------------------------------------------------------------- 표
st.markdown('<div class="section">시즌별 기록</div>', unsafe_allow_html=True)
tb = trio[["Player", "season", "경기", "선발", "출전분", "골", "도움", "골p90"]].copy()
tb["Player"] = tb["Player"].map(KOR)
tb.columns = ["선수", "시즌", "경기", "선발", "출전분", "골", "도움", "골p90"]
st.dataframe(tb.sort_values(["시즌", "골"], ascending=[True, False])
             .set_index("시즌"), use_container_width=True, height=360)

st.markdown("""
<div class="credits">
<b>데이터</b> FBref 클럽 전 대회 합산 — 라리가·챔피언스리그·코파 델 레이·
수페르코파를 모두 더한 값이다. 라리가만 담은 다른 페이지와 숫자가 다른 이유다.<br>
<b>삼각형</b> 셋 사이의 연계는 Understat 라리가 골에서 도움-득점 짝을 뽑았다.
컵대회에서 나온 연계는 원본에 없어 빠진다.<br>
<b>범위</b> 세 명이 함께 뛴 2014/15~2016/17 세 시즌만 담았다. 네이마르는
2017년 여름 파리로 떠났고, 그 뒤 바르사는 이 조합을 다시 만들지 못했다.
</div>
""", unsafe_allow_html=True)
