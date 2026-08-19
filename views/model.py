"""AI 모델 — 경기 전 정보만으로 라리가 결과를 예측하고, 그 한계를 그대로 보인다."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from _lib import (BLAU, GOLD, GRANA, GRID, PLOT, PROCESSED, WHITE, b64,
                  load_json, load_parquet, load_seasons, metric_cards, setup)

seasons = load_seasons()
setup(seasons)

MODEL_DIR = PROCESSED / "model"


mt = load_json(MODEL_DIR / "metrics.json")
pr = load_parquet(MODEL_DIR / "predictions.parquet")

st.markdown(f"""
<div class="hero">
  <img class="hero-crest" src="{b64('crest.svg')}" alt="">
  <div class="hero-kicker">Match Outcome Model · Pre-match features only</div>
  <h1>AI 모델</h1>
  <div class="hero-motto">경기 시작 전에 알 수 있는 정보만으로 승·무·패를
  예측한다. 잘 맞히는 부분과 못 맞히는 부분을 함께 보여준다.</div>
  <div class="accent-rule"></div>
</div>
""", unsafe_allow_html=True)

if not mt or pr.empty:
    st.warning("모델 결과가 없습니다. `python train_model.py`를 먼저 실행하세요.")
    st.stop()

best = mt["best"]
bm = mt["models"][best]

# ---------------------------------------------------------------- 설계
st.markdown('<div class="section">어떻게 만들었나</div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="lede">
슛·코너 같은 <b>경기 중 기록은 피처에서 뺐다</b>. 넣으면 정확도는 오르지만
경기가 끝나야 알 수 있는 값이라, 예측이 아니라 결과를 되짚는 셈이 된다.
쓴 것은 직전 5·10경기 폼, 홈/원정, 상대의 직전 시즌 순위와 그 시점 폼,
해당 상대와의 최근 상대전적, 시즌 진행도, 직전 경기와의 간격이다.<br><br>
검증은 <b>시간 순서를 지켰다</b>. 무작위로 섞으면 미래 경기로 과거를 맞히게 된다.
{mt['n_train']:,}경기로 학습하고 마지막 다섯 시즌
({mt['test_seasons'][0]}~{mt['test_seasons'][-1]}) {mt['n_test']}경기로만 평가했다.
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- 성능
st.markdown('<div class="section">성능</div>', unsafe_allow_html=True)
st.markdown(metric_cards([
    ("최종 모델", best, f"평가 {mt['n_test']}경기"),
    ("정확도", f"{bm['accuracy'] * 100:.1f}%",
     f"기준선 {mt['baseline_always_win'] * 100:.1f}% (항상 승)"),
    ("로그손실", f"{bm['log_loss']:.3f}",
     f"기준선 {mt['baseline_prior_log_loss']:.3f} (비율 예측)"),
    ("승 확률 AUC", f"{mt['auc_win']:.3f}", "0.5 = 무작위 · 1.0 = 완벽"),
]), unsafe_allow_html=True)

st.markdown("""
<div class="lede">
<b>정확도만 보면 이 모델은 쓸모없어 보인다.</b> 바르사는 리그에서 70% 넘게
이기기 때문에, 아무 생각 없이 "무조건 승"만 찍어도 70.5%가 나온다. 모델은
70.0%로 그보다 낮다. 로그손실도 기준선과 거의 같다.<br><br>
그런데 <b>줄 세우는 능력은 분명히 있다.</b> 모델이 승리 확률을 높게 본 경기와
낮게 본 경기의 실제 승률이 크게 갈린다. 즉 "이길 확률이 얼마인가"를 맞히지는
못해도 <b>"어느 경기가 위험한가"는 짚어낸다</b>. 아래 사분위 표가 그 근거다.
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- 캘리브레이션
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="section">예측 구간별 실제 승률</div>', unsafe_allow_html=True)
    cal = pd.DataFrame(mt["calibration"])
    f1 = go.Figure()
    f1.add_trace(go.Bar(x=cal["구간"], y=cal["실제승률"], name="실제 승률",
                        marker_color=GRANA, text=cal["실제승률"],
                        textposition="outside", textfont_color="#f2f6fc"))
    f1.add_trace(go.Scatter(x=cal["구간"], y=cal["예측승률"], name="모델 예측",
                            mode="lines+markers", line=dict(color=GOLD, width=2.4)))
    f1.add_hline(y=mt["baseline_always_win"] * 100, line_dash="dot", line_color=BLAU,
                 annotation_text=f"평균 {mt['baseline_always_win'] * 100:.1f}%",
                 annotation_font_color="#94a8c4")
    f1.update_layout(height=360, yaxis_title="승률(%)",
                     legend=dict(orientation="h", y=1.12), **PLOT)
    f1.update_xaxes(gridcolor=GRID)
    f1.update_yaxes(gridcolor=GRID, range=[0, 100])
    st.plotly_chart(f1, use_container_width=True)
    lift = cal["실제승률"].iloc[-1] - cal["실제승률"].iloc[0]
    st.caption(f"모델이 가장 자신 있어 한 25%는 실제로 {cal['실제승률'].iloc[-1]:.1f}% 승리했고, "
               f"가장 불안해한 25%는 {cal['실제승률'].iloc[0]:.1f}%였다. 격차 {lift:.1f}%p.")

