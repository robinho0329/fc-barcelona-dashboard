"""MSN — 메시·수아레스·네이마르, 2014/15~2016/17."""
import pathlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, b64, load_dir, load_sb,
                  load_seasons, load_understat, metric_cards,
                  portrait_map, sb_names, setup)

def draw_triangle(links: pd.DataFrame, order: list, kor: dict, color: dict,
                  photos: dict, note: str) -> None:
    """세 사람 사이의 도움→득점을 삼각형으로 그린다.

    같은 두 사람 사이에 방향이 둘이라 곡선을 겹치지 않게 해야 한다. 법선을
    **항상 삼각형 바깥**으로 돌리고 반지름만 다르게 줘 동심 아치로 만든다.
    한쪽이라도 안으로 휘면 그 라벨들이 무게중심에 겹쳐 쌓인다.
    """
    R = 1.62
    ang = {order[0]: np.pi / 2,
           order[1]: np.pi / 2 + 2 * np.pi / 3,
           order[2]: np.pi / 2 - 2 * np.pi / 3}
    pos = {n: (R * np.cos(a), R * np.sin(a)) for n, a in ang.items()}

    fig = go.Figure()
    for r in links.itertuples():
        a, b = r.도움, r.득점
        if a not in pos or b not in pos:
            continue
        x0, y0 = pos[a]
        x1, y1 = pos[b]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        lo, hi = sorted((a, b), key=order.index)
        fx0, fy0 = pos[lo]
        fx1, fy1 = pos[hi]
        nx, ny = -(fy1 - fy0), (fx1 - fx0)
        norm = (nx ** 2 + ny ** 2) ** .5 or 1
        nx, ny = nx / norm, ny / norm
        if nx * mx + ny * my < 0:
            nx, ny = -nx, -ny
        off = 0.45 if a == lo else 1.65
        cx, cy = mx + nx * off, my + ny * off
        t_ = np.linspace(0, 1, 40)
        bx = (1 - t_) ** 2 * x0 + 2 * (1 - t_) * t_ * cx + t_ ** 2 * x1
        by = (1 - t_) ** 2 * y0 + 2 * (1 - t_) * t_ * cy + t_ ** 2 * y1
        fig.add_trace(go.Scatter(
            x=bx, y=by, mode="lines",
            line=dict(color=color[a], width=2.5 + r.골 * 0.6), opacity=.85,
            hovertemplate=f"<b>{kor[a]} \u2192 {kor[b]}</b><br>{r.골}골<extra></extra>",
            showlegend=False))
        fig.add_annotation(x=bx[36], y=by[36], ax=bx[32], ay=by[32],
                           xref="x", yref="y", axref="x", ayref="y",
                           showarrow=True, arrowhead=3, arrowsize=1.3,
                           arrowwidth=2, arrowcolor=color[a], text="")
        tl = 0.5
        lx = (1 - tl) ** 2 * x0 + 2 * (1 - tl) * tl * cx + tl ** 2 * x1
        ly = (1 - tl) ** 2 * y0 + 2 * (1 - tl) * tl * cy + tl ** 2 * y1
        lx += nx * 0.16
        ly += ny * 0.16
        fig.add_annotation(x=lx, y=ly, text=f"<b>{r.골}</b>", showarrow=False,
                           font=dict(size=20, color="#f2f6fc"),
                           bgcolor="rgba(4,16,31,.92)",
                           bordercolor=color[a], borderwidth=2, borderpad=5)

    imgs = [dict(source=photos[n], x=x, y=y, sizex=1.55, sizey=1.55,
                 xref="x", yref="y", xanchor="center", yanchor="middle",
                 sizing="contain", layer="above")
            for n, (x, y) in pos.items() if photos.get(n)]
    for n in order:
        fig.add_annotation(x=pos[n][0], y=pos[n][1] - 0.92,
                           text=f"<b>{kor[n]}</b>", showarrow=False,
                           font=dict(size=16, color="#f2f6fc"),
                           bgcolor="rgba(4,16,31,.9)",
                           bordercolor=color[n], borderwidth=1.5, borderpad=3)
    fig.update_layout(
        height=760, images=imgs,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(range=[-2.7, 2.7], visible=False, constrain="domain"),
        yaxis=dict(range=[-3.0, 2.8], visible=False, scaleanchor="x", scaleratio=1))
    st.plotly_chart(fig, width="stretch")

    tbl = (links.assign(도움=links["도움"].map(kor), 득점=links["득점"].map(kor))
           .sort_values("골", ascending=False)[["도움", "득점", "골"]])
    st.dataframe(tbl.reset_index(drop=True), width="stretch",
                 hide_index=True)
    st.caption(note)


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
    out = (g.groupby(["player_assisted", "player_name"]).size()
           .reset_index(name="골"))
    out.columns = ["도움", "득점", "골"]
    return out


