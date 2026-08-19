"""라리가 원본(football-data.co.uk SP1) → 바르사 시즌 지표.

수집한 CSV를 시즌 단위로 합쳐 승점·득실·순위를 계산한다.
football-data는 순위를 주지 않으므로 리그 전체 경기에서 직접 집계한다.
"""
import glob
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
CLUB = "Barcelona"


def load_all() -> pd.DataFrame:
    frames = []
    for f in sorted(RAW.glob("SP1_*.csv")):
        code = re.search(r"SP1_(\d{4})", f.name).group(1)
        yy = int(code[:2])
        season = f"{1900 + yy if yy >= 90 else 2000 + yy}/{code[2:]}"
        d = pd.read_csv(f, on_bad_lines="skip", engine="python", encoding="latin-1")
        d = d.dropna(subset=["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"])
        d["Season"] = season
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def league_table(df: pd.DataFrame) -> pd.DataFrame:
    """시즌별 전 구단 순위표. 승점 → 골득실 → 다득점 순."""
    recs = []
    for season, g in df.groupby("Season"):
        acc = {}
        for _, r in g.iterrows():
            for team, gf, ga in ((r["HomeTeam"], r["FTHG"], r["FTAG"]),
                                 (r["AwayTeam"], r["FTAG"], r["FTHG"])):
                a = acc.setdefault(team, dict(P=0, W=0, D=0, L=0, GF=0, GA=0))
                a["P"] += 1; a["GF"] += gf; a["GA"] += ga
                a["W" if gf > ga else ("D" if gf == ga else "L")] += 1
        t = pd.DataFrame(acc).T.reset_index(names="team")
        t["GD"] = t["GF"] - t["GA"]
        t["Pts"] = t["W"] * 3 + t["D"]
        t = t.sort_values(["Pts", "GD", "GF"], ascending=False).reset_index(drop=True)
        t["rank"] = t.index + 1
        t["Season"] = season
        recs.append(t)
    return pd.concat(recs, ignore_index=True)


def main() -> None:
    df = load_all()
    table = league_table(df)
    table.to_parquet(OUT / "league_table.parquet", index=False)

    club = table[table["team"] == CLUB].sort_values("Season").reset_index(drop=True)
    club["PPG"] = (club["Pts"] / club["P"]).round(3)
    club["decade"] = club["Season"].str[:3] + "0s"
    club.to_parquet(OUT / "club_season.parquet", index=False)

    matches = df[(df["HomeTeam"] == CLUB) | (df["AwayTeam"] == CLUB)].copy()
    matches.to_parquet(OUT / "club_matches.parquet", index=False)

    print(f"시즌 {len(club)}개 · 경기 {len(matches)}건")
    print(f"리그 우승 {int((club['rank'] == 1).sum())}회 · 총 득점 {int(club['GF'].sum())}")
    print(club.tail(3)[["Season", "P", "W", "D", "L", "GF", "GA", "Pts", "rank"]].to_string(index=False))


if __name__ == "__main__":
    main()
