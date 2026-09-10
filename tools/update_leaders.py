"""Fetch current-season Barcelona La Liga goals and assists from FotMob."""
from __future__ import annotations

import json
import gzip
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data" / "processed" / "current_leaders.json"
TEAM_URL = "https://www.fotmob.com/api/data/teams?id=8634&ccode3=USA"
TEAM_ID = 8634


def fetch_json(url: str, attempts: int = 3) -> dict:
    error = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
                if raw.startswith(b"\x1f\x8b"):
                    raw = gzip.decompress(raw)
                return json.loads(raw.decode("utf-8"))
        except Exception as exc:
            error = exc
            if attempt + 1 < attempts:
                time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"선수 리더 다운로드 실패: {error}") from error


def extract_stat(table: dict, stat_name: str) -> list[dict]:
    lists = table.get("TopLists", [])
    target = next((item for item in lists if item.get("StatName") == stat_name), None)
    if target is None:
        raise ValueError(f"FotMob {stat_name} 표가 없습니다")
    players = [
        {"Player": row["ParticipantName"], "value": int(row["StatValue"])}
        for row in target.get("StatList", []) if int(row.get("TeamId", 0)) == TEAM_ID
    ]
    players.sort(key=lambda row: (-row["value"], row["Player"]))
    if not players or players[0]["value"] < 0:
        raise ValueError(f"FotMob {stat_name} 바르셀로나 값이 없습니다")
    return players[:5]


def main() -> None:
    team = fetch_json(TEAM_URL)
    stats = team.get("stats", {}).get("players", [])
    urls = {item.get("name"): item.get("fetchAllUrl") for item in stats}
    if not urls.get("goals") or not urls.get("goal_assist"):
        raise ValueError("FotMob 팀 응답에 득점·도움 표 주소가 없습니다")
    goals = extract_stat(fetch_json(urls["goals"]), "goals")
    assists = extract_stat(fetch_json(urls["goal_assist"]), "goal_assist")
    payload = {"season": "2026/27", "source": "FotMob", "goals": goals, "assists": assists}
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if TARGET.exists() and TARGET.read_bytes() == encoded:
        print("득점·도움 리더 변경 없음")
        return
    temp = TARGET.with_suffix(".json.tmp")
    temp.write_bytes(encoded)
    temp.replace(TARGET)
    print(f"리더 갱신: 득점 {goals[0]['Player']} {goals[0]['value']} · "
          f"도움 {assists[0]['Player']} {assists[0]['value']}")


if __name__ == "__main__":
    main()