with c2:
    st.markdown('<div class="section">혼동 행렬</div>', unsafe_allow_html=True)
    cm = pd.DataFrame(bm["confusion"], index=bm["classes"], columns=bm["classes"])
    f2 = go.Figure(go.Heatmap(
        z=cm.values, x=[f"예측 {c}" for c in cm.columns],
        y=[f"실제 {c}" for c in cm.index],
        text=cm.values, texttemplate="%{text}", textfont=dict(size=15),
        colorscale=[[0, "rgba(4,16,31,0)"], [.5, "rgba(0,77,152,.6)"],
                    [1, "rgba(165,0,68,.9)"]],
        hovertemplate="%{y} → %{x}<br>%{z}경기<extra></extra>", showscale=False))
    f2.update_layout(height=360, **PLOT)
    st.plotly_chart(f2, use_container_width=True)
    st.caption("모델은 사실상 '승'만 고른다. 무승부와 패배를 거의 못 짚는데, "
               "이건 데이터가 승리로 크게 치우쳐 있어서다.")

# ---------------------------------------------------------------- 모델 비교
st.markdown('<div class="section">모델 비교</div>', unsafe_allow_html=True)
rows = []
for name, m in mt["models"].items():
    rows.append({"모델": name, "정확도": round(m["accuracy"] * 100, 1),
                 "로그손실": m["log_loss"]})
rows.append({"모델": "기준선 (항상 승)",
             "정확도": round(mt["baseline_always_win"] * 100, 1),
             "로그손실": mt["baseline_prior_log_loss"]})
cmp = pd.DataFrame(rows)
f3 = go.Figure()
f3.add_trace(go.Bar(x=cmp["모델"], y=cmp["정확도"], name="정확도(%)",
                    marker_color=[GRANA if m != "기준선 (항상 승)" else "#6b7d99"
                                  for m in cmp["모델"]],
                    text=cmp["정확도"], textposition="outside",
                    textfont_color="#f2f6fc", yaxis="y"))
f3.add_trace(go.Scatter(x=cmp["모델"], y=cmp["로그손실"], name="로그손실 (낮을수록 좋음)",
                        mode="lines+markers", line=dict(color=GOLD, width=2.4),
                        yaxis="y2"))
f3.update_layout(height=340,
                 yaxis=dict(title="정확도(%)", gridcolor=GRID, range=[0, 100]),
                 yaxis2=dict(title="로그손실", overlaying="y", side="right",
                             showgrid=False, range=[0, 1.2]),
                 legend=dict(orientation="h", y=1.14), **PLOT)
f3.update_xaxes(gridcolor=GRID)
st.plotly_chart(f3, use_container_width=True)

