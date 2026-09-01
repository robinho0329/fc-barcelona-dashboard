"""티키타카 지수 — 바르사의 패스 축구가 언제 정점이었고 어떻게 변했나."""
import pathlib

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, WHITE, b64, load_dir,
                  load_sb, load_seasons, metric_cards, setup)

seasons = load_seasons()
setup(seasons)

# 감독 시대 — eras.py와 같은 구분을 쓴다
ERA_OF = [
    ("크루이프", "1993/94", "1995/96", GOLD),
    ("과도기", "1996/97", "2002/03", "#6b7d99"),
    ("레이카르트", "2003/04", "2007/08", BLAU),
    ("과르디올라", "2008/09", "2011/12", GRANA),
    ("MSN", "2012/13", "2016/17", "#e0748f"),
    ("포스트 펩", "2017/18", "2020/21", "#7ab8ff"),
    ("재건", "2021/22", "2025/26", "#4fb0a5"),
]
ORDER = seasons["Season"].tolist()
SHORT_PASS = 15  # 야드. 이보다 짧으면 '짧은 패스'로 본다


def era_of(s: str) -> tuple[str, str]:
    if s not in ORDER:
        return "기타", "#6b7d99"
    i = ORDER.index(s)
    for name, a, b, c in ERA_OF:
        if ORDER.index(a) <= i <= ORDER.index(b):
            return name, c
    return "기타", "#6b7d99"


@st.cache_data
def build_index(pass_stamp: float, poss_stamp: str) -> pd.DataFrame:
    """시즌별 패스 지표와 점유율을 모아 0~100 지수를 만든다.

    지수는 세 축을 같은 비중으로 섞은 값이다 — 경기당 패스 수, 패스 성공률,
    짧은 패스 비율. 각 축을 이 데이터 안 최소~최대로 0~100에 늘려 평균 낸다.
    절대 척도가 아니라 **이 33시즌 안에서의 상대 위치**다.
    """
    ps = load_sb("passes")
    if ps.empty:
        return pd.DataFrame()

    ps = ps.copy()
    ps["short"] = ps["length"] < SHORT_PASS
    g = ps.groupby("season").agg(
        경기=("match_id", "nunique"), 패스=("player", "size"),
        성공률=("complete", "mean"), 짧은패스=("short", "mean"),
        평균길이=("length", "mean"))
    # 표본이 한두 경기뿐인 시즌은 지수가 흔들려 뺀다
    g = g[g["경기"] >= 5].copy()
    g["경기당패스"] = g["패스"] / g["경기"]
    g["성공률"] *= 100
    g["짧은패스"] *= 100

    def stretch(s: pd.Series) -> pd.Series:
        lo, hi = s.min(), s.max()
        return (s - lo) / (hi - lo) * 100 if hi > lo else s * 0 + 50

    g["지수"] = (stretch(g["경기당패스"]) + stretch(g["성공률"])
                + stretch(g["짧은패스"])) / 3

    # FBref 점유율(2014/15~)을 옆에 붙인다. StatsBomb이 끊긴 뒤를 잇는 지표다.
    ac = load_dir("fbref_allcomps")
    if not ac.empty and "Poss" in ac.columns:
        poss = (ac.assign(Poss=pd.to_numeric(ac["Poss"], errors="coerce"))
                .dropna(subset=["Poss"]).groupby("season")["Poss"].mean())
        g["점유율"] = g.index.map(poss)
    else:
        g["점유율"] = np.nan

    g = g.reset_index()
    g[["시대", "색"]] = g["season"].apply(lambda s: pd.Series(era_of(s)))
    return g.sort_values("season").reset_index(drop=True)


@st.cache_data
def possession_series(stamp: str) -> pd.DataFrame:
    """점유율만 따로. StatsBomb이 없는 최근 시즌까지 이어진다."""
    ac = load_dir("fbref_allcomps")
    if ac.empty or "Poss" not in ac.columns:
        return pd.DataFrame()
    d = ac.assign(Poss=pd.to_numeric(ac["Poss"], errors="coerce")).dropna(subset=["Poss"])
    out = d.groupby("season").agg(경기=("Poss", "size"), 점유율=("Poss", "mean")).reset_index()
    out[["시대", "색"]] = out["season"].apply(lambda s: pd.Series(era_of(s)))
    return out


