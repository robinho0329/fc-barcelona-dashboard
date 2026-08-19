"""시즌별 기록 검색 — 라리가 1,251경기를 조건으로 찾아본다."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, PROCESSED, WHITE, b64,
                  load_seasons, metric_cards, setup)

seasons = load_seasons()
setup(seasons)


@st.cache_data
def load_matches() -> pd.DataFrame:
    m = pd.read_parquet(PROCESSED / "club_matches.parquet").copy()
    m["date"] = pd.to_datetime(m["Date"], format="mixed", dayfirst=True)
    home = m["HomeTeam"] == "Barcelona"
    m["gf"] = m["FTHG"].where(home, m["FTAG"]).astype(int)
    m["ga"] = m["FTAG"].where(home, m["FTHG"]).astype(int)
    m["venue"] = home.map({True: "홈", False: "원정"})
    m["opponent"] = m["AwayTeam"].where(home, m["HomeTeam"])
    m["gd"] = m["gf"] - m["ga"]
    m["result"] = m["gd"].apply(lambda d: "승" if d > 0 else ("무" if d == 0 else "패"))
    m["score"] = m["gf"].astype(str) + "-" + m["ga"].astype(str)
    # 하프타임 스코어와 슈팅 지표는 시즌마다 제공 여부가 다르다
    if {"HTHG", "HTAG"} <= set(m.columns):
        m["ht_gf"] = m["HTHG"].where(home, m["HTAG"])
        m["ht_ga"] = m["HTAG"].where(home, m["HTHG"])
    for ours, theirs, name in [("HS", "AS", "슛"), ("HST", "AST", "유효슛"),
                               ("HC", "AC", "코너"), ("HF", "AF", "파울"),
                               ("HY", "AY", "경고"), ("HR", "AR", "퇴장")]:
        if {ours, theirs} <= set(m.columns):
            m[name] = m[ours].where(home, m[theirs])
            m[f"상대{name}"] = m[theirs].where(home, m[ours])
    return m.sort_values("date").reset_index(drop=True)


matches = load_matches()

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">La Liga · {len(matches):,} matches</div>
  <h1>시즌 기록 검색</h1>
  <div class="hero-motto">1993/94부터 {seasons['Season'].iloc[-1]}까지 라리가
  {len(matches):,}경기. 시즌·상대·결과·점수차로 원하는 경기를 찾는다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- 필터
st.markdown('<div class="section">조건</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
season_sel = c1.multiselect("시즌", sorted(matches["Season"].unique(), reverse=True))
opp_sel = c2.multiselect("상대", sorted(matches["opponent"].unique()))
res_sel = c3.multiselect("결과", ["승", "무", "패"])

c4, c5, c6 = st.columns(3)
venue_sel = c4.selectbox("장소", ["전체", "홈", "원정"])
min_gd = c5.slider("최소 점수차 (절대값)", 0, 8, 0)
min_goals = c6.slider("최소 총 득점 (양 팀)", 0, 10, 0)

view = matches.copy()
if season_sel:
    view = view[view["Season"].isin(season_sel)]
if opp_sel:
    view = view[view["opponent"].isin(opp_sel)]
if res_sel:
    view = view[view["result"].isin(res_sel)]
if venue_sel != "전체":
    view = view[view["venue"] == venue_sel]
view = view[view["gd"].abs() >= min_gd]
view = view[(view["gf"] + view["ga"]) >= min_goals]

if view.empty:
    st.info("조건에 맞는 경기가 없습니다. 조건을 완화해 보세요.")
    st.stop()

# ---------------------------------------------------------------- 결과 요약
w = int((view["result"] == "승").sum())
d = int((view["result"] == "무").sum())
lo = int((view["result"] == "패").sum())
st.markdown('<div class="section">검색 결과</div>', unsafe_allow_html=True)
st.markdown(metric_cards([
    ("경기", f"{len(view):,}", f"{view['Season'].nunique()}시즌 · 상대 {view['opponent'].nunique()}팀"),
    ("전적", f"{w}-{d}-{lo}", f"승률 {w / len(view) * 100:.1f}%"),
    ("득실", f"{int(view['gf'].sum())}-{int(view['ga'].sum())}",
     f"경기당 {view['gf'].mean():.2f} : {view['ga'].mean():.2f}"),
    ("최다 점수차", f"{int(view['gd'].abs().max())}골",
     f"{view.loc[view['gd'].abs().idxmax(), 'Season']} "
     f"{view.loc[view['gd'].abs().idxmax(), 'score']}"),
]), unsafe_allow_html=True)

pw, pd_, pl = (x / len(view) * 100 for x in (w, d, lo))
st.markdown(f"""
<div class="h2h-bar">
  <div class="h2h-seg h2h-w" style="width:{pw:.1f}%">{w}승</div>
  <div class="h2h-seg h2h-d" style="width:{pd_:.1f}%">{d}무</div>
  <div class="h2h-seg h2h-l" style="width:{pl:.1f}%">{lo}패</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- 분포
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="section">스코어 빈도 상위 10</div>', unsafe_allow_html=True)
    sc = view["score"].value_counts().head(10).iloc[::-1]
    colors = [GRANA if int(s.split("-")[0]) > int(s.split("-")[1])
              else (GOLD if s.split("-")[0] == s.split("-")[1] else WHITE)
              for s in sc.index]
    f1 = go.Figure(go.Bar(x=sc.values, y=sc.index, orientation="h",
                          marker_color=colors, text=sc.values,
                          textposition="outside", textfont_color="#f2f6fc",
                          hovertemplate="<b>%{y}</b><br>%{x}경기<extra></extra>"))
    f1.update_layout(height=360, xaxis_title="경기 수", **PLOT)
    f1.update_xaxes(gridcolor=GRID, range=[0, int(sc.max()) * 1.2])
    f1.update_yaxes(gridcolor=GRID, type="category")
    st.plotly_chart(f1, use_container_width=True)

