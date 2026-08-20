"""페이지 공통 자산 — 팔레트, CSS, 데이터 로더, 사이드바.

app.py가 st.navigation으로 views/ 아래 페이지를 묶고, 각 페이지는
여기서 CSS와 데이터를 가져다 쓴다.
"""
import base64
import json
import re
import unicodedata
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
def _parquet_cached(path_str: str, stamp: float) -> pd.DataFrame:
    p = Path(path_str)
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def load_parquet(path: Path) -> pd.DataFrame:
    """parquet 로더.

    수정 시각을 캐시 키에 넣는다. 경로만 키로 쓰면 수집 스크립트를 다시 돌려
    파일이 바뀌어도 옛 내용이 계속 나온다. 파일이 없으면 빈 DataFrame.
    """
    stamp = path.stat().st_mtime if path.exists() else 0.0
    return _parquet_cached(str(path), stamp)


def load_seasons() -> pd.DataFrame:
    return load_parquet(PROCESSED / "club_season.parquet")


def load_clasico() -> pd.DataFrame:
    cl = load_parquet(PROCESSED / "clasico.parquet").copy()
    cl["decade"] = cl["Season"].str[:3] + "0s"
    return cl


@st.cache_data
def _json_cached(path_str: str, stamp: float) -> dict:
    p = Path(path_str)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def load_json(path: Path) -> dict:
    """수정 시각을 캐시 키에 포함해, 나중에 갱신된 파일도 다시 읽는다."""
    stamp = path.stat().st_mtime if path.exists() else 0.0
    return _json_cached(str(path), stamp)


def load_credits() -> dict:
    return load_json(ASSETS / "credits.json")


@st.cache_data
def _b64_cached(name: str, stamp: float) -> str:
    p = ASSETS / name
    if not p.exists():
        return ""
    mime = "image/svg+xml" if p.suffix == ".svg" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"


def b64(name: str) -> str:
    """자산 파일을 data URI로. 클라우드 정적서빙 설정 없이 HTML에 심기 위함.

    캐시 키에 수정 시각을 함께 넣는다. 파일명만 키로 쓰면, 아직 내려받기 전에
    조회해 캐시된 빈 문자열이 파일이 생긴 뒤에도 계속 돌아온다.
    """
    p = ASSETS / name
    stamp = p.stat().st_mtime if p.exists() else 0.0
    return _b64_cached(name, stamp)


