"""FC Barcelona — 1993년 이후 라리가 33시즌 기록.

football-data.co.uk 라리가(SP1) 원본에서 직접 집계한 수치만 표시한다.
레이아웃은 바이에른 뮌헨 페이지 구조를 따르되, 테마는 클럽 공식 팔레트
(블라우 #004d98 · 그라나 #a50044 · 노랑 #edbb00)로 새로 짰다.
"""
import base64
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
PROCESSED = ROOT / "data" / "processed"

GRANA = "#a50044"  # 클럽 공식 그라나
BLAU = "#004d98"  # 클럽 공식 블라우
GOLD = "#edbb00"  # 클럽 공식 노랑

st.set_page_config(page_title="FC Barcelona · Més que un club",
                   page_icon="🔵", layout="wide")


# ---------------------------------------------------------------- 데이터/자산

@st.cache_data
def load_seasons() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "club_season.parquet")


@st.cache_data
def b64(name: str) -> str:
    """자산 파일을 data URI로. 클라우드 정적서빙 설정 없이 HTML에 심기 위함."""
    p = ASSETS / name
    if not p.exists():
        return ""
    mime = "image/svg+xml" if p.suffix == ".svg" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


@st.cache_data
def load_clasico() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "clasico.parquet")


@st.cache_data
def load_credits() -> dict:
    p = ASSETS / "credits.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


