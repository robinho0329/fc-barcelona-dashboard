"""연계 네트워크 — 누가 누구에게 어시스트했나."""
import pathlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, WHITE, b64, load_sb,
                  load_seasons, load_understat, metric_cards, setup)

seasons = load_seasons()
setup(seasons)


@st.cache_data
def links(stamp: float) -> pd.DataFrame:
    """어시스트 → 득점 조합. Understat이 두 이름을 모두 주므로 이쪽을 쓴다.

    StatsBomb 패스에도 어시스트 표시가 있지만 '받은 사람'이 없어 조합을 만들 수
    없다. Understat은 골마다 player(득점)와 player_assisted(도움)를 함께 준다.
    """
    u = load_understat()
    if u.empty:
        return pd.DataFrame()
    d = u[u["is_barca"] & u["goal"] & u["player_assisted"].notna()].copy()
    d = d[d["player_assisted"].astype(str).str.strip() != ""]
    return d.rename(columns={"player_assisted": "도움", "player_name": "득점"})


_u = pathlib.Path("data/understat/shots.parquet")
raw = links(_u.stat().st_mtime if _u.exists() else 0.0)

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">Assist Network · Understat</div>
  <h1>연계 네트워크</h1>
  <div class="hero-motto">골은 혼자 만들지 않는다. 누가 누구에게 건네 골이 됐는지,
  바르사를 굴린 조합을 찾아본다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if raw.empty:
    st.warning("어시스트 데이터가 없습니다. `python fetch_understat.py`를 먼저 실행하세요.")
    st.stop()

# ---------------------------------------------------------------- 필터
c1, c2 = st.columns([1.3, 1])
season_opts = ["전체"] + sorted(raw["season"].unique(), reverse=True)
season = c1.selectbox("시즌", season_opts)
view = raw if season == "전체" else raw[raw["season"] == season]
min_link = c2.slider("최소 연결 횟수", 1, 10, 3 if season == "전체" else 1)

if view.empty:
    st.info("조건에 맞는 골이 없습니다.")
    st.stop()

pairs = (view.groupby(["도움", "득점"]).size().reset_index(name="골")
         .sort_values("골", ascending=False))
strong = pairs[pairs["골"] >= min_link]

