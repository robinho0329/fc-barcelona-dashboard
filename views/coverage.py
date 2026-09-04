"""데이터 제공 범위 — 어떤 소스가 어디까지 덮는지, 무엇이 비는지."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, PROCESSED, ROOT, WHITE, b64,
                  load_clasico, load_sb, load_seasons, metric_cards, setup)

seasons = load_seasons()
setup(seasons)

SEASON_ORDER = seasons["Season"].tolist()


@st.cache_data
def source_coverage() -> pd.DataFrame:
    """소스별로 어느 시즌을 덮는지와 규모를 모은다. 파일이 없으면 그대로 비운다."""
    rows = []

    m = pd.read_parquet(PROCESSED / "club_matches.parquet")
    rows.append({"소스": "football-data.co.uk", "단위": "경기 결과",
                 "시즌": sorted(m["Season"].unique()), "건수": len(m),
                 "설명": "라리가 전 경기 스코어. 2005/06부터 슛·코너·파울·카드 추가"})

    p = PROCESSED / "players.parquet"
    if p.exists():
        pl = pd.read_parquet(p)
        rows.append({"소스": "FBref", "단위": "선수 시즌 스탯",
                     "시즌": sorted(pl["season"].unique()), "건수": len(pl),
                     "설명": f"바르사 선수 {pl['Player'].nunique()}명의 시즌 기록"})

    ac = ROOT / "data" / "fbref_allcomps"
    if ac.exists() and list(ac.glob("*.parquet")):
        alls = pd.concat([pd.read_parquet(f) for f in sorted(ac.glob("*.parquet"))],
                         ignore_index=True)
        rows.append({"소스": "FBref (전 대회)", "단위": "경기 결과",
                     "시즌": sorted(alls["season"].unique()), "건수": len(alls),
                     "설명": "챔피언스리그·코파 델 레이 포함. 점유율·포메이션 제공"})

    sb = load_sb("shots")
    if not sb.empty:
        pa = load_sb("passes")
        rows.append({"소스": "StatsBomb", "단위": "이벤트(슛·패스)",
                     "시즌": sorted(sb["season"].unique()),
                     "건수": len(sb) + len(pa),
                     "설명": f"슛 {len(sb):,} · 패스 {len(pa):,}. 좌표와 xG 포함"})

    up = ROOT / "data" / "understat" / "shots.parquet"
    if up.exists():
        us = pd.read_parquet(up)
        rows.append({"소스": "Understat", "단위": "이벤트(슛)",
                     "시즌": sorted(us["season"].unique()), "건수": len(us),
                     "설명": "슛 좌표와 xG. StatsBomb이 끊긴 최근 시즌을 잇는다"})

    pt = ROOT / "assets" / "portraits"
    if pt.exists():
        rows.append({"소스": "Transfermarkt", "단위": "선수 사진",
                     "시즌": SEASON_ORDER, "건수": len(list(pt.glob("*.jpg"))),
                     "설명": "시즌 스쿼드에서 받은 선수 증명사진"})

    return pd.DataFrame(rows)


cov = source_coverage()

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">Data Coverage · {len(cov)} sources</div>
  <h1>데이터 제공 범위</h1>
  <div class="hero-motto">이 대시보드가 쓰는 소스가 어디까지 덮고 무엇이 비는지.
  빈 곳을 감추지 않고 그대로 보인다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- 총괄
st.markdown('<div class="section">한눈에</div>', unsafe_allow_html=True)
st.markdown(metric_cards([
    ("소스", f"{len(cov)}곳", "모두 공개 데이터"),
    ("분석 시즌", f"{len(SEASON_ORDER)}", f"{SEASON_ORDER[0]} ~ {SEASON_ORDER[-1]}"),
    ("총 레코드", f"{int(cov['건수'].sum()):,}", "경기·선수·이벤트 합계"),
    ("가장 넓은 소스", f"{cov.loc[cov['시즌'].map(len).idxmax(), '소스']}",
     f"{cov['시즌'].map(len).max()}시즌"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------- 커버리지 지도
st.markdown('<div class="section">소스별 시즌 커버리지</div>', unsafe_allow_html=True)
z, ytick, hover = [], [], []
for _, r in cov.iterrows():
    have = set(r["시즌"])
    z.append([1 if s in have else 0 for s in SEASON_ORDER])
    ytick.append(r["소스"])
    hover.append([f"{r['소스']}<br>{s}<br>{'제공' if s in have else '없음'}"
                  for s in SEASON_ORDER])

fig = go.Figure(go.Heatmap(
    z=z, x=SEASON_ORDER, y=ytick, text=hover, hoverinfo="text",
    colorscale=[[0, "rgba(23,51,85,.35)"], [1, GRANA]],
    showscale=False, xgap=1.5, ygap=4))
fig.update_layout(height=60 + 42 * len(cov), **PLOT)
fig.update_xaxes(gridcolor=GRID, tickangle=-60, side="bottom")
fig.update_yaxes(gridcolor=GRID, autorange="reversed")
st.plotly_chart(fig, width="stretch")
st.caption("그라나 = 그 시즌 데이터 있음 · 어두운 칸 = 없음")

# ---------------------------------------------------------------- 소스 카드
st.markdown('<div class="section">소스별 상세</div>', unsafe_allow_html=True)
cards = ""
for _, r in cov.iterrows():
    ss = r["시즌"]
    cards += (
        f'<div class="timeline-card">'
        f'<div class="timeline-year">{ss[0]} ~ {ss[-1]} · {len(ss)}시즌</div>'
        f'<div class="timeline-title">{r["소스"]}</div>'
        f'<div class="timeline-score" style="font-size:1.05rem">'
        f'{r["단위"]} · {r["건수"]:,}건</div>'
        f'<div class="timeline-body">{r["설명"]}</div></div>')
st.markdown(f'<div class="timeline-grid">{cards}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- 항목별 결측
st.markdown('<div class="section">시즌별 제공 항목</div>', unsafe_allow_html=True)
m = pd.read_parquet(PROCESSED / "club_matches.parquet")
per_season = m.groupby("Season").agg(
    경기=("Season", "size"),
    슛기록=("HS", lambda s: int(s.notna().sum())) if "HS" in m.columns else ("Season", "size"),
).reindex(SEASON_ORDER).fillna(0)

f2 = go.Figure()
f2.add_trace(go.Bar(x=per_season.index, y=per_season["경기"], name="경기 수",
                    marker_color=BLAU))
if "HS" in m.columns:
    f2.add_trace(go.Bar(x=per_season.index, y=per_season["슛기록"],
                        name="슈팅 기록 있는 경기", marker_color=GOLD))
f2.update_layout(height=340, barmode="overlay", yaxis_title="경기 수",
                 legend=dict(orientation="h", y=1.14), **PLOT)
f2.update_xaxes(gridcolor=GRID, tickangle=-60)
f2.update_yaxes(gridcolor=GRID)
st.plotly_chart(f2, width="stretch")
st.caption("2004/05는 원본 파일이 27경기에서 잘려 있고, "
           "슈팅·코너·파울·카드는 2005/06부터 제공된다.")

# ---------------------------------------------------------------- 알려진 한계
st.markdown('<div class="section">알려진 한계</div>', unsafe_allow_html=True)
# 공개 범위를 손으로 적으면 어긋난다. 실제 데이터에서 뽑는다.
# 옛 시즌 몇 개는 경기 한두 개만 공개된 희소 표본이라 따로 구분해 말한다.
_sb_cnt = load_sb("shots").groupby("season").size() if not load_sb("shots").empty else None
if _sb_cnt is not None and len(_sb_cnt):
    _thin = _sb_cnt[_sb_cnt < 50].index.tolist()
    _dense = _sb_cnt[_sb_cnt >= 50].index.tolist()
    _sb_span = f"{_sb_cnt.index.min()}~{_sb_cnt.index.max()}"
    _sb_thin = ("·".join(_thin) if _thin else "없음")
    _sb_dense = (f"{_dense[0]}~{_dense[-1]}" if _dense else "없음")
else:
    _sb_span = _sb_thin = _sb_dense = "확인 불가"

LIMITS = [
    ("2004/05 원본 손실",
     "football-data의 2004/05 파일이 27경기에서 잘려 있다. 그 시즌 승점·순위와 "
     "엘클라시코 두 경기가 빠져 있다."),
    ("컵대회 미포함 (일부 페이지)",
     "홈·시대분석·엘클라시코·감독 성적은 라리가 경기만 집계한다. 클럽 공식 "
     "통산 기록과 숫자가 다른 이유다. 챔피언스리그·코파는 FBref 전 대회 "
     "데이터로 따로 받아 두었다."),
    ("순위 산출 방식",
     "라리가 규정대로 승점 → 동률 팀 간 상대전적 → 골득실 순으로 계산한다. "
     "3팀 이상 동률처럼 규정이 더 복잡해지는 경우는 단순화돼 있다."),
    ("FBref 세부 지표 결측",
     "FBref가 라리가 페이지에서 패스 성공률·태클·터치 등 28개 열을 빈 값으로 "
     "내려준다. 재시도로 해결되지 않아 열을 제외했고, 해당 지표는 StatsBomb "
     "이벤트로 대체한다."),
    ("StatsBomb 공개 범위",
     f"라리가 오픈데이터는 {_sb_span}이다. 다만 {_sb_thin}은 경기 몇 개만 "
     "공개된 희소 표본이라 시즌을 대표하지 못한다. 실질적인 연속 구간은 "
     f"{_sb_dense}다. 시즌마다 공개 경기 수도 달라 시즌 간 총량 비교는 "
     "조심해야 한다. 최근 시즌은 Understat으로 메웠다."),
    ("출전 시간 근사",
     "StatsBomb 원본에 교체 시각이 없어, 선수가 이벤트에 마지막으로 등장한 분을 "
     "출전 시간으로 썼다. 90분당 지표는 대략적인 비교용이다."),
]
cards = "".join(
    f'<div class="timeline-card tl-loss"><div class="timeline-year">한계</div>'
    f'<div class="timeline-title">{t}</div><div class="timeline-body">{b}</div></div>'
    for t, b in LIMITS
)
st.markdown(f'<div class="timeline-grid">{cards}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- 표
with st.expander("소스별 커버 시즌 목록"):
    tb = cov[["소스", "단위", "건수"]].copy()
    tb["시즌 수"] = cov["시즌"].map(len)
    tb["범위"] = cov["시즌"].map(lambda s: f"{s[0]} ~ {s[-1]}")
    st.dataframe(tb.set_index("소스"), width="stretch")

st.markdown("""
<div class="credits">
<b>수집 방식</b> 모두 공개된 데이터를 직접 받아 집계했다.
football-data.co.uk는 CSV 다운로드, FBref·Transfermarkt·Understat은
브라우저 자동화로 레이트 리밋을 지키며 수집했다(FBref 6초, Transfermarkt 5초).
StatsBomb은 공식 오픈데이터 저장소에서 받았다.<br>
<b>재현</b> 저장소의 <code>build_data.py</code>, <code>crawl_fbref.py</code>,
<code>build_players.py</code>, <code>fetch_statsbomb.py</code>,
<code>fetch_understat.py</code>, <code>crawl_allcomps.py</code>,
<code>crawl_managers.py</code>, <code>train_model.py</code> 순으로 실행하면
같은 결과가 나온다.
</div>
""", unsafe_allow_html=True)
