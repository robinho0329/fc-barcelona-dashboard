"""선수 고급 기록 — StatsBomb 이벤트로 만든 90분당 지표와 선수 비교."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, b64, load_sb, load_seasons,
                  metric_cards, portrait_map, position_map, setup)

seasons = load_seasons()
setup(seasons)

pm = load_sb("player_match")

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">StatsBomb Open Data · Per 90</div>
  <h1>선수 고급 기록</h1>
  <div class="hero-motto">골과 도움만으로는 보이지 않는 것들.
  패스·드리블·압박·수비 관여를 90분 기준으로 맞춰 비교한다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if pm.empty:
    st.warning("StatsBomb 이벤트 데이터가 없습니다. `python fetch_statsbomb.py`를 먼저 실행하세요.")
    st.stop()

barca = pm[pm["team"] == "Barcelona"].copy()

# minutes_seen은 그 선수가 마지막으로 등장한 분이라 출전 시간의 근사치다.
# 90분을 넘길 수 없도록 자르고, 경기당 최소 15분 이상 뛴 기록만 쓴다.
barca["minutes"] = barca["minutes_seen"].clip(upper=95)

METRICS = {
    "패스": "passes", "드리블 성공": "dribbles", "전진 운반": "carries",
    "압박": "pressures", "슛": "shots", "태클": "tackles",
    "인터셉트": "interceptions", "xG": "xg", "골": "goals",
}


@st.cache_data
def per90(df: pd.DataFrame, min_minutes: int) -> pd.DataFrame:
    """선수별 90분당 지표. 출전 시간이 짧은 선수는 표본이 흔들려 제외한다."""
    g = df.groupby("player").agg(
        경기=("match_id", "nunique"), 분=("minutes", "sum"),
        시즌=("season", "nunique"),
        **{k: (v, "sum") for k, v in METRICS.items()},
        패스성공=("passes_completed", "sum"))
    g = g[g["분"] >= min_minutes]
    nineties = g["분"] / 90
    out = g[["경기", "분", "시즌"]].copy()
    for k in METRICS:
        out[k] = (g[k] / nineties).round(2)
    out["패스 성공률"] = (g["패스성공"] / g["패스"].replace(0, np.nan) * 100).round(1)
    return out.sort_values("분", ascending=False)


# ---------------------------------------------------------------- 필터
c1, c2 = st.columns([1.2, 1.6])
season_opts = ["전체"] + sorted(barca["season"].unique())
season = c1.selectbox("시즌", season_opts)
scope = barca if season == "전체" else barca[barca["season"] == season]
min_min = c2.slider("최소 출전 시간(분)", 200, 4000, 900, step=100)

table = per90(scope, min_min)
if table.empty:
    st.info("조건을 만족하는 선수가 없습니다. 최소 출전 시간을 낮춰 보세요.")
    st.stop()

st.markdown('<div class="section">범위</div>', unsafe_allow_html=True)
st.markdown(metric_cards([
    ("대상 선수", f"{len(table)}명", f"최소 {min_min:,}분 이상"),
    ("합계 경기", f"{int(scope['match_id'].nunique()):,}", f"{scope['season'].nunique()}시즌"),
    ("최다 출전", f"{int(table['분'].max()):,}분", f"{table['분'].idxmax()}"),
    ("최고 패스 성공률", f"{table['패스 성공률'].max():.1f}%",
     f"{table['패스 성공률'].idxmax()}"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------- 90분당 순위
st.markdown('<div class="section">90분당 지표 순위</div>', unsafe_allow_html=True)
metric = st.selectbox("지표", list(METRICS) + ["패스 성공률"], index=0)
top = table.nlargest(15, metric).iloc[::-1]
f1 = go.Figure(go.Bar(
    y=top.index, x=top[metric], orientation="h", marker_color=GRANA,
    text=top[metric], textposition="outside", textfont_color="#f2f6fc",
    customdata=top[["경기", "분"]].values,
    hovertemplate="<b>%{y}</b><br>" + metric + " %{x}<br>"
                  "%{customdata[0]}경기 · %{customdata[1]:,.0f}분<extra></extra>"))
f1.update_layout(height=460, xaxis_title=f"90분당 {metric}", **PLOT)
f1.update_xaxes(gridcolor=GRID, range=[0, float(top[metric].max()) * 1.18])
f1.update_yaxes(gridcolor=GRID, type="category")
st.plotly_chart(f1, width="stretch")

# ---------------------------------------------------------------- 선수 비교
st.markdown('<div class="section">선수 비교 (레이더)</div>', unsafe_allow_html=True)
RADAR = ["패스", "드리블 성공", "전진 운반", "압박", "슛", "태클"]
pool = table.index.tolist()
picked = st.multiselect("선수 선택 (2~4명)", pool, default=pool[:2], max_selections=4)

if len(picked) < 2:
    st.info("두 명 이상 고르면 비교 그래프가 나옵니다.")
else:
    # 각 지표를 그 범위 안 최댓값으로 나눠 0~100으로 맞춘다. 절대값이 아니라
    # "이 집단 안에서 어느 위치인가"를 보는 그림이다.
    base = table[RADAR]
    norm = (base / base.max()).fillna(0) * 100
    f2 = go.Figure()
    for color, name in zip([GRANA, BLAU, GOLD, "#7ab8ff"], picked):
        vals = norm.loc[name, RADAR].tolist()
        raw = base.loc[name, RADAR].tolist()
        f2.add_trace(go.Scatterpolar(
            r=vals + vals[:1], theta=RADAR + RADAR[:1], name=name,
            fill="toself", opacity=.42, line=dict(color=color, width=2.2),
            customdata=[[v] for v in raw + raw[:1]],
            hovertemplate="<b>" + name + "</b><br>%{theta}: %{customdata[0]}"
                          " (상대 %{r:.0f})<extra></extra>"))
    f2.update_layout(
        height=470,
        polar=dict(bgcolor="rgba(0,0,0,0)",
                   radialaxis=dict(range=[0, 100], gridcolor=GRID, tickfont=dict(size=10)),
                   angularaxis=dict(gridcolor=GRID)),
        legend=dict(orientation="h", y=1.1),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#94a8c4", size=12),
        margin=dict(l=40, r=40, t=50, b=20))
    st.plotly_chart(f2, width="stretch")
    st.caption("각 축은 이 필터 안 최댓값을 100으로 놓은 상대값이다. "
               "숫자에 마우스를 올리면 실제 90분당 값이 나온다.")

# ---------------------------------------------------------------- 관계
st.markdown('<div class="section">지표 사이 관계</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
xm = c1.selectbox("가로축", list(METRICS) + ["패스 성공률"], index=0)
ym = c2.selectbox("세로축", list(METRICS) + ["패스 성공률"], index=3)
# 한 색으로 그리면 어느 점이 어떤 유형인지 알 수 없다. 세 가지를 겹쳐 쓴다.
#   색   = 포지션
#   위치 = 각 축 평균으로 나눈 사분면 (모서리에 유형 이름을 단다)
#   사진 = 점이 적을 때만. 많으면 겹쳐서 오히려 못 읽는다
POS_COLOR = {"골키퍼": "#4fb0a5", "수비수": BLAU, "미드필더": GOLD,
             "공격수": GRANA, "미상": "#6b7d99"}
POS_KO = {"GK": "골키퍼", "DF": "수비수", "MF": "미드필더", "FW": "공격수"}
POS_ORDER = ["골키퍼", "수비수", "미드필더", "공격수", "미상"]
PHOTO_LIMIT = 24          # 이보다 많으면 사진 대신 점으로 그린다

pos_raw = position_map(table.index)
table_pos = pd.Series({n: POS_KO.get(pos_raw.get(n, ""), "미상")
                       for n in table.index})

use_photo = st.checkbox(
    f"선수 사진으로 보기 (대상 {len(table)}명 · {PHOTO_LIMIT}명 이하일 때만)",
    value=len(table) <= PHOTO_LIMIT, disabled=len(table) > PHOTO_LIMIT,
    help="사진은 점보다 크기 때문에 인원이 많으면 서로 가려 읽기 어려워진다. "
         "위의 최소 출전 시간을 올려 인원을 줄이면 켤 수 있다.")
photos = portrait_map(table.index) if use_photo else {}

x_mid, y_mid = table[xm].mean(), table[ym].mean()
f3 = go.Figure()
for pos_name in POS_ORDER:
    idx = table_pos[table_pos == pos_name].index
    if len(idx) == 0:
        continue
    part = table.loc[idx]
    # 이름은 눈에 띄는 점에만. 다 달면 겹쳐서 못 읽는다.
    n_lbl = min(3, len(part))
    top = (set(part.nlargest(n_lbl, xm).index)
           | set(part.nlargest(n_lbl, ym).index))
    show_text = not use_photo
    f3.add_trace(go.Scatter(
        x=part[xm], y=part[ym],
        mode="markers+text" if show_text else "markers",
        name=pos_name,
        text=[n.split()[-1] if n in top else "" for n in part.index] if show_text else None,
        textposition="top center", textfont=dict(size=9, color="#c3d2e6"),
        marker=dict(size=np.clip(part["분"] / 260, 8, 26),
                    color=POS_COLOR[pos_name],
                    opacity=.25 if use_photo else .78,
                    line=dict(width=.9, color="#0b1b2f")),
        customdata=np.stack([part.index, part["경기"], part["분"]], axis=-1),
        hovertemplate="<b>%{customdata[0]}</b> · " + pos_name + "<br>"
                      + xm + " %{x}<br>" + ym + " %{y}<br>"
                      "%{customdata[1]}경기 · %{customdata[2]:,.0f}분<extra></extra>"))

# 사진 모드 — 마커 위에 얼굴을 얹고 이름을 아래에 단다
imgs = []
if use_photo:
    x_span = max(table[xm].max() - table[xm].min(), 1e-6)
    y_span = max(table[ym].max() - table[ym].min(), 1e-6)
    for name in table.index:
        uri = photos.get(name)
        if not uri:
            continue
        imgs.append(dict(source=uri, x=table.loc[name, xm], y=table.loc[name, ym],
                         sizex=x_span * 0.075, sizey=y_span * 0.075,
                         xref="x", yref="y", xanchor="center", yanchor="middle",
                         sizing="contain", layer="above"))
    f3.add_trace(go.Scatter(
        x=table[xm], y=table[ym] - y_span * 0.055, mode="text",
        text=[n.split()[-1] for n in table.index],
        textposition="middle center", textfont=dict(size=9, color="#dbe6f5"),
        hoverinfo="skip", showlegend=False))

# 사분면 — 각 축 평균으로 나누고 모서리에 유형 이름을 단다
f3.add_vline(x=x_mid, line_dash="dot", line_color="#3d5a80")
f3.add_hline(y=y_mid, line_dash="dot", line_color="#3d5a80")
x_lo, x_hi = table[xm].min(), table[xm].max()
y_lo, y_hi = table[ym].min(), table[ym].max()
pad_x, pad_y = (x_hi - x_lo) * 0.06 or 1, (y_hi - y_lo) * 0.08 or 1
for qx, qy, ax, ay, label in [
    (x_hi, y_hi, "right", "top", f"{xm}↑ {ym}↑"),
    (x_lo, y_hi, "left", "top", f"{xm}↓ {ym}↑"),
    (x_lo, y_lo, "left", "bottom", f"{xm}↓ {ym}↓"),
    (x_hi, y_lo, "right", "bottom", f"{xm}↑ {ym}↓"),
]:
    f3.add_annotation(x=qx, y=qy, text=label, showarrow=False,
                      xanchor=ax, yanchor=ay,
                      font=dict(size=10, color="#6f849f"))

f3.update_layout(height=560 if use_photo else 500,
                 xaxis_title=f"90분당 {xm}", yaxis_title=f"90분당 {ym}",
                 images=imgs, legend=dict(orientation="h", y=1.1), **PLOT)
f3.update_xaxes(gridcolor=GRID, range=[x_lo - pad_x, x_hi + pad_x])
f3.update_yaxes(gridcolor=GRID, range=[y_lo - pad_y * 1.4, y_hi + pad_y])
st.plotly_chart(f3, width="stretch")

n_unknown = int((table_pos == "미상").sum())
n_photo = sum(1 for n in table.index if photos.get(n)) if use_photo else 0
st.caption(
    "색 = 포지션 · 점 크기 = 출전 시간 · 점선 = 각 축의 평균. "
    "네 모서리 글씨가 그 사분면의 성격이다 — 오른쪽 위로 갈수록 두 지표가 모두 높다."
    + (f" 사진 {n_photo}/{len(table)}명 (없는 선수는 점으로)." if use_photo
       else " 이름은 각 포지션에서 두 축 상위 3명에게만 달았다.")
    + (f" 포지션을 못 찾은 {n_unknown}명은 '미상'으로 묶었다." if n_unknown else ""))

with st.expander("전체 수치 표"):
    st.dataframe(table.round(2), width="stretch", height=430)

st.markdown("""
<div class="credits">
<b>데이터</b> StatsBomb Open Data 라리가 2004/05~2020/21 바르셀로나 경기의
이벤트를 선수-경기 단위로 집계한 뒤 90분당으로 환산했다.<br>
<b>출전 시간</b> 원본에 교체 시각이 없어, 그 선수가 이벤트에 마지막으로 등장한
분을 출전 시간의 근사치로 썼다(95분 상한). 실제 출전 시간과 다를 수 있어
90분당 값은 대략적인 비교용으로만 봐야 한다.<br>
<b>압박·전진 운반</b> StatsBomb이 2015/16 무렵부터 기록하기 시작한 이벤트라,
그 이전 시즌 선수는 값이 낮게 잡힌다. 시즌을 좁혀 비교하는 편이 안전하다.
</div>
""", unsafe_allow_html=True)