CSS = """
<style>
:root{--grana:#a50044;--blau:#004d98;--gold:#edbb00;
      --bg:#04101f;--panel:#0a1c33;--panel2:#061527;
      --ink:#f2f6fc;--muted:#94a8c4;--line:#173355;}

/* 액센트 — 세녜라 줄무늬는 이 크기에서 뭉개져 붉은 덩어리로 보인다.
   대신 블라우/그라나 2톤 바로 통일하고, 노랑은 글자 강조에만 쓴다. */
.accent-rule{height:5px;width:104px;border-radius:3px;margin-top:1.1rem;position:relative;
      background:linear-gradient(90deg,var(--blau) 0 50%,var(--grana) 50% 100%);}

[data-testid="stAppViewContainer"]{
      background:radial-gradient(1200px 620px at 78% -12%,rgba(0,77,152,.30),transparent 62%),
                 radial-gradient(900px 520px at 8% 4%,rgba(165,0,68,.22),transparent 60%),
                 var(--bg);}
[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:1.4rem;max-width:1180px;}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#061829,#04101f);
      border-right:1px solid var(--line);}
.side-brand{text-align:center;padding:1.2rem 0 .4rem;}
.side-brand img{width:118px;filter:drop-shadow(0 10px 18px rgba(0,0,0,.38));}
.side-name{color:var(--ink);font-weight:800;letter-spacing:.02em;margin-top:.7rem;font-size:1.02rem;}
.side-motto{color:var(--gold);font-size:.74rem;letter-spacing:.13em;text-transform:uppercase;margin-top:.25rem;}
.side-row{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);
          padding:.5rem 0;font-size:.82rem;}
.side-row span:first-child{color:var(--muted);}
.side-row span:last-child{color:var(--ink);font-weight:650;}

/* 히어로 — 벽지식 줄무늬 대신 조용한 블라우→그라나 그라디언트 위에
   엠블럼을 크게 워터마크로 앉힌다. 줄무늬는 오른쪽 끝에만 얇게 남긴다. */
.hero{position:relative;overflow:hidden;min-height:250px;padding:2.4rem 2.6rem;
      border-radius:20px;display:flex;flex-direction:column;justify-content:center;margin-bottom:1.8rem;
      border:1px solid var(--line);
      background:linear-gradient(112deg,#0b2447 0%,#071a31 46%,#2a0a24 100%);}
.hero::after{content:"";position:absolute;right:0;top:0;bottom:0;width:6px;
      background:linear-gradient(180deg,var(--blau),var(--grana));}
.hero-crest{position:absolute;right:2.6rem;top:50%;transform:translateY(-50%);
      height:210px;opacity:.16;pointer-events:none;}
.hero-kicker{position:relative;color:var(--gold);font-size:.72rem;letter-spacing:.24em;
      text-transform:uppercase;font-weight:700;}
.hero h1{position:relative;color:var(--ink);font-size:clamp(2rem,3.15vw,3.45rem);
      letter-spacing:-.035em;white-space:nowrap;font-weight:860;margin:.4rem 0 .55rem;}
.hero-motto{position:relative;color:#c3d2e6;font-size:1.02rem;font-style:italic;max-width:600px;}

/* 섹션 제목 앞 블라우그라나 태그. 노랑 글자와 함께 클럽 색을 반복한다. */
.section{color:var(--gold);font-size:.72rem;letter-spacing:.15em;text-transform:uppercase;
      font-weight:800;margin:2rem 0 .8rem;display:flex;align-items:center;gap:.6rem;}
.section::before{content:"";width:20px;height:4px;border-radius:2px;flex:none;
      background:linear-gradient(90deg,var(--blau) 0 50%,var(--grana) 50% 100%);}
.lede{color:var(--muted);font-size:.92rem;line-height:1.75;margin-bottom:.6rem;}
.lede b{color:var(--ink);}

.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem;}
.metric-card{background:linear-gradient(150deg,var(--panel),var(--panel2));
      border:1px solid var(--line);border-top:4px solid var(--grana);border-radius:12px;min-height:112px;
      padding:1rem 1.1rem;display:flex;flex-direction:column;justify-content:center;}
.metric-card:nth-child(even){border-top-color:var(--blau);}
.metric-label{color:var(--muted);font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;}
.metric-value{color:var(--ink);font-size:1.7rem;font-weight:850;line-height:1.15;
      margin:.3rem 0 .15rem;word-break:keep-all;}
.metric-note{color:var(--muted);font-size:.74rem;}

.timeline-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;}
/* 연표 카드 — 왼쪽에 블라우/그라나를 번갈아 세워 유니폼 줄무늬를 암시한다. */
.timeline-card{position:relative;overflow:hidden;min-height:150px;border-radius:14px;
      padding:1.1rem 1.2rem 1.1rem 1.45rem;border:1px solid var(--line);
      background:linear-gradient(145deg,var(--panel),var(--panel2));}
.timeline-card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:5px;background:var(--grana);}
.timeline-card:nth-child(even)::before{background:var(--blau);}
.timeline-card::after{content:"";position:absolute;width:76px;height:76px;right:-28px;bottom:-34px;
      border:14px solid rgba(0,77,152,.22);border-radius:50%;}
.timeline-year{color:var(--gold);font-size:.72rem;letter-spacing:.16em;font-weight:800;}
.timeline-title{color:var(--ink);font-size:1.02rem;font-weight:780;margin:.35rem 0 .4rem;}
.timeline-body{color:var(--muted);font-size:.82rem;line-height:1.6;}

.photo-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;}
.photo-card{border-radius:14px;overflow:hidden;background:var(--panel2);border:1px solid var(--line);}
.photo-card img{width:100%;height:190px;object-fit:cover;display:block;
      border-bottom:3px solid var(--grana);}
.photo-card:nth-child(even) img{border-bottom-color:var(--blau);}
.photo-cap{padding:.7rem .9rem .85rem;}
.photo-cap b{color:var(--ink);font-size:.88rem;display:block;}
.photo-cap span{color:var(--muted);font-size:.72rem;}

/* 엘클라시코 최근 폼 — 승/무/패를 칩으로 늘어놓는다. */
.form-strip{display:flex;flex-wrap:wrap;gap:.4rem;margin:.2rem 0 .4rem;}
.form-chip{min-width:58px;flex:1 1 58px;max-width:96px;border-radius:9px;padding:.5rem .3rem;text-align:center;
      border:1px solid var(--line);background:var(--panel2);}
.form-chip .fc-res{font-size:.92rem;font-weight:850;line-height:1.1;}
.form-chip .fc-score{color:var(--ink);font-size:.78rem;font-weight:700;margin-top:.15rem;}
.form-chip .fc-meta{color:var(--muted);font-size:.62rem;margin-top:.15rem;}
.fc-w{color:var(--gold);} .fc-d{color:#9fb2cc;} .fc-l{color:#e0748f;}

.credits{color:#6f849f;font-size:.68rem;line-height:1.7;border-top:1px solid var(--line);
      padding-top:.9rem;margin-top:2rem;}
@media(max-width:900px){
  .metric-grid,.timeline-grid,.photo-grid{grid-template-columns:1fr;}
  .hero h1{white-space:normal;}
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

seasons = load_seasons()
credits = load_credits()

titles = int((seasons["rank"] == 1).sum())
total_goals = int(seasons["GF"].sum())
total_matches = int(seasons["P"].sum())
gpg = total_goals / total_matches
latest = seasons.iloc[-1]
best_ppg = seasons.loc[seasons["PPG"].idxmax()]
best_gf = seasons.loc[seasons["GF"].idxmax()]

# ---------------------------------------------------------------- 사이드바
st.sidebar.markdown(f"""
<div class="side-brand">
  <img src="{b64('crest.svg')}" alt="FC Barcelona">
  <div class="side-name">Futbol Club Barcelona</div>
  <div class="side-motto">Més que un club</div>
