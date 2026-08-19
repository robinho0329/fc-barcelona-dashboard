"""페이지 공통 자산 — 팔레트, CSS, 데이터 로더, 사이드바.

app.py가 st.navigation으로 views/ 아래 페이지를 묶고, 각 페이지는
여기서 CSS와 데이터를 가져다 쓴다.
"""
import base64
import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
PROCESSED = ROOT / "data" / "processed"

GRANA = "#a50044"  # 클럽 공식 그라나
BLAU = "#004d98"  # 클럽 공식 블라우
GOLD = "#edbb00"  # 클럽 공식 노랑
WHITE = "#c9d3e0"  # 레알 마드리드를 가리킬 때만 쓰는 흰색
GRID = "#173355"

# plotly 공통 레이아웃
PLOT = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a8c4", size=12), margin=dict(l=10, r=10, t=30, b=10))


# ---------------------------------------------------------------- 데이터/자산

@st.cache_data
def load_seasons() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "club_season.parquet")


@st.cache_data
def load_clasico() -> pd.DataFrame:
    cl = pd.read_parquet(PROCESSED / "clasico.parquet")
    cl["decade"] = cl["Season"].str[:3] + "0s"
    return cl


@st.cache_data
def load_credits() -> dict:
    p = ASSETS / "credits.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


@st.cache_data
def b64(name: str) -> str:
    """자산 파일을 data URI로. 클라우드 정적서빙 설정 없이 HTML에 심기 위함."""
    p = ASSETS / name
    if not p.exists():
        return ""
    mime = "image/svg+xml" if p.suffix == ".svg" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


# ---------------------------------------------------------------- 사진 목록
PHOTOS = [
    ("camp_nou", "캄 노우", "관중 99,354석. 유럽 최대 규모 축구 전용 경기장"),
    ("cruyff", "요한 크루이프", "선수(1973~78)와 감독(1988~96)으로 클럽 철학을 세움"),
    ("messi", "리오넬 메시", "라 마시아 출신, 클럽 통산 최다 득점자"),
]


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

/* 히어로 — 조용한 그라디언트 위에 엠블럼을 워터마크로 앉힌다. */
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