# 캐시 키 — 파일이 바뀌면 다시 계산되게 한다
_sb = pathlib.Path("data/statsbomb/passes.parquet")
_pass_stamp = _sb.stat().st_mtime if _sb.exists() else 0.0
_ac_dir = pathlib.Path("data/fbref_allcomps")
_poss_stamp = "|".join(sorted(f"{f.name}:{f.stat().st_mtime}" for f in _ac_dir.glob("*.parquet"))) \
    if _ac_dir.exists() else ""

idx = build_index(_pass_stamp, _poss_stamp)
poss = possession_series(_poss_stamp)

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">Tiki-Taka Index · StatsBomb + FBref</div>
  <h1>티키타카 지수</h1>
  <div class="hero-motto">짧은 패스를 많이, 정확하게. 바르사를 정의한 그 축구가
  언제 정점이었고 지금 어디쯤인지 숫자로 따라간다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if idx.empty:
    st.warning("패스 데이터가 없습니다. `python fetch_statsbomb.py`를 먼저 실행하세요.")
    st.stop()

# ---------------------------------------------------------------- 커버리지 한계
_all_seasons = seasons["Season"].tolist()
_covered = set(idx["season"])
_missing = [s for s in _all_seasons if s not in _covered and ORDER.index(s) > ORDER.index(idx["season"].iloc[-1])]
if _missing:
    st.warning(
        f"**최근 {len(_missing)}시즌({_missing[0]}~{_missing[-1]})은 지수에 없다.** "
        f"패스 좌표를 주는 무료 소스가 StatsBomb Open Data뿐인데, 바르사 경기 공개가 "
        f"{idx['season'].iloc[-1]}에서 멈춰 있다. Understat은 슛 이벤트만 주고 패스는 "
        f"애초에 제공하지 않아 대체할 수 없다. 아래 지수 곡선은 {idx['season'].iloc[0]}~"
        f"{idx['season'].iloc[-1]}까지만 그려지고, 그 이후는 점유율(FBref)로만 이어 본다.")

# ---------------------------------------------------------------- 유래
st.markdown('<div class="section">티키타카라는 말은 어디서 왔나</div>',
            unsafe_allow_html=True)
st.markdown("""
<div class="lede">
공을 짧게 주고받을 때 나는 소리를 흉내 낸 <b>의성어</b>다. 스페인 방송인
<b>안드레스 몬테스</b>가 2006년 월드컵 중계에서 스페인-튀니지전을 두고
"Estamos tocando tiki-taka tiki-taka"라고 말한 것이 널리 퍼진 계기였다.
그 전부터 스페인 축구계에서 쓰이던 표현이고, 당시 아틀레틱 빌바오 감독
하비에르 클레멘테가 <b>비꼬는 뜻으로</b> 썼다는 이야기도 남아 있다.
칭찬으로 시작한 말이 아니었던 셈이다.<br><br>
뿌리는 요한 크루이프가 감독으로 있던 1988~96년에 심어졌다. 토탈 풋볼의 원리를
가져오되 <b>모든 것을 패스에 종속시킨</b> 형태로 바꿨고, 가짜 9번이나 골키퍼가
뒤에서부터 공을 굴리는 방식이 여기서 나왔다. 다만 정작
<b>과르디올라 본인은 이 말을 싫어했다</b>. 2014년에 그는 "패스를 위한 패스,
그 티키타카라는 걸 나는 혐오한다. 다 헛소리다"라고 말했다. 바르사가 한 것은
목적 없이 공을 돌리는 게 아니라 <b>공간을 만들기 위한 배치</b>였다는 뜻이다.<br><br>
그래서 아래 지수는 "티키타카를 얼마나 잘했나"가 아니라
<b>"패스로 경기를 지배하는 성향이 얼마나 강했나"</b>로 읽는 편이 정확하다.
</div>
""", unsafe_allow_html=True)
st.caption("유래와 인용은 위키백과 Tiki-taka 문서를 확인해 정리했다.")