# ---------------------------------------------------------------- 사진 목록
# 홈 페이지 사진. 모두 바르사 소속 시절 사진으로 맞춘다.
PHOTOS = [
    ("camp_nou", "캄 노우", "관중 99,354석. 유럽 최대 규모 축구 전용 경기장"),
    ("cruyff", "요한 크루이프", "바르사 시절 경기 장면. 1973~78년 선수, 1988~96년 감독"),
    ("messi", "리오넬 메시", "캄 노우 라리가 경기. 클럽 통산 최다 출전·최다 득점"),
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

/* 레전드 카드 — 선택된 카드는 그라나 테두리로 표시 */
.legend-card{border-radius:14px;overflow:hidden;background:var(--panel2);
      border:1px solid var(--line);border-bottom:3px solid var(--blau);margin-bottom:.4rem;}
.legend-card-on{border-color:var(--grana);border-bottom-color:var(--grana);
      box-shadow:0 0 0 1px var(--grana) inset;}
.legend-card img{width:100%;height:150px;object-fit:cover;object-position:top center;display:block;}
.legend-noimg{height:150px;display:flex;align-items:center;justify-content:center;
      color:var(--muted);font-size:.74rem;background:#0a1728;}
.legend-cap{padding:.5rem .6rem .6rem;text-align:center;}
.legend-cap b{color:var(--ink);font-size:.8rem;display:block;line-height:1.2;}
.legend-cap span{color:var(--muted);font-size:.66rem;}

.legend-hero{border-radius:14px;overflow:hidden;border:1px solid var(--line);
      border-bottom:4px solid var(--grana);background:var(--panel2);}
.legend-hero img{width:100%;display:block;object-fit:cover;max-height:330px;object-position:top center;}
.legend-bio{background:linear-gradient(150deg,var(--panel),var(--panel2));
      border:1px solid var(--line);border-left:4px solid var(--grana);border-radius:12px;
      padding:1.2rem 1.4rem;height:100%;}
.legend-full{color:var(--ink);font-size:1.15rem;font-weight:800;}
.legend-pos{color:var(--gold);font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;
      font-weight:700;margin-top:.3rem;}
.legend-tag{color:#c3d2e6;font-size:.95rem;font-style:italic;margin:.8rem 0 1rem;line-height:1.6;}
.legend-honors{color:var(--muted);font-size:.82rem;line-height:1.6;
      border-top:1px solid var(--line);padding-top:.8rem;}
.legend-honors span{display:block;color:var(--gold);font-size:.66rem;letter-spacing:.12em;
      text-transform:uppercase;font-weight:800;margin-bottom:.25rem;}


/* 감독 카드 — 초상 사진이 3:4로 규격이 같다. cover로 자르면 턱과 이마가
   날아가므로 contain으로 전체를 보여주고 여백은 배경으로 채운다. */
.mg-card img{width:100%;height:auto;aspect-ratio:3/4;object-fit:contain;
      background:linear-gradient(150deg,#0d2038,#081426);}
.mg-initial{font-size:1.9rem;font-weight:850;color:var(--gold);letter-spacing:.04em;
      aspect-ratio:3/4;height:auto;background:linear-gradient(150deg,#0d2038,#081426);}
.mg-hero-initial{display:flex;align-items:center;justify-content:center;height:330px;
      font-size:4rem;font-weight:850;color:var(--gold);letter-spacing:.05em;
      border-radius:14px;border:1px solid var(--line);border-bottom:4px solid var(--grana);
      background:linear-gradient(150deg,#0d2038,#081426);}
/* 상세의 큰 사진도 자르지 않는다 */
.mg-hero img{object-fit:contain !important;max-height:360px;
      background:linear-gradient(150deg,#0d2038,#081426);}

/* 시대 카드 — 대표 인물 사진을 위에 얹는다 */
.era-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;}
.era-card{position:relative;overflow:hidden;border-radius:14px;border:1px solid var(--line);
      background:linear-gradient(145deg,var(--panel),var(--panel2));display:flex;
      flex-direction:column;}
/* 시대 사진은 가로 장면이라 중앙 기준으로 담는다 */
.era-photo{width:100%;aspect-ratio:16/9;object-fit:cover!important;
      object-position:center!important;
      display:block;background:#081426;}
.era-body{padding:1rem 1.15rem 1.1rem;flex:1;}
.era-caption{color:var(--gold);font-size:.68rem;letter-spacing:.08em;margin-top:.65rem;
      text-transform:uppercase;font-weight:700;}

/* 감독 한 줄 평 */
.mg-note{color:#c3d2e6;font-size:.94rem;line-height:1.75;margin:.2rem 0 1rem;
      padding:.95rem 1.2rem;border-radius:12px;border:1px solid var(--line);
      border-left:4px solid var(--gold);
      background:linear-gradient(150deg,rgba(13,32,56,.7),rgba(8,20,38,.7));}

/* 라 마시아 대표 선수 — 초상을 잘라내면 이마와 턱이 날아간다.
   감독 카드와 같은 방식으로 3:4 비율에 contain으로 담는다. */
.masia-card{overflow:hidden;}
.masia-photo{width:100%;height:auto !important;aspect-ratio:3/4;
      object-fit:contain !important;object-position:center !important;
      background:linear-gradient(150deg,#0d2038,#081426);}
div.legend-noimg.masia-photo{display:flex;align-items:center;justify-content:center;}

/* MSN 카드 — 세 사람을 나란히 */
.msn-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:.85rem;}
.msn-card{border-radius:14px;overflow:hidden;border:1px solid var(--line);
      background:linear-gradient(150deg,var(--panel),var(--panel2));
      display:flex;flex-direction:column;}
.msn-photo{width:100%;height:300px;object-fit:cover!important;
      object-position:center 28%!important;
      background:linear-gradient(150deg,#0d2038,#081426);}
.msn-banner{width:100%;height:400px;object-fit:cover!important;
      object-position:center 30%!important;
      border-radius:14px;border:1px solid var(--line);
      display:block;margin:.2rem 0 .4rem;}
.msn-photo.whole{height:300px;object-fit:cover!important;
      object-position:center 22%!important;}
.msn-body{padding:.9rem 1.1rem 1.1rem;}
.msn-name{color:var(--ink);font-size:1.25rem;font-weight:860;}
.msn-full{color:var(--muted);font-size:.72rem;letter-spacing:.06em;margin-top:.1rem;}
.msn-line{color:var(--gold);font-size:1.02rem;font-weight:700;margin-top:.6rem;}
.msn-line b{color:var(--ink);font-size:1.3rem;}
.msn-sub{color:var(--muted);font-size:.76rem;margin-top:.25rem;}

/* 갤러리 — 클라시코 역사 이미지 */
.gallery{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem;}
.gallery figure{margin:0;border-radius:14px;overflow:hidden;background:var(--panel2);
      border:1px solid var(--line);border-bottom:3px solid var(--grana);}
.gallery figure:nth-child(even){border-bottom-color:var(--blau);}
.gallery img{width:100%;height:200px;object-fit:cover;display:block;}
.gallery figcaption{padding:.7rem .9rem .85rem;}
.gallery figcaption b{color:var(--ink);font-size:.86rem;display:block;margin-bottom:.15rem;}
.gallery figcaption span{color:var(--muted);font-size:.74rem;line-height:1.5;}

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
  .metric-grid,.timeline-grid,.photo-grid,.gallery,.era-grid,.msn-grid{grid-template-columns:1fr;}
  .hero h1{white-space:normal;}
  .hero-vs{flex-direction:column;align-items:flex-start;gap:.2rem;}
}

/* ---- 데이터 센터형 홈 카드 -------------------------------------------- */
.dc-card{border:1px solid var(--line);border-radius:16px;padding:1.05rem 1.15rem;
      background:linear-gradient(155deg,var(--panel),var(--panel2));height:100%;}
.dc-head{display:flex;align-items:baseline;justify-content:space-between;
      gap:.6rem;margin-bottom:.75rem;}
.dc-title{color:var(--ink);font-size:.98rem;font-weight:800;letter-spacing:.01em;}
.dc-note{color:var(--muted);font-size:.72rem;}
/* 히어로 — 큰 배너 카드 */
.dc-hero{position:relative;border:1px solid var(--line);border-radius:18px;
      overflow:hidden;background:linear-gradient(120deg,#0b1e38 0%,#12294a 45%,
      #4a1030 100%);padding:1.5rem 1.7rem 1.6rem;min-height:430px;
      display:flex;flex-direction:column;justify-content:center;}
.dc-hero::after{content:"";position:absolute;inset:0;
      background:radial-gradient(circle at 82% 22%,rgba(255,199,44,.20),transparent 58%);
      pointer-events:none;}
.dc-kick{color:var(--gold);font-size:.76rem;font-weight:800;letter-spacing:.16em;
      text-transform:uppercase;}
.dc-hero h2{color:#fff;font-size:2.5rem;font-weight:900;margin:.3rem 0 .1rem;
      line-height:1.06;letter-spacing:-.02em;}
.dc-sub{color:#b9cbe4;font-size:.9rem;margin-bottom:1.1rem;}
.dc-score{display:flex;align-items:center;gap:1.1rem;flex-wrap:wrap;
      position:relative;z-index:1;}
.dc-team{color:#fff;font-size:1.0rem;font-weight:800;}
.dc-num{color:var(--gold);font-size:2.3rem;font-weight:900;line-height:1;}
.dc-vs{color:#8fa6c4;font-size:.8rem;font-weight:800;letter-spacing:.1em;}
/* 오른쪽 요약 */
.dc-rank{color:var(--gold);font-size:3.5rem;font-weight:900;line-height:.95;}
.dc-rank small{font-size:1.1rem;color:#b9cbe4;font-weight:700;margin-left:.15rem;}
.dc-wdl{color:var(--ink);font-size:1.5rem;font-weight:900;}
.dc-wdl small{font-size:.8rem;color:var(--muted);font-weight:700;margin-left:.1rem;}
.dc-bar{height:7px;border-radius:99px;background:#132a46;overflow:hidden;
      margin:.45rem 0 .2rem;}
.dc-bar i{display:block;height:100%;background:linear-gradient(90deg,var(--grana),
      var(--gold));}
.dc-dots{display:flex;gap:.28rem;flex-wrap:wrap;}
.dc-dot{width:25px;height:25px;border-radius:50%;display:flex;align-items:center;
      justify-content:center;font-size:.72rem;font-weight:900;color:#04101f;}
.dc-w{background:var(--gold);} .dc-d{background:#7d92ad;} .dc-l{background:#8d2440;color:#fff;}
.dc-row{display:flex;align-items:center;justify-content:space-between;gap:.5rem;
      padding:.42rem 0;border-bottom:1px solid rgba(255,255,255,.055);}
.dc-row:last-child{border-bottom:none;}
.dc-rl{color:#c8d7ea;font-size:.82rem;display:flex;align-items:center;gap:.5rem;
      min-width:0;}
.dc-rl b{color:var(--ink);font-weight:700;overflow:hidden;text-overflow:ellipsis;
      white-space:nowrap;}
.dc-rr{color:var(--gold);font-size:.95rem;font-weight:800;white-space:nowrap;}
.dc-pill{font-size:.66rem;font-weight:900;border-radius:5px;padding:.1rem .34rem;
      color:#04101f;}
.dc-idx{color:var(--muted);font-size:.74rem;width:1.1rem;text-align:right;
      font-weight:800;flex:none;}
.dc-face{width:26px;height:26px;border-radius:50%;object-fit:cover;flex:none;
      background:#0d2038;}
[data-testid="stColumn"]>div,[data-testid="stColumn"]>div>div{height:100%;}
@media(max-width:900px){.dc-hero h2{font-size:1.9rem;}.dc-rank{font-size:2.6rem;}}
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


# ---------------------------------------------------------------- 피치 그리기

def pitch_shapes(x0: float = 0, y0: float = 0, x1: float = 120, y1: float = 80) -> list:
    """StatsBomb 좌표계(120×80) 축구장 라인. plotly layout.shapes에 넣는다.

    공격 방향은 +x, 골대는 x=120. 페널티박스는 골라인에서 18야드(=18단위),
    골에어리어는 6야드다.
    """
    line = dict(type="line", line=dict(color="#2f4d78", width=1.4))
    rect = dict(type="rect", line=dict(color="#2f4d78", width=1.4))
    circle = dict(type="circle", line=dict(color="#2f4d78", width=1.4))
    return [
        {**rect, "x0": x0, "y0": y0, "x1": x1, "y1": y1},          # 외곽
        {**line, "x0": 60, "y0": y0, "x1": 60, "y1": y1},           # 하프라인
        {**circle, "x0": 50, "y0": 30, "x1": 70, "y1": 50},         # 센터서클
        {**rect, "x0": 0, "y0": 18, "x1": 18, "y1": 62},            # 좌 페널티박스
        {**rect, "x0": 102, "y0": 18, "x1": 120, "y1": 62},         # 우 페널티박스
        {**rect, "x0": 0, "y0": 30, "x1": 6, "y1": 50},             # 좌 골에어리어
        {**rect, "x0": 114, "y0": 30, "x1": 120, "y1": 50},         # 우 골에어리어
    ]


def pitch_layout(height: int = 470, **kw) -> dict:
    """피치 위 산점도용 레이아웃. 종횡비를 고정해 경기장이 찌그러지지 않게 한다."""
    base = dict(
        height=height, shapes=pitch_shapes(), showlegend=False,
        xaxis=dict(range=[-2, 122], visible=False, constrain="domain"),
        yaxis=dict(range=[-2, 82], visible=False, scaleanchor="x", scaleratio=1),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a8c4", size=12), margin=dict(l=6, r=6, t=30, b=6),
    )
    base.update(kw)
    return base


def load_sb(name: str) -> pd.DataFrame:
    """StatsBomb 집계 parquet. 아직 수집 전이면 빈 DataFrame."""
    return load_parquet(PROCESSED.parent / "statsbomb" / f"{name}.parquet")


def load_understat() -> pd.DataFrame:
    """Understat 슛. StatsBomb이 끊긴 2021/22 이후를 잇는다."""
    return load_parquet(PROCESSED.parent / "understat" / "shots.parquet")


@st.cache_data
def _concat_cached(key: str, files: tuple[str, ...]) -> pd.DataFrame:
    if not files:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def load_dir(dirname: str, pattern: str = "*.parquet") -> pd.DataFrame:
    """디렉터리 안 parquet을 모두 합친다. 파일 목록과 수정 시각이 캐시 키다."""
    d = PROCESSED.parent / dirname
    files = sorted(d.glob(pattern)) if d.exists() else []
    key = "|".join(f"{f.name}:{f.stat().st_mtime}" for f in files)
    return _concat_cached(key, tuple(str(f) for f in files))


# ---------------------------------------------------------------- 선수 사진

def _name_key(name: str) -> str:
    """발음기호를 벗기고 소문자로. 소스마다 표기가 달라 비교용 키가 필요하다."""
    n = unicodedata.normalize("NFKD", str(name))
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", "", n.lower()).strip()


@st.cache_data
def _portrait_index(stamp: float) -> dict:
    """선수 이름 → 썸네일 data URI.

    Transfermarkt와 FBref의 표기가 달라(Ion/Jon Goikoetxea, Eusebio Sacristán/
    Eusebio) 정확히 일치하는 키 외에 성(姓)만으로도 찾을 수 있게 색인을 둘로
    만든다. 성이 겹치면 애매하므로 그런 성은 아예 빼서 엉뚱한 얼굴이 붙는 것을
    막는다.
    """
    p = PROCESSED / "portraits.json"
    if not p.exists():
        return {"exact": {}, "surname": {}}
    idx = json.loads(p.read_text(encoding="utf-8"))

    exact, by_surname = {}, {}
    for key, v in idx.items():
        thumb = ASSETS / "portraits_thumb" / v["file"]
        if not thumb.exists():
            continue
        uri = f"data:image/jpeg;base64,{base64.b64encode(thumb.read_bytes()).decode()}"
        exact[key] = uri
        parts = key.split()
        if parts:
            by_surname.setdefault(parts[-1], []).append(uri)

    # 성이 유일한 경우만 남긴다
    surname = {k: v[0] for k, v in by_surname.items() if len(v) == 1}
    return {"exact": exact, "surname": surname}


def portrait_map(names) -> dict:
    """주어진 이름들에 대한 사진 URI. 없으면 빈 문자열."""
    p = PROCESSED / "portraits.json"
    stamp = p.stat().st_mtime if p.exists() else 0.0
    idx = _portrait_index(stamp)
    out = {}
    for n in names:
        key = _name_key(n)
        uri = idx["exact"].get(key)
        if not uri:
            parts = key.split()
            if parts:
                uri = idx["surname"].get(parts[-1])
        out[n] = uri or ""
    return out


@st.cache_data
def _position_index(stamp: str) -> dict:
    """선수 이름 → 주 포지션(GK/DF/MF/FW).

    FBref 전 대회 표의 Pos를 쓰되, 한 선수가 여러 포지션이면 출전 시간이 가장
    많은 쪽을 택한다. 소스마다 표기가 달라(Ferrán/Ferran, Rakitic/Rakitić)
    정규화 키로 맞추고, 그래도 없으면 성으로 한 번 더 찾는다.
    """
    d = PROCESSED.parent / "fbref_allcomps_players"
    files = sorted(d.glob("*.parquet")) if d.exists() else []
    if not files:
        return {"exact": {}, "surname": {}}
    ac = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    ac = ac[ac.get("대회", "") == "전 대회"].copy()
    if ac.empty:
        return {"exact": {}, "surname": {}}

    ac["main"] = ac["Pos"].fillna("").str.split(",").str[0].str.strip()
    ac = ac[ac["main"].isin(["GK", "DF", "MF", "FW"])]
    ac["key"] = ac["Player"].map(_name_key)
    exact = (ac.groupby(["key", "main"])["출전분"].sum().reset_index()
             .sort_values("출전분", ascending=False).drop_duplicates("key")
             .set_index("key")["main"].to_dict())

    by_sur = {}
    for k, v in exact.items():
        parts = k.split()
        if parts:
            by_sur.setdefault(parts[-1], set()).add(v)
    surname = {k: next(iter(v)) for k, v in by_sur.items() if len(v) == 1}
    return {"exact": exact, "surname": surname,
            "tokens": {k: frozenset(k.split()) for k in exact}}


def position_map(names) -> dict:
    """주어진 이름들의 주 포지션. 못 찾으면 빈 문자열.

    소스마다 이름 길이가 다르다. StatsBomb은 정식 이름을 쓰고
    (`Lionel Andrés Messi Cuccittini`) FBref는 약칭을 쓴다(`Lionel Messi`).
    그래서 정확히 같은 키 → 성 → **토큰 포함** 순으로 세 번 찾는다.
    토큰 포함은 FBref 이름의 모든 조각이 상대 이름 안에 들어 있으면 같은
    사람으로 보는 방식이고, 후보가 둘 이상이면 애매하므로 버린다.
    """
    d = PROCESSED.parent / "fbref_allcomps_players"
    files = sorted(d.glob("*.parquet")) if d.exists() else []
    stamp = "|".join(f"{f.name}:{f.stat().st_mtime}" for f in files)
    idx = _position_index(stamp)
    tokens = idx.get("tokens", {})

    out = {}
    for n in names:
        key = _name_key(n)
        p = idx["exact"].get(key)
        if not p:
            parts = key.split()
            if parts:
                p = idx["surname"].get(parts[-1])
        if not p and key:
            q = set(key.split())
            hits = [k for k, tk in tokens.items() if tk and tk <= q]
            if len(hits) == 1:
                p = idx["exact"][hits[0]]
            elif len(hits) > 1:
                # 조각이 가장 많이 겹치는 하나가 유일할 때만 채택
                best = max(len(tokens[k]) for k in hits)
                top = [k for k in hits if len(tokens[k]) == best]
                if len(top) == 1:
                    p = idx["exact"][top[0]]
        out[n] = p or ""
    return out
