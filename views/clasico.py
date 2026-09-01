"""엘클라시코 — 레알 마드리드와의 리그 맞대결 전용 페이지."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (ASSETS, GOLD, GRANA, GRID, PLOT, WHITE, b64, credits_block,
                  load_clasico, load_credits, load_json, load_seasons,
                  metric_cards, setup)

seasons = load_seasons()
credits = load_credits()
setup(seasons)

cl = load_clasico()
W = int((cl["result"] == "승").sum())
D = int((cl["result"] == "무").sum())
L = int((cl["result"] == "패").sum())
home, away = cl[cl["venue"] == "홈"], cl[cl["venue"] == "원정"]
biggest = cl.loc[cl["gd"].idxmax()]
worst = cl.loc[cl["gd"].idxmin()]

RES_COLOR = {"승": GRANA, "무": "#6b7d99", "패": WHITE}
CLS = {"승": "fc-w", "무": "fc-d", "패": "fc-l"}

CLASICO_NOTE = (" 엘클라시코는 리그 맞대결만 집계하며, 컵대회·챔피언스리그 맞대결과 "
                "원본 파일이 잘려 있는 2004/05 두 경기는 빠져 있음.")


def longest_run(mask: pd.Series) -> tuple[int, int, int]:
    """연속 True의 최대 길이와 시작·끝 인덱스."""
    best = cur = start = 0
    bs = be = 0
    for i, v in enumerate(mask.tolist()):
        if not v:
            cur = 0
            continue
        if cur == 0:
            start = i
        cur += 1
        if cur > best:
            best, bs, be = cur, start, i
    return best, bs, be


# ---------------------------------------------------------------- 히어로
st.markdown(f"""
<div class="hero hero-clasico">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">El Clàssic · La Liga</div>
  <div class="hero-vs">
    <span class="vs-side">FC BARCELONA</span>
    <span class="vs-mark">VS</span>
    <span class="vs-side">REAL MADRID</span>
  </div>
  <div class="hero-motto">스페인 축구를 둘로 가른 {cl['Season'].nunique()}시즌 {len(cl)}경기.
  바르사 기준 {W}승 {D}무 {L}패.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- 역사
st.markdown('<div class="section">왜 이 경기가 특별한가</div>', unsafe_allow_html=True)
st.markdown("""
<div class="lede">
두 클럽이 처음 만난 것은 <b>1902년 5월 13일</b>, 코파 데 라 코로나시온 준결승이었다.
바르사가 3-1로 이겼다. 이때만 해도 그저 한 경기였지만, 20세기 스페인의 정치가
이 대결에 다른 무게를 실었다. 바르셀로나는 마드리드의 중앙집권에 맞선
<b>카탈루냐 정체성의 상징</b>이 됐고, 레알 마드리드는 스페인 단일 국가를 대표하는
쪽에 놓였다. 경기장에서 벌어지는 90분이 그대로 두 지역의 대리전으로 읽힌 것이다.<br><br>

<b>프랑코 독재기</b>(1936~1975)에 이 구도는 훨씬 날카로워졌다. 1936년 바르사 회장
<b>조셉 수뇰</b>이 프랑코군에게 총살당했다. 카탈루냐어와 카탈루냐 깃발이 금지된
시기에 캄 노우는 카탈루냐 사람들이 모국어로 목소리를 낼 수 있는 몇 안 되는
공간이었고, 그래서 레알전은 단순한 축구가 아니었다.<br><br>

경기 외적인 사건들이 감정을 더 키웠다. 1953년 <b>알프레도 디 스테파노</b>의 이적을
두고 두 클럽이 정면충돌했고, 결국 그는 마드리드로 가 레알의 유럽 제패를 이끌었다.
2000년에는 바르사 주장이던 <b>루이스 피구</b>가 레알로 넘어갔다. 2002년 캄 노우에
돌아온 그에게 관중석에서 <b>돼지머리</b>가 날아든 장면은 지금도 이 라이벌리를
설명하는 사진으로 쓰인다.
</div>
""", unsafe_allow_html=True)