# ---------------------------------------------------------------- 피처 방향
st.markdown('<div class="section">무엇이 승리 확률을 밀어올리나</div>', unsafe_allow_html=True)
coef = pd.Series(mt["coef"]["승"]).sort_values()
NAMES = {
    "is_home": "홈 경기", "form_pts_5": "최근 5경기 승점률",
    "form_gf_5": "최근 5경기 득점", "form_ga_5": "최근 5경기 실점",
    "form_pts_10": "최근 10경기 승점률", "form_gf_10": "최근 10경기 득점",
    "form_ga_10": "최근 10경기 실점", "opp_prev_rank": "상대 직전 시즌 순위",
    "opp_form_pts": "상대 최근 승점률", "opp_form_gf": "상대 최근 득점",
    "opp_form_ga": "상대 최근 실점", "opp_season_ppg": "상대 시즌 승점률",
    "h2h_pts_3": "이 상대와 최근 3경기", "round_ratio": "시즌 진행도",
    "rest_days": "직전 경기 후 휴식일",
}
f4 = go.Figure(go.Bar(
    y=[NAMES.get(i, i) for i in coef.index], x=coef.values, orientation="h",
    marker_color=[GRANA if v > 0 else WHITE for v in coef.values],
    hovertemplate="<b>%{y}</b><br>계수 %{x:.3f}<extra></extra>"))
f4.update_layout(height=460, xaxis_title="로지스틱 회귀 계수 (승 클래스)", **PLOT)
f4.update_xaxes(gridcolor=GRID, zerolinecolor="#2b4a72")
f4.update_yaxes(gridcolor=GRID, type="category")
st.plotly_chart(f4, use_container_width=True)
st.caption("그라나 = 승리 확률을 올리는 방향 · 흰색 = 내리는 방향. "
           "표준화한 값의 계수라 서로 크기를 비교할 수 있다. "
           "상대 순위는 숫자가 클수록 약한 팀이라는 뜻이다.")

# ---------------------------------------------------------------- 경기별
st.markdown('<div class="section">평가 구간 경기별 예측</div>', unsafe_allow_html=True)
c1, c2 = st.columns([1.2, 1])
season_pick = c1.selectbox("시즌", ["전체"] + sorted(pr["Season"].unique(), reverse=True))
only_miss = c2.checkbox("빗나간 경기만", value=False)

v = pr if season_pick == "전체" else pr[pr["Season"] == season_pick]
if only_miss:
    v = v[~v["적중"]]

if v.empty:
    st.info("조건에 맞는 경기가 없습니다.")
else:
    st.caption(f"{len(v)}경기 · 적중 {int(v['적중'].sum())}건 "
               f"({v['적중'].mean() * 100:.1f}%)")
    tb = v.copy()
    tb["날짜"] = tb["date"].dt.strftime("%Y-%m-%d")
    tb["장소"] = tb["is_home"].map({1: "홈", 0: "원정"})
    tb["승 확률"] = (tb["p_승"] * 100).round(1)
    tb["무 확률"] = (tb["p_무"] * 100).round(1)
    tb["패 확률"] = (tb["p_패"] * 100).round(1)
    tb["적중"] = tb["적중"].map({True: "○", False: "×"})
    show = tb[["날짜", "Season", "장소", "opponent", "승 확률", "무 확률", "패 확률",
               "예측", "result", "적중"]]
    show.columns = ["날짜", "시즌", "장소", "상대", "승 확률", "무 확률", "패 확률",
                    "예측", "실제", "적중"]
    st.dataframe(show.sort_values("날짜", ascending=False).set_index("날짜"),
                 use_container_width=True, height=430)

st.markdown("""
<div class="credits">
<b>데이터</b> football-data.co.uk 라리가 1993/94~2025/26 바르셀로나 경기.
컵대회·챔피언스리그는 이 원본에 없어 학습에서 빠져 있다.<br>
<b>피처</b> 경기 시작 전에 알 수 있는 값만 썼다. 폼 지표는 모두 직전 경기까지로
잘라(shift) 당일 결과가 새어 들어가지 않게 했다.<br>
<b>한계</b> 승리가 70%를 넘는 편중된 데이터라 정확도로는 기준선을 넘기 어렵다.
이 모델의 쓸모는 '몇 %로 이긴다'를 맞히는 데 있지 않고 경기 간 난이도를
줄 세우는 데 있다. 부상·이적·감독 교체·컵대회 일정 같은 맥락은 원본에 없어
반영되지 않는다.
</div>
""", unsafe_allow_html=True)
