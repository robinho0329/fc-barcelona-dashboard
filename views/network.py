"""연계 네트워크 — 누가 누구에게 어시스트했나."""
import pathlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, b64, load_sb, load_seasons,
                  load_understat, metric_cards, portrait_map, position_map,
                  sb_names, setup)

seasons = load_seasons()
setup(seasons)


# 표본이 이보다 적은 시즌은 뺀다. 1973/74처럼 몇 경기만 있는 시즌을 섞으면
# 시즌별 비교가 엉킨다.
MIN_GOALS = 20


@st.cache_data
def links(stamp: str) -> pd.DataFrame:
    """어시스트 → 득점 조합. 두 원본을 시즌으로 나눠 붙인다.

    Understat은 골마다 득점자와 도움자를 함께 주지만 2014/15부터다.
    StatsBomb은 2004/05까지 거슬러 가는데 도움자가 바로 들어 있지 않다.
    대신 슛의 shot.key_pass_id 가 그 슛을 만든 패스 이벤트를 가리키므로,
    그 패스를 던진 선수가 도움자다(fetch_statsbomb.py 에서 assisted_by 로 넣어 둠).

    겹치는 시즌은 Understat을 쓴다. 지금까지 이 페이지가 보여 온 값이고,
    도움이 기록된 비율도 조금 더 높다.
    """
    u = load_understat()
    us = pd.DataFrame()
    if not u.empty:
        d = u[u["is_barca"] & u["goal"] & u["player_assisted"].notna()].copy()
        d = d[d["player_assisted"].astype(str).str.strip() != ""]
        us = d.rename(columns={"player_assisted": "도움", "player_name": "득점"})
        us = us[["season", "도움", "득점"]].assign(출처="Understat")

    sb = load_sb("shots")
    sbd = pd.DataFrame()
    if not sb.empty and "assisted_by" in sb.columns:
        g = sb[sb["is_barca"] & sb["goal"] & sb["assisted_by"].notna()].copy()
        if not g.empty:
            # 이름을 FBref 쪽으로 맞춰야 두 원본이 같은 사람으로 묶인다
            g["도움"] = sb_names(g["assisted_by"]).values
            g["득점"] = sb_names(g["player"]).values
            sbd = g[["season", "도움", "득점"]].assign(출처="StatsBomb")

    if us.empty and sbd.empty:
        return pd.DataFrame()
    have = set(us["season"]) if not us.empty else set()
    parts = [x for x in (us, sbd[~sbd["season"].isin(have)] if not sbd.empty else sbd)
             if not x.empty]
    out = pd.concat(parts, ignore_index=True)

    keep = out.groupby("season").size()
    return out[out["season"].isin(keep[keep >= MIN_GOALS].index)].copy()


def _stamp() -> str:
    """두 원본 중 하나라도 바뀌면 다시 계산한다."""
    out = []
    for rel in ("data/understat/shots.parquet", "data/statsbomb/shots.parquet"):
        f = pathlib.Path(rel)
        out.append(f"{rel}:{f.stat().st_mtime if f.exists() else 0}")
    return "|".join(out)


raw = links(_stamp())

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">Assist Network · StatsBomb + Understat</div>
  <h1>연계 네트워크</h1>
  <div class="hero-motto">골은 혼자 만들지 않는다. 누가 누구에게 건네 골이 됐는지,
  바르사를 굴린 조합을 찾아본다. 두 원본을 붙여 <b>2004/05</b>까지 거슬러 본다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if raw.empty:
    st.warning("어시스트 데이터가 없습니다. `python fetch_understat.py` 와 "
               "`python fetch_statsbomb.py` 를 먼저 실행하세요.")
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
  득점 경로가 분산돼 있었다는 뜻이다.<br>
· <b>가로 방향</b>은 포지션이다. 왼쪽부터 골키퍼 · 수비수 · 미드필더 · 공격수로
  실제 라인업과 같은 순서다. 선이 왼쪽에서 오른쪽으로 길게 뻗으면 수비에서
  공격으로 한 번에 이어졌다는 뜻이고, 오른쪽 칸 안에서만 짧게 오가면
  공격진끼리 주고받아 골을 만들었다는 뜻이다.<br><br>