_d = pathlib.Path("data/fbref_allcomps_players")
_stamp = "|".join(sorted(f"{f.name}:{f.stat().st_mtime}" for f in _d.glob("*.parquet"))) \
    if _d.exists() else ""
_u = pathlib.Path("data/understat/shots.parquet")

trio = trio_stats(_stamp)
team = team_goals(_stamp)
links = trio_links(_u.stat().st_mtime if _u.exists() else 0.0)

# 트랜스퍼마르크트 증명사진은 얼굴만 나오고 소속팀도 제각각이다(수아레스는
# 인터 마이애미, 네이마르는 대표팀). 역사 페이지에 쓰던 2015/16 3인 사진을
# 세로로 잘라 쓰고, 없을 때만 증명사진으로 떨어진다.
CROP = {"Lionel Messi": "msn/messi.jpg", "Luis Suárez": "msn/suarez.jpg",
        "Neymar": "msn/neymar.jpg"}
photos = portrait_map(TRIO)
for _n, _rel in CROP.items():
    if (pathlib.Path("assets") / _rel).exists():
        photos[_n] = b64(_rel)

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">삼각편대의 역사 · 2010 – 2017</div>
  <h1>삼각편대의 역사</h1>
  <div class="hero-motto">바르사에는 시대를 대표한 공격 삼각형이 둘 있었다.
  먼저 온 <b>MVP</b>(메시·비야·페드로), 그다음이 <b>MSN</b>(메시·수아레스·네이마르)다.
  시간순으로 놓고 같은 기준으로 잰다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)
if trio.empty:
    st.warning("선수 데이터가 없습니다. `python crawl_allcomps.py`를 먼저 실행하세요.")
    st.stop()

# ---------------------------------------------------------------- 1기 MVP
# MSN 이전에도 삼각편대가 있었다. 과르디올라 말기의 메시·비야·페드로다.
# 같은 기준(FBref 전 대회)으로 재서 두 조합을 나란히 놓는다.
MVP = ["Lionel Messi", "David Villa", "Pedro"]
MVP_SEASONS = ["2010/11", "2011/12"]
MVP_KOR = {"Lionel Messi": "메시", "David Villa": "비야", "Pedro": "페드로"}
MVP_COLOR = {"Lionel Messi": GRANA, "David Villa": GOLD, "Pedro": BLAU}


# StatsBomb 은 선수 이름을 전체 이름으로 준다. FBref 짧은 이름과 잇는다.
SB_MVP = {"Lionel Andrés Messi Cuccittini": "Lionel Messi",
          "David Villa Sánchez": "David Villa",
          "Pedro Eliezer Rodríguez Ledesma": "Pedro"}


@st.cache_data
def mvp_links(stamp: float) -> pd.DataFrame:
    """1기 셋 사이에서 나온 골.

    Understat 은 2014/15부터라 이 시기가 비어 있다. 대신 StatsBomb 슛의
    shot.key_pass_id 를 그 슛을 만든 패스 이벤트와 이어 도움 준 선수를 얻는다.
    """
    sh = load_sb("shots")
    if sh.empty or "assisted_by" not in sh.columns:
        return pd.DataFrame()
    g = sh[sh["is_barca"] & sh["goal"] & sh["season"].isin(["2010/11", "2011/12"])
           & sh["player"].isin(SB_MVP) & sh["assisted_by"].isin(SB_MVP)]
    if g.empty:
        return pd.DataFrame()
    out = (g.groupby([g["assisted_by"].map(SB_MVP), g["player"].map(SB_MVP)])
           .size().reset_index(name="골"))
    out.columns = ["도움", "득점", "골"]
    return out