</div>
<div class="side-row"><span>창단</span><span>1899년 11월 29일</span></div>
<div class="side-row"><span>연고</span><span>바르셀로나, 카탈루냐</span></div>
<div class="side-row"><span>홈구장</span><span>스포티파이 캄 노우</span></div>
<div class="side-row"><span>소유 구조</span><span>소시오 조합원</span></div>
<div class="side-row"><span>분석 범위</span><span>{seasons['Season'].iloc[0]}~{latest['Season']}</span></div>
<div class="side-row"><span>라리가 우승</span><span>{titles}회</span></div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- 히어로
st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">Des de 1899 · Barcelona</div>
  <h1>FC BARCELONA</h1>
  <div class="hero-motto">"Més que un club" — 클럽 그 이상. 카탈루냐의 정체성을
  대변해 온 소시오 조합원 소유 구단의 {len(seasons)}시즌 기록.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

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
photos = [
    ("camp_nou", "캄 노우", "관중 99,354석. 유럽 최대 규모 축구 전용 경기장"),
    ("cruyff", "요한 크루이프", "선수(1973~78)와 감독(1988~96)으로 클럽 철학을 세움"),
    ("messi", "리오넬 메시", "라 마시아 출신, 클럽 통산 최다 득점자"),
]
USED_PHOTOS = {k for k, _, _ in photos}
cards = "".join(
    f'<div class="photo-card"><img src="{b64(k + ".jpg")}" alt="{t}">'
    f'<div class="photo-cap"><b>{t}</b><span>{d}</span></div></div>'
    for k, t, d in photos if b64(k + ".jpg")
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
metrics = [
    ("분석 시즌", f"{len(seasons)}", f"{seasons['Season'].iloc[0]} ~ {latest['Season']}"),
    ("리그 경기", f"{total_matches:,}", "라리가 정규시즌 기준"),
    ("리그 우승", f"{titles}회", f"{titles / len(seasons) * 100:.0f}% 시즌에서 1위"),
    ("총 득점", f"{total_goals:,}", f"경기당 {gpg:.2f}골"),
    ("최고 승점률", f"{best_ppg['PPG']:.2f}", f"{best_ppg['Season']} · 승점 {int(best_ppg['Pts'])}"),
    ("최다 득점 시즌", f"{int(best_gf['GF'])}골", f"{best_gf['Season']}"),
    ("통산 승률", f"{seasons['W'].sum() / total_matches * 100:.1f}%",
     f"{int(seasons['W'].sum())}승 {int(seasons['D'].sum())}무 {int(seasons['L'].sum())}패"),
    ("평균 실점", f"{seasons['GA'].sum() / total_matches:.2f}", "경기당 · 전 시즌 평균"),
]
cards = "".join(
    f'<div class="metric-card"><div class="metric-label">{lab}</div>'
    f'<div class="metric-value">{val}</div><div class="metric-note">{note}</div></div>'
    for lab, val, note in metrics
)
st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- 차트
PLOT = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a8c4", size=12), margin=dict(l=10, r=10, t=30, b=10))

st.markdown('<div class="section">시즌별 경기당 승점</div>', unsafe_allow_html=True)
fig = go.Figure()
fig.add_trace(go.Bar(
    x=seasons["Season"], y=seasons["PPG"],
    marker_color=[GOLD if r == 1 else GRANA for r in seasons["rank"]],
    hovertemplate="<b>%{x}</b><br>경기당 승점 %{y:.2f}<extra></extra>"))
fig.add_hline(y=seasons["PPG"].mean(), line_dash="dot", line_color=BLAU,
              annotation_text=f"평균 {seasons['PPG'].mean():.2f}",
              annotation_font_color="#94a8c4")
fig.update_layout(height=340, yaxis_title="경기당 승점", **PLOT)
fig.update_xaxes(gridcolor="#173355", tickangle=-60)
fig.update_yaxes(gridcolor="#173355")
st.plotly_chart(fig, use_container_width=True)
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
    f2.update_xaxes(gridcolor="#173355")
    f2.update_yaxes(gridcolor="#173355", range=[0, int(dec.max()) + 2])
    st.plotly_chart(f2, use_container_width=True)

with c2:
    st.markdown('<div class="section">시즌별 득점 · 실점</div>', unsafe_allow_html=True)
    f3 = go.Figure()
    f3.add_trace(go.Scatter(x=seasons["Season"], y=seasons["GF"], name="득점",
                            line=dict(color=GRANA, width=2.4)))
    f3.add_trace(go.Scatter(x=seasons["Season"], y=seasons["GA"], name="실점",
                            line=dict(color=BLAU, width=2.4)))
    f3.update_layout(height=300, yaxis_title="골", legend=dict(orientation="h", y=1.12), **PLOT)
    f3.update_xaxes(gridcolor="#173355", tickangle=-60)
    f3.update_yaxes(gridcolor="#173355")
    st.plotly_chart(f3, use_container_width=True)

# ---------------------------------------------------------------- 엘클라시코
cl = load_clasico()
w = int((cl["result"] == "승").sum())
d = int((cl["result"] == "무").sum())
lo = int((cl["result"] == "패").sum())
biggest = cl.loc[cl["gd"].idxmax()]
worst = cl.loc[cl["gd"].idxmin()]

st.markdown('<div class="section">엘클라시코 — 레알 마드리드 상대전적</div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="lede">
리그 경기만 집계한 수치다. 컵대회·챔피언스리그 맞대결은 원본에 없어 빠져 있고,
원본 파일이 잘려 있는 2004/05 두 경기도 제외된다.
최다 점수차 승리는 <b>{biggest['Season']} {biggest['venue']} {biggest['score']}</b>,
최다 점수차 패배는 <b>{worst['Season']} {worst['venue']} {worst['score']}</b>.
</div>
""", unsafe_allow_html=True)

home, away = cl[cl["venue"] == "홈"], cl[cl["venue"] == "원정"]
metrics = [
    ("맞대결", f"{len(cl)}경기", f"{cl['Season'].nunique()}시즌 · 리그 한정"),
    ("전적", f"{w}-{d}-{lo}", f"{w}승 {d}무 {lo}패 · 승률 {w / len(cl) * 100:.0f}%"),
    ("득실", f"{int(cl['gf'].sum())}-{int(cl['ga'].sum())}",
     f"경기당 {cl['gf'].mean():.2f} : {cl['ga'].mean():.2f}"),
    ("홈 / 원정 승리", f"{int((home['result'] == '승').sum())} / {int((away['result'] == '승').sum())}",
     f"각 {len(home)}경기 · 캄 노우에서 더 강했다"),
]
cards = "".join(
    f'<div class="metric-card"><div class="metric-label">{lab}</div>'
    f'<div class="metric-value">{val}</div><div class="metric-note">{note}</div></div>'
    for lab, val, note in metrics
)
st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)

RES_COLOR = {"승": GRANA, "무": "#6b7d99", "패": "#c9d3e0"}
st.markdown('<div class="section">경기별 골 득실차 (오래된 순)</div>', unsafe_allow_html=True)
f4 = go.Figure(go.Bar(
    x=cl["date"], y=cl["gd"],
    marker_color=[RES_COLOR[r] for r in cl["result"]],
    customdata=cl[["Season", "venue", "score", "result"]].values,
    hovertemplate="<b>%{customdata[0]} %{customdata[1]}</b><br>"
                  "%{customdata[2]} %{customdata[3]}<extra></extra>"))
f4.update_layout(height=300, yaxis_title="골 득실차", showlegend=False, **PLOT)
f4.update_xaxes(gridcolor="#173355")
f4.update_yaxes(gridcolor="#173355", zerolinecolor="#2b4a72")
st.plotly_chart(f4, use_container_width=True)
st.caption("그라나 = 승 · 회색 = 무 · 흰색 = 패")

st.markdown('<div class="section">최근 10경기</div>', unsafe_allow_html=True)
cls = {"승": "fc-w", "무": "fc-d", "패": "fc-l"}
chips = "".join(
    f'<div class="form-chip"><div class="fc-res {cls[r.result]}">{r.result}</div>'
    f'<div class="fc-score">{r.score}</div>'
    f'<div class="fc-meta">{r.Season} {r.venue}</div></div>'
    for r in cl.tail(10).itertuples()
)
st.markdown(f'<div class="form-strip">{chips}</div>', unsafe_allow_html=True)

with st.expander("엘클라시코 64경기 전체 보기"):
    tb = cl.copy()
    tb["date"] = tb["date"].dt.strftime("%Y-%m-%d")
    tb.columns = ["시즌", "날짜", "장소", "득점", "실점", "득실차", "결과", "스코어"]
    st.dataframe(tb.set_index("날짜"), use_container_width=True, height=380)

# ---------------------------------------------------------------- 최신 시즌
st.markdown(f'<div class="section">{latest["Season"]} 시즌 요약</div>', unsafe_allow_html=True)
rows = [
    ("최종 순위", f"{int(latest['rank'])}위", f"{int(latest['P'])}경기"),
    ("전적", f"{int(latest['W'])}-{int(latest['D'])}-{int(latest['L'])}",
     f"{int(latest['W'])}승 {int(latest['D'])}무 {int(latest['L'])}패"),
    ("승점", f"{int(latest['Pts'])}점", f"경기당 {latest['PPG']:.2f}"),
    ("골 득실", f"{int(latest['GD']):+d}", f"{int(latest['GF'])}득점 {int(latest['GA'])}실점"),
]
cards = "".join(
    f'<div class="metric-card"><div class="metric-label">{lab}</div>'
    f'<div class="metric-value">{val}</div><div class="metric-note">{note}</div></div>'
    for lab, val, note in rows
)
st.markdown(f'<div class="metric-grid">{cards}</div>', unsafe_allow_html=True)

with st.expander("시즌별 전체 기록 보기"):
    tbl = seasons[["Season", "P", "W", "D", "L", "GF", "GA", "GD", "Pts", "rank", "PPG"]].copy()
    tbl.columns = ["시즌", "경기", "승", "무", "패", "득점", "실점", "득실차", "승점", "순위", "경기당승점"]
    st.dataframe(tbl.set_index("시즌"), use_container_width=True, height=420)

# ---------------------------------------------------------------- 출처
lines = "".join(
    f"· {t} — {credits[k]['artist']} / {credits[k]['license']} (Wikimedia Commons)<br>"
    for k, t, _ in photos if k in credits
)
st.markdown(f"""
<div class="credits">
<b>데이터</b> football-data.co.uk 라리가(SP1) 원본 —
{seasons['Season'].iloc[0]}~{latest['Season']} 전 경기 결과에서 직접 집계.
순위는 승점 → 골득실 → 다득점 순으로 산출한 값으로, 상대전적 우선 규정을 적용하는
공식 순위와 일부 시즌에서 다를 수 있음.<br>
<b>이미지</b> 클럽 엠블럼은 FC Barcelona 소유. 사진 출처:<br>{lines}
</div>
""", unsafe_allow_html=True)