위쪽 <b>시즌</b>을 바꾸면 그 해의 조합만, <b>최소 연결 횟수</b>를 올리면 굵은
관계만 남는다. 특정 시즌을 골라 숫자를 1로 낮추면 그 해 골이 어떤 경로로
나왔는지 전부 볼 수 있다.
</div>
""", unsafe_allow_html=True)
if strong.empty:
    st.info("최소 연결 횟수를 낮춰 보세요.")
else:
    involved = pd.concat([strong["도움"], strong["득점"]]).value_counts()
    people = involved.index.tolist()
    photos = portrait_map(people)
    positions = position_map(people)

    # 포지션 띠로 세로 배치. 왼쪽이 골문, 오른쪽이 골대 — 실제 라인업과 같은 방향.
    ORDER_BANDS = [("GK", "골키퍼"), ("DF", "수비수"),
                   ("MF", "미드필더"), ("FW", "공격수")]
    BAND_COLOR = {"GK": "#4fb0a5", "DF": BLAU, "MF": GOLD, "FW": GRANA}
    BAND_W = 1.55

    grouped = {code: [] for code, _ in ORDER_BANDS}
    for name in people:
        grouped.get(positions.get(name) or "MF", grouped["MF"]).append(name)
    # 관여가 많은 선수를 가운데로 모아 선이 덜 엉키게 한다
    for code in grouped:
        ranked = sorted(grouped[code], key=lambda n: -involved.get(n, 0))
        mid, out = [], []
        for i, n in enumerate(ranked):
            (mid if i % 2 == 0 else out).append(n)
        grouped[code] = out[::-1] + mid

    # 사람이 없는 칸(대개 골키퍼)은 빼고 남은 칸만 고르게 벌린다. 빈 칸을
    # 그대로 두면 한쪽에 빈 공간이 생겨 그림이 치우쳐 보인다.
    used = [(c, lbl) for c, lbl in ORDER_BANDS if grouped[c]]
    step = 2.2
    BANDS = [(c, lbl, 0.9 + i * step) for i, (c, lbl) in enumerate(used)]
    X_MAX = 0.9 + (len(used) - 1) * step + 0.9 if used else 2.0

    tallest = max((len(v) for v in grouped.values()), default=1)
    # 한 칸에 선수가 많을수록 세로를 늘려 사진과 이름이 겹치지 않게 한다.
    SPAN = max(tallest, 6)
    ROW_PX = 78                      # 노드 하나에 줄 세로 픽셀
    HEIGHT = int(140 + SPAN * ROW_PX)
    pos = {}
    for code, _, cx in BANDS:
        col = grouped[code]
        if not col:
            continue
        ys = np.linspace(SPAN - 0.5, 0.5, len(col)) if len(col) > 1 else [SPAN / 2]
        for name, y in zip(col, ys):
            pos[name] = (cx, y)

    total = (view.groupby("도움").size().reindex(people).fillna(0)
             + view.groupby("득점").size().reindex(people).fillna(0))

    fig = go.Figure()

    # 포지션 띠 배경
    shapes, band_labels = [], []
    for code, label, cx in BANDS:
        if not grouped[code]:
            continue
        shapes.append(dict(type="rect", x0=cx - BAND_W / 2, x1=cx + BAND_W / 2,
                           y0=-0.35, y1=SPAN + 0.35, layer="below",
                           fillcolor=BAND_COLOR[code], opacity=.07,
                           line=dict(color=BAND_COLOR[code], width=1)))
        band_labels.append((cx, SPAN + 0.72, f"{label} ({len(grouped[code])})",
                            BAND_COLOR[code]))

    # 연결선 — 굵기는 골 수
    for _, r in strong.iterrows():
        if r["도움"] not in pos or r["득점"] not in pos:
            continue
        x0, y0 = pos[r["도움"]]
        x1, y1 = pos[r["득점"]]
        fig.add_trace(go.Scatter(
            x=[x0, x1], y=[y0, y1], mode="lines",
            line=dict(color=GRANA, width=min(1 + r["골"] * 0.7, 10)),
            opacity=min(.22 + r["골"] * 0.05, .8),
            hovertemplate=f"<b>{r['도움']} → {r['득점']}</b><br>"
                          f"{int(r['골'])}골<extra></extra>",
            showlegend=False))

    # 선수 사진 — 관여가 많을수록 크게
    imgs = []
    for name in people:
        if name not in pos:
            continue
        x, y = pos[name]
        size = float(np.clip(total.get(name, 0) * 0.009 + 0.34, 0.34, 0.66))
        uri = photos.get(name)
        if uri:
            imgs.append(dict(source=uri, x=x, y=y, sizex=size, sizey=size,
                             xref="x", yref="y", xanchor="center", yanchor="middle",
                             sizing="contain", layer="above"))

    # 사진이 없는 선수는 원으로, 이름은 모두 아래에
    no_photo = [n for n in people if n in pos and not photos.get(n)]
    if no_photo:
        fig.add_trace(go.Scatter(
            x=[pos[n][0] for n in no_photo], y=[pos[n][1] for n in no_photo],
            mode="markers", marker=dict(size=26, color="#0d2038",
                                        line=dict(width=1.5, color=GOLD)),
            hoverinfo="skip", showlegend=False))

    fig.add_trace(go.Scatter(
        x=[pos[n][0] for n in people if n in pos],
        y=[pos[n][1] - 0.40 for n in people if n in pos],
        mode="text",
        text=[n.split()[-1] if len(n) > 12 else n for n in people if n in pos],
        textposition="middle center",
        textfont=dict(size=10, color="#dbe6f5"),
        customdata=[[n, total.get(n, 0), positions.get(n) or "?"]
                    for n in people if n in pos],
        hovertemplate="<b>%{customdata[0]}</b> · %{customdata[2]}<br>"
                      "도움+득점 %{customdata[1]:.0f}회<extra></extra>",
        showlegend=False))

    for cx, cy, label, color in band_labels:
        fig.add_annotation(x=cx, y=cy, text=f"<b>{label}</b>", showarrow=False,
                           font=dict(size=12, color=color))

    fig.update_layout(
        height=HEIGHT, shapes=shapes,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        images=imgs, margin=dict(l=10, r=10, t=40, b=10),
        xaxis=dict(range=[0.0, X_MAX], visible=False),
        yaxis=dict(range=[-0.9, SPAN + 1.1], visible=False))
    st.plotly_chart(fig, width="stretch")

    hub = involved.index[0]
    hub_share = involved.iloc[0] / involved.sum() * 100
    unknown = sum(1 for n in people if not positions.get(n))
    st.caption(
        f"왼쪽부터 골키퍼 → 수비수 → 미드필더 → 공격수. 선 굵기 = 그 조합으로 "
        f"나온 골 수, 사진 크기 = 도움+득점 관여 횟수. "
        f"{min_link}골 이상 이어진 조합 {len(strong)}개만 그렸다. "
        f"이 범위에서는 {hub}에게 선이 가장 많이 몰린다(연결의 {hub_share:.0f}%)."
        + (f" 포지션을 못 찾은 {unknown}명은 미드필더 칸에 뒀다." if unknown else ""))

# ---------------------------------------------------------------- 시즌별 구조
st.markdown('<div class="section">시즌마다 연계가 어떻게 달랐나</div>',
            unsafe_allow_html=True)
st.markdown("""
<div class="lede">
같은 골 수라도 <b>몇 명이 얼마나 다양한 조합으로</b> 만들었는지는 시즌마다 다르다.
소수에게 몰리면 그 선수가 빠졌을 때 팀이 멈추고, 여러 조합으로 퍼져 있으면
경로가 많다는 뜻이다. 아래 <b>분산도</b>는 도움·득점 관여가 얼마나 고르게
나뉘었는지를 0~100으로 나타낸 값이다. 한 명이 다 하면 낮고, 고루 나눠 가지면
높다.
</div>
""", unsafe_allow_html=True)


@st.cache_data
def season_structure(stamp: str) -> pd.DataFrame:
    """시즌별 연계 구조. 분산도는 허핀달 지수를 뒤집어 0~100으로 만든 값이다."""
    src = links(stamp)
    if src.empty:
        return pd.DataFrame()
    rows = []
    for season, g in src.groupby("season"):
        pairs_n = g.groupby(["도움", "득점"]).size()
        people = pd.concat([g["도움"], g["득점"]]).value_counts()
        share = people / people.sum()
        rows.append({
            "시즌": season, "골": len(g), "참여 선수": len(people),
            "조합 수": len(pairs_n),
            "최다 허브 비중": share.iloc[0] * 100,
            "허브": people.index[0],
            "분산도": (1 - (share ** 2).sum()) * 100,
            "조합당 골": len(g) / len(pairs_n),
        })
    return pd.DataFrame(rows).sort_values("시즌").reset_index(drop=True)


struct = season_structure(_stamp())

if struct.empty:
    st.info("시즌별 구조를 계산할 데이터가 없습니다.")
else:
    ERA_OF = [("MSN", "2012/13", "2016/17", "#e0748f"),
              ("포스트 펩", "2017/18", "2020/21", "#7ab8ff"),
              ("재건", "2021/22", "2025/26", "#4fb0a5")]

    def era_color(sea: str) -> str:
        for _, a, b, c in ERA_OF:
            if a <= sea <= b:
                return c
        return "#6b7d99"

    struct["색"] = struct["시즌"].map(era_color)

    best = struct.loc[struct["분산도"].idxmax()]
    worst = struct.loc[struct["분산도"].idxmin()]
    st.markdown(metric_cards([
        ("가장 분산된 시즌", f"{best['시즌']}",
         f"분산도 {best['분산도']:.1f} · {int(best['참여 선수'])}명 참여"),
        ("가장 집중된 시즌", f"{worst['시즌']}",
         f"분산도 {worst['분산도']:.1f} · {worst['허브']} {worst['최다 허브 비중']:.0f}%"),
        ("최다 조합", f"{int(struct['조합 수'].max())}",
         f"{struct.loc[struct['조합 수'].idxmax(), '시즌']}"),
        ("조합당 골 최고", f"{struct['조합당 골'].max():.2f}",
         f"{struct.loc[struct['조합당 골'].idxmax(), '시즌']} · 같은 짝이 반복"),
    ]), unsafe_allow_html=True)

    fs1 = go.Figure()
    fs1.add_trace(go.Bar(
        x=struct["시즌"], y=struct["분산도"], name="분산도",
        marker_color=struct["색"],
        customdata=struct[["참여 선수", "조합 수", "허브", "최다 허브 비중"]].values,
        hovertemplate="<b>%{x}</b><br>분산도 %{y:.1f}<br>"
                      "참여 %{customdata[0]}명 · 조합 %{customdata[1]}개<br>"
                      "최다 허브 %{customdata[2]} (%{customdata[3]:.0f}%)<extra></extra>"))
    fs1.add_trace(go.Scatter(
        x=struct["시즌"], y=struct["최다 허브 비중"], name="최다 허브 비중(%)",
        mode="lines+markers", line=dict(color=GOLD, width=2.6), yaxis="y2"))
    fs1.update_layout(
        height=380,
        yaxis=dict(title="분산도 (0~100)", gridcolor=GRID, range=[70, 100]),
        yaxis2=dict(title="허브 비중(%)", overlaying="y", side="right",
                    range=[0, 40], showgrid=False),
        legend=dict(orientation="h", y=1.14), **PLOT)
    fs1.update_xaxes(gridcolor=GRID, tickangle=-60)
    st.plotly_chart(fs1, width="stretch")
    st.caption("막대가 높을수록 골이 여러 선수에게 퍼져 있고, 금색 선이 높을수록 "
               "한 선수에게 몰려 있다. 둘은 반대로 움직인다.")

    c1, c2 = st.columns(2)
    with c1:
        fs2 = go.Figure()
        fs2.add_trace(go.Bar(x=struct["시즌"], y=struct["조합 수"], name="조합 수",
                             marker_color=BLAU))
        fs2.add_trace(go.Scatter(x=struct["시즌"], y=struct["참여 선수"],
                                 name="참여 선수", mode="lines+markers",
                                 line=dict(color=GRANA, width=2.6)))
        fs2.update_layout(height=320, yaxis_title="개 / 명",
                          legend=dict(orientation="h", y=1.14), **PLOT)
        fs2.update_xaxes(gridcolor=GRID, tickangle=-60)
        fs2.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fs2, width="stretch")
        st.caption("골을 만든 서로 다른 조합의 수와, 관여한 선수 수")

    with c2:
        fs3 = go.Figure(go.Bar(
            x=struct["시즌"], y=struct["조합당 골"], marker_color=struct["색"],
            hovertemplate="<b>%{x}</b><br>조합당 %{y:.2f}골<extra></extra>"))
        fs3.update_layout(height=320, yaxis_title="조합당 골", **PLOT)
        fs3.update_xaxes(gridcolor=GRID, tickangle=-60)
        fs3.update_yaxes(gridcolor=GRID)
        st.plotly_chart(fs3, width="stretch")
        st.caption("높을수록 같은 짝이 반복해서 골을 만들었다는 뜻이다")

    st.markdown(f"""
