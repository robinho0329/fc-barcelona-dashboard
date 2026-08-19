"""StatsBomb 오픈데이터에서 바르셀로나 경기 이벤트를 받아 집계한다.

라리가(competition_id=11) 2004/05~2020/21 바르사 524경기. 원본 이벤트는 합계
1.3GB라 그대로 두지 않고, 대시보드가 쓸 형태로 줄여 parquet 4종만 남긴다.

  shots.parquet    슛 전량 (좌표·xG·결과) — 패스맵/슈팅맵용
  passes.parquet   바르사 패스 전량 (시작·종료 좌표) — 패스맵용
  player_match     선수-경기 단위 집계
  matches.parquet  경기 메타

  python fetch_statsbomb.py
"""
import json
import logging
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "statsbomb"
CACHE = ROOT / "data" / ".sb_cache"
OUT.mkdir(parents=True, exist_ok=True)
CACHE.mkdir(parents=True, exist_ok=True)

BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
UA = {"User-Agent": "BarcaDashboard/1.0 (educational portfolio project)"}
CLUB = "Barcelona"
LALIGA = 11
SEASONS = {37: "2004/05", 38: "2005/06", 39: "2006/07", 40: "2007/08", 41: "2008/09",
           21: "2009/10", 22: "2010/11", 23: "2011/12", 24: "2012/13", 25: "2013/14",
           26: "2014/15", 27: "2015/16", 2: "2016/17", 1: "2017/18", 4: "2018/19",
           42: "2019/20", 90: "2020/21"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("statsbomb")


def get_json(path: str, cache_name: str | None = None):
    """네트워크 호출 결과를 캐시한다. 재실행 시 이미 받은 경기는 건너뛴다."""
    if cache_name:
        cached = CACHE / cache_name
        if cached.exists():
            return json.loads(cached.read_text(encoding="utf-8"))
    for attempt in range(4):
        try:
            r = requests.get(f"{BASE}/{path}", headers=UA, timeout=90)
            r.raise_for_status()
            data = r.json()
            if cache_name:
                (CACHE / cache_name).write_text(json.dumps(data), encoding="utf-8")
            return data
        except (requests.RequestException, ValueError) as exc:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
            log.warning("재시도 %d — %s (%s)", attempt + 1, path, type(exc).__name__)
    return None


def collect_matches() -> pd.DataFrame:
    rows = []
    for sid, label in SEASONS.items():
        for m in get_json(f"matches/{LALIGA}/{sid}.json", f"matches_{sid}.json"):
            h, a = m["home_team"]["home_team_name"], m["away_team"]["away_team_name"]
            if CLUB not in h and CLUB not in a:
                continue
            is_home = CLUB in h
            rows.append({
                "match_id": m["match_id"], "season": label, "date": m["match_date"],
                "venue": "홈" if is_home else "원정",
                "opponent": a if is_home else h,
                "gf": m["home_score"] if is_home else m["away_score"],
                "ga": m["away_score"] if is_home else m["home_score"],
            })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def parse_events(match_id: int, meta: dict) -> tuple[list, list, dict]:
    """한 경기 이벤트에서 슛·바르사 패스·선수별 집계를 뽑는다."""
    events = get_json(f"events/{match_id}.json", f"events_{match_id}.json")
    shots, passes, players = [], [], {}

    for e in events:
        etype = e["type"]["name"]
        team = e.get("team", {}).get("name", "")
        player = e.get("player", {}).get("name")
        loc = e.get("location") or [None, None]

        if player:
            p = players.setdefault(player, {
                "player": player, "team": team, "minutes_seen": 0,
                "passes": 0, "passes_completed": 0, "shots": 0, "goals": 0,
                "xg": 0.0, "carries": 0, "dribbles": 0, "pressures": 0,
                "tackles": 0, "interceptions": 0,
            })
            p["minutes_seen"] = max(p["minutes_seen"], e.get("minute", 0))

        if etype == "Shot":
            sh = e["shot"]
            xg = sh.get("statsbomb_xg", 0.0) or 0.0
            outcome = sh.get("outcome", {}).get("name", "")
            shots.append({
                "match_id": match_id, "season": meta["season"], "team": team,
                "is_barca": team == CLUB, "player": player,
                "minute": e.get("minute"), "x": loc[0], "y": loc[1],
                "xg": xg, "outcome": outcome, "goal": outcome == "Goal",
                "body_part": sh.get("body_part", {}).get("name", ""),
                "technique": sh.get("technique", {}).get("name", ""),
                "pattern": e.get("play_pattern", {}).get("name", ""),
            })
            if player:
                players[player]["shots"] += 1
                players[player]["xg"] += xg
                players[player]["goals"] += int(outcome == "Goal")

        elif etype == "Pass":
            ps = e["pass"]
            end = ps.get("end_location") or [None, None]
            complete = "outcome" not in ps  # StatsBomb은 성공 패스에 outcome을 안 넣는다
            if team == CLUB:
                passes.append({
                    "match_id": match_id, "season": meta["season"], "player": player,
                    "x": loc[0], "y": loc[1], "end_x": end[0], "end_y": end[1],
                    "complete": complete,
                    "length": ps.get("length"), "angle": ps.get("angle"),
                    "height": ps.get("height", {}).get("name", ""),
                    "pass_type": ps.get("type", {}).get("name", ""),
                    "is_cross": bool(ps.get("cross")),
                    "is_assist": bool(ps.get("goal_assist")),
                })
            if player:
                players[player]["passes"] += 1
                players[player]["passes_completed"] += int(complete)

        elif etype == "Carry" and player:
            players[player]["carries"] += 1
        elif etype == "Dribble" and player:
            players[player]["dribbles"] += int(
                e.get("dribble", {}).get("outcome", {}).get("name") == "Complete")
        elif etype == "Pressure" and player:
            players[player]["pressures"] += 1
        elif etype == "Duel" and player:
            if e.get("duel", {}).get("type", {}).get("name", "").startswith("Tackle"):
                players[player]["tackles"] += 1
        elif etype == "Interception" and player:
            players[player]["interceptions"] += 1

    return shots, passes, players


def main() -> None:
    matches = collect_matches()
    matches.to_parquet(OUT / "matches.parquet", index=False)
    log.info("경기 %d건 (%s ~ %s)", len(matches),
             matches["season"].iloc[0], matches["season"].iloc[-1])

    all_shots, all_passes, all_players = [], [], []
    t0 = time.time()
    for i, m in enumerate(matches.itertuples(), 1):
        meta = {"season": m.season}
        try:
            shots, passes, players = parse_events(m.match_id, meta)
        except Exception as exc:  # noqa: BLE001 — 한 경기 실패로 전체를 멈추지 않는다
            log.error("[%d/%d] match %s — %s: %s", i, len(matches), m.match_id,
                      type(exc).__name__, exc)
            continue
        all_shots += shots
        all_passes += passes
        for p in players.values():
            p |= {"match_id": m.match_id, "season": m.season,
                  "opponent": m.opponent, "venue": m.venue}
            all_players.append(p)

        if i % 25 == 0 or i == len(matches):
            rate = (time.time() - t0) / i
            log.info("[%d/%d] 슛 %d · 패스 %d · 평균 %.1fs/경기 · 남은 %.0f분",
                     i, len(matches), len(all_shots), len(all_passes),
                     rate, rate * (len(matches) - i) / 60)

    pd.DataFrame(all_shots).to_parquet(OUT / "shots.parquet", index=False)
    pd.DataFrame(all_passes).to_parquet(OUT / "passes.parquet", index=False)
    pd.DataFrame(all_players).to_parquet(OUT / "player_match.parquet", index=False)

    log.info("완료 — 슛 %d · 패스 %d · 선수-경기 %d · %.1f분",
             len(all_shots), len(all_passes), len(all_players), (time.time() - t0) / 60)
    for f in sorted(OUT.glob("*.parquet")):
        log.info("  %-22s %6.1fMB", f.name, f.stat().st_size / 1024 / 1024)


if __name__ == "__main__":
    main()
