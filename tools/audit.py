"""대시보드가 쓰는 데이터의 논리적 모순을 훑는다.

    python tools/audit.py

모순이 하나라도 있으면 종료 코드 1을 낸다. 데이터를 다시 만든 뒤
(크롤링·파싱) 반드시 한 번 돌릴 것.
"""
import csv
from collections import Counter
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
P = ROOT / "data" / "processed"
issues = []
sys.path.insert(0, str(ROOT))


def check(name, cond_count, detail=""):
    flag = "X " if cond_count else "OK"
    print(f"  [{flag}] {name:34s} {cond_count}건 {detail}")
    if cond_count:
        issues.append(name)


print("=== 1. 시즌 지표 (club_season) ===")
s = pd.read_parquet(P / "club_season.parquet")
check("승+무+패 != 경기", int(((s.W + s.D + s.L) != s.P).sum()))
check("승점 != 승*3+무", int((s.Pts != s.W * 3 + s.D).sum()))
check("득실차 != 득점-실점", int((s.GD != s.GF - s.GA).sum()))
check("순위 범위 밖(1~25)", int(((s["rank"] < 1) | (s["rank"] > 25)).sum()))
check("경기당승점 불일치", int(((s.PPG - s.Pts / s.P).abs() > 0.01).sum()))

print("\n=== 2. 경기 (club_matches) ===")
m = pd.read_parquet(P / "club_matches.parquet")
check("바르사 없는 경기", int((~((m.HomeTeam == "Barcelona") | (m.AwayTeam == "Barcelona"))).sum()))
check("스코어 결측", int(m[["FTHG", "FTAG"]].isna().any(axis=1).sum()))
check("시즌 합계 != 시즌표", int((m.groupby("Season").size() != s.set_index("Season")["P"]).sum()))

print("\n=== 3. 엘클라시코 ===")
cl = pd.read_parquet(P / "clasico.parquet")
check("결과-득실 불일치", int((((cl.gf > cl.ga) & (cl.result != "승"))
                        | ((cl.gf == cl.ga) & (cl.result != "무"))
                        | ((cl.gf < cl.ga) & (cl.result != "패"))).sum()))
check("스코어 문자열 불일치",
      int((cl.score != cl.gf.astype(str) + "-" + cl.ga.astype(str)).sum()))
check("날짜 역순", int((cl.date.diff().dt.days.dropna() < 0).sum()))

print("\n=== 3a. 원본 → 산출물 정합성 ===")
# 가공 코드와 독립적으로 핵심 열만 읽는다. 2004/05처럼 뒤쪽 배당률 열의
# 길이가 달라도 경기를 버리지 않으며, 원본과 산출물이 함께 빠진 경우를 잡는다.
raw_rows = []
for path in sorted((ROOT / "data" / "raw").glob("SP1_*.csv")):
    code = path.stem.split("_")[-1]
    yy = int(code[:2])
    season = f"{1900 + yy if yy >= 90 else 2000 + yy}/{code[2:]}"
    with path.open(encoding="latin-1", newline="") as stream:
        for row in csv.DictReader(stream):
            fields = [row.get(k) for k in ("Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG")]
            if all(value is not None and str(value).strip() for value in fields):
                raw_rows.append([season, *fields])
