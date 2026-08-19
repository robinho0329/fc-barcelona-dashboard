"""레전드 TOP 10 — 카드를 고르면 경력·연혁·스탯이 아래에 펼쳐진다."""
import plotly.graph_objects as go
import streamlit as st

from _lib import (ASSETS, GOLD, GRANA, GRID, PLOT, b64, load_json, load_sb,
                  load_seasons, metric_cards, setup)

seasons = load_seasons()
setup(seasons)

# 선정은 클럽 기여도·상징성·수상 이력을 기준으로 한 편집 판단이다.
# stats_name은 StatsBomb 이벤트에 기록된 표기와 맞춘 것으로, 비어 있으면
# 이벤트 데이터 범위(2004/05~2020/21) 밖 선수라 스탯이 붙지 않는다.
LEGENDS = [
    {
        "key": "messi", "name": "리오넬 메시", "full": "Lionel Andrés Messi",
        "years": "2004–2021", "pos": "포워드 · 우측 윙어",
        "stats_name": "Lionel Andrés Messi Cuccittini",
        "photo": "legends/messi.jpg",
        "tagline": "클럽 통산 최다 출전·최다 득점. 바르사 그 자체.",
        "career": [
            ("2000", "라 마시아 입단", "13세에 아르헨티나를 떠나 바르사 유스로. 성장호르몬 치료비를 클럽이 부담했다."),
            ("2004", "1군 데뷔", "17세 114일, 에스파뇰전 교체 출전으로 데뷔."),
            ("2009", "첫 6관왕", "과르디올라 체제에서 한 해 6개 대회 전관왕. 첫 발롱도르."),
            ("2012", "한 해 91골", "자연년 기준 91골로 게르트 뮐러의 85골을 넘어섰다."),
            ("2015", "두 번째 트레블", "네이마르·수아레스와 MSN을 이뤄 리그·코파·챔스 석권."),
            ("2021", "이적", "재정 규정 문제로 계약 연장이 무산돼 파리로 떠났다."),
        ],
        "honors": "발롱도르 8회 · 라리가 10회 · 챔피언스리그 4회 · 월드컵 우승(2022, 대표팀)",
    },
    {
        "key": "cruyff", "name": "요한 크루이프", "full": "Hendrik Johannes Cruijff",
        "years": "1973–1978 (선수) · 1988–1996 (감독)", "pos": "포워드 · 감독",
        "stats_name": "", "photo": "legends/cruyff.jpg",
        "tagline": "선수로 한 번, 감독으로 또 한 번 클럽의 방향을 바꿨다.",
        "career": [
            ("1973", "아약스에서 이적", "당시 세계 최고 이적료. 첫 시즌 14년 만의 리그 우승."),
            ("1974", "베르나베우 0-5", "적지에서 5골. 카탈루냐에서 상징적인 경기로 남았다."),
            ("1988", "감독 부임", "'드림팀'을 만들며 클럽 축구 철학의 뼈대를 세웠다."),
            ("1992", "웸블리 유러피언컵", "삼프도리아를 꺾고 클럽 첫 유럽 정상."),
            ("1991", "리그 4연패 시작", "1991~94 라리가 4연속 우승."),
            ("1979", "라 마시아 구상", "유스 아카데미 체계의 토대를 만들었다."),
        ],
        "honors": "발롱도르 3회 · 감독으로 라리가 4연패 · 유러피언컵 1회",
    },
    {
        "key": "xavi", "name": "차비 에르난데스", "full": "Xavier Hernández Creus",
        "years": "1998–2015", "pos": "중앙 미드필더",
        "stats_name": "Xavier Hernández Creus", "photo": "legends/xavi.jpg",
        "tagline": "티키타카의 메트로놈. 라 마시아가 만든 가장 완성된 8번.",
        "career": [
            ("1998", "1군 데뷔", "마요르카전 데뷔골. 과르디올라의 뒤를 잇는 자리로 지목됐다."),
            ("2008", "과르디올라 체제", "부임 첫 시즌 6관왕의 중심."),
            ("2010", "발롱도르 3위", "메시·이니에스타와 함께 최종 3인. 셋 다 라 마시아 출신."),
            ("2011", "웸블리 결승", "맨유전 3-1 승리, 챔피언스리그 4번째 우승."),
            ("2015", "고별", "767경기 출전 클럽 기록을 남기고 알사드로."),
            ("2021", "감독 복귀", "감독으로 돌아와 2022/23 리그 우승."),
        ],
        "honors": "라리가 8회 · 챔피언스리그 4회 · 월드컵(2010)·유로(2008·2012)",
    },
    {
        "key": "iniesta", "name": "안드레스 이니에스타", "full": "Andrés Iniesta Luján",
        "years": "2002–2018", "pos": "중앙 · 공격형 미드필더",
        "stats_name": "Andrés Iniesta Luján", "photo": "legends/iniesta.jpg",
        "tagline": "가장 좁은 공간에서 가장 조용하게 경기를 풀어낸 선수.",
        "career": [
            ("2002", "1군 데뷔", "라 마시아를 거쳐 브루헤전으로 데뷔."),
            ("2009", "스탬퍼드 브리지", "첼시전 원정 후반 추가시간 동점골로 결승 진출."),
            ("2010", "월드컵 결승골", "네덜란드전 연장 골로 스페인에 첫 월드컵을."),
            ("2012", "주장 승계", "푸욜에 이어 완장을 물려받았다."),
            ("2015", "트레블 주장", "두 번째 트레블을 주장으로 이끌었다."),
            ("2018", "고별", "16시즌 674경기를 남기고 일본 고베로."),
        ],
        "honors": "라리가 9회 · 챔피언스리그 4회 · 월드컵 결승골(2010)",
    },
    {
        "key": "kubala", "name": "라디슬라오 쿠발라", "full": "László Kubala Stecz",
        "years": "1951–1961", "pos": "포워드 · 인사이드 포워드",
        "stats_name": "", "photo": "legends/kubala.jpg",
        "tagline": "캄 노우를 짓게 만든 선수. 관중이 넘쳐 새 구장이 필요했다.",
        "career": [
            ("1951", "입단", "헝가리를 떠나 망명 끝에 바르사행. 곧바로 팀의 중심이 됐다."),
            ("1952", "5관왕", "한 시즌 5개 대회 우승."),
            ("1952", "한 경기 7골", "스포르팅 히혼전 7골, 지금도 라리가 기록."),
            ("1957", "캄 노우 개장", "관중을 감당 못해 새 구장을 지었다는 말이 따라붙는다."),
            ("1961", "은퇴 후", "이후 감독으로도 클럽과 스페인 대표팀을 맡았다."),
            ("1999", "동상 건립", "캄 노우 외부에 그의 동상이 세워졌다."),
        ],
        "honors": "라리가 4회 · 코파 델 헤네랄리시모 5회 · 클럽 최고 선수 투표 1위(1999)",
    },
    {
        "key": "ronaldinho", "name": "호나우지뉴", "full": "Ronaldo de Assis Moreira",
        "years": "2003–2008", "pos": "공격형 미드필더 · 좌측 윙어",
        "stats_name": "Ronaldo de Assis Moreira", "photo": "legends/ronaldinho.jpg",
        "tagline": "침체기의 클럽을 다시 즐겁게 만든 선수.",
        "career": [
            ("2003", "입단", "레알과의 경쟁 끝에 PSG에서 합류. 재건의 출발점."),
            ("2005", "발롱도르", "리그 우승과 함께 세계 최고 선수로."),
            ("2005", "베르나베우 기립박수", "레알 원정 3-0 승리 후 상대 팬들이 일어나 박수를 보냈다."),
            ("2006", "챔피언스리그", "파리 결승에서 아스널을 꺾고 14년 만의 유럽 정상."),
            ("2006", "메시의 멘토", "10대 메시가 1군에 자리 잡는 과정을 곁에서 도왔다."),
            ("2008", "이적", "밀란으로 떠나며 5년의 시대를 마감."),
        ],
        "honors": "발롱도르(2005) · 라리가 2회 · 챔피언스리그 1회",
    },
    {
        "key": "puyol", "name": "카를레스 푸욜", "full": "Carles Puyol i Saforcada",
        "years": "1999–2014", "pos": "센터백",
        "stats_name": "Carles Puyol i Saforcada", "photo": "legends/puyol.jpg",
        "tagline": "15년을 한 클럽에서. 주장 완장의 기준이 된 수비수.",
        "career": [
            ("1999", "1군 데뷔", "라 마시아 출신 수비수로 자리 잡았다."),
            ("2004", "주장", "이후 10년간 완장을 달았다."),
            ("2009", "6관왕", "과르디올라 체제 수비의 축."),
            ("2010", "월드컵 4강 결승골", "독일전 헤더로 스페인을 결승에 올렸다."),
            ("2011", "웸블리", "네 번째 챔피언스리그 우승."),
            ("2014", "은퇴", "부상 누적으로 593경기를 남기고 은퇴."),
        ],
        "honors": "라리가 6회 · 챔피언스리그 3회 · 월드컵(2010)·유로(2008)",
    },
    {
        "key": "guardiola", "name": "펩 과르디올라", "full": "Josep Guardiola i Sala",
        "years": "1990–2001 (선수) · 2008–2012 (감독)", "pos": "수비형 미드필더 · 감독",
        "stats_name": "", "photo": "legends/guardiola.jpg",
        "tagline": "드림팀의 4번이었고, 훗날 6관왕의 감독이 됐다.",
        "career": [
            ("1990", "크루이프의 발탁", "유스에서 끌어올려 드림팀의 중심 수비형 미드필더로."),
            ("1992", "웸블리 우승", "20대 초반에 유러피언컵을 들었다."),
            ("2001", "이적", "브레시아로 떠나며 선수 생활 후반을 이탈리아에서."),
            ("2008", "1군 감독", "B팀에서 곧바로 1군으로. 첫 시즌 6관왕."),
            ("2009", "6관왕", "리그·코파·챔스·수페르코파·UEFA 슈퍼컵·클럽월드컵."),
            ("2012", "사임", "4년간 14개 트로피를 남기고 물러났다."),
        ],
        "honors": "선수: 라리가 6회 · 유러피언컵 1회 / 감독: 라리가 3회 · 챔피언스리그 2회",
    },
    {
        "key": "stoichkov", "name": "흐리스토 스토이치코프", "full": "Hristo Stoichkov",
        "years": "1990–1995 · 1996–1998", "pos": "좌측 윙어 · 포워드",
        "stats_name": "", "photo": "legends/stoichkov.jpg",
        "tagline": "드림팀의 화력. 성격도 슛도 거칠었다.",
        "career": [
            ("1990", "입단", "CSKA 소피아에서 합류해 드림팀 공격의 한 축이 됐다."),
            ("1991", "리그 4연패", "1991~94 라리가 4연속 우승의 주역."),
            ("1992", "웸블리", "유러피언컵 우승."),
            ("1994", "발롱도르", "월드컵 득점왕과 함께 그해 최고 선수로."),
            ("1996", "복귀", "파르마를 거쳐 잠시 돌아왔다."),
            ("1998", "고별", "두 차례에 걸쳐 총 8시즌을 뛰었다."),
        ],
        "honors": "발롱도르(1994) · 라리가 5회 · 유러피언컵 1회",
    },
    {
        "key": "suarez", "name": "루이스 수아레스 미라몬테스", "full": "Luis Suárez Miramontes",
        "years": "1954–1961", "pos": "인사이드 포워드 · 플레이메이커",
        "stats_name": "", "photo": "legends/suarez.jpg",
        "tagline": "스페인 태생 선수 중 유일한 발롱도르 수상자.",
        "career": [
            ("1954", "입단", "라 코루냐 출신으로 바르사에 합류."),
            ("1959", "리그·코파 더블", "엘레니오 에레라 체제에서 팀을 이끌었다."),
            ("1960", "발롱도르", "스페인에서 태어난 선수로는 지금까지 유일한 수상."),
            ("1960", "인터시티스 페어스컵", "유럽 대회 우승에 기여."),
            ("1961", "인테르 이적", "당시 최고 이적료로 밀라노행."),
            ("2023", "타계", "88세로 세상을 떠났다."),
        ],
        "honors": "발롱도르(1960) · 라리가 2회 · 페어스컵 2회",
    },
]