with c2:
    st.markdown('<div class="section">상대별 전적 (상위 12팀)</div>', unsafe_allow_html=True)
    opp = (view.groupby("opponent")
           .agg(경기=("result", "size"),
                승=("result", lambda s: (s == "승").sum()),
                무=("result", lambda s: (s == "무").sum()),
                패=("result", lambda s: (s == "패").sum()))
           .nlargest(12, "경기").iloc[::-1])
    f2 = go.Figure()
    for col, color in [("승", GRANA), ("무", "#6b7d99"), ("패", WHITE)]:
        f2.add_trace(go.Bar(y=opp.index, x=opp[col], orientation="h", name=col,
                            marker_color=color))
    f2.update_layout(height=360, barmode="stack", xaxis_title="경기 수",
                     legend=dict(orientation="h", y=1.1), **PLOT)
    f2.update_xaxes(gridcolor=GRID)
    f2.update_yaxes(gridcolor=GRID, type="category")
    st.plotly_chart(f2, use_container_width=True)

# ---------------------------------------------------------------- 시즌 흐름
st.markdown('<div class="section">시즌별 경기 수와 승률</div>', unsafe_allow_html=True)
by_season = (view.groupby("Season")
             .agg(경기=("result", "size"),
                  승=("result", lambda s: (s == "승").sum()))
             .reset_index())
by_season["승률"] = (by_season["승"] / by_season["경기"] * 100).round(1)
f3 = go.Figure()
f3.add_trace(go.Bar(x=by_season["Season"], y=by_season["경기"], name="경기 수",
                    marker_color=BLAU, yaxis="y"))
f3.add_trace(go.Scatter(x=by_season["Season"], y=by_season["승률"], name="승률(%)",
                        mode="lines+markers", line=dict(color=GOLD, width=2.4),
                        yaxis="y2"))
f3.update_layout(height=340,
                 yaxis=dict(title="경기 수", gridcolor=GRID),
                 yaxis2=dict(title="승률(%)", overlaying="y", side="right",
                             range=[0, 100], showgrid=False),
                 legend=dict(orientation="h", y=1.14), **PLOT)
f3.update_xaxes(gridcolor=GRID, tickangle=-60)
st.plotly_chart(f3, use_container_width=True)

# ---------------------------------------------------------------- 표
st.markdown('<div class="section">경기 목록</div>', unsafe_allow_html=True)
cols = ["Season", "date", "venue", "opponent", "score", "result", "gd"]
labels = ["시즌", "날짜", "장소", "상대", "스코어", "결과", "득실차"]
for extra in ["슛", "유효슛", "코너", "경고"]:
    if extra in view.columns:
        cols.append(extra)
        labels.append(extra)
tb = view[cols].copy()
tb["date"] = tb["date"].dt.strftime("%Y-%m-%d")
tb.columns = labels
st.dataframe(tb.sort_values("날짜", ascending=False).set_index("날짜"),
             use_container_width=True, height=460)
st.caption("슛·유효슛·코너·경고는 2005/06 시즌부터 원본에 들어 있어, "
           "그 이전 경기는 빈칸이다.")

st.markdown("""
<div class="credits">
<b>데이터</b> football-data.co.uk 라리가(SP1) 1993/94~2025/26 전 경기.
바르셀로나가 치른 리그 경기만 담았다.<br>
<b>결측</b> 슈팅·코너·파울·카드는 2005/06 시즌부터만 제공된다.
2004/05는 원본 파일이 27경기에서 잘려 있어 그 시즌 경기 수가 적다.<br>
<b>범위</b> 컵대회·챔피언스리그 경기는 원본에 없어 빠져 있다.
</div>
""", unsafe_allow_html=True)