raw = pd.DataFrame(raw_rows, columns=["Season", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"])
check("원본 CSV 경기 없음", int(raw.empty))


def match_records(frame):
    """행 순서와 숫자 타입에 무관하되 중복 횟수까지 비교한다."""
    frame = frame[["Season", "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]].copy()
    frame["Date"] = pd.to_datetime(frame["Date"], format="mixed", dayfirst=True)
    frame[["FTHG", "FTAG"]] = frame[["FTHG", "FTAG"]].astype(float)
    return Counter(frame.itertuples(index=False, name=None))


def record_gap(left, right):
    return sum((left - right).values()) + sum((right - left).values())


all_matches = pd.read_parquet(P / "all_matches.parquet")
raw_club = raw[(raw.HomeTeam == "Barcelona") | (raw.AwayTeam == "Barcelona")].copy()
check("원본 vs 전체 경기 누락·변경", record_gap(match_records(raw), match_records(all_matches)))
check("원본 vs 바르사 경기 누락·변경", record_gap(match_records(raw_club), match_records(m)))
check("바르사 경기 중복", int(m.duplicated(["Season", "HomeTeam", "AwayTeam"]).sum()))
home = raw_club.HomeTeam == "Barcelona"
raw_club["GF"] = raw_club.FTHG.where(home, raw_club.FTAG).astype(float)
raw_club["GA"] = raw_club.FTAG.where(home, raw_club.FTHG).astype(float)
raw_club["W"] = (raw_club.GF > raw_club.GA).astype(int)
raw_club["D"] = (raw_club.GF == raw_club.GA).astype(int)
raw_club["L"] = (raw_club.GF < raw_club.GA).astype(int)
metrics = ["W", "D", "L", "GF", "GA"]
expected = raw_club.groupby("Season")[metrics].sum()
actual = s.set_index("Season")[metrics]
expected, actual = expected.align(actual)
check("원본 vs 시즌 전적·득실", int((expected != actual).any(axis=1).sum()))

standings = pd.read_parquet(P / "standings.parquet")
standing_club = standings[standings.team == "Barcelona"].set_index("season")
columns = ["P", *metrics, "GD", "Pts", "rank", "complete"]
expected, actual = standing_club[columns].align(s.set_index("Season")[columns])
check("순위표 vs 시즌표 불일치", int((expected != actual).any(axis=1).sum()))
# 상대전적 우선순위가 잘못 바뀌면 우승 횟수가 늘어나는 실제 회귀 사례.
tie_season = standings[(standings.season == "2006/07") & standings.team.isin(["Barcelona", "Real Madrid"])]
check("2006/07 상대전적 순위 회귀",
      int(tie_season.set_index("team")["rank"].to_dict() != {"Real Madrid": 1, "Barcelona": 2}))

rival = raw_club[(raw_club.HomeTeam == "Real Madrid") | (raw_club.AwayTeam == "Real Madrid")].copy()
rival["date"] = pd.to_datetime(rival.Date, format="mixed", dayfirst=True)
rival["venue"] = (rival.HomeTeam == "Barcelona").map({True: "홈", False: "원정"})
rival = rival.rename(columns={"GF": "gf", "GA": "ga"})
cl_columns = ["Season", "date", "venue", "gf", "ga"]
check("원본 vs 클라시코 누락·변경", record_gap(
    Counter(rival[cl_columns].itertuples(index=False, name=None)),
    Counter(cl[cl_columns].itertuples(index=False, name=None))))

print("\n=== 4. 감독 (managers) ===")
g = pd.read_parquet(P / "managers.parquet")
check("승+무+패 != 경기", int(((g.승 + g.무 + g.패) != g.경기).sum()))
check("승점 != 승*3+무", int((g.승점 != g.승 * 3 + g.무).sum()))
check("재임 종료 < 시작", int((g.end < g.start).sum()))
check("경기 합계 != 전체 경기",
      abs(int(g.경기.sum()) - len(m)), f"(감독 {int(g.경기.sum())} / 전체 {len(m)})")
manager_metrics = {"승": "W", "무": "D", "패": "L", "득점": "GF", "실점": "GA"}
for manager_column, season_column in manager_metrics.items():
    check(f"감독 {manager_column} 합계 != 원본",
          abs(int(g[manager_column].sum()) - int(raw_club[season_column].sum())))
# 완료 시즌의 우승보다 감독 귀속 우승이 많을 수 없다. 감독 교체 시즌에는
# 귀속 기준(2/3 이상 지휘) 때문에 합계가 작을 수 있으므로 동등성은 강제하지 않는다.
completed_titles = int(((s["rank"] == 1) & s["complete"]).sum())
check("감독 우승 > 완료 시즌 우승", max(0, int(g["우승"].sum()) - completed_titles),
      f"(감독 {int(g['우승'].sum())} / 완료 시즌 {completed_titles})")
ov = 0
gs = g.sort_values("start").reset_index(drop=True)
for i in range(len(gs) - 1):
    if gs.loc[i, "end"] > gs.loc[i + 1, "start"] + pd.Timedelta(days=1):
        ov += 1
check("재임 구간 겹침", ov)

print("\n=== 5. 선수 대회별 (fbref_allcomps_players) ===")
d = pd.concat([pd.read_parquet(f) for f in
               sorted((ROOT / "data" / "fbref_allcomps_players").glob("*.parquet"))],
              ignore_index=True)
check("선발 > 경기", int((d.선발 > d.경기).sum()))
check("경기 결측", int(d.경기.isna().sum()))
check("골 < PK골", int((d.골 < d.PK골).sum()))
check("출전분 > 경기*120", int((d.출전분 > d.경기 * 120).sum()))
# '전 대회'는 나머지 대회의 합과 같아야 한다
tot = d[d["대회"] == "전 대회"].groupby(["Player", "season"])["골"].sum()
part = d[d["대회"] != "전 대회"].groupby(["Player", "season"])["골"].sum()
both = pd.concat([tot.rename("전체"), part.rename("합")], axis=1).dropna()
check("전 대회 != 대회 합", int(((both.전체 - both.합).abs() > 0.5).sum()),
      f"(비교 {len(both)}쌍)")

print("\n=== 6. 라리가 상세 (players) ===")
pl = pd.read_parquet(P / "players.parquet")
check("선발 > 경기", int((pl.선발 > pl.경기).sum()))
check("골 < PK골", int((pl.골 < pl["PK골"]).sum()))
check("유효슛 > 슛", int((pl.유효슛 > pl.슛).sum()))
check("경기 > 42", int((pl.경기 > 42).sum()))

print("\n=== 7. StatsBomb ===")
sb = ROOT / "data" / "statsbomb"
sh = pd.read_parquet(sb / "shots.parquet")
ps = pd.read_parquet(sb / "passes.parquet")
check("슛 좌표 결측", int(sh[["x", "y"]].isna().any(axis=1).sum()))
check("xG 범위 밖(0~1)", int(((sh.xg < 0) | (sh.xg > 1)).sum()))
check("좌표 범위 밖", int(((sh.x < 0) | (sh.x > 120) | (sh.y < 0) | (sh.y > 80)).sum()))
check("패스 좌표 결측", int(ps[["x", "y", "end_x", "end_y"]].isna().any(axis=1).sum()))

# StatsBomb은 호나우지뉴를 법적 이름 `Ronaldo de Assis Moreira`로 준다.
# 전 시즌 FBref 명단에서 토큰만 맞추면 호나우두와 합쳐지므로 회귀 검사한다.
from _lib import sb_names

linked = sh[sh["is_barca"] & sh["goal"] & sh["assisted_by"].notna()].copy()
linked["mapped_player"] = sb_names(linked["player"]).values
linked["mapped_assist"] = sb_names(linked["assisted_by"]).values
modern_ronaldo = ((linked["season"].str[:4].astype(int) >= 2004)
                  & (linked[["mapped_player", "mapped_assist"]] == "Ronaldo").any(axis=1))
check("호나우지뉴→Ronaldo 오매칭", int(modern_ronaldo.sum()))
r06 = linked[linked["season"] == "2006/07"]
r06_goals = int((r06["mapped_player"] == "Ronaldinho").sum())
r06_assists = int((r06["mapped_assist"] == "Ronaldinho").sum())
check("호나우지뉴 06/07 연계 회귀", int((r06_goals, r06_assists) != (5, 7)),
      f"(득점 {r06_goals} / 도움 {r06_assists})")

print("\n=== 8. Understat ===")
us = pd.read_parquet(ROOT / "data" / "understat" / "shots.parquet")
check("좌표 범위 밖", int(((us.x < 0) | (us.x > 120) | (us.y < 0) | (us.y > 80)).sum()))
check("xG 범위 밖", int(((us.xg < 0) | (us.xg > 1)).sum()))
check("goal != outcome", int((us.goal != (us.outcome == "Goal")).sum()))
# 시즌별 바르사 골이 리그 원본과 맞는지
ug = us[us.is_barca & us.goal].groupby("season").size()
lg = d[(d["대회"] == "라리가")].groupby("season")["골"].sum()
cmp = pd.concat([ug.rename("understat"), lg.rename("fbref")], axis=1).dropna()
gap = (cmp.understat - cmp.fbref).abs()
check("Understat vs FBref 골 차이>3", int((gap > 3).sum()),
      f"(최대 {int(gap.max()) if len(gap) else 0})")

print("\n" + "=" * 52)
print("문제 있는 항목:", issues if issues else "없음")
sys.exit(1 if issues else 0)
