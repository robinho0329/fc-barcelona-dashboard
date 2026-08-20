"""역대 감독 — 카드를 고르면 재임 기간의 라리가 성적이 펼쳐진다."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pathlib import Path

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, PROCESSED, b64, load_dir,
                  load_parquet, load_sb, load_seasons, load_understat,
                  metric_cards, setup)

seasons = load_seasons()
setup(seasons)


def load_matches() -> pd.DataFrame:
    """바르사 기준 득실·승패로 정규화한 경기 목록."""
    m = load_parquet(PROCESSED / "club_matches.parquet").copy()
    m["date"] = pd.to_datetime(m["Date"], format="mixed", dayfirst=True)
    home = m["HomeTeam"] == "Barcelona"
    m["gf"] = m["FTHG"].where(home, m["FTAG"]).astype(int)
    m["ga"] = m["FTAG"].where(home, m["FTHG"]).astype(int)
    m["venue"] = home.map({True: "홈", False: "원정"})
    m["opponent"] = m["AwayTeam"].where(home, m["HomeTeam"])
    m["gd"] = m["gf"] - m["ga"]
    m["result"] = m["gd"].apply(lambda d: "승" if d > 0 else ("무" if d == 0 else "패"))
    return m.sort_values("date").reset_index(drop=True)


mg = load_parquet(PROCESSED / "managers.parquet")

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">Entrenadors · 1993/94 – {seasons['Season'].iloc[-1]}</div>
  <h1>역대 감독</h1>
  <div class="hero-motto">33시즌을 이끈 감독들. 카드를 고르면 그가 지휘한
  라리가 경기만 따로 집계해 보여준다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if mg.empty:
    st.warning("감독 데이터가 없습니다. `python crawl_managers.py` 후 "
               "`python build_managers.py`를 실행하세요.")
    st.stop()

matches = load_matches()
mg = mg.sort_values("start").reset_index(drop=True)

# ---------------------------------------------------------------- 총괄
st.markdown('<div class="section">33시즌 요약</div>', unsafe_allow_html=True)
regular = mg[mg["role"] == "정식"]
enough = regular[regular["경기"] >= 30]
best = enough.loc[enough["경기당승점"].idxmax()]
longest = mg.loc[mg["경기"].idxmax()]
st.markdown(metric_cards([
    ("감독", f"{mg['tm_id'].nunique()}명", f"재임 {len(mg)}회 · 임시 {int((mg['role'] == '임시').sum())}회"),
    ("최장수", f"{int(longest['경기'])}경기", f"{longest['표시명']}"),
    ("최고 승점률", f"{best['경기당승점']:.2f}", f"{best['표시명']} · 30경기 이상"),
    ("최다 우승", f"{int(mg['우승'].max())}회", f"{mg.loc[mg['우승'].idxmax(), '표시명']}"),
]), unsafe_allow_html=True)

# ---------------------------------------------------------------- 카드
if "manager" not in st.session_state:
    st.session_state.manager = int(mg["경기"].idxmax())


def initials(name: str) -> str:
    parts = [p for p in name.split() if p and p[0].isalpha()]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


st.markdown('<div class="section">감독을 고르세요</div>', unsafe_allow_html=True)
PER_ROW = 6
for start in range(0, len(mg), PER_ROW):
    chunk = mg.iloc[start:start + PER_ROW]
    cols = st.columns(PER_ROW, gap="small")
    for col, (idx, r) in zip(cols, chunk.iterrows()):
        with col:
            src = b64(f"managers/{r['file']}") if r["file"] else ""
            sel = "legend-card-on" if st.session_state.manager == idx else ""
            img = (f'<img src="{src}" alt="{r["name"]}">' if src
                   else f'<div class="legend-noimg mg-initial">{initials(r["name"])}</div>')
            tag = ' · 임시' if r["role"] == "임시" else ""
            st.markdown(f"""