BY_KEY = {x["key"]: x for x in LEGENDS}


def legend_credits() -> dict:
    return load_json(ASSETS / "legends" / "credits.json")


# ---------------------------------------------------------------- 히어로
st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">Llegendes del Barça</div>
  <h1>레전드 TOP 10</h1>
  <div class="hero-motto">쿠발라부터 메시까지. 카드를 고르면 경력 연혁과
  이벤트 데이터 기반 스탯이 아래에 펼쳐진다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if "legend" not in st.session_state:
    st.session_state.legend = LEGENDS[0]["key"]

# ---------------------------------------------------------------- 카드 그리드
st.markdown('<div class="section">인물을 고르세요</div>', unsafe_allow_html=True)
for row in (LEGENDS[:5], LEGENDS[5:]):
    cols = st.columns(5, gap="small")
    for col, lg in zip(cols, row):
        with col:
            src = b64(lg["photo"])
            selected = "legend-card-on" if st.session_state.legend == lg["key"] else ""
            img = (f'<img src="{src}" alt="{lg["name"]}">' if src
                   else '<div class="legend-noimg">사진 없음</div>')
            st.markdown(f"""
<div class="legend-card {selected}">{img}
  <div class="legend-cap"><b>{lg["name"]}</b><span>{lg["years"].split(" ")[0]}</span></div>
</div>""", unsafe_allow_html=True)
            # 라벨에 이름을 또 넣으면 카드와 중복돼 지저분하다. 위치로 대상이 분명하다.
            label = "선택됨" if st.session_state.legend == lg["key"] else "자세히"
            if st.button(label, key=f"btn_{lg['key']}", use_container_width=True,
                         disabled=st.session_state.legend == lg["key"]):
                st.session_state.legend = lg["key"]
                st.rerun()

