"""Fetch the free current-season Barcelona snapshot used outside the home page.

FotMob's team endpoint exposes the active squad, La Liga player tables, team
tables and fixtures without an API key.  This is an *aggregate* snapshot: it
does not claim to contain event-level pass coordinates.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from update_leaders import TEAM_ID, TEAM_URL, fetch_json

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data" / "processed" / "current_2627.json"
PLAYER_STATS = ("goals", "goal_assist", "rating", "mins_played", "expected_goals", "accurate_pass")
TEAM_STATS = ("possession_percentage_team", "goals_team_match", "expected_goals_team")


def stat_rows(table: dict) -> list[dict]:
    """Return only Barcelona entries from a FotMob leaderboard response."""
    lists = table.get("TopLists", [])
    if not lists:
        return []
    return [
        {"name": row["ParticipantName"], "value": row.get("StatValue"),
         "minutes": row.get("MinutesPlayed"), "matches": row.get("MatchesPlayed")}
        for row in lists[0].get("StatList", [])
        if int(row.get("TeamId", 0)) == TEAM_ID
    ]


def main() -> None:
    team = fetch_json(TEAM_URL)
    player_urls = {x.get("name"): x.get("fetchAllUrl") for x in team.get("stats", {}).get("players", [])}
    team_urls = {u.rsplit("/", 1)[-1].removesuffix(".json"): u
                 for x in team.get("stats", {}).get("teams", [])
                 if (u := x.get("fetchAllUrl"))}

    players: dict[str, dict] = {}
    for stat in PLAYER_STATS:
        for row in stat_rows(fetch_json(player_urls[stat])):
            item = players.setdefault(row["name"], {"Player": row["name"]})
            item[stat] = row["value"]
            item["minutes"] = row["minutes"]
            item["matches"] = row["matches"]

    squad = []
    for group in team.get("squad", {}).get("squad", []):
        for member in group.get("members", []):
            if member.get("excludeFromRanking"):
                continue
            squad.append({"Player": member.get("name"), "Pos": member.get("positionIdsDesc"),
                          "Age": member.get("age"), "shirt": member.get("shirtNumber")})

    team_stats = {}
    for stat in TEAM_STATS:
        rows = stat_rows(fetch_json(team_urls[stat]))
        if rows:
            team_stats[stat] = rows[0]["value"]

    fixtures = []
    for fixture in team.get("fixtures", {}).get("allFixtures", {}).get("fixtures", []):
        status = fixture.get("status", {})
        if not status.get("finished"):
            continue
        home, away = fixture.get("home", {}), fixture.get("away", {})
        fixtures.append({"id": fixture.get("id"), "date": status.get("utcTime"),
                         "competition": fixture.get("tournament", {}).get("name"),
                         "home": home.get("name"), "away": away.get("name"),
                         "home_score": home.get("score"), "away_score": away.get("score")})

    payload = {
        "season": "2026/27", "source": "FotMob", "updated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "무료 집계 데이터: 선수·팀·경기 결과. 패스 좌표와 전체 이벤트는 포함하지 않음.",
        "players": sorted(players.values(), key=lambda r: (-float(r.get("goals") or 0), r["Player"])),
        "squad": squad, "team_stats": team_stats, "fixtures": fixtures,
    }
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"현재 시즌 스냅샷: 선수 {len(players)}명 · 명단 {len(squad)}명 · 결과 {len(fixtures)}경기")


if __name__ == "__main__":
    main()