@st.cache_data
def mvp_routes(stamp: float) -> pd.DataFrame:
    """1기 셋이 넣은 골의 상황·부위·마무리, 그리고 도움 준 사람.

    2기는 Understat을 쓰지만 이 시기는 없어서 StatsBomb을 쓴다. 두 원본은
    값 이름이 달라(Regular Play vs OpenPlay) 표를 따로 둔다.
    """
    sh = load_sb("shots")
    if sh.empty:
        return pd.DataFrame()
    g = sh[sh["is_barca"] & sh["goal"]
           & sh["season"].isin(["2010/11", "2011/12"])].copy()
    if g.empty:
        return pd.DataFrame()
    g["이름"] = sb_names(g["player"]).values
    g["도움"] = sb_names(g["assisted_by"]).values
    return g[g["이름"].isin(MVP)].copy()


@st.cache_data
def mvp_stats(stamp: str) -> pd.DataFrame:
    ac = load_dir("fbref_allcomps_players")
    if ac.empty:
        return pd.DataFrame()
    return ac[(ac["대회"] == "전 대회") & ac["Player"].isin(MVP)
              & ac["season"].isin(MVP_SEASONS)].copy()


@st.cache_data
def mvp_team_goals(stamp: str) -> pd.Series:
    ac = load_dir("fbref_allcomps_players")
    if ac.empty:
        return pd.Series(dtype=float)
    return (ac[(ac["대회"] == "전 대회") & ac["season"].isin(MVP_SEASONS)]
            .groupby("season")["골"].sum())


mvp = mvp_stats(_stamp)
mvp_team = mvp_team_goals(_stamp)