# ---------------------------------------------------------------- 상세
lg = BY_KEY[st.session_state.legend]
st.markdown(f'<div class="section">{lg["name"]} · {lg["years"]}</div>', unsafe_allow_html=True)

c1, c2 = st.columns([1, 2.3], gap="medium")
with c1:
    src = b64(lg["photo"])
    if src:
        st.markdown(f'<div class="legend-hero"><img src="{src}" alt="{lg["name"]}"></div>',
                    unsafe_allow_html=True)
with c2:
    st.markdown(f"""
<div class="legend-bio">
  <div class="legend-full">{lg["full"]}</div>
  <div class="legend-pos">{lg["pos"]}</div>
  <div class="legend-tag">{lg["tagline"]}</div>
  <div class="legend-honors"><span>주요 이력</span>{lg["honors"]}</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- 연혁
st.markdown('<div class="section">연혁</div>', unsafe_allow_html=True)
cards = "".join(
    f'<div class="timeline-card"><div class="timeline-year">{y}</div>'
    f'<div class="timeline-title">{t}</div><div class="timeline-body">{b}</div></div>'
    for y, t, b in lg["career"]
)
st.markdown(f'<div class="timeline-grid">{cards}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- 스탯
st.markdown('<div class="section">이벤트 데이터 기반 스탯</div>', unsafe_allow_html=True)
pm = load_sb("player_match")

if not lg["stats_name"]:
    st.info(f"{lg['name']}은 StatsBomb 공개 범위(2004/05~2020/21) 밖에서 뛰었습니다. "
            "이 선수의 수치는 원본에 없어 표시하지 않습니다.")
elif pm.empty:
    st.warning("StatsBomb 데이터가 아직 없습니다. `python fetch_statsbomb.py`를 먼저 실행하세요.")
else:
    mine = pm[(pm["player"] == lg["stats_name"]) & (pm["team"] == "Barcelona")]
    if mine.empty:
        st.info(f"공개된 경기에서 {lg['name']}의 기록을 찾지 못했습니다.")
    else:
        pass_pct = mine["passes_completed"].sum() / max(mine["passes"].sum(), 1) * 100
        st.markdown(metric_cards([
            ("기록된 경기", f"{len(mine):,}", f"{mine['season'].nunique()}시즌"),
            ("골", f"{int(mine['goals'].sum()):,}", f"경기당 {mine['goals'].mean():.2f}"),
            ("누적 xG", f"{mine['xg'].sum():.1f}", f"슛 {int(mine['shots'].sum()):,}회"),
            ("패스 성공률", f"{pass_pct:.1f}%", f"패스 {int(mine['passes'].sum()):,}회"),
            ("드리블 성공", f"{int(mine['dribbles'].sum()):,}", f"경기당 {mine['dribbles'].mean():.1f}"),
            ("전진 운반", f"{int(mine['carries'].sum()):,}", "캐리 이벤트 수"),
            ("태클", f"{int(mine['tackles'].sum()):,}", f"인터셉트 {int(mine['interceptions'].sum()):,}"),
            ("압박", f"{int(mine['pressures'].sum()):,}", f"경기당 {mine['pressures'].mean():.1f}"),
        ]), unsafe_allow_html=True)

        by_season = (mine.groupby("season")
                     .agg(경기=("match_id", "nunique"), 골=("goals", "sum"),
                          xG=("xg", "sum"), 패스=("passes", "sum"))
                     .reset_index())
        f1 = go.Figure()
        f1.add_trace(go.Bar(x=by_season["season"], y=by_season["골"], name="골",
                            marker_color=GRANA))
        f1.add_trace(go.Scatter(x=by_season["season"], y=by_season["xG"], name="xG",
                                mode="lines+markers", line=dict(color=GOLD, width=2.4)))
        f1.update_layout(height=320, yaxis_title="골 / xG",
                         legend=dict(orientation="h", y=1.12), **PLOT)
        f1.update_xaxes(gridcolor=GRID, tickangle=-45)
        f1.update_yaxes(gridcolor=GRID)
        st.plotly_chart(f1, use_container_width=True)
        st.caption("StatsBomb 공개 경기만 집계한 값이라 실제 통산 기록과 다르다. "
                   "시즌마다 공개된 경기 수가 달라 시즌 간 직접 비교도 조심해야 한다.")

# ---------------------------------------------------------------- 출처
cred = legend_credits()
lines = "".join(
    f"· {BY_KEY[k]['name']} — {v['artist']} / {v['license']} (Wikimedia Commons)<br>"
    for k, v in cred.items() if k in BY_KEY
)
st.markdown(f"""
<div class="credits">
<b>선정 기준</b> 클럽 기여도·상징성·수상 이력을 함께 본 편집 판단이며, 데이터로
산출한 순위가 아니다.<br>
<b>연혁</b> 위키백과 각 선수 문서를 확인해 정리했다.<br>
<b>스탯</b> StatsBomb Open Data 2004/05~2020/21 공개 경기 한정.
그 이전 선수는 원본이 없어 수치를 붙이지 않았다.<br>
<b>이미지</b> 사진 출처:<br>{lines}
</div>
""", unsafe_allow_html=True)