/* 클라시코 히어로 — 왼쪽 블라우그라나, 오른쪽 화이트로 두 팀을 갈라놓는다. */
.hero-clasico{background:linear-gradient(100deg,#0b2447 0%,#3d0b2a 40%,#1b2432 62%,#39414d 100%);}
.hero-clasico::after{background:linear-gradient(180deg,#c9d3e0,#8d97a6);}
.hero-vs{position:relative;display:flex;align-items:center;gap:1.1rem;margin:.4rem 0 .55rem;}
.hero-vs .vs-side{color:var(--ink);font-size:clamp(1.2rem,2.1vw,2rem);font-weight:860;
      letter-spacing:-.02em;white-space:nowrap;}
.hero-vs .vs-mark{color:var(--gold);font-size:.9rem;font-weight:800;letter-spacing:.18em;}

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
/* 클라시코 명경기 카드는 결과에 따라 왼쪽 색을 바꾼다. */
.tl-win::before{background:var(--grana) !important;}
.tl-loss::before{background:#c9d3e0 !important;}
.timeline-score{color:var(--ink);font-size:1.35rem;font-weight:860;margin:.15rem 0 .35rem;}

.photo-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;}
.photo-card{border-radius:14px;overflow:hidden;background:var(--panel2);border:1px solid var(--line);}
.photo-card img{width:100%;height:190px;object-fit:cover;display:block;
      border-bottom:3px solid var(--grana);}
.photo-card:nth-child(even) img{border-bottom-color:var(--blau);}
.photo-cap{padding:.7rem .9rem .85rem;}
.photo-cap b{color:var(--ink);font-size:.88rem;display:block;}
.photo-cap span{color:var(--muted);font-size:.72rem;}

/* 승/무/패 칩 */
.form-strip{display:flex;flex-wrap:wrap;gap:.4rem;margin:.2rem 0 .4rem;}
.form-chip{min-width:58px;flex:1 1 58px;max-width:96px;border-radius:9px;padding:.5rem .3rem;
      text-align:center;border:1px solid var(--line);background:var(--panel2);}
.form-chip .fc-res{font-size:.92rem;font-weight:850;line-height:1.1;}
.form-chip .fc-score{color:var(--ink);font-size:.78rem;font-weight:700;margin-top:.15rem;}
.form-chip .fc-meta{color:var(--muted);font-size:.62rem;margin-top:.15rem;}
.fc-w{color:var(--gold);} .fc-d{color:#9fb2cc;} .fc-l{color:#e0748f;}

/* 상대전적 비율 바 — 승/무/패를 한 줄로 */
.h2h-bar{display:flex;height:40px;border-radius:10px;overflow:hidden;border:1px solid var(--line);
      margin:.3rem 0 .5rem;}
.h2h-seg{display:flex;align-items:center;justify-content:center;font-size:.82rem;font-weight:800;}
.h2h-w{background:var(--grana);color:#fff;}
.h2h-d{background:#3c4a5e;color:#e6ecf5;}
.h2h-l{background:#c9d3e0;color:#12203a;}
.h2h-legend{color:var(--muted);font-size:.74rem;display:flex;gap:1.1rem;flex-wrap:wrap;}

.credits{color:#6f849f;font-size:.68rem;line-height:1.7;border-top:1px solid var(--line);
      padding-top:.9rem;margin-top:2rem;}
@media(max-width:900px){
  .metric-grid,.timeline-grid,.photo-grid{grid-template-columns:1fr;}
  .hero h1{white-space:normal;}
  .hero-vs{flex-direction:column;align-items:flex-start;gap:.2rem;}
}
</style>
"""


def setup(seasons: pd.DataFrame) -> None:
    """모든 페이지 공통 — CSS 주입 + 사이드바 클럽 정보."""
    st.markdown(CSS, unsafe_allow_html=True)
    titles = int((seasons["rank"] == 1).sum())
    st.sidebar.markdown(f"""
<div class="side-brand">
  <img src="{b64('crest.svg')}" alt="FC Barcelona">
  <div class="side-name">Futbol Club Barcelona</div>
  <div class="side-motto">Més que un club</div>
</div>
<div class="side-row"><span>창단</span><span>1899년 11월 29일</span></div>
<div class="side-row"><span>연고</span><span>바르셀로나, 카탈루냐</span></div>
<div class="side-row"><span>홈구장</span><span>스포티파이 캄 노우</span></div>
<div class="side-row"><span>분석 범위</span><span>{seasons['Season'].iloc[0]}~{seasons['Season'].iloc[-1]}</span></div>
<div class="side-row"><span>라리가 우승</span><span>{titles}회</span></div>
""", unsafe_allow_html=True)


def metric_cards(items) -> str:
    """(라벨, 값, 부연) 목록을 카드 그리드 HTML로."""
    cards = "".join(
        f'<div class="metric-card"><div class="metric-label">{lab}</div>'
        f'<div class="metric-value">{val}</div><div class="metric-note">{note}</div></div>'
        for lab, val, note in items
    )
    return f'<div class="metric-grid">{cards}</div>'


def credits_block(seasons: pd.DataFrame, credits: dict, extra: str = "") -> str:
    lines = "".join(
        f"· {t} — {credits[k]['artist']} / {credits[k]['license']} (Wikimedia Commons)<br>"
        for k, t, _ in PHOTOS if k in credits
    )
    return f"""
<div class="credits">
<b>데이터</b> football-data.co.uk 라리가(SP1) 원본 —
{seasons['Season'].iloc[0]}~{seasons['Season'].iloc[-1]} 전 경기 결과에서 직접 집계.
순위는 승점 → 골득실 → 다득점 순으로 산출한 값으로, 상대전적 우선 규정을 적용하는
공식 순위와 일부 시즌에서 다를 수 있음.{extra}<br>
<b>이미지</b> 클럽 엠블럼은 FC Barcelona 소유. 사진 출처:<br>{lines}
</div>
"""