history = [
    ("1902", "첫 맞대결", "5월 13일 코파 데 라 코로나시온 준결승. 바르사 3-1 승리."),
    ("1936", "조셉 수뇰 피살", "바르사 회장이 프랑코군에 총살됐다. 클럽이 정치의 한복판에 놓인 순간."),
    ("1943", "논란의 11-1", "코파 델 헤네랄리시모 준결승. 1차전 바르사 3-0 뒤 2차전 11-1 패배. "
                          "원정 응원 금지와 위협이 있었다는 증언이 남아 있다."),
    ("1953", "디 스테파노 분쟁", "양 클럽이 영입권을 두고 충돌했고 그는 레알로 갔다. "
                             "이후 레알이 유러피언컵 5연패를 이룬다."),
    ("1974", "베르나베우 0-5", "크루이프의 데뷔 시즌. 적지에서 5골을 넣고 14년 만에 리그를 되찾았다."),
    ("2000", "피구의 이적", "주장이 레알로. 2002년 캄 노우 복귀전에서 돼지머리가 날아들었다."),
]
cards = "".join(
    f'<div class="timeline-card"><div class="timeline-year">{y}</div>'
    f'<div class="timeline-title">{t}</div><div class="timeline-body">{b}</div></div>'
    for y, t, b in history
)
st.markdown(f'<div class="timeline-grid">{cards}</div>', unsafe_allow_html=True)
st.caption("연표는 위키백과 El Clásico 문서를 확인해 정리했다. "
           "아래 수치는 모두 1993/94 이후 리그 경기 원본에서 직접 집계한 값이다.")

# ---------------------------------------------------------------- 갤러리
GALLERY = [
    ("coronacion", "코파 데 라 코로나시온",
     "1902년 첫 맞대결이 열린 대회의 우승컵. 바르사가 준결승에서 마드리드를 3-1로 꺾었다."),
    ("sunyol", "조셉 수뇰 추모",
     "1936년 프랑코군에 총살당한 바르사 회장. 생전 사진이 공개 라이선스로 없어 "
     "바르셀로나에 세워진 추모 기념물로 대신한다."),
    ("franco", "프란시스코 프랑코",
     "1936~75년 독재기. 카탈루냐어와 깃발이 금지되면서 캄 노우의 의미가 달라졌다."),
    ("di_stefano", "알프레도 디 스테파노",
     "1953년 영입 분쟁 끝에 레알로. 이후 레알의 유러피언컵 5연패를 이끌었다."),
    ("figo", "피구의 캄 노우 복귀전",
     "2002년 11월 23일. 코너킥을 차러 간 피구 주위로 관중석에서 물건이 쏟아졌고, "
     "그중 돼지머리가 있었다. 경기는 10여 분간 중단됐다."),
    ("bernabeu", "산티아고 베르나베우",
     "레알의 홈. 1974년 크루이프의 0-5, 2009년 2-6이 이곳에서 나왔다."),
]
shots_html = "".join(
    f'<figure><img src="{b64("clasico/" + k + ".jpg")}" alt="{t}">'
    f'<figcaption><b>{t}</b><span>{d}</span></figcaption></figure>'
    for k, t, d in GALLERY if b64("clasico/" + k + ".jpg")
)
if shots_html:
    st.markdown('<div class="section">갤러리</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="gallery">{shots_html}</div>', unsafe_allow_html=True)
    gc = load_json(ASSETS / "clasico" / "credits.json")
    names = {k: t for k, t, _ in GALLERY}
    st.caption("사진 출처 — " + " · ".join(
        f"{names[k]}: {v['artist']} / {v['license']}" for k, v in gc.items() if k in names))

# ---------------------------------------------------------------- 총평
st.markdown('<div class="section">통산 상대전적</div>', unsafe_allow_html=True)
st.markdown(metric_cards([
    ("맞대결", f"{len(cl)}경기", f"{cl['Season'].nunique()}시즌 · 리그 한정"),
    ("전적", f"{W}-{D}-{L}", f"승률 {W / len(cl) * 100:.0f}% · 무패율 {(W + D) / len(cl) * 100:.0f}%"),
    ("득실", f"{int(cl['gf'].sum())}-{int(cl['ga'].sum())}",
     f"경기당 {cl['gf'].mean():.2f} : {cl['ga'].mean():.2f}"),
    ("홈 / 원정 승리", f"{int((home['result'] == '승').sum())} / {int((away['result'] == '승').sum())}",
     f"각 {len(home)}경기 · 캄 노우에서 더 강했다"),
]), unsafe_allow_html=True)