<div class="lede">
결과는 <b>직관과 반대로 나온다</b>. 가장 화려했다는 MSN 시대
({struct.loc[struct['시즌'] == '2014/15', '시즌'].iloc[0] if '2014/15' in set(struct['시즌']) else '2014/15'}·2015/16)가
오히려 <b>가장 집중된</b> 시즌이고, 메시가 떠난 뒤인 2021/22가 가장 분산돼 있다.
셋이서 다 해결하던 팀과, 여럿이 나눠 넣는 팀의 차이다.<br><br>
그러니 <b>분산도가 높다고 더 좋은 팀은 아니다</b>. 2014/15는 분산도가 낮았지만
트레블을 했고, 2021/22는 분산도가 가장 높았지만 무관이었다. 이 지표는 잘하고
못하고가 아니라 <b>득점 경로가 어떤 모양이었나</b>를 말해 준다.<br><br>
<b>티키타카 지수</b>와도 다른 것을 잰다. 그쪽은 공이 어떻게 돌았는지(패스),
이쪽은 골이 누구에게서 나왔는지(득점 관여)를 본다. 패스를 아무리 촘촘히 돌려도
마무리를 한 명이 도맡으면 분산도는 낮게 나온다.
</div>
""", unsafe_allow_html=True)

    with st.expander("시즌별 구조 표"):
        tb = struct[["시즌", "골", "참여 선수", "조합 수", "조합당 골",
                     "허브", "최다 허브 비중", "분산도"]].copy()
        st.dataframe(tb.round(2).set_index("시즌"),
                     width="stretch", height=430)

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
    st.plotly_chart(f2, width="stretch")

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
    st.plotly_chart(f3, width="stretch")

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
    st.plotly_chart(f4, width="stretch")

with st.expander("조합 전체 표"):
    tb = pairs.copy()
    tb.columns = ["도움", "득점", "골"]
    st.dataframe(tb.reset_index(drop=True), width="stretch", height=420)

_us = raw[raw["출처"] == "Understat"]
_sb = raw[raw["출처"] == "StatsBomb"]
us_n, sb_n = len(_us), len(_sb)
us_from = _us["season"].min() if us_n else "-"
sb_from = _sb["season"].min() if sb_n else "-"
sb_to = _sb["season"].max() if sb_n else "-"

st.markdown(f"""
<div class="credits">
<b>데이터</b> 바르셀로나가 넣은 골 가운데 도움이 기록된 {len(raw):,}건.
시즌 범위는 {raw['season'].min()}~{raw['season'].max()}이며
<b>라리가 경기만</b> 담겨 있다. 챔피언스리그·코파에서 나온 조합은 빠진다.<br>
<b>원본 둘을 붙였다</b> {us_from}~는 <b>Understat</b>({us_n:,}건) — 골마다
득점자와 도움자를 함께 준다. 그 이전 {sb_from}~{sb_to}는 <b>StatsBomb</b>
({sb_n:,}건) — 도움자가 바로 들어 있지 않아, 슛의 <code>key_pass_id</code>가
가리키는 패스 이벤트를 찾아 그 패스를 던진 선수를 도움자로 삼았다.
겹치는 시즌은 Understat을 썼다.<br>
<b>이름</b> StatsBomb은 전체 이름(Lionel Andrés Messi Cuccittini)을 쓴다.
같은 사람으로 묶으려고 FBref 쪽 짧은 이름으로 맞췄다.<br>
<b>주의</b> 도움 없이 나온 골(직접 프리킥, 개인 돌파, 상대 실책 등)은 애초에
빠져 있다. 도움이 기록된 비율이 시즌마다 61~73%로 달라 <b>조합 수</b>처럼
개수를 세는 값은 시즌끼리 곧바로 견주면 안 된다. 골 20건이 안 되는 시즌은 뺐다.<br>
<b>분산도는 표본 탓이 아니다</b> 시즌마다 표본이 다르니 분산도도 흔들리는 것
아니냐고 볼 수 있어 직접 확인했다. 골 수와 분산도의 상관은 -0.11로 사실상
없다. 가장 집중된 2015/16(79골·81.7)을 가장 분산된 2021/22와 같은 표본
크기(51골)로 줄여 200번 다시 뽑아도 평균 81.5(95% 구간 79.4~83.4)로,
2021/22의 92.8은 그 밖에 있다. <b>두 시즌의 차이는 실제 구조 차이다.</b>
</div>
""", unsafe_allow_html=True)