<div class="legend-card mg-card {sel}">{img}
  <div class="legend-cap"><b>{r['name']}</b>
  <span>{r['첫시즌'][:4]}~{r['끝시즌'][:4]}{tag}</span></div>
</div>""", unsafe_allow_html=True)
            label = "선택됨" if st.session_state.manager == idx else "자세히"
            if st.button(label, key=f"mg_{idx}", use_container_width=True,
                         disabled=st.session_state.manager == idx):
                st.session_state.manager = idx
                st.rerun()

# ---------------------------------------------------------------- 상세
r = mg.loc[st.session_state.manager]
part = matches[(matches["date"] >= r["start"]) & (matches["date"] <= r["end"])]

st.markdown(f'<div class="section">{r["표시명"]} · {r["첫시즌"]} ~ {r["끝시즌"]}</div>',
            unsafe_allow_html=True)
c1, c2 = st.columns([1, 2.3], gap="medium")
with c1:
    src = b64(f"managers/{r['file']}") if r["file"] else ""
    if src:
        st.markdown(f'<div class="legend-hero mg-hero"><img src="{src}" alt="{r["name"]}"></div>',
                    unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="legend-hero mg-hero-initial">{initials(r["name"])}</div>',
                    unsafe_allow_html=True)
with c2:
    span = f"{r['start'].strftime('%Y년 %m월 %d일')} ~ " + (
        "현재" if r["is_current"] else r["end"].strftime("%Y년 %m월 %d일"))
    st.markdown(f"""
<div class="legend-bio">
  <div class="legend-full">{r['name']}</div>
  <div class="legend-pos">{r['role']} 감독 · {r['시즌수']}시즌 · 재임 {r['days']:,}일</div>
  <div class="legend-tag">{span}</div>
  <div class="legend-honors"><span>라리가 성적</span>
  {int(r['경기'])}경기 {int(r['승'])}승 {int(r['무'])}무 {int(r['패'])}패 ·
  승점 {int(r['승점'])} · 경기당 {r['경기당승점']:.2f} ·
  리그 우승 {int(r['우승'])}회</div>