if not mvp.empty:
    st.markdown('<div class="section">1기 · MVP — 메시 · 비야 · 페드로 (2010/11~2011/12)</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="lede">
먼저 온 조합이다. 과르디올라 마지막 두 시즌, 메시 옆에는 <b>다비드 비야</b>와
<b>페드로</b>가 있었다. 셋 다 발이 빠르고 뒷공간을 노려, 점유율로 상대를 눌러 놓고
한 번에 찌르는 방식이었다. 2011년 12월 비야가 정강이 골절로 빠지면서 사실상
해체됐다. 아래는 2기와 <b>같은 기준</b>(FBref 전 대회 합산)으로 잰 수치다.
</div>
""", unsafe_allow_html=True)

    # 2기와 같은 방식 — 셋이 함께 있는 사진 한 장을 세로로 잘라 카드에 쓴다.
    if pathlib.Path("assets/mvp/line.jpg").exists():
        st.markdown(f'<img class="msn-banner" src="{b64("mvp/line.jpg")}" '
                    'alt="페드로 · 비야 · 메시">', unsafe_allow_html=True)
        st.caption("가슴의 카타르 재단 로고로 보아 2011/12 시즌. 왼쪽부터 다비드 비야(7) · 메시 · 페드로.")

    MVP_CROP = {}
    for _n, _f in [("Lionel Messi", "mvp/messi.jpg"), ("David Villa", "mvp/villa.jpg"),
                   ("Pedro", "mvp/pedro.jpg")]:
        if (pathlib.Path("assets") / _f).exists():
            MVP_CROP[_n] = b64(_f)
    mvp_faces = portrait_map(MVP)
    cards = ""
    for name in MVP:
        part = mvp[mvp["Player"] == name]
        g, a = int(part["골"].sum()), int(part["도움"].sum())
        mp = int(part["경기"].sum())
        src = MVP_CROP.get(name) or mvp_faces.get(name, "")
        # 1기 사진은 배너에서 잘라낸 것이라 세로로 짧다. 2기처럼 cover 로
        # 다시 자르면 머리가 날아가므로 전체를 보여준다.
        img = (f'<img class="msn-photo whole" src="{src}" alt="{name}">' if src else "")
        cards += (
            f'<div class="msn-card" style="border-top:4px solid {MVP_COLOR[name]}">'
            f'{img}<div class="msn-body"><div class="msn-name">{MVP_KOR[name]}</div>'
            f'<div class="msn-full">{name}</div>'
            f'<div class="msn-line"><b>{g}</b>골 · <b>{a}</b>도움</div>'
            f'<div class="msn-sub">{mp}경기 · 경기당 {g / max(mp, 1):.2f}골</div>'
            f'</div></div>')
    st.markdown(f'<div class="msn-grid">{cards}</div>', unsafe_allow_html=True)

    # ---- 연혁
    st.markdown('<div class="section">1기 연혁</div>', unsafe_allow_html=True)
    MVP_HISTORY = [
        ("2010.05", "비야 합류", "발렌시아에서 4천만 유로에 도착. 직전 남아공 "
                                "월드컵에서 스페인의 결승골을 넣고 온 최전성기였다."),
        ("2010.08", "페드로의 도약", "라 마시아 출신 윙어가 주전으로 올라서며 "
                                   "오른쪽을 맡았다. 셋의 배치가 자리를 잡았다."),
        ("2011.05", "웸블리 결승", "맨유를 3-1로 꺾고 유럽 정상. 페드로가 선제골, "
                                 "메시가 추가골, 비야가 쐐기골을 넣었다."),
        ("2011.12", "비야 정강이 골절", "클럽월드컵 알사드전에서 골절. 시즌 아웃되며 "
                                     "삼각편대가 사실상 해체됐다."),
        ("2012.05", "과르디올라 이임", "4년 임기를 마치고 떠났다. 비야는 2013년 "
                                    "아틀레티코로, 페드로는 2015년 첼시로 향했다."),
    ]
    cards2 = "".join(
        f'<div class="timeline-card"><div class="timeline-year">{y}</div>'
        f'<div class="timeline-title">{ti}</div><div class="timeline-body">{b}</div></div>'
        for y, ti, b in MVP_HISTORY)
    st.markdown(f'<div class="timeline-grid">{cards2}</div>', unsafe_allow_html=True)

    # ---- 트로피
    st.markdown('<div class="section">1기가 든 트로피</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="lede">
셋이 함께 뛴 두 시즌 동안 바르사는 <b>6개 대회에서 우승</b>했다. 2010/11에
리그와 챔피언스리그를 가져갔고, 2011년에는 UEFA 슈퍼컵과 클럽월드컵까지
더했다. 다만 2011/12 리그는 레알 마드리드에 9점 차로 내줬다.
</div>
""", unsafe_allow_html=True)
    MVP_TROPHIES = [
        ("2010/11", "라리가 · 챔피언스리그", "웸블리에서 맨유 3-1. 리그는 승점 96점"),
        ("2011", "수페르코파 · UEFA 슈퍼컵", "레알에 합계 5-4, 포르투에 2-0"),
        ("2011/12", "클럽월드컵 · 코파 델 레이", "산투스 4-0, 빌바오 3-0. 리그는 2위"),
    ]
    cards3 = "".join(
        f'<div class="timeline-card tl-win"><div class="timeline-year">{y}</div>'
        f'<div class="timeline-title">{ti}</div><div class="timeline-body">{b}</div></div>'
        for y, ti, b in MVP_TROPHIES)
    st.markdown(f'<div class="timeline-grid">{cards3}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section">두 시즌 합계</div>', unsafe_allow_html=True)
    mvp_goals = int(mvp["골"].sum())
    mvp_team_total = int(mvp_team.sum())
    msn_goals = int(trio["골"].sum())
    msn_team_total = int(sum(team.get(s, 0) for s in SEASONS))
    st.markdown(metric_cards([
        ("합계 득점", f"{mvp_goals}골",
         f"{MVP_SEASONS[0]}~{MVP_SEASONS[-1]} · 2시즌"),
        ("팀 득점 비중", f"{mvp_goals / max(mvp_team_total, 1) * 100:.1f}%",
         f"팀 {mvp_team_total}골 중"),
        ("메시 비중", f"{int(mvp[mvp['Player'] == 'Lionel Messi']['골'].sum())}골",
         f"셋 중 {int(mvp[mvp['Player'] == 'Lionel Messi']['골'].sum()) / max(mvp_goals, 1) * 100:.0f}%"),
        ("합계 도움", f"{int(mvp['도움'].sum())}도움", "전 대회 기준"),
    ]), unsafe_allow_html=True)

    # ---- 시즌별 득점
    st.markdown('<div class="section">1기 시즌별 득점</div>', unsafe_allow_html=True)
    mv1, mv2 = st.columns(2)
    with mv1:
        fm = go.Figure()
        for name in MVP:
            ys = (mvp[mvp["Player"] == name].set_index("season")["골"]
                  .reindex(MVP_SEASONS).fillna(0))
            fm.add_trace(go.Bar(x=MVP_SEASONS, y=ys.values, name=MVP_KOR[name],
                                marker_color=MVP_COLOR[name],
                                hovertemplate=f"<b>{MVP_KOR[name]}</b><br>"
                                              "%{x} %{y}골<extra></extra>"))
        fm.update_layout(height=360, barmode="stack", yaxis_title="골",
                         legend=dict(orientation="h", y=1.12), **PLOT)
        fm.update_xaxes(gridcolor=GRID)
        fm.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fm, width="stretch")
        st.caption("전 대회 합산. 2011/12에 비야가 빠진 자리가 그대로 보인다")

    with mv2:
        sh = [mvp[mvp["season"] == s]["골"].sum()
              / max(mvp_team.get(s, 1), 1) * 100 for s in MVP_SEASONS]
        fs2 = go.Figure(go.Bar(x=MVP_SEASONS, y=sh, marker_color=GRANA,
                               text=[f"{v:.0f}%" for v in sh], textposition="outside",
                               textfont_color="#f2f6fc",
                               hovertemplate="<b>%{x}</b><br>%{y:.1f}%<extra></extra>"))
        fs2.update_layout(height=360, yaxis_title="팀 득점 중 셋의 비중(%)", **PLOT)
        fs2.update_xaxes(gridcolor=GRID)
        fs2.update_yaxes(gridcolor=GRID, range=[0, 100])
        st.plotly_chart(fs2, width="stretch")
        st.caption(f"비야가 빠진 2011/12에 {sh[0] - sh[1]:.0f}%p 떨어졌다")

    with st.expander("1기 시즌별 기록 표"):
        tb = (mvp.assign(선수=mvp["Player"].map(MVP_KOR))
              [["season", "선수", "경기", "선발", "출전분", "골", "도움"]]
              .sort_values(["season", "골"], ascending=[True, False]))
        tb.columns = ["시즌", "선수", "경기", "선발", "출전분", "골", "도움"]
        st.dataframe(tb, width="stretch", hide_index=True)

    # ---- 셋 사이의 삼각형
    _sb = pathlib.Path("data/statsbomb/shots.parquet")
    mvp_tri = mvp_links(_sb.stat().st_mtime if _sb.exists() else 0.0)
    if not mvp_tri.empty:
        st.markdown('<div class="section">1기 · 셋 사이의 삼각형</div>',
                    unsafe_allow_html=True)
        st.markdown("""
<div class="lede">
셋이 서로 건네 넣은 골만 뽑았다. 화살표는 <b>도움 → 득점</b> 방향이고 숫자는
그렇게 나온 골 수다. 2기와 달리 이 시기는 Understat에 없어, <b>StatsBomb</b>
원본에서 슛을 만든 패스를 되짚어 도움 준 선수를 찾았다.
</div>
""", unsafe_allow_html=True)
        draw_triangle(
            mvp_tri, MVP, MVP_KOR, MVP_COLOR, MVP_CROP,
            f"라리가 경기만 집계. 셋 사이에서만 {int(mvp_tri['골'].sum())}골이 나왔다. "
            "2기(85골)보다 훨씬 적은데, 원본이 달라서가 아니다. 같은 StatsBomb으로 "
            "2기를 재도 81골이 나온다. 시즌당으로 맞추면 1기 14.5 대 2기 27.0으로, "
            "실제로 두 배 가까이 차이가 난다. 비야·페드로가 두 시즌 합쳐 57골인 반면 "
            "수아레스·네이마르는 세 시즌 205골이었고, 1기는 셋끼리보다 "
            "차비·이니에스타·알베스에게 공을 받았다. 도움이 기록되지 않은 골"
            "(직접 프리킥·개인 돌파 등)은 애초에 빠져 있어 실제 합작은 이보다 많다.")
    else:
        st.caption("1기의 내부 삼각형을 만들 데이터가 없다. "
                   "`python fetch_statsbomb.py` 를 먼저 실행하면 채워진다.")

    # ---- 주 공격 루트
    mvp_rt = mvp_routes(_sb.stat().st_mtime if _sb.exists() else 0.0)
    if not mvp_rt.empty:
        st.markdown('<div class="section">1기 · 주 공격 루트</div>',
                    unsafe_allow_html=True)
        # StatsBomb 표기는 Understat 과 다르다(Regular Play vs OpenPlay).
        SB_PATTERN = {"Regular Play": "오픈 플레이", "From Free Kick": "프리킥 상황",
                      "From Throw In": "스로인 상황", "From Counter": "역습",
                      "From Corner": "코너", "From Goal Kick": "골킥 상황",
                      "From Kick Off": "킥오프", "From Keeper": "골키퍼 전개",
                      "Other": "기타"}
        SB_BODY = {"Left Foot": "왼발", "Right Foot": "오른발", "Head": "헤더",
                   "Other": "기타"}
        SB_TECH = {"Normal": "일반", "Half Volley": "하프발리", "Volley": "발리",
                   "Lob": "로빙", "Overhead Kick": "오버헤드",
                   "Backheel": "백힐", "Diving Header": "다이빙 헤더"}

        r1, r2 = st.columns(2)
        with r1:
            pat = (mvp_rt.assign(상황=mvp_rt["pattern"].map(SB_PATTERN).fillna("기타"))
                   .groupby(["이름", "상황"]).size().unstack(fill_value=0)
                   .reindex(MVP).fillna(0))
            fp = go.Figure()
            for col in pat.columns:
                fp.add_trace(go.Bar(x=[MVP_KOR[i] for i in pat.index],
                                    y=pat[col], name=col))
            fp.update_layout(height=340, barmode="stack", yaxis_title="골",
                             legend=dict(orientation="h", y=1.14), **PLOT)
            fp.update_xaxes(gridcolor=GRID)
            fp.update_yaxes(gridcolor=GRID)
            st.plotly_chart(fp, width="stretch")
            st.caption("상황별 득점. 흐름 속에서 나온 골이 절반을 넘는다")

        with r2:
            bod = (mvp_rt.assign(부위=mvp_rt["body_part"].map(SB_BODY).fillna("기타"))
                   .groupby(["이름", "부위"]).size().unstack(fill_value=0)
                   .reindex(MVP).fillna(0))
            fb = go.Figure()
            for col in bod.columns:
                fb.add_trace(go.Bar(x=[MVP_KOR[i] for i in bod.index],
                                    y=bod[col], name=col))
            fb.update_layout(height=340, barmode="stack", yaxis_title="골",
                             legend=dict(orientation="h", y=1.14), **PLOT)
            fb.update_xaxes(gridcolor=GRID)
            fb.update_yaxes(gridcolor=GRID)
            st.plotly_chart(fb, width="stretch")
            st.caption("왼발 득점이 오른발의 두 배가 넘는다 — 메시 몫이 크다")

        # Understat 의 lastAction 은 StatsBomb 에 없다. 대신 골로 이어진 패스
        # 자체의 속성(스루패스·크로스·코너 등)으로 같은 자리를 채웠다.
        # fetch_statsbomb.py 의 assist_kind 를 보라.
        if "assist_kind" in mvp_rt.columns:
            act = mvp_rt["assist_kind"].value_counts().iloc[::-1]
            st.markdown('<div class="section">1기 · 골 직전에 무슨 일이 있었나</div>',
                        unsafe_allow_html=True)
            fa = go.Figure(go.Bar(y=act.index, x=act.values, orientation="h",
                                  marker_color=GRANA, text=act.values,
                                  textposition="outside", textfont_color="#f2f6fc",
                                  hovertemplate="<b>%{y}</b><br>%{x}골<extra></extra>"))
            fa.update_layout(height=320, xaxis_title="골", **PLOT)
            fa.update_xaxes(gridcolor=GRID, range=[0, int(act.max()) * 1.2])
            fa.update_yaxes(gridcolor=GRID, type="category")
            st.plotly_chart(fa, width="stretch")
            st.caption(
                "'직접'은 도움 없이 혼자 만든 골이다(개인 돌파·직접 프리킥 등). "
                "같은 원본으로 2기를 재면 **스루패스 19.1% · 크로스 13.4%** 인데 "
                "1기는 **스루패스 27.0% · 크로스 6.6%** 다. 발 빠른 셋이 뒷공간으로 "
                "달리고 거기로 찔러 넣는 방식이었다는 뜻이다.")

        tech = (mvp_rt["technique"].map(lambda v: SB_TECH.get(v, "기타"))
                .value_counts().iloc[::-1])
        with st.expander("1기 · 어떻게 마무리했나 (슛 기술)"):
            ft = go.Figure(go.Bar(y=tech.index, x=tech.values, orientation="h",
                                  marker_color=BLAU, text=tech.values,
                                  textposition="outside", textfont_color="#f2f6fc",
                                  hovertemplate="<b>%{y}</b><br>%{x}골<extra></extra>"))
            ft.update_layout(height=280, xaxis_title="골", **PLOT)
            ft.update_xaxes(gridcolor=GRID, range=[0, int(tech.max()) * 1.2])
            ft.update_yaxes(gridcolor=GRID, type="category")
            st.plotly_chart(ft, width="stretch")

        feed = (mvp_rt[mvp_rt["도움"].notna() & ~mvp_rt["도움"].isin(MVP)]
                ["도움"].value_counts().head(8).iloc[::-1])
        if not feed.empty:
            st.markdown('<div class="section">1기 · 셋에게 공을 대준 사람들</div>',
                        unsafe_allow_html=True)
            ff = go.Figure(go.Bar(y=feed.index, x=feed.values, orientation="h",
                                  marker_color=BLAU, text=feed.values,
                                  textposition="outside", textfont_color="#f2f6fc",
                                  hovertemplate="<b>%{y}</b><br>%{x}도움<extra></extra>"))
            ff.update_layout(height=320, xaxis_title="셋에게 준 도움", **PLOT)
            ff.update_xaxes(gridcolor=GRID, range=[0, int(feed.max()) * 1.25])
            ff.update_yaxes(gridcolor=GRID, type="category")
            st.plotly_chart(ff, width="stretch")
            st.caption("셋 바깥에서 온 공. 오른쪽 풀백 알베스가 압도적으로 많다 — "
                       "1기가 셋끼리보다 측면과 중원에서 받았다는 뜻이다.")


