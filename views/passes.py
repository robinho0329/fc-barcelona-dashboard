"""패스 맵 — StatsBomb 이벤트 기반.

라리가 2004/05~2020/21 바르사 524경기의 패스 364,353건을 좌표로 본다.
개별 화살표를 다 그리면 브라우저가 버티지 못해, 기본은 구역별 밀도로 보여주고
화살표는 표본을 뽑아 겹쳐 그린다.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, b64, load_sb, load_seasons,
                  metric_cards, pitch_layout, pitch_shapes, setup)

seasons = load_seasons()
setup(seasons)

passes = load_sb("passes")

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">StatsBomb Open Data · Event Level</div>
  <h1>패스 맵</h1>
  <div class="hero-motto">바르사가 공을 어디서 잡아 어디로 보냈는지.
  티키타카를 좌표로 펼쳐 본다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if passes.empty:
    st.warning("StatsBomb 이벤트 데이터가 없습니다. `python fetch_statsbomb.py`를 먼저 실행하세요.")
    st.stop()

# ---------------------------------------------------------------- 필터
c1, c2, c3 = st.columns([1.1, 1.6, 1.1])
season_opts = ["전체"] + sorted(passes["season"].unique())
season = c1.selectbox("시즌", season_opts)
view = passes if season == "전체" else passes[passes["season"] == season]

vol = view.groupby("player").size().sort_values(ascending=False)
player_opts = ["전체"] + [p for p in vol.index if isinstance(p, str)]
player = c2.selectbox("선수", player_opts)
if player != "전체":
    view = view[view["player"] == player]

mode = c3.selectbox("보기", ["구역별 밀도", "패스 화살표", "도착 지점"])

if view.empty:
    st.info("조건에 맞는 패스가 없습니다.")
    st.stop()

# ---------------------------------------------------------------- 요약
# 전진 패스: 시작보다 골대 쪽으로 5단위 이상 나아간 패스
progressive = view["end_x"] - view["x"] >= 5
final_third = (view["end_x"] >= 80) & (view["x"] < 80)
box = (view["end_x"] >= 102) & (view["end_y"].between(18, 62))

st.markdown('<div class="section">요약</div>', unsafe_allow_html=True)
st.markdown(metric_cards([
    ("패스", f"{len(view):,}", f"{view['match_id'].nunique()}경기"),
    ("성공률", f"{view['complete'].mean() * 100:.1f}%",
     f"성공 {int(view['complete'].sum()):,}건"),
    ("평균 길이", f"{view['length'].mean():.1f}",
     f"경기당 {len(view) / max(view['match_id'].nunique(), 1):.0f}회"),
    ("전진 패스", f"{progressive.mean() * 100:.0f}%", "5단위 이상 전진"),
    ("파이널서드 진입", f"{int(final_third.sum()):,}", f"전체의 {final_third.mean() * 100:.1f}%"),
    ("박스 투입", f"{int(box.sum()):,}", f"전체의 {box.mean() * 100:.1f}%"),
    ("크로스", f"{int(view['is_cross'].sum()):,}",
     f"성공률 {view.loc[view['is_cross'], 'complete'].mean() * 100:.0f}%"
     if view["is_cross"].any() else "없음"),
    ("어시스트", f"{int(view['is_assist'].sum()):,}", "골로 이어진 패스"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------- 피치
title = f"{player if player != '전체' else '바르셀로나 전체'} · {season}"
st.markdown(f'<div class="section">{mode}</div>', unsafe_allow_html=True)

if mode == "구역별 밀도":
    # 12x8 구역으로 나눠 시작 지점 밀도를 본다
    xb = np.linspace(0, 120, 13)
    yb = np.linspace(0, 80, 9)
    h, _, _ = np.histogram2d(view["x"], view["y"], bins=[xb, yb])
    fig = go.Figure(go.Heatmap(
        z=h.T, x=(xb[:-1] + xb[1:]) / 2, y=(yb[:-1] + yb[1:]) / 2,
        colorscale=[[0, "rgba(4,16,31,0)"], [.35, "rgba(0,77,152,.55)"],
                    [.7, "rgba(165,0,68,.8)"], [1, "rgba(237,187,0,.95)"]],
        hovertemplate="구역 (%{x:.0f}, %{y:.0f})<br>패스 %{z:.0f}건<extra></extra>",
        colorbar=dict(title="패스 수", thickness=12)))
    lay = pitch_layout(height=500, showlegend=False)
    lay["shapes"] = pitch_shapes()
    fig.update_layout(**lay)
    st.plotly_chart(fig, width="stretch")
    st.caption("패스를 **시작한** 지점 기준. 공격 방향은 오른쪽.")

elif mode == "도착 지점":
    xb = np.linspace(0, 120, 13)
    yb = np.linspace(0, 80, 9)
    h, _, _ = np.histogram2d(view["end_x"], view["end_y"], bins=[xb, yb])
    fig = go.Figure(go.Heatmap(
        z=h.T, x=(xb[:-1] + xb[1:]) / 2, y=(yb[:-1] + yb[1:]) / 2,
        colorscale=[[0, "rgba(4,16,31,0)"], [.35, "rgba(0,77,152,.55)"],
                    [.7, "rgba(165,0,68,.8)"], [1, "rgba(237,187,0,.95)"]],
        hovertemplate="구역 (%{x:.0f}, %{y:.0f})<br>도착 %{z:.0f}건<extra></extra>",
        colorbar=dict(title="패스 수", thickness=12)))
    lay = pitch_layout(height=500, showlegend=False)
    lay["shapes"] = pitch_shapes()
    fig.update_layout(**lay)
    st.plotly_chart(fig, width="stretch")
    st.caption("패스가 **도착한** 지점 기준.")

else:  # 패스 화살표
    only_prog = st.checkbox("전진 패스만 보기", value=True)
    src = view[progressive] if only_prog else view
    cap = 1200
    sample = src.sample(min(cap, len(src)), random_state=42) if len(src) > cap else src

    fig = go.Figure()
    for ok, color, name in [(True, GRANA, "성공"), (False, "#6b7d99", "실패")]:
        part = sample[sample["complete"] == ok]
        if part.empty:
            continue
        # None으로 구분해 한 트레이스에 선분을 모두 담는다 (성능)
        xs = np.empty(len(part) * 3)
        ys = np.empty(len(part) * 3)
        xs[0::3], xs[1::3], xs[2::3] = part["x"], part["end_x"], np.nan
        ys[0::3], ys[1::3], ys[2::3] = part["y"], part["end_y"], np.nan
        fig.add_trace(go.Scattergl(x=xs, y=ys, mode="lines", name=name,
                                   line=dict(color=color, width=1),
                                   opacity=.5, hoverinfo="skip"))
    lay = pitch_layout(height=500, showlegend=True,
                       legend=dict(orientation="h", y=1.06))
    fig.update_layout(**lay)
    st.plotly_chart(fig, width="stretch")
    st.caption(f"{len(sample):,}건 표시"
               + (f" (전체 {len(src):,}건 중 무작위 표본)" if len(src) > cap else "")
               + ". 선 하나가 패스 하나다.")

# ---------------------------------------------------------------- 유형·거리
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="section">패스 길이 분포</div>', unsafe_allow_html=True)
    bins = [0, 10, 20, 30, 45, 200]
    labels = ["~10", "10~20", "20~30", "30~45", "45+"]
    cut = pd.cut(view["length"], bins, labels=labels)
    agg = view.groupby(cut, observed=True)["complete"].agg(["size", "mean"])
    f2 = go.Figure()
    f2.add_trace(go.Bar(x=agg.index.astype(str), y=agg["size"], name="패스 수",
                        marker_color=BLAU, yaxis="y"))
    f2.add_trace(go.Scatter(x=agg.index.astype(str), y=agg["mean"] * 100, name="성공률",
                            mode="lines+markers", line=dict(color=GOLD, width=2.4),
                            yaxis="y2"))
    f2.update_layout(height=320, yaxis=dict(title="패스 수", gridcolor=GRID),
                     yaxis2=dict(title="성공률(%)", overlaying="y", side="right",
                                 range=[0, 100], showgrid=False),
                     legend=dict(orientation="h", y=1.14), **PLOT)
    f2.update_xaxes(gridcolor=GRID, title="길이(야드)")
    st.plotly_chart(f2, width="stretch")

with c2:
    st.markdown('<div class="section">전진 패스 상위 선수</div>', unsafe_allow_html=True)
    scope = passes if season == "전체" else passes[passes["season"] == season]
    prog_all = scope[scope["end_x"] - scope["x"] >= 5]
    top = prog_all.groupby("player").size().nlargest(12).iloc[::-1]
    f3 = go.Figure(go.Bar(y=top.index, x=top.values, orientation="h",
                          marker_color=GRANA,
                          hovertemplate="<b>%{y}</b><br>전진 패스 %{x:,}건<extra></extra>"))
    f3.update_layout(height=320, xaxis_title="전진 패스 수", **PLOT)
    f3.update_xaxes(gridcolor=GRID)
    f3.update_yaxes(gridcolor=GRID, type="category")
    st.plotly_chart(f3, width="stretch")

st.markdown("""
<div class="credits">
<b>데이터</b> StatsBomb Open Data — 라리가 2004/05~2020/21 바르셀로나 경기의
패스 이벤트. 바르셀로나가 시도한 패스만 담았고 상대 팀 패스는 제외했다.<br>
<b>좌표</b> StatsBomb 좌표계(가로 120 × 세로 80). 공격 방향을 오른쪽으로 통일했다.
'전진 패스'는 도착 지점이 시작 지점보다 골대 쪽으로 5단위 이상 나아간 패스로
정의한 값이며, StatsBomb이 제공하는 공식 지표가 아니다.<br>
<b>공개 범위</b> 시즌마다 공개된 경기 수가 달라 시즌 간 총량 비교는 조심해야 한다.
</div>
""", unsafe_allow_html=True)