</div>
""", unsafe_allow_html=True)

# 감독 한 줄 평. 수치가 말해주지 않는 맥락(무엇을 물려받아 무엇을 남겼나)을
# 채운다. 성적 수치는 아래 카드가 데이터로 보여주므로 여기서는 반복하지 않는다.
NOTES = {
    "Johan Cruyff": "드림팀의 마지막 3년. 리그 4연패의 뒷부분을 지켰지만 "
                    "세대 교체에 실패하며 저물었다. 성적보다 남긴 축구 철학과 "
                    "라 마시아 체계가 클럽의 다음 30년을 만들었다.",
    "Sir Bobby Robson": "한 시즌만에 떠났지만 경기당 2.14점으로 크루이프보다 높았다. "
                        "호나우두를 데려왔고, 통역으로 데리고 온 조수가 무리뉴였다. "
                        "리그는 레알에 내줬다.",
    "Louis van Gaal (1기)": "부임 두 시즌 연속 리그 우승. 네덜란드 색채를 강하게 "
                           "입혔지만 언론·여론과 계속 부딪혔고, 세 번째 시즌 "
                           "성적이 꺾이며 물러났다.",
    "Lorenzo Serra Ferrer": "시즌을 끝내지 못하고 4월에 경질됐다. 경기당 1.65점은 "
                           "이 33시즌에서 최하위권이다. 클럽이 방향을 잃은 시기의 "
                           "한복판에 있었다.",
    "Carles Rexach": "세라 페레르 뒤를 급히 이어받아 4위로 챔피언스리그 진출권을 "
                     "지켰다. 크루이프의 수석코치 출신이지만 지휘봉을 잡은 성적은 "
                     "평범했다. 메시를 냅킨에 계약한 인물로 더 유명하다.",
    "Louis van Gaal (2기)": "두 번째 부임은 반 시즌 만에 끝났다. 경기당 1.21점은 "
                           "33시즌 통틀어 최저다. 클럽 역사상 가장 낮은 지점.",
    "Radomir Antić": "무너진 시즌을 넘겨받아 경기당 1.83점으로 수습했다. "
                     "임시 지휘봉치고는 반등 폭이 컸지만 시즌 종료와 함께 떠났다.",
    "Frank Rijkaard": "부임 첫해는 흔들렸으나 호나우지뉴를 축으로 팀을 다시 세웠다. "
                      "리그 2연패와 2006년 유럽 정상. 마지막 두 시즌은 기강이 풀리며 "
                      "무관으로 끝났고, 그 자리를 B팀 감독이 물려받았다.",
    "Pep Guardiola": "경기당 2.45점, 이 33시즌 최고 수치다. 부임 첫해 6관왕은 "
                     "축구사에서 전례가 없다. 크루이프가 심은 것을 가장 완성된 형태로 "
                     "꺼내 보인 4년이었다.",
    "Tito Vilanova": "단 한 시즌, 경기당 2.63점으로 승점 100을 찍었다. 이 표에서 "
                     "가장 높은 숫자다. 투병으로 그 한 시즌이 전부가 됐다.",
    "Tata Martino": "승점 87로 나쁘지 않았지만 마지막 라운드에서 리그를 놓쳤다. "
                    "바르사의 축구와 결이 다르다는 평이 따라다녔고 한 시즌으로 끝났다.",
    "Luis Enrique": "부임 첫해 트레블. MSN 삼각편대를 앞세워 경기당 2.41점을 "
                    "3년간 유지했다. 과르디올라 이후 가장 성공한 감독으로 남았다.",
    "Ernesto Valverde": "리그 2연패에 경기당 2.32점. 국내 성적만 보면 훌륭했다. "
                        "다만 로마·리버풀에서의 유럽 붕괴가 모든 평가를 덮었다.",
    "Quique Setién": "코로나로 끊긴 시즌을 넘겨받아 리그를 내주고, 뮌헨전 2-8로 "
                     "끝났다. 반년 만에 경질됐다.",
    "Ronald Koeman": "재정 붕괴와 메시 이적을 정면으로 맞은 시기. 경기당 1.96점은 "
                     "이 시대 클럽 상황을 그대로 보여주는 숫자다. 코파 우승이 위안.",
    "Sergi Barjuan": "쿠만 경질과 차비 부임 사이 열흘. 2경기 모두 무승부로 "
                     "자리를 지키고 넘겼다.",
    "Xavi": "재정난 속에서 경기당 2.23점으로 팀을 다시 세우고 2022/23 리그를 "
            "되찾았다. 선수 시절의 상징성이 감독으로서는 부담으로도 작용했다.",
    "Hansi Flick": "부임과 함께 수비 라인을 끌어올리며 경기당 2.40점. 첫 두 시즌 "
                   "연속 리그 우승으로 과르디올라 이후 가장 빠른 출발을 했다.",
}
# 두 번 부임한 감독은 표시명에 "(1기)"가 붙는다. 표시명 → 이름 순으로 찾는다.
note = NOTES.get(r["표시명"]) or NOTES.get(r["name"])
if note:
    st.markdown(f'<div class="mg-note">{note}</div>', unsafe_allow_html=True)

st.markdown(metric_cards([
    ("경기", f"{int(r['경기'])}", f"{r['시즌수']}시즌"),
    ("승률", f"{r['승률']:.1f}%", f"{int(r['승'])}승 {int(r['무'])}무 {int(r['패'])}패"),
    ("경기당 승점", f"{r['경기당승점']:.2f}", f"승점 {int(r['승점'])}"),
    ("리그 우승", f"{int(r['우승'])}회", "재임 중 종료 시즌 기준"),
    ("득실", f"{int(r['득점'])}-{int(r['실점'])}",
     f"경기당 {r['득점'] / r['경기']:.2f} : {r['실점'] / r['경기']:.2f}"),
    ("홈 승률", f"{(part[part['venue'] == '홈']['result'] == '승').mean() * 100:.0f}%",
     f"{len(part[part['venue'] == '홈'])}경기"),
    ("원정 승률", f"{(part[part['venue'] == '원정']['result'] == '승').mean() * 100:.0f}%",
     f"{len(part[part['venue'] == '원정'])}경기"),
    ("무실점", f"{int((part['ga'] == 0).sum())}경기",
     f"전체의 {(part['ga'] == 0).mean() * 100:.0f}%"),
]), unsafe_allow_html=True)

# 재임 중 시즌별 성적
by_season = (part.groupby("Season")
             .agg(경기=("result", "size"),
                  승=("result", lambda s: (s == "승").sum()),
                  무=("result", lambda s: (s == "무").sum()),
                  패=("result", lambda s: (s == "패").sum()),
                  득점=("gf", "sum"), 실점=("ga", "sum"))
             .reset_index())
by_season["승점"] = by_season["승"] * 3 + by_season["무"]
by_season["경기당승점"] = (by_season["승점"] / by_season["경기"]).round(2)

if len(by_season) > 1:
    st.markdown('<div class="section">재임 중 시즌별 경기당 승점</div>', unsafe_allow_html=True)
    f1 = go.Figure(go.Bar(
        x=by_season["Season"], y=by_season["경기당승점"], marker_color=GRANA,
        text=by_season["경기당승점"], textposition="outside", textfont_color="#f2f6fc",
        customdata=by_season[["경기", "승", "무", "패"]].values,
        hovertemplate="<b>%{x}</b><br>경기당 %{y:.2f}점<br>"
                      "%{customdata[0]}경기 %{customdata[1]}승 %{customdata[2]}무 "
                      "%{customdata[3]}패<extra></extra>"))
    f1.update_layout(height=320, yaxis_title="경기당 승점", **PLOT)
    f1.update_xaxes(gridcolor=GRID)
    f1.update_yaxes(gridcolor=GRID, range=[0, 3.1])
    st.plotly_chart(f1, use_container_width=True)

# 상대별 성적
st.markdown('<div class="section">상대별 성적 (최다 맞대결 10팀)</div>', unsafe_allow_html=True)
opp = (part.groupby("opponent")
       .agg(경기=("result", "size"),
            승=("result", lambda s: (s == "승").sum()),
            무=("result", lambda s: (s == "무").sum()),
            패=("result", lambda s: (s == "패").sum()))
       .nlargest(10, "경기").iloc[::-1])
f2 = go.Figure()
for col, color in [("승", GRANA), ("무", "#6b7d99"), ("패", "#c9d3e0")]:
    f2.add_trace(go.Bar(y=opp.index, x=opp[col], orientation="h", name=col,
                        marker_color=color))
f2.update_layout(height=380, barmode="stack", xaxis_title="경기 수",
                 legend=dict(orientation="h", y=1.1), **PLOT)
f2.update_xaxes(gridcolor=GRID)
f2.update_yaxes(gridcolor=GRID, type="category")
st.plotly_chart(f2, use_container_width=True)

# ---------------------------------------------------------------- 전술 성향
# 네 소스를 재임 **날짜** 구간으로 잘라 감독별 성향을 만든다. 시즌으로 자르면
# 세티엔처럼 시즌 중간에 부임한 감독이 앞사람 몫까지 가져간다.
#   football-data (2005/06~)         슛·코너·파울·경고
#   StatsBomb    (2003/04~2020/21)   패스량·성공률·짧은 패스 — 티키타카 지수와 같은 정의
#   FBref 전 대회 (2014/15~)          점유율
#   Understat    (2014/15~)          슛당 xG, xG 대비 골, 연계 분산도
SHORT_PASS = 15
GAME_COLS = {"슛": ("HS", "AS"), "유효슛": ("HST", "AST"), "코너": ("HC", "AC"),
             "파울": ("HF", "AF"), "경고": ("HY", "AY")}


@st.cache_data
def style_table(stamp: str) -> pd.DataFrame:
    mgr = load_parquet(PROCESSED / "managers.parquet")
    if mgr.empty:
        return pd.DataFrame()

    # 1) 경기 지표
    m = load_parquet(PROCESSED / "club_matches.parquet").copy()
    m["date"] = pd.to_datetime(m["Date"], format="mixed", dayfirst=True)
    home = m["HomeTeam"] == "Barcelona"
    for name, (a, b) in GAME_COLS.items():
        if {a, b} <= set(m.columns):
            m[name] = pd.to_numeric(m[a].where(home, m[b]), errors="coerce")
            m["상대" + name] = pd.to_numeric(m[b].where(home, m[a]), errors="coerce")

    # 2) 패스 — 경기 날짜를 붙여야 재임 구간으로 자를 수 있다
    ps = load_sb("passes")
    sbm = load_sb("matches")
    if not ps.empty and not sbm.empty:
        ps = ps.merge(sbm[["match_id", "date"]], on="match_id", how="left")
        ps["date"] = pd.to_datetime(ps["date"])
        ps["short"] = ps["length"] < SHORT_PASS

    # 3) 점유율
    ac = load_dir("fbref_allcomps")
    if not ac.empty and "Poss" in ac.columns:
        ac = ac.assign(Poss=pd.to_numeric(ac["Poss"], errors="coerce"),
                       date=pd.to_datetime(ac["Date"], errors="coerce"))
        ac = ac.dropna(subset=["Poss", "date"])

    # 4) 슛·연계
    us = load_understat()
    us_b = (us.assign(date=pd.to_datetime(us["date"], errors="coerce"))
            .pipe(lambda d: d[d["is_barca"]]) if not us.empty else pd.DataFrame())

    rows = []
    for r in mgr.itertuples():
        lo, hi = r.start, r.end
        rec = {"감독": r.표시명, "구분": r.role}

        if "슛" in m.columns:
            part = m[(m["date"] >= lo) & (m["date"] <= hi)].dropna(subset=["슛"])
            if len(part) >= 20:
                rec.update({
                    "경기당 슛": part["슛"].mean(),
                    "유효슛률": part["유효슛"].sum() / max(part["슛"].sum(), 1) * 100,
                    "경기당 코너": part["코너"].mean(),
                    "경기당 파울": part["파울"].mean(),
                    "허용 슛": part["상대슛"].mean(),
                    "경기당 경고": part["경고"].mean(),
                })

        if not ps.empty:
            pp = ps[(ps["date"] >= lo) & (ps["date"] <= hi)]
            n_games = pp["match_id"].nunique()
            if n_games >= 10:
                rec.update({
                    "경기당 패스": len(pp) / n_games,
                    "패스 성공률": pp["complete"].mean() * 100,
                    "짧은 패스 비율": pp["short"].mean() * 100,
                })

        if not ac.empty:
            aa = ac[(ac["date"] >= lo) & (ac["date"] <= hi)]
            if len(aa) >= 15:
                rec["점유율"] = aa["Poss"].mean()

        if not us_b.empty:
            uu = us_b[(us_b["date"] >= lo) & (us_b["date"] <= hi)]
            if len(uu) >= 100:
                goals = uu[uu["goal"]]
                rec["슛당 xG"] = uu["xg"].mean()
                rec["xG 대비 골"] = len(goals) - uu["xg"].sum()
                asst = goals[goals["player_assisted"].notna()]
                if len(asst) >= 20:
                    people = pd.concat([asst["player_assisted"],
                                        asst["player_name"]]).value_counts()
                    share = people / people.sum()
                    rec["연계 분산도"] = (1 - (share ** 2).sum()) * 100
        rows.append(rec)

    return pd.DataFrame(rows)


def _stamp(*paths) -> str:
    """파일이 바뀌면 캐시를 다시 계산하도록 수정 시각을 모은다."""
    out = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            out += [f"{f.name}:{f.stat().st_mtime}" for f in sorted(p.glob("*.parquet"))]
        elif p.exists():
            out.append(f"{p.name}:{p.stat().st_mtime}")
    return "|".join(out)


style = style_table(_stamp(
    PROCESSED / "managers.parquet", PROCESSED / "club_matches.parquet",
    PROCESSED.parent / "statsbomb" / "passes.parquet",
    PROCESSED.parent / "understat" / "shots.parquet",
    PROCESSED.parent / "fbref_allcomps"))

if not style.empty:
    st.markdown('<div class="section">전술 성향</div>', unsafe_allow_html=True)
    st.markdown("""
