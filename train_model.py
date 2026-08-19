"""바르셀로나 라리가 경기 결과 예측 모델.

경기 **전에** 알 수 있는 정보만 쓴다. 슛·코너 같은 경기 중 기록을 넣으면
정확도는 올라가지만 예측이 아니라 결과를 되짚는 꼴이 된다.

피처
  - 직전 5·10경기 폼 (승점률, 득점, 실점)
  - 홈/원정
  - 상대의 직전 시즌 순위 (없으면 중간값)
  - 해당 상대와의 최근 상대전적
  - 시즌 내 진행도(라운드 비율)

검증은 시간 순서를 지킨다. 무작위로 섞으면 미래 경기로 과거를 맞히게 된다.

  python train_model.py
"""
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, log_loss,
                             roc_auc_score)
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"
OUT = PROCESSED / "model"
OUT.mkdir(parents=True, exist_ok=True)

RANDOM_STATE = 42
CLASSES = ["패", "무", "승"]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("model")


def load() -> pd.DataFrame:
    m = pd.read_parquet(PROCESSED / "club_matches.parquet").copy()
    m["date"] = pd.to_datetime(m["Date"], format="mixed", dayfirst=True)
    home = m["HomeTeam"] == "Barcelona"
    m["is_home"] = home.astype(int)
    m["gf"] = m["FTHG"].where(home, m["FTAG"]).astype(float)
    m["ga"] = m["FTAG"].where(home, m["FTHG"]).astype(float)
    m["opponent"] = m["AwayTeam"].where(home, m["HomeTeam"])
    m["gd"] = m["gf"] - m["ga"]
    m["result"] = np.where(m["gd"] > 0, "승", np.where(m["gd"] == 0, "무", "패"))
    m["points"] = m["result"].map({"승": 3, "무": 1, "패": 0})
    return m.sort_values("date").reset_index(drop=True)


def opponent_form() -> pd.DataFrame:
    """리그 전 경기에서 팀별 '그 경기 직전까지의' 폼을 만든다.

    상대가 얼마나 좋은 팀인지가 예측의 핵심인데, 직전 시즌 순위만으로는
    시즌 중 변화를 못 잡는다. 리그 전체 경기를 팀 시점으로 펼쳐 계산한다.
    """
    df = pd.read_parquet(PROCESSED / "all_matches.parquet").copy()
    df["date"] = pd.to_datetime(df["Date"], format="mixed", dayfirst=True)

    rows = []
    for _, r in df.iterrows():
        for team, gf, ga in ((r["HomeTeam"], r["FTHG"], r["FTAG"]),
                             (r["AwayTeam"], r["FTAG"], r["FTHG"])):
            rows.append({"team": team, "date": r["date"], "Season": r["Season"],
                         "gf": gf, "ga": ga,
                         "pts": 3 if gf > ga else (1 if gf == ga else 0)})
    t = pd.DataFrame(rows).sort_values(["team", "date"]).reset_index(drop=True)

    g = t.groupby("team", group_keys=False)
    t["opp_form_pts"] = g["pts"].apply(lambda s: s.shift(1).rolling(6, min_periods=2).mean())
    t["opp_form_gf"] = g["gf"].apply(lambda s: s.shift(1).rolling(6, min_periods=2).mean())
    t["opp_form_ga"] = g["ga"].apply(lambda s: s.shift(1).rolling(6, min_periods=2).mean())
    # 시즌 누적 승점률(직전 경기까지)
    t["opp_season_ppg"] = (t.groupby(["team", "Season"], group_keys=False)["pts"]
                           .apply(lambda s: s.shift(1).expanding(min_periods=2).mean()))
    return t[["team", "date", "opp_form_pts", "opp_form_gf", "opp_form_ga",
              "opp_season_ppg"]]


def opponent_strength() -> dict:
    """상대의 직전 시즌 순위. 승격팀처럼 기록이 없으면 중간 순위로 둔다."""
    tbl = pd.read_parquet(PROCESSED / "league_table.parquet")
    seasons = sorted(tbl["Season"].unique())
    nxt = {s: seasons[i + 1] for i, s in enumerate(seasons[:-1])}
    out = {}
    for _, r in tbl.iterrows():
        target = nxt.get(r["Season"])
        if target:
            out[(target, r["team"])] = r["rank"]
    return out