pw, pd_, pl = (x / len(cl) * 100 for x in (W, D, L))
st.markdown(f"""
<div class="h2h-bar">
  <div class="h2h-seg h2h-w" style="width:{pw:.1f}%">{W}승</div>
  <div class="h2h-seg h2h-d" style="width:{pd_:.1f}%">{D}무</div>
  <div class="h2h-seg h2h-l" style="width:{pl:.1f}%">{L}패</div>
</div>
<div class="h2h-legend"><span>그라나 = 바르사 승</span><span>회색 = 무승부</span>
<span>흰색 = 레알 승</span></div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- 명경기
st.markdown('<div class="section">기억되는 클라시코</div>', unsafe_allow_html=True)
top_wins = cl.nlargest(3, "gd")
top_losses = cl.nsmallest(3, "gd")
famous = pd.concat([top_wins, top_losses]).sort_values("date")
cards = "".join(
    f'<div class="timeline-card {"tl-win" if r.gd > 0 else "tl-loss"}">'
    f'<div class="timeline-year">{r.Season} · {r.venue}</div>'
    f'<div class="timeline-score">{r.score}</div>'
    f'<div class="timeline-body">{r.date.strftime("%Y년 %m월 %d일")} · '
    f'{"바르사" if r.gd > 0 else "레알"} {abs(int(r.gd))}골 차 승</div></div>'
    for r in famous.itertuples()
)
st.markdown(f'<div class="timeline-grid">{cards}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- 흐름
st.markdown('<div class="section">경기별 골 득실차 (오래된 순)</div>', unsafe_allow_html=True)
f1 = go.Figure(go.Bar(
    x=cl["date"], y=cl["gd"],
    marker_color=[RES_COLOR[r] for r in cl["result"]],
    customdata=cl[["Season", "venue", "score", "result"]].values,
    hovertemplate="<b>%{customdata[0]} %{customdata[1]}</b><br>"
                  "%{customdata[2]} %{customdata[3]}<extra></extra>"))
f1.update_layout(height=310, yaxis_title="골 득실차", showlegend=False, **PLOT)
f1.update_xaxes(gridcolor=GRID)
f1.update_yaxes(gridcolor=GRID, zerolinecolor="#2b4a72")
st.plotly_chart(f1, width="stretch")

# ---------------------------------------------------------------- 시대별
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="section">10년 단위 전적</div>', unsafe_allow_html=True)
    dec = (cl.groupby("decade")["result"].value_counts().unstack(fill_value=0)
           .reindex(columns=["승", "무", "패"], fill_value=0)
           .reindex(["1990s", "2000s", "2010s", "2020s"], fill_value=0))
    f2 = go.Figure()
    for res in ("승", "무", "패"):
        f2.add_trace(go.Bar(x=dec.index, y=dec[res], name=res,
                            marker_color=RES_COLOR[res],
                            hovertemplate="<b>%{x}</b><br>" + res + " %{y}경기<extra></extra>"))
    f2.update_layout(height=300, barmode="stack", yaxis_title="경기 수",
                     legend=dict(orientation="h", y=1.14), **PLOT)
    f2.update_xaxes(gridcolor=GRID)
    f2.update_yaxes(gridcolor=GRID)
    st.plotly_chart(f2, width="stretch")
    st.caption(f"2020년대는 {int(dec.loc['2020s', '승'])}승 {int(dec.loc['2020s', '무'])}무 "
               f"{int(dec.loc['2020s', '패'])}패로 처음 열세다.")

with c2:
    st.markdown('<div class="section">스코어 빈도 상위 8</div>', unsafe_allow_html=True)
    sc = cl["score"].value_counts().head(8).iloc[::-1]
    colors = [GRANA if int(s.split("-")[0]) > int(s.split("-")[1])
              else (GOLD if s.split("-")[0] == s.split("-")[1] else WHITE) for s in sc.index]
    f3 = go.Figure(go.Bar(x=sc.values, y=sc.index, orientation="h", marker_color=colors,
                          text=sc.values, textposition="outside", textfont_color="#f2f6fc",
                          hovertemplate="<b>%{y}</b><br>%{x}경기<extra></extra>"))
    f3.update_layout(height=300, xaxis_title="경기 수", **PLOT)
    f3.update_xaxes(gridcolor=GRID, range=[0, int(sc.max()) + 2])
    f3.update_yaxes(gridcolor=GRID, type="category")
    st.plotly_chart(f3, width="stretch")
    st.caption("바르사 기준 스코어 (득점-실점)")

# ---------------------------------------------------------------- 기록
st.markdown('<div class="section">연속 기록과 경기 성향</div>', unsafe_allow_html=True)
n_unb, a_unb, b_unb = longest_run(cl["result"] != "패")
n_win, a_win, b_win = longest_run(cl["result"] == "승")
n_los, a_los, b_los = longest_run(cl["result"] == "패")
total_goals = int((cl["gf"] + cl["ga"]).sum())
st.markdown(metric_cards([
    ("최장 무패", f"{n_unb}경기", f"{cl.loc[a_unb, 'Season']} ~ {cl.loc[b_unb, 'Season']}"),
    ("최장 연승", f"{n_win}경기", f"{cl.loc[a_win, 'Season']} ~ {cl.loc[b_win, 'Season']}"),
    ("최장 연패", f"{n_los}경기", f"{cl.loc[a_los, 'Season']} ~ {cl.loc[b_los, 'Season']}"),
    ("경기당 총 골", f"{total_goals / len(cl):.2f}", f"통산 {total_goals}골 · 난타전이 잦다"),
    ("무실점 승부", f"{int((cl['ga'] == 0).sum())}경기", f"무득점 {int((cl['gf'] == 0).sum())}경기"),
    ("양 팀 득점", f"{int(((cl['gf'] > 0) & (cl['ga'] > 0)).sum())}경기",
     f"전체의 {((cl['gf'] > 0) & (cl['ga'] > 0)).mean() * 100:.0f}%"),
    ("3골 차 이상", f"{int((cl['gd'].abs() >= 3).sum())}경기", "일방적으로 끝난 경기"),
    ("최다 점수차", f"{int(cl['gd'].abs().max())}골",
     f"{biggest['Season']} {biggest['score']} · {worst['Season']} {worst['score']}"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------- 최근
st.markdown('<div class="section">최근 10경기</div>', unsafe_allow_html=True)
chips = "".join(
    f'<div class="form-chip"><div class="fc-res {CLS[r.result]}">{r.result}</div>'
    f'<div class="fc-score">{r.score}</div>'
    f'<div class="fc-meta">{r.Season} {r.venue}</div></div>'
    for r in cl.tail(10).itertuples()
)
st.markdown(f'<div class="form-strip">{chips}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- 탐색
st.markdown('<div class="section">경기 찾아보기</div>', unsafe_allow_html=True)
f1c, f2c, f3c = st.columns(3)
venue = f1c.selectbox("장소", ["전체", "홈", "원정"])
res = f2c.selectbox("결과", ["전체", "승", "무", "패"])
decs = f3c.multiselect("연대", ["1990s", "2000s", "2010s", "2020s"], default=[])

view = cl.copy()
if venue != "전체":
    view = view[view["venue"] == venue]
if res != "전체":
    view = view[view["result"] == res]
if decs:
    view = view[view["decade"].isin(decs)]

if view.empty:
    st.info("조건에 맞는 경기가 없습니다.")
else:
    vw = int((view["result"] == "승").sum())
    vd = int((view["result"] == "무").sum())
    vl = int((view["result"] == "패").sum())
    st.caption(f"{len(view)}경기 · {vw}승 {vd}무 {vl}패 · "
               f"{int(view['gf'].sum())}득 {int(view['ga'].sum())}실")
    tb = view[["Season", "date", "venue", "score", "result", "gd"]].copy()
    tb["date"] = tb["date"].dt.strftime("%Y-%m-%d")
    tb.columns = ["시즌", "날짜", "장소", "스코어", "결과", "득실차"]
    st.dataframe(tb.set_index("날짜"), width="stretch", height=380)

st.markdown(credits_block(seasons, credits, CLASICO_NOTE), unsafe_allow_html=True)