# ---------------------------------------------------------------- 정의
st.markdown('<div class="section">지수를 어떻게 만들었나</div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="lede">
티키타카에 공식 지표는 없다. 그래서 그 축구를 설명하는 세 가지를 골라 섞었다 —
<b>경기당 패스 수</b>(얼마나 많이 돌리나), <b>패스 성공률</b>(얼마나 정확한가),
<b>짧은 패스 비율</b>({SHORT_PASS}야드 미만, 얼마나 촘촘한가). 세 축을 이 데이터
안의 최소~최대에 맞춰 0~100으로 늘린 뒤 같은 비중으로 평균 냈다.<br><br>
따라서 이 값은 <b>절대 척도가 아니라 이 시즌들 안에서의 상대 위치</b>다.
지수 100은 "완벽한 티키타카"가 아니라 "여기 담긴 시즌 중 가장 티키타카에
가깝다"는 뜻이다. 패스 좌표를 주는 무료 소스가 StatsBomb뿐이라 지수는
{idx['season'].iloc[0]}~{idx['season'].iloc[-1]}까지만 계산된다.
그 이후는 아래 점유율로 이어 본다.
</div>
""", unsafe_allow_html=True)

peak = idx.loc[idx["지수"].idxmax()]
latest = idx.iloc[-1]
st.markdown(metric_cards([
    ("정점", f"{peak['season']}", f"지수 {peak['지수']:.0f} · {peak['시대']}"),
    ("정점 패스량", f"{peak['경기당패스']:.0f}", f"경기당 · 성공률 {peak['성공률']:.1f}%"),
    ("짧은 패스 최고", f"{idx['짧은패스'].max():.1f}%",
     f"{idx.loc[idx['짧은패스'].idxmax(), 'season']}"),
    ("최근 (지수 기준)", f"{latest['지수']:.0f}",
     f"{latest['season']} · 정점 대비 {latest['지수'] - peak['지수']:+.0f}"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------- 지수 곡선
st.markdown('<div class="section">시즌별 티키타카 지수</div>', unsafe_allow_html=True)
fig = go.Figure()
fig.add_trace(go.Bar(
    x=idx["season"], y=idx["지수"], marker_color=idx["색"],
    customdata=idx[["시대", "경기당패스", "성공률", "짧은패스", "경기"]].values,
    hovertemplate="<b>%{x}</b> · %{customdata[0]}<br>지수 %{y:.0f}<br>"
                  "경기당 패스 %{customdata[1]:.0f}<br>"
                  "성공률 %{customdata[2]:.1f}%<br>"
                  "짧은 패스 %{customdata[3]:.1f}%<br>"
                  "%{customdata[4]}경기 집계<extra></extra>"))
fig.add_hline(y=idx["지수"].mean(), line_dash="dot", line_color="#94a8c4",
              annotation_text=f"평균 {idx['지수'].mean():.0f}",
              annotation_font_color="#94a8c4")
fig.update_layout(height=400, yaxis_title="티키타카 지수 (0~100)", **PLOT)
fig.update_xaxes(gridcolor=GRID, tickangle=-60)
fig.update_yaxes(gridcolor=GRID, range=[0, 105])
st.plotly_chart(fig, width="stretch")
st.caption("막대 색 = 감독 시대. " + " · ".join(f"{n}" for n, *_ in ERA_OF))

# ---------------------------------------------------------------- 구성 요소
st.markdown('<div class="section">지수를 이루는 세 축</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1:
    f2 = go.Figure()
    f2.add_trace(go.Scatter(x=idx["season"], y=idx["경기당패스"], name="경기당 패스",
                            mode="lines+markers", line=dict(color=GRANA, width=2.6)))
    f2.update_layout(height=320, yaxis_title="경기당 패스", **PLOT)
    f2.update_xaxes(gridcolor=GRID, tickangle=-60)
    f2.update_yaxes(gridcolor=GRID)
    st.plotly_chart(f2, width="stretch")
    st.caption(f"최고 {idx['경기당패스'].max():.0f}회 "
               f"({idx.loc[idx['경기당패스'].idxmax(), 'season']})")

with c2:
    f3 = go.Figure()
    f3.add_trace(go.Scatter(x=idx["season"], y=idx["성공률"], name="패스 성공률",
                            mode="lines+markers", line=dict(color=BLAU, width=2.6)))
    f3.add_trace(go.Scatter(x=idx["season"], y=idx["짧은패스"], name=f"짧은 패스 비율",
                            mode="lines+markers", line=dict(color=GOLD, width=2.6)))
    f3.update_layout(height=320, yaxis_title="%",
                     legend=dict(orientation="h", y=1.14), **PLOT)
    f3.update_xaxes(gridcolor=GRID, tickangle=-60)
    f3.update_yaxes(gridcolor=GRID)
    st.plotly_chart(f3, width="stretch")
    st.caption(f"짧은 패스 = {SHORT_PASS}야드 미만")

# ---------------------------------------------------------------- 시대별
st.markdown('<div class="section">시대별 평균</div>', unsafe_allow_html=True)
by_era = (idx.groupby("시대")
          .agg(시즌=("season", "size"), 지수=("지수", "mean"),
               경기당패스=("경기당패스", "mean"), 성공률=("성공률", "mean"),
               짧은패스=("짧은패스", "mean"))
          .reindex([n for n, *_ in ERA_OF]).dropna(subset=["지수"]))
colors = {n: c for n, _, _, c in ERA_OF}
f4 = go.Figure(go.Bar(
    x=by_era.index, y=by_era["지수"], marker_color=[colors[i] for i in by_era.index],
    text=by_era["지수"].round(0), textposition="outside", textfont_color="#f2f6fc",
    customdata=by_era[["시즌", "경기당패스", "성공률", "짧은패스"]].values,
    hovertemplate="<b>%{x}</b><br>지수 %{y:.0f}<br>%{customdata[0]}시즌<br>"
                  "경기당 패스 %{customdata[1]:.0f}<br>"
                  "성공률 %{customdata[2]:.1f}%<br>"
                  "짧은 패스 %{customdata[3]:.1f}%<extra></extra>"))
f4.update_layout(height=360, yaxis_title="평균 지수", **PLOT)
f4.update_xaxes(gridcolor=GRID)
f4.update_yaxes(gridcolor=GRID, range=[0, 110])
st.plotly_chart(f4, width="stretch")

# ---------------------------------------------------------------- 점유율
if not poss.empty:
    st.markdown('<div class="section">점유율 — 지수가 끊긴 뒤</div>', unsafe_allow_html=True)
    st.markdown(f"""
<div class="lede">
StatsBomb 패스 좌표가 {idx['season'].iloc[-1]}에서 끊겨 지수도 거기서 멈춘다.
대신 FBref가 {poss['season'].iloc[0]}부터 경기 점유율을 준다. 패스의 성격까지는
알 수 없지만, 공을 얼마나 쥐고 있었는지는 최근 시즌까지 이어 볼 수 있다.
</div>
""", unsafe_allow_html=True)
    f5 = go.Figure(go.Bar(
        x=poss["season"], y=poss["점유율"], marker_color=poss["색"],
        text=poss["점유율"].round(1), textposition="outside", textfont_color="#f2f6fc",
        customdata=poss[["시대", "경기"]].values,
        hovertemplate="<b>%{x}</b> · %{customdata[0]}<br>점유율 %{y:.1f}%<br>"
                      "%{customdata[1]}경기<extra></extra>"))
    f5.update_layout(height=340, yaxis_title="평균 점유율(%)", **PLOT)
    f5.update_xaxes(gridcolor=GRID, tickangle=-60)
    f5.update_yaxes(gridcolor=GRID, range=[50, 75])
    st.plotly_chart(f5, width="stretch")
    hi = poss.loc[poss["점유율"].idxmax()]
    st.caption(f"전 대회 기준. 최고 {hi['점유율']:.1f}% ({hi['season']}) · "
               f"최근 {poss.iloc[-1]['season']} {poss.iloc[-1]['점유율']:.1f}%")

# ---------------------------------------------------------------- 표
with st.expander("시즌별 수치 표"):
    tb = idx[["season", "시대", "경기", "경기당패스", "성공률", "짧은패스",
              "평균길이", "점유율", "지수"]].copy()
    tb.columns = ["시즌", "시대", "집계 경기", "경기당 패스", "성공률(%)",
                  "짧은 패스(%)", "평균 길이", "점유율(%)", "지수"]
    st.dataframe(tb.round(1).set_index("시즌"), width="stretch", height=430)

st.markdown(f"""
<div class="credits">
<b>지수</b> 공식 지표가 아니라 이 대시보드가 정의한 값이다. 경기당 패스 수·패스
성공률·짧은 패스 비율을 각각 0~100으로 늘려 같은 비중으로 평균 냈다. 세 축의
비중을 다르게 잡으면 순위도 달라진다.<br>
<b>데이터</b> 패스는 StatsBomb Open Data
({idx['season'].iloc[0]}~{idx['season'].iloc[-1]}), 점유율은 FBref 전 대회
({poss['season'].iloc[0] if not poss.empty else '-'}~
{poss['season'].iloc[-1] if not poss.empty else '-'}).<br>
<b>주의</b> StatsBomb은 시즌마다 공개 경기 수가 다르다(집계 경기 열 참고).
표본이 5경기 미만인 시즌은 지수가 흔들려 제외했다. 패스 지표는 라리가 위주라
컵대회 성격이 반영되지 않는다.
</div>
""", unsafe_allow_html=True)