def build_features(m: pd.DataFrame) -> pd.DataFrame:
    """경기 시점 이전 정보만으로 피처를 만든다. shift(1)로 당일 결과를 배제."""
    d = m.copy()
    prev_rank = opponent_strength()
    mid = 10.0

    for n in (5, 10):
        d[f"form_pts_{n}"] = d["points"].shift(1).rolling(n, min_periods=2).mean()
        d[f"form_gf_{n}"] = d["gf"].shift(1).rolling(n, min_periods=2).mean()
        d[f"form_ga_{n}"] = d["ga"].shift(1).rolling(n, min_periods=2).mean()

    d["opp_prev_rank"] = [prev_rank.get((s, o), mid)
                          for s, o in zip(d["Season"], d["opponent"])]

    # 같은 상대와의 최근 3경기 승점률 (직전 경기까지만)
    h2h = []
    for i, r in d.iterrows():
        past = d.iloc[:i]
        same = past[past["opponent"] == r["opponent"]].tail(3)
        h2h.append(same["points"].mean() if len(same) else np.nan)
    d["h2h_pts_3"] = h2h

    # 시즌 진행도 — 시즌 초반과 막판은 성격이 다르다
    d["round_ratio"] = d.groupby("Season").cumcount() / d.groupby("Season")["Season"].transform("size")

    # 직전 경기와의 간격(일). 일정 과밀 여부의 대리 지표
    d["rest_days"] = d["date"].diff().dt.days.clip(0, 30)

    # 상대 팀의 그 시점 폼을 붙인다
    form = opponent_form()
    d = d.merge(form, left_on=["opponent", "date"], right_on=["team", "date"],
                how="left").drop(columns=["team"])

    return d


FEATURES = ["is_home", "form_pts_5", "form_gf_5", "form_ga_5",
            "form_pts_10", "form_gf_10", "form_ga_10",
            "opp_prev_rank", "opp_form_pts", "opp_form_gf", "opp_form_ga",
            "opp_season_ppg", "h2h_pts_3", "round_ratio", "rest_days"]


