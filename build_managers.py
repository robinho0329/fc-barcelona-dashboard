"""감독 재임 기간과 라리가 경기를 맞춰 감독별 성적을 집계한다.

Transfermarkt 표의 성적 수치는 컵대회를 포함한 값이라 이 대시보드가 쓰는
라리가 원본과 기준이 다르다. 그래서 부임·이임 날짜만 가져오고 승·무·패는
경기 날짜를 재임 구간에 넣어 직접 센다.

  python build_managers.py
"""
import json
import logging
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"
RAW = PROCESSED / "managers_raw.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("managers")

# 분석 범위 밖(1993/94 이전)에 끝난 재임은 붙일 경기가 없어 버린다.
FIRST_MATCH = pd.Timestamp("1993-08-01")

# Transfermarkt 감독 이력 표에 빠져 있는 두 명을 보충한다.
# 카를레스 레샥은 세라 페레르 경질 뒤 2001년 4월 지휘봉을 잡아 2001/02를 온전히
# 이끌었고, 티토 빌라노바는 과르디올라의 수석코치에서 승격해 2012/13 우승을
# 이끌었다. 둘 다 TM 표에 행이 없어 각각 38경기가 감독 없이 남았다.
# 사진도 TM에 없어 따로 받아 assets/managers/에 넣었다.
MISSING = [
    {"name": "Carles Rexach", "tm_id": "manual-rexach",
     "file": "manual-rexach.jpg",
     "born": "13/01/1947", "appointed": "24/04/2001", "left": "30/06/2002"},
    {"name": "Tito Vilanova", "tm_id": "manual-vilanova",
     "file": "manual-vilanova.jpg",
     "born": "17/09/1968", "appointed": "01/07/2012", "left": "19/07/2013"},
]

# 임시(대행) 감독. 시즌 중 급히 투입돼 짧게 지휘한 경우다.
# TM 표에 역할 구분이 없어 직접 표시한다.
CARETAKERS = {"Sergi Barjuan", "Radomir Antić"}


def load_matches() -> pd.DataFrame:
    m = pd.read_parquet(PROCESSED / "club_matches.parquet").copy()
    m["date"] = pd.to_datetime(m["Date"], format="mixed", dayfirst=True)
    home = m["HomeTeam"] == "Barcelona"
    m["gf"] = m["FTHG"].where(home, m["FTAG"]).astype(int)
    m["ga"] = m["FTAG"].where(home, m["FTHG"]).astype(int)
    m["venue"] = home.map({True: "홈", False: "원정"})
    m["opponent"] = m["AwayTeam"].where(home, m["HomeTeam"])
    m["gd"] = m["gf"] - m["ga"]
    m["result"] = m["gd"].apply(lambda d: "승" if d > 0 else ("무" if d == 0 else "패"))
    return m.sort_values("date").reset_index(drop=True)


def main() -> None:
    spells = json.loads(RAW.read_text(encoding="utf-8")) + MISSING
    matches = load_matches()
    last = matches["date"].max()

    rows = []
    for s in spells:
        start = pd.to_datetime(s["appointed"], format="%d/%m/%Y")
        end = pd.to_datetime(s["left"], format="%d/%m/%Y") if s["left"] else last
        if end < FIRST_MATCH:
            continue
        # 부임일 당일 경기부터, 이임일 당일 경기까지 포함
        part = matches[(matches["date"] >= start) & (matches["date"] <= end)]
        if part.empty:
            continue
        w = int((part["result"] == "승").sum())
        d = int((part["result"] == "무").sum())
        lo = int((part["result"] == "패").sum())
        seasons = sorted(part["Season"].unique())
        rows.append({
            "name": s["name"], "tm_id": s["tm_id"], "file": s.get("file", ""),
            "born": s["born"], "start": start, "end": end,
            "is_current": not s["left"],
            "role": "임시" if s["name"] in CARETAKERS else "정식",
            "days": int((end - start).days),
            "경기": len(part), "승": w, "무": d, "패": lo,
            "득점": int(part["gf"].sum()), "실점": int(part["ga"].sum()),
            "승점": w * 3 + d,
            "승률": round(w / len(part) * 100, 1),
            "경기당승점": round((w * 3 + d) / len(part), 3),
            "첫시즌": seasons[0], "끝시즌": seasons[-1],
            "시즌수": len(seasons),
        })

    df = pd.DataFrame(rows).sort_values("start").reset_index(drop=True)

    # 같은 감독의 재임이 여러 번이면 표기해 둔다 (판 할, 레샥 등)
    df["재임차수"] = df.groupby("tm_id").cumcount() + 1
    df["표시명"] = df.apply(
        lambda r: f"{r['name']} ({r['재임차수']}기)" if (df["tm_id"] == r["tm_id"]).sum() > 1
        else r["name"], axis=1)

    # 리그 우승 횟수 — 해당 감독 재임 중 종료된 시즌만 센다
    seasons_tbl = pd.read_parquet(PROCESSED / "club_season.parquet")
    champs = set(seasons_tbl.loc[seasons_tbl["rank"] == 1, "Season"])
    titles = []
    for r in df.itertuples():
        part = matches[(matches["date"] >= r.start) & (matches["date"] <= r.end)]
        # 그 시즌 경기의 3분의 2 이상을 이끈 경우에만 우승을 귀속시킨다
        n = 0
        for season, g in part.groupby("Season"):
            if season not in champs:
                continue
            total = (matches["Season"] == season).sum()
            if total and len(g) / total >= 2 / 3:
                n += 1
        titles.append(n)
    df["우승"] = titles

    df.to_parquet(PROCESSED / "managers.parquet", index=False)
    log.info("감독 재임 %d건 · %d명 · %d경기 커버",
             len(df), df["tm_id"].nunique(), int(df["경기"].sum()))
    log.info("전체 라리가 경기 %d건 중 미배정 %d건",
             len(matches), len(matches) - int(df["경기"].sum()))
    top = df.nlargest(6, "경기")[["표시명", "첫시즌", "끝시즌", "경기", "승", "무", "패",
                                "경기당승점", "우승"]]
    log.info("\n%s", top.to_string(index=False))


if __name__ == "__main__":
    main()