<div class="lede">
전술 페이지들이 쓰는 지표를 감독 단위로 다시 잘랐다. 재임 <b>날짜</b> 구간으로
자르는데, 시즌 단위로 자르면 시즌 중간에 부임한 감독이 앞사람 몫까지 가져간다.<br><br>
소스마다 덮는 기간이 달라 <b>모든 감독에게 모든 지표가 있지는 않다</b>.
경기 지표는 2005/06부터, 패스는 2003/04~2020/21, 점유율·슛질·연계는 2014/15부터다.
값이 없는 감독은 그 지표에서 빠지고, 표본이 얇은 구간도 제외했다.
</div>
""", unsafe_allow_html=True)

    GROUPS = {
        "경기 지표 (2005/06~)": ["경기당 슛", "유효슛률", "경기당 코너",
                              "경기당 파울", "허용 슛", "경기당 경고"],
        "패스 (2003/04~2020/21)": ["경기당 패스", "패스 성공률", "짧은 패스 비율"],
        "점유 · 마무리 (2014/15~)": ["점유율", "슛당 xG", "xG 대비 골", "연계 분산도"],
    }
    HINT = {
        "허용 슛": "낮을수록 상대에게 기회를 덜 줬다",
        "경기당 파울": "낮을수록 덜 거칠게 싸웠다",
        "경기당 경고": "낮을수록 덜 거칠게 싸웠다",
        "짧은 패스 비율": "15야드 미만 패스의 비중 — 티키타카 지수와 같은 정의",
        "경기당 패스": "티키타카 지수의 첫 번째 축",
        "슛당 xG": "높을수록 좋은 자리에서 쐈다",
        "xG 대비 골": "양수면 기대치보다 많이 넣었다",
        "연계 분산도": "높을수록 골이 여러 선수에게 퍼졌다 — 연계 네트워크와 같은 정의",
        "점유율": "전 대회 평균",
    }
    LOWER_BETTER = {"허용 슛", "경기당 파울", "경기당 경고"}

    grp = st.selectbox("지표 묶음", list(GROUPS), key="style_group")
    avail = [c for c in GROUPS[grp] if c in style.columns and style[c].notna().any()]
    if not avail:
        st.info("이 묶음에 쓸 수 있는 데이터가 없습니다.")
    else:
        metric = st.selectbox("지표", avail, key="style_metric")
        lower = metric in LOWER_BETTER
        srt = style.dropna(subset=[metric]).sort_values(metric, ascending=lower)
        base = BLAU if lower else GRANA
        colors = [GOLD if n == r["표시명"] else base for n in srt["감독"]]

        fs = go.Figure(go.Bar(
            y=srt["감독"], x=srt[metric], orientation="h", marker_color=colors,
            text=srt[metric].round(2), textposition="outside",
            textfont_color="#f2f6fc",
            hovertemplate="<b>%{y}</b><br>" + metric + " %{x:.2f}<extra></extra>"))
        fs.update_layout(height=max(320, 36 * len(srt)), xaxis_title=metric, **PLOT)
        lo_x = min(0.0, float(srt[metric].min()) * 1.25)
        fs.update_xaxes(gridcolor=GRID,
                        range=[lo_x, float(srt[metric].max()) * 1.22],
                        zerolinecolor="#2b4a72")
        fs.update_yaxes(gridcolor=GRID, type="category")
        st.plotly_chart(fs, use_container_width=True)

        note = HINT.get(metric, "")
        st.caption(f"금색 = 지금 고른 감독 · 대상 {len(srt)}명"
                   + (f" · {note}" if note else "")
                   + (". 낮을수록 좋은 지표라 오름차순으로 놓았다." if lower else ""))

    with st.expander("전술 지표 표 (빈칸 = 그 시기에 원본이 없음)"):
        st.dataframe(style.set_index("감독").round(2),
                     use_container_width=True, height=420)

# ---------------------------------------------------------------- 전체 비교
st.markdown('<div class="section">감독 전체 비교</div>', unsafe_allow_html=True)
min_games = st.slider("최소 경기 수", 0, 100, 30, step=10)
comp = mg[mg["경기"] >= min_games].sort_values("경기당승점")
if comp.empty:
    st.info("조건에 맞는 감독이 없습니다.")
else:
    colors = [GOLD if i == st.session_state.manager else
              (GRANA if row["role"] == "정식" else "#6b7d99")
              for i, row in comp.iterrows()]
    f3 = go.Figure(go.Bar(
        y=comp["표시명"], x=comp["경기당승점"], orientation="h", marker_color=colors,
        text=comp["경기당승점"].round(2), textposition="outside", textfont_color="#f2f6fc",
        customdata=comp[["경기", "승", "무", "패", "우승"]].values,
        hovertemplate="<b>%{y}</b><br>경기당 %{x:.2f}점<br>"
                      "%{customdata[0]}경기 · %{customdata[1]}승 %{customdata[2]}무 "
                      "%{customdata[3]}패<br>리그 우승 %{customdata[4]}회<extra></extra>"))
    f3.update_layout(height=max(320, 30 * len(comp)), xaxis_title="경기당 승점", **PLOT)
    f3.update_xaxes(gridcolor=GRID, range=[0, 3.0])
    f3.update_yaxes(gridcolor=GRID, type="category")
    st.plotly_chart(f3, use_container_width=True)
    st.caption("금색 = 지금 고른 감독 · 회색 = 임시 감독")

with st.expander("감독 전체 기록 표"):
    tb = mg[["표시명", "role", "첫시즌", "끝시즌", "시즌수", "경기", "승", "무", "패",
             "득점", "실점", "승점", "승률", "경기당승점", "우승"]].copy()
    tb.columns = ["감독", "구분", "첫 시즌", "끝 시즌", "시즌", "경기", "승", "무", "패",
                  "득점", "실점", "승점", "승률", "경기당승점", "리그 우승"]
    st.dataframe(tb.set_index("감독"), use_container_width=True, height=430)

st.markdown("""
<div class="credits">
<b>명단·사진</b> Transfermarkt 감독 이력. 카를레스 레샥(2001/02)과
티토 빌라노바(2012/13)는 그 표에 행이 없어 직접 보충했고, 두 사람은 사진 대신
이니셜로 표시한다.<br>
<b>성적</b> Transfermarkt 표의 수치는 컵대회를 합친 값이라 쓰지 않았다.
football-data.co.uk 라리가 원본에서 경기 날짜를 재임 구간에 넣어 직접 집계했다.
따라서 리그 경기만 반영되며 컵대회·챔피언스리그 성적은 빠져 있다.<br>
<b>리그 우승</b> 그 시즌 경기의 3분의 2 이상을 지휘한 감독에게만 귀속시켰다.
순위는 승점 → 동률 팀 간 상대전적 → 골득실 순으로 산출한다.<br>
<b>임시 감독</b> 원본에 역할 구분이 없어, 시즌 중 급히 투입돼 짧게 지휘한
세르지 바르주안과 라도미르 안티치를 직접 표시했다.<br>
<b>전술 성향</b> 슈팅·코너·파울은 원본이 2005/06 시즌부터만 제공한다. 그래서
크루이프·로브손·판 할 등 그 이전 감독은 이 구역에 나오지 않는다. 20경기 미만
지휘한 감독도 표본이 얇아 제외했다.
</div>
""", unsafe_allow_html=True)