def main() -> None:
    m = load()
    d = build_features(m).dropna(subset=["form_pts_10"]).reset_index(drop=True)
    log.info("학습 대상 %d경기 (%s ~ %s)", len(d),
             d["Season"].iloc[0], d["Season"].iloc[-1])

    # 시간 순 분할 — 마지막 5시즌을 평가에 쓴다
    seasons = sorted(d["Season"].unique())
    test_seasons = set(seasons[-5:])
    train = d[~d["Season"].isin(test_seasons)]
    test = d[d["Season"].isin(test_seasons)]
    log.info("학습 %d경기 / 평가 %d경기 (%s~)", len(train), len(test), seasons[-5])

    X_tr, y_tr = train[FEATURES], train["result"]
    X_te, y_te = test[FEATURES], test["result"]

    models = {
        # 처음 만나는 상대는 h2h가, 첫 경기는 rest_days가 비어 있다.
        # 부스팅은 결측을 그대로 다루지만 로지스틱은 못 하므로 중앙값으로 채운다.
        "로지스틱 회귀": make_pipeline(
            SimpleImputer(strategy="median"),
            StandardScaler(),
            # sklearn 1.7에서 multi_class 인자가 제거됐다. 다중 클래스는 기본 동작.
            LogisticRegression(max_iter=2000, random_state=RANDOM_STATE)),
        "그래디언트 부스팅": HistGradientBoostingClassifier(
            max_depth=4, learning_rate=0.06, max_iter=260,
            l2_regularization=1.0, random_state=RANDOM_STATE),
    }

    # 기준선 둘.
    #  (1) 항상 '승'만 찍기 — 정확도 기준선
    #  (2) 학습 구간의 승/무/패 비율을 그대로 확률로 내놓기 — 로그손실 기준선
    # 바르사는 리그 승률이 70%에 가까워 (1)을 정확도로 넘기기가 매우 어렵다.
    # 그래서 확률의 질을 보는 로그손실을 주 지표로 삼는다.
    base_acc = (y_te == "승").mean()
    # log_loss는 labels를 사전순으로 가정하므로 확률 열도 그 순서로 맞춘다.
    lex = sorted(CLASSES)
    prior = y_tr.value_counts(normalize=True).reindex(lex).fillna(0).to_numpy()
    prior_proba = np.tile(prior, (len(y_te), 1))
    base_ll = log_loss(y_te, prior_proba, labels=lex)
    results = {
        "baseline_always_win": round(float(base_acc), 4),
        "baseline_prior_log_loss": round(float(base_ll), 4),
        "models": {},
    }
    log.info("기준선 — 항상 승 정확도 %.3f · 비율 예측 로그손실 %.3f", base_acc, base_ll)

    best_name, best_acc, best_ll = None, -1.0, None
    for name, clf in models.items():
        clf.fit(X_tr, y_tr)
        pred = clf.predict(X_te)
        proba = clf.predict_proba(X_te)
        acc = accuracy_score(y_te, pred)
        ll = log_loss(y_te, proba, labels=list(clf.classes_))
        cm = confusion_matrix(y_te, pred, labels=CLASSES)
        results["models"][name] = {
            "accuracy": round(float(acc), 4),
            "log_loss": round(float(ll), 4),
            "classes": CLASSES,
            "confusion": cm.tolist(),
        }
        log.info("%-12s 정확도 %.3f · 로그손실 %.3f (기준선 대비 %+.3f)",
                 name, acc, ll, ll - base_ll)
        # 정확도가 아니라 로그손실이 낮은 쪽을 고른다
        if best_ll is None or ll < best_ll:
            best_name, best_acc, best_ll = name, acc, ll
            best_clf, best_proba = clf, proba

    results["best"] = best_name
    results["best_log_loss"] = round(float(best_ll), 4)
    results["test_seasons"] = sorted(test_seasons)
    results["features"] = FEATURES
    results["n_train"] = len(train)
    results["n_test"] = len(test)

    # 정확도·로그손실만 보면 이 모델은 기준선과 다를 바 없어 보인다. 하지만
    # 승률 70%인 팀에서 중요한 건 "어느 경기가 위험한가"를 줄 세우는 능력이다.
    # 그래서 승 확률의 판별력(AUC)과 사분위별 실제 승률을 함께 남긴다.
    # 이 블록은 metrics.json을 쓰기 전에 와야 한다.
    win_col = list(best_clf.classes_).index("승")
    p_win = best_proba[:, win_col]
    actual_win = (y_te == "승").astype(int).to_numpy()
    results["auc_win"] = round(float(roc_auc_score(actual_win, p_win)), 4)

    q = pd.qcut(p_win, 4, labels=["하위 25%", "중하", "중상", "상위 25%"])
    cal = (pd.DataFrame({"bin": q, "p": p_win, "win": actual_win})
           .groupby("bin", observed=True)
           .agg(경기=("win", "size"), 예측승률=("p", "mean"), 실제승률=("win", "mean")))
    results["calibration"] = [
        {"구간": str(i), "경기": int(r["경기"]),
         "예측승률": round(float(r["예측승률"]) * 100, 1),
         "실제승률": round(float(r["실제승률"]) * 100, 1)}
        for i, r in cal.iterrows()]
    log.info("승 확률 AUC %.3f · 상위25%% 실제승률 %.1f%% vs 하위25%% %.1f%%",
             results["auc_win"], results["calibration"][-1]["실제승률"],
             results["calibration"][0]["실제승률"])

    # 로지스틱 계수로 방향성만 본다(부스팅은 계수가 없다)
    lr = models["로지스틱 회귀"]
    coef = lr[-1].coef_
    results["coef"] = {
        cls: {f: round(float(c), 3) for f, c in zip(FEATURES, row)}
        for cls, row in zip(lr[-1].classes_, coef)}

    # 평가 구간 경기별 예측 확률을 저장해 페이지에서 보여준다
    out = test[["Season", "date", "opponent", "is_home", "result"]].copy()
    for i, cls in enumerate(best_clf.classes_):
        out[f"p_{cls}"] = best_proba[:, i].round(4)
    out["예측"] = best_clf.predict(X_te)
    out["적중"] = out["예측"] == out["result"]
    out.to_parquet(OUT / "predictions.parquet", index=False)

    (OUT / "metrics.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("최고 모델: %s · 로그손실 %.3f (기준선 %.3f, %+.3f) · 정확도 %.3f",
             best_name, best_ll, base_ll, best_ll - base_ll, best_acc)


if __name__ == "__main__":
    main()
