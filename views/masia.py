"""라 마시아 — 바르사 B 출신 선수의 1군 출전 시간 비중."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (ASSETS, BLAU, GOLD, GRANA, GRID, PLOT, PROCESSED, _name_key,
                  b64, load_json, load_parquet, load_seasons, metric_cards,
                  portrait_map, setup)


seasons = load_seasons()
setup(seasons)

players = load_parquet(PROCESSED / "players.parquet").copy()
masia = load_json(PROCESSED / "masia.json")

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">BARÇA B · 1993/94–2025/26</div>
  <h1>라 마시아</h1>
  <div class="hero-motto">유스 시스템을 거친 선수들이 1군의 시간을 얼마나
  책임졌는지, 33시즌의 흐름으로 본다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if players.empty or not masia:
    st.warning("라 마시아 데이터가 없습니다. `python crawl_masia.py`와 "
               "`python build_players.py`를 먼저 실행하세요.")
    st.stop()

st.markdown('<div class="section">건물에서 철학으로</div>',
            unsafe_allow_html=True)
st.markdown("""
라 마시아의 이름은 캄 노우 옆에 있던 1702년 건축 농가 ‘마시아 데 칸 플라네스’에서
왔다. 바르사의 유소년 축구는 그보다 앞선 1901년 2·3·4군 창설에서 시작됐지만,
1979년 이 건물이 타지 출신 유망주를 위한 기숙사로 문을 열면서 ‘라 마시아’는
생활·학업·축구를 함께 가르치는 육성 체계의 이름이 됐다.

오늘날 라 마시아는 특정 건물만을 뜻하지 않는다. 겸손·노력·야망·존중·팀워크를
공통 가치로 삼고, 같은 경기 언어를 여러 연령대에 이어 주는 바르사의 교육 모델이다.
2011년 기숙사는 산트 조안 데스피의 오리올 토르트 훈련센터로 옮겼지만,
‘집에서 선수를 키워 1군의 정체성으로 연결한다’는 역할은 그대로 이어지고 있다.
""")
# 라 마시아는 한 세대로 끝난 이야기가 아니라 지금도 이어진다. 그래서
# 전성기 세대와 현재 세대를 나눠 보여준다.
# 사진은 **바르사 유니폼**을 입은 것으로 쓴다. Transfermarkt 초상은 대표팀
# 유니폼이거나 머리만 나와 클럽 페이지에 맞지 않는다. 지정한 파일이 없으면
# 그때만 TM 초상으로 내려간다.
GOLDEN_GEN = [
    ("Carles Puyol", "수비 · 주장", "헌신과 리더십의 기준", "legends/puyol.jpg"),
    ("Xavi", "미드필더", "점유와 위치 축구의 설계자", "legends/xavi.jpg"),
    ("Andrés Iniesta", "미드필더", "좁은 공간을 푼 기술과 판단", "legends/iniesta.jpg"),
    ("Lionel Messi", "공격수", "아카데미가 배출한 최고 기록 보유자", "legends/messi.jpg"),
    ("Sergio Busquets", "미드필더", "보이지 않는 공간을 지배한 중심축", "masia/busquets.jpg"),
]
CURRENT_GEN = [
    ("Lamine Yamal", "우측 윙어", "16세에 주전이 된 다음 세대의 얼굴", "masia/yamal.jpg"),
    ("Pau Cubarsí", "센터백", "17세에 수비 라인을 맡은 계보의 증거", "masia/cubarsi.jpg"),
    ("Gavi", "미드필더", "차비·이니에스타의 자리를 물려받은 투지", "masia/gavi.jpg"),
    ("Pedri", "미드필더", "경기 속도를 조절하는 지금의 설계자", "masia/pedri.jpg"),
    ("Fermín López", "공격형 미드필더", "결정적인 순간에 나타나는 침투", "masia/fermin.jpg"),
]
portrait_index = load_json(PROCESSED / "portraits.json")
st.image(str(ASSETS / "masia_lineage.jpg"), width="stretch")
st.caption("하나의 철학, 여러 세대 — 크루이프 시대에 확립된 축구의 언어가 "
           "지도자와 선수를 거쳐 다음 유소년의 어깨로 이어진다. · AI 생성 이미지")

history = [
    ("1901", "유소년 축구의 시작",
     "구단 이사이자 선수였던 류이스 도소가 2·3·4군을 만들었다. 라 마시아 건물보다 먼저 시작된 바르사 육성 체계의 뿌리다."),
    ("1979", "선수 기숙사 개관",
     "10월 20일, 캄 노우 옆 칸 플라네스 농가가 스페인 최초의 축구선수 기숙사로 문을 열었다."),
    ("2010", "발롱도르를 채우다",
     "메시·이니에스타·차비가 최종 1~3위를 모두 차지했다. 한 구단 아카데미 출신 세 명이 시상대를 독점한 유일한 사례다."),
    ("2011", "새로운 집",
     "10월 20일, 기숙사가 조안 감페르 훈련단지의 오리올 토르트 센터로 이전했다. 교육·생활 시설도 함께 확장됐다."),
    ("2012", "11명이 모두 유스 출신",
     "11월 25일 레반테전에서 약 46분 동안 필드의 바르사 선수 전원이 유스 출신이었다. 경기는 4-0으로 끝났다."),
    ("2025", "2,000경기 연속 계승",
     "1990년부터 1군 2,000경기 연속으로 최소 한 명의 라 마시아 출신이 그라운드를 밟았다."),
]
history_cards = "".join(
    f'<div class="timeline-card"><div class="timeline-year">{year}</div>'
    f'<div class="timeline-title">{title}</div>'
    f'<div class="timeline-body">{body}</div></div>'
    for year, title, body in history
)
st.markdown(f'<div class="timeline-grid">{history_cards}</div>',
            unsafe_allow_html=True)

def rep_cards(people, accent: str) -> None:
    """대표 선수 카드 한 줄. 사진은 잘라내지 않고 전체를 보여준다."""
    cols = st.columns(len(people), gap="small")
    for col, (name, role, note, photo) in zip(cols, people):
        with col:
            src = b64(photo) if photo else ""
            if not src:  # 지정 사진이 없으면 TM 초상으로
                entry = portrait_index.get(_name_key(name), {})
                src = b64(f"portraits/{entry['file']}") if entry.get("file") else ""
            img = (f'<img class="masia-photo" src="{src}" alt="{name}">' if src
                   else '<div class="legend-noimg masia-photo">사진 없음</div>')
            st.markdown(f"""
