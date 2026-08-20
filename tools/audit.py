"""대시보드가 쓰는 데이터의 논리적 모순을 훑는다.

    python tools/audit.py

모순이 하나라도 있으면 종료 코드 1을 낸다. 데이터를 다시 만든 뒤
(크롤링·파싱) 반드시 한 번 돌릴 것.
"""
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(r"D:\workspace\barcelona")
P = ROOT / "data" / "processed"
issues = []


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

print("\n=== 4. 감독 (managers) ===")
g = pd.read_parquet(P / "managers.parquet")
check("승+무+패 != 경기", int(((g.승 + g.무 + g.패) != g.경기).sum()))
check("승점 != 승*3+무", int((g.승점 != g.승 * 3 + g.무).sum()))
check("재임 종료 < 시작", int((g.end < g.start).sum()))
check("경기 합계 != 전체 경기",
      abs(int(g.경기.sum()) - len(m)), f"(감독 {int(g.경기.sum())} / 전체 {len(m)})")
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