# ---------------------------------------------------------------- 요약
top_pair = pairs.iloc[0]
assist_top = view["도움"].value_counts()
score_top = view["득점"].value_counts()
st.markdown('<div class="section">범위</div>', unsafe_allow_html=True)
st.markdown(metric_cards([
    ("도움 붙은 골", f"{len(view):,}", f"{view['season'].nunique()}시즌"),
    ("최다 조합", f"{int(top_pair['골'])}골", f"{top_pair['도움']} → {top_pair['득점']}"),
    ("최다 도움", f"{int(assist_top.iloc[0])}", f"{assist_top.index[0]}"),
    ("최다 득점", f"{int(score_top.iloc[0])}", f"{score_top.index[0]}"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------- 네트워크
st.markdown('<div class="section">연계 지도</div>', unsafe_allow_html=True)
st.markdown("""
<div class="lede">
동그라미 하나가 선수 하나, 두 선수를 잇는 선은 <b>그 둘 사이에서 나온 골</b>이다.
한쪽이 건네고 다른 쪽이 넣었다는 뜻이며, 아래 세 가지로 읽으면 된다.<br><br>
· <b>선이 굵을수록</b> 그 조합으로 골이 많이 나왔다. 오래 함께 뛰며 서로를
  찾는 습관이 밴 짝일수록 굵어진다.<br>
· <b>원이 클수록</b> 도움과 득점을 합쳐 골에 많이 관여했다. 크기는 실력이
  아니라 <b>관여량</b>이라, 오래 뛴 선수가 자연히 커진다.<br>
· <b>선이 몰리는 자리</b>가 그 시기 공격의 통로다. 한 명에게 선이 집중되면
  팀이 그 선수에게 의존했다는 신호이고, 여러 명에게 고르게 퍼져 있으면
  득점 경로가 분산돼 있었다는 뜻이다.<br><br>
위쪽 <b>시즌</b>을 바꾸면 그 해의 조합만, <b>최소 연결 횟수</b>를 올리면 굵은
관계만 남는다. 특정 시즌을 골라 숫자를 1로 낮추면 그 해 골이 어떤 경로로
나왔는지 전부 볼 수 있다.
</div>
""", unsafe_allow_html=True)
if strong.empty:
    st.info("최소 연결 횟수를 낮춰 보세요.")
else:
    # 등장 인물을 원형으로 배치한다. 관여가 많은 선수를 위쪽부터 시계방향으로.
    involved = pd.concat([strong["도움"], strong["득점"]]).value_counts()
    people = involved.index.tolist()
    n = len(people)
    ang = np.linspace(np.pi / 2, np.pi / 2 - 2 * np.pi, n, endpoint=False)
    pos = {p: (np.cos(a), np.sin(a)) for p, a in zip(people, ang)}

    total = view.groupby("도움").size().reindex(people).fillna(0) \
        + view.groupby("득점").size().reindex(people).fillna(0)

    fig = go.Figure()
    # 선 — 굵기는 연결 횟수. 개수가 많아 트레이스를 굵기별로 묶는다.
    for _, r in strong.iterrows():
        x0, y0 = pos[r["도움"]]
        x1, y1 = pos[r["득점"]]
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1], mode="lines",
            line=dict(color=GRANA, width=min(1 + r["골"] * 0.6, 9)),
            opacity=min(.25 + r["골"] * 0.05, .85),
            hovertemplate=f"<b>{r['도움']} → {r['득점']}</b><br>"
                          f"{int(r['골'])}골<extra></extra>",
            showlegend=False))

    fig.add_trace(go.Scatter(
        x=[pos[p][0] for p in people], y=[pos[p][1] for p in people],
        mode="markers+text", text=people, textposition="middle center",
        textfont=dict(size=9, color="#04101f"),
        marker=dict(size=np.clip(total.to_numpy() * 1.6 + 22, 22, 62),
                    color=GOLD, line=dict(width=1.5, color="#0b1b2f")),
        customdata=total.to_numpy(),
        hovertemplate="<b>%{text}</b><br>도움+득점 %{customdata:.0f}회<extra></extra>",
        showlegend=False))

    fig.update_layout(
        height=620, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(range=[-1.35, 1.35], visible=False, constrain="domain"),
        yaxis=dict(range=[-1.35, 1.35], visible=False,
                   scaleanchor="x", scaleratio=1))
    st.plotly_chart(fig, use_container_width=True)
    hub = involved.index[0]
    hub_share = involved.iloc[0] / involved.sum() * 100
    st.caption(f"선 굵기 = 그 조합으로 나온 골 수 · 원 크기 = 도움+득점 관여 횟수. "
               f"{min_link}골 이상 이어진 조합 {len(strong)}개만 그렸다. "
               f"이 범위에서는 **{hub}**에게 선이 가장 많이 몰린다"
               f"(연결의 {hub_share:.0f}%).")

# ---------------------------------------------------------------- 상위 조합
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="section">상위 조합</div>', unsafe_allow_html=True)
    top = pairs.head(14).iloc[::-1]
    label = top["도움"] + " → " + top["득점"]
    f2 = go.Figure(go.Bar(
        y=label, x=top["골"], orientation="h", marker_color=GRANA,
        text=top["골"], textposition="outside", textfont_color="#f2f6fc",
        hovertemplate="<b>%{y}</b><br>%{x}골<extra></extra>"))
    f2.update_layout(height=440, xaxis_title="골", **PLOT)
    f2.update_xaxes(gridcolor=GRID, range=[0, int(top["골"].max()) * 1.2])
    f2.update_yaxes(gridcolor=GRID, type="category")
    st.plotly_chart(f2, use_container_width=True)

with c2:
    st.markdown('<div class="section">도움 · 득점 관여</div>', unsafe_allow_html=True)
    both = pd.DataFrame({
        "도움": view["도움"].value_counts(),
        "득점": view["득점"].value_counts()}).fillna(0)
    both["합"] = both["도움"] + both["득점"]
    both = both.nlargest(14, "합").iloc[::-1]
    f3 = go.Figure()
    f3.add_trace(go.Bar(y=both.index, x=both["득점"], orientation="h", name="득점",
                        marker_color=GRANA))
    f3.add_trace(go.Bar(y=both.index, x=both["도움"], orientation="h", name="도움",
                        marker_color=BLAU))
    f3.update_layout(height=440, barmode="stack", xaxis_title="횟수",
                     legend=dict(orientation="h", y=1.08), **PLOT)
    f3.update_xaxes(gridcolor=GRID)
    f3.update_yaxes(gridcolor=GRID, type="category")
    st.plotly_chart(f3, use_container_width=True)

# ---------------------------------------------------------------- 상호 연계
st.markdown('<div class="section">주고받은 사이</div>', unsafe_allow_html=True)
st.markdown("""
<div class="lede">
한쪽만 건네는 관계가 있고, 서로 주고받는 관계가 있다. 아래는 <b>양방향으로</b>
골을 만든 조합이다. 오래 함께 뛰며 서로를 살린 짝일수록 위로 온다.
</div>
""", unsafe_allow_html=True)
key = pairs.assign(a=pairs[["도움", "득점"]].min(axis=1),
                   b=pairs[["도움", "득점"]].max(axis=1))
mutual = (key.groupby(["a", "b"])
          .agg(합=("골", "sum"), 방향=("골", "size")).reset_index())
mutual = mutual[mutual["방향"] == 2].nlargest(12, "합")

if mutual.empty:
    st.info("이 범위에는 양방향 조합이 없습니다.")
else:
    rows = []
    for r in mutual.itertuples():
        ab = int(pairs[(pairs["도움"] == r.a) & (pairs["득점"] == r.b)]["골"].sum())
        ba = int(pairs[(pairs["도움"] == r.b) & (pairs["득점"] == r.a)]["골"].sum())
        rows.append({"짝": f"{r.a} ↔ {r.b}", f"→": ab, f"←": ba, "합": ab + ba})
    mt = pd.DataFrame(rows).iloc[::-1]
    f4 = go.Figure()
    f4.add_trace(go.Bar(y=mt["짝"], x=mt["→"], orientation="h",
                        name="앞사람이 도움", marker_color=GRANA))
    f4.add_trace(go.Bar(y=mt["짝"], x=mt["←"], orientation="h",
                        name="뒷사람이 도움", marker_color=BLAU))
    f4.update_layout(height=440, barmode="stack", xaxis_title="골",
                     legend=dict(orientation="h", y=1.08), **PLOT)
    f4.update_xaxes(gridcolor=GRID)
    f4.update_yaxes(gridcolor=GRID, type="category")
    st.plotly_chart(f4, use_container_width=True)

with st.expander("조합 전체 표"):
    tb = pairs.copy()
    tb.columns = ["도움", "득점", "골"]
    st.dataframe(tb.reset_index(drop=True), use_container_width=True, height=420)

st.markdown(f"""
<div class="credits">
<b>데이터</b> Understat — 바르셀로나가 넣은 골 가운데 도움이 기록된
{len(raw):,}건. 시즌 범위는 {raw['season'].min()}~{raw['season'].max()}이며
<b>라리가 경기만</b> 담겨 있다. 챔피언스리그·코파에서 나온 조합은 빠진다.<br>
<b>StatsBomb을 쓰지 않은 이유</b> 패스 이벤트에 어시스트 표시는 있지만 그 패스를
받아 넣은 선수가 기록돼 있지 않아 조합을 만들 수 없다. Understat은 골마다
득점자와 도움을 함께 주므로 이쪽을 썼다.<br>
<b>주의</b> 도움 없이 나온 골(직접 프리킥, 개인 돌파, 상대 실책 등)은 애초에
빠져 있다. 함께 뛴 시간이 길수록 조합 수가 커지는 것도 감안해서 봐야 한다.
</div>
""", unsafe_allow_html=True)