# ---------------------------------------------------------------- 2기 MSN
st.markdown('<div class="section">2기 · MSN — 메시 · 수아레스 · 네이마르 (2014/15~2016/17)</div>', unsafe_allow_html=True)
# 세 사람이 함께 있는 한 장. 아래 카드 사진은 모두 이 사진에서 잘라낸 것이다.
if pathlib.Path("assets/eras/era_msn.jpg").exists():
    st.markdown(f'<img class="msn-banner" src="{b64("eras/era_msn.jpg")}" '
                'alt="수아레스 · 네이마르 · 메시">', unsafe_allow_html=True)
    st.caption("2015/16 캄 노우. 왼쪽부터 수아레스(9) · 네이마르(11) · 메시(10).")

st.markdown('<div class="section">세 사람</div>', unsafe_allow_html=True)
cards = ""
for name in TRIO:
    part = trio[trio["Player"] == name]
    g = int(part["골"].sum())
    a = int(part["도움"].sum())
    mp = int(part["경기"].sum())
    src = photos.get(name, "")
    # 잘라낸 뒷모습이 아니라 개별 사진이라 비율이 제각각이다. 1기와 같이
    # 채우되 얼굴이 남도록 위쪽을 기준으로 자른다.
    img = (f'<img class="msn-photo whole" src="{src}" alt="{name}">' if src else "")
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
    st.plotly_chart(f1, width="stretch")
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
    st.plotly_chart(f2, width="stretch")
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
    draw_triangle(
        links, TRIO, KOR, COLOR, photos,
        f"라리가 경기만 집계. 셋 사이에서만 {int(links['골'].sum())}골이 나왔다. "
        "선 색과 화살표는 도움을 준 쪽이다. 원본에 도움이 기록되지 않은 골"
        "(직접 프리킥·개인 돌파·세컨드볼 등)은 애초에 빠져 있어, 실제 합작은 "
        "이보다 많다.")

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
        st.plotly_chart(fr, width="stretch")
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
        st.plotly_chart(fb, width="stretch")
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
    st.plotly_chart(fa, width="stretch")

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
        st.plotly_chart(ff, width="stretch")
        st.caption("셋을 뺀 나머지 선수들의 도움. 알바·알베스 같은 풀백이 위에 있다")