<div class="legend-card masia-card" style="border-top:4px solid {accent}">{img}
  <div class="legend-cap"><b>{name}</b><span>{role}<br>{note}</span></div>
</div>""", unsafe_allow_html=True)


st.markdown('<div class="section">전성기 세대</div>', unsafe_allow_html=True)
rep_cards(GOLDEN_GEN, GRANA)
st.caption("2008~2015년 팀의 뼈대를 이룬 아카데미 출신들. "
           "2010년 발롱도르 최종 3인이 모두 여기서 나왔다.")

st.markdown('<div class="section">지금의 세대</div>', unsafe_allow_html=True)
rep_cards(CURRENT_GEN, GOLD)
st.caption("계보는 끊기지 않았다. 아래 수치는 명성이나 수상 경력이 아니라 "
           "실제 라리가 출전 시간으로 그 흐름을 본다.")
# 현역 선수는 자유 라이선스 경기 사진이 거의 없어 보도사진을 썼다.
# 저작권이 있는 사진이므로 출처를 밝혀 둔다.
st.caption("사진 출처 · 가비, 페르민 로페스 — Getty Images (각각 sportalkorea, "
           "InterFootball 경유). 저작권이 있는 보도사진이며 비상업 학습 목적으로 "
           "인용했다. 세르히오 부스케츠 — הגמל התימני / CC BY-SA 4.0 "
           "(Wikimedia Commons).")

# crawl_masia.py가 수집한 바르사 B 시즌 명단에 등장한 선수를 유스 출신으로 본다.
# 이름은 악센트와 구두점을 제거한 키로만 정확히 대조한다. 성만 맞추면 Arturo
# Vidal/Marc Vidal처럼 전혀 다른 선수를 붙일 수 있어 느슨한 매칭은 하지 않는다.
players["masia_key"] = players["Player"].map(_name_key)
players["유스출신"] = players["masia_key"].isin(masia)
players["출전분"] = pd.to_numeric(players["출전분"], errors="coerce").fillna(0)
players["유스출전분"] = players["출전분"].where(players["유스출신"], 0)

trend = (players.groupby("season", as_index=False)
         .agg(전체출전분=("출전분", "sum"), 유스출전분=("유스출전분", "sum"),
              전체선수=("Player", "nunique")))
youth_counts = (players[players["유스출신"] & players["출전분"].gt(0)]
                .groupby("season")["Player"]
                .nunique().rename("유스선수"))
trend = trend.join(youth_counts, on="season").fillna({"유스선수": 0})
trend["유스비중"] = trend["유스출전분"].div(trend["전체출전분"]).mul(100)
trend = trend.sort_values("season").reset_index(drop=True)

matched = players.loc[players["유스출신"], "Player"].nunique()
peak = trend.loc[trend["유스비중"].idxmax()]
latest = trend.iloc[-1]
overall = players["유스출전분"].sum() / players["출전분"].sum() * 100

st.markdown('<div class="section">33시즌 한눈에 보기</div>',
            unsafe_allow_html=True)
st.markdown(metric_cards([
    ("B팀 명단", f"{len(masia):,}명", "Transfermarkt 시즌 스쿼드 수집"),
    ("1군 기록 매칭", f"{matched}명", "FBref 라리가 기록과 정확히 대조"),
    ("최고 비중", f"{peak['유스비중']:.1f}%", f"{peak['season']} · {int(peak['유스선수'])}명"),
    ("최근 시즌", f"{latest['유스비중']:.1f}%", f"{latest['season']} · 33시즌 전체 {overall:.1f}%"),
]), unsafe_allow_html=True)

st.info("여기서 ‘라 마시아 출신’은 수집 가능한 **바르사 B 시즌 명단에 등장한 선수**를 "
        "뜻합니다. 유스팀에서 바로 해외로 떠났거나 B팀을 거치지 않은 선수는 빠질 수 "
        "있으므로, 공식 아카데미 전체 명단이 아니라 일관된 하한선 지표로 보세요.")

st.markdown('<div class="section">시즌별 유스 출전 시간 비중</div>',
            unsafe_allow_html=True)
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=trend["season"], y=trend["유스비중"], mode="lines+markers",
    name="유스 출전 비중", line=dict(color=GRANA, width=3),
    marker=dict(color=GOLD, size=7, line=dict(color=GRANA, width=1.5)),
    fill="tozeroy", fillcolor="rgba(165,0,68,.14)",
    customdata=trend[["유스출전분", "전체출전분", "유스선수"]],
    hovertemplate=("<b>%{x}</b><br>유스 비중 %{y:.1f}%"
                   "<br>유스 출전 %{customdata[0]:,.0f}분 / %{customdata[1]:,.0f}분"
                   "<br>유스 선수 %{customdata[2]:.0f}명<extra></extra>")))
fig.add_hline(y=overall, line_dash="dot", line_color=BLAU,
              annotation_text=f"33시즌 평균 {overall:.1f}%",
              annotation_font_color="#94a8c4")
fig.add_annotation(x=peak["season"], y=peak["유스비중"],
                   text=f"정점 {peak['season']} · {peak['유스비중']:.1f}%",
                   showarrow=True, arrowcolor=GOLD, arrowhead=2, ay=-45,
                   font=dict(color=GOLD))
fig.update_layout(height=430, yaxis_title="팀 전체 출전 시간 중 비중(%)",
                  showlegend=False, **PLOT)
fig.update_xaxes(gridcolor=GRID, tickangle=-45)
fig.update_yaxes(gridcolor=GRID, range=[0, max(65, peak["유스비중"] + 6)],
                 ticksuffix="%")
st.plotly_chart(fig, width="stretch")
st.caption("라리가 선수별 출전분 합계를 분모로 계산. 골키퍼를 포함한 팀 전체 출전 시간 "
           "중 바르사 B 경유 선수의 몫이다.")

st.markdown('<div class="section">누가 그 시간을 만들었나</div>',
            unsafe_allow_html=True)
c1, c2 = st.columns([1.05, 1.35])

with c1:
    career = (players[players["유스출신"]].groupby("Player")
              .agg(출전분=("출전분", "sum"), 경기=("경기", "sum"),
                   골=("골", "sum"), 시즌=("season", "nunique"))
              .nlargest(12, "출전분").sort_values("출전분"))
    f2 = go.Figure(go.Bar(
        y=career.index, x=career["출전분"], orientation="h",
        marker_color=BLAU,
        customdata=career[["경기", "골", "시즌"]],
        hovertemplate=("<b>%{y}</b><br>%{x:,.0f}분 · %{customdata[0]:.0f}경기"
                       "<br>%{customdata[1]:.0f}골 · %{customdata[2]:.0f}시즌"
                       "<extra></extra>")))
    f2.update_layout(height=475, xaxis_title="라리가 출전 시간(분)", **PLOT)
    f2.update_xaxes(gridcolor=GRID)
    f2.update_yaxes(gridcolor=GRID)
    st.plotly_chart(f2, width="stretch")
    st.caption("33시즌 누적 라리가 출전 시간 상위 12명")

with c2:
    selected = st.selectbox("시즌 상세", trend["season"].tolist(),
                            index=len(trend) - 1)
    one = players[(players["season"] == selected) & players["유스출신"] &
                  players["출전분"].gt(0)].copy()
    one = one.sort_values("출전분", ascending=False)
    selected_summary = trend[trend["season"] == selected].iloc[0]
    st.markdown(metric_cards([
        ("유스 비중", f"{selected_summary['유스비중']:.1f}%", selected),
        ("유스 선수", f"{int(selected_summary['유스선수'])}명", "1분 이상 기록 포함"),
    ]), unsafe_allow_html=True)
    table = one[["Player", "Pos", "경기", "선발", "출전분", "골", "도움"]].copy()
    table.columns = ["선수", "포지션", "경기", "선발", "출전분", "골", "도움"]
    photos = portrait_map(table["선수"].unique())
    table.insert(0, "사진", table["선수"].map(photos))
    st.dataframe(table.set_index("선수"), width="stretch", height=360,
                 column_config={"사진": st.column_config.ImageColumn("사진", width="small")})

st.markdown("""
<div class="credits">
<b>데이터</b> Transfermarkt 바르셀로나 B 시즌 스쿼드(유스 판별) + FBref 라리가
선수 기록 1993/94~2025/26(출전 시간). 이름은 악센트와 구두점을 정규화한 뒤
정확히 일치할 때만 연결했다.<br>
<b>해석 한계</b> 바르사 B 명단을 기준으로 하므로 B팀을 거치지 않은 아카데미 출신은
누락될 수 있다. 반대로 B팀 명단에 있었던 선수는 유스 체류 기간과 관계없이 포함된다.
출전분은 FBref가 기록한 선수별 합계이며 라리가만 포함한다.<br>
<b>역사 출처</b>
<a href="https://www.fcbarcelona.com/en/news/1457129/la-masia-is-40-years-old" target="_blank">FC Barcelona · La Masia is 40 years old</a> ·
<a href="https://www.fcbarcelona.com/en/club/identity/la-masia" target="_blank">FC Barcelona · La Masia</a> ·
<a href="https://www.fcbarcelona.com/en/news/1924303/10-years-since-a-unique-ballon-dor-podium" target="_blank">2010 Ballon d'Or podium</a> ·
<a href="https://www.fcbarcelona.com/en/news/2914090/10-years-since-11-from-la-masia-appeared-in-the-line-up" target="_blank">2012 La Masia XI</a> ·
<a href="https://www.fcbarcelona.com/en/news/4273670/la-masia-presence-in-2000-consecutive-games" target="_blank">2,000 consecutive games</a>
</div>
""", unsafe_allow_html=True)