# ---------------------------------------------------------------- 표
st.markdown('<div class="section">시즌별 기록</div>', unsafe_allow_html=True)
tb = trio[["Player", "season", "경기", "선발", "출전분", "골", "도움", "골p90"]].copy()
tb["Player"] = tb["Player"].map(KOR)
tb.columns = ["선수", "시즌", "경기", "선발", "출전분", "골", "도움", "골p90"]
st.dataframe(tb.sort_values(["시즌", "골"], ascending=[True, False])
             .set_index("시즌"), width="stretch", height=360)

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


# ------------------------------------------------------------------ 1기 vs 2기
if not mvp.empty:
    st.markdown('<div class="section">1기와 2기, 무엇이 달랐나</div>',
                unsafe_allow_html=True)
    st.markdown("""
<div class="lede">
시즌 수가 2 대 3으로 달라 총합으로는 견줄 수 없다. <b>시즌당</b>으로 맞추고,
팀 득점에서 차지한 비중을 함께 본다. 비중이 높다는 건 그만큼 공격을 셋에게
<b>의존했다</b>는 뜻이기도 하다.
</div>
""", unsafe_allow_html=True)

    # 두 조합을 한 눈에 — 시즌 수가 달라 '시즌당'으로 맞춘다
    comp = pd.DataFrame([
        {"조합": "MVP (2010~12)", "시즌당 득점": mvp_goals / len(MVP_SEASONS),
         "팀 득점 비중": mvp_goals / max(mvp_team_total, 1) * 100},
        {"조합": "MSN (2014~17)", "시즌당 득점": msn_goals / len(SEASONS),
         "팀 득점 비중": msn_goals / max(msn_team_total, 1) * 100},
    ])
    cc1, cc2 = st.columns(2)
    for col, metric, unit in [(cc1, "시즌당 득점", "골"), (cc2, "팀 득점 비중", "%")]:
        with col:
            fc = go.Figure(go.Bar(
                x=comp["조합"], y=comp[metric], marker_color=[GOLD, GRANA],
                text=comp[metric].round(1), textposition="outside",
                textfont_color="#f2f6fc",
                hovertemplate="<b>%{x}</b><br>" + metric + " %{y:.1f}"
                              + unit + "<extra></extra>"))
            fc.update_layout(height=320, yaxis_title=f"{metric} ({unit})", **PLOT)
            fc.update_xaxes(gridcolor=GRID)
            fc.update_yaxes(gridcolor=GRID,
                            range=[0, float(comp[metric].max()) * 1.25])
            st.plotly_chart(fc, width="stretch")

    st.caption(
        f"MVP는 2시즌 {mvp_goals}골(팀의 "
        f"{mvp_goals / max(mvp_team_total, 1) * 100:.1f}%), MSN은 3시즌 {msn_goals}골"
        f"(팀의 {msn_goals / max(msn_team_total, 1) * 100:.1f}%). "
        "시즌 수가 달라 왼쪽은 시즌당으로 맞춰 비교했다. 비중은 MVP가 더 높은데, "
        "그만큼 공격을 셋에게 의존했다는 뜻이기도 하다."
    )
