"""Download and validate the current La Liga results CSV atomically."""
from __future__ import annotations

import argparse
import csv
import io
import re
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = ROOT / "data" / "raw" / "SP1_2627.csv"
DEFAULT_URL = "https://raw.githubusercontent.com/openfootball/espana/master/2026-27/1-liga.txt"
KEY = ("Date", "HomeTeam", "AwayTeam")
REQUIRED = (*KEY, "Div", "FTHG", "FTAG", "FTR")
TEAM_NAMES = {
    "Deportivo Alavés": "Alaves", "Getafe CF": "Getafe", "Sevilla FC": "Sevilla",
    "Rayo Vallecano de Madrid": "Vallecano", "Real Racing Club de Santander": "Santander",
    "Villarreal CF": "Villarreal", "RCD Espanyol de Barcelona": "Espanol",
    "Levante UD": "Levante", "RC Deportivo La Coruña": "La Coruna", "Elche CF": "Elche",
    "Club Atlético de Madrid": "Ath Madrid", "Málaga CF": "Malaga",
    "Real Betis Balompié": "Betis", "Real Sociedad de Fútbol": "Sociedad",
    "Athletic Club": "Ath Bilbao", "Valencia CF": "Valencia", "Real Madrid CF": "Real Madrid",
    "FC Barcelona": "Barcelona", "CA Osasuna": "Osasuna", "RC Celta de Vigo": "Celta",
}
MONTH = {m: i for i, m in enumerate(
    ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"), 1)}


def read_rows(raw: bytes) -> list[dict[str, str]]:
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    text = raw.decode("latin-1")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or not set(REQUIRED).issubset(rows[0]):
        raise ValueError("필수 경기 결과 열이 없는 응답입니다")
    complete = [r for r in rows if all((r.get(c) or "").strip() for c in REQUIRED)]
    if len(complete) != len(rows):
        raise ValueError("결과가 비어 있는 행이 포함됐습니다")
    if not any(r["HomeTeam"] == "Barcelona" or r["AwayTeam"] == "Barcelona" for r in rows):
        raise ValueError("Barcelona 경기가 없습니다")
    return rows


def validate_update(old: bytes, new: bytes) -> tuple[int, int]:
    old_rows, new_rows = read_rows(old), read_rows(new)
    old_keys = {tuple(r[c] for c in KEY) for r in old_rows}
    new_keys = {tuple(r[c] for c in KEY) for r in new_rows}
    missing = old_keys - new_keys
    if missing:
        raise ValueError(f"기존 완료 경기 {len(missing)}건이 새 원본에서 사라졌습니다")
    if len(new_rows) < len(old_rows):
        raise ValueError("새 원본의 경기 수가 감소했습니다")
    return len(old_rows), len(new_rows)


def merge_openfootball(old: bytes, source: bytes) -> bytes:
    """Append completed OpenFootball results using the existing CSV schema."""
    old_text = old.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(old_text))
    rows, fields = list(reader), reader.fieldnames
    if not fields:
        raise ValueError("기존 CSV 헤더가 없습니다")
    known = {(r["Date"], r["HomeTeam"], r["AwayTeam"]) for r in rows}
    current_date = None
    date_re = re.compile(r"^\s+(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) ([A-Z][a-z]{2}) (\d{1,2})(?: (\d{4}))?\s*$")
    match_re = re.compile(r"^\s+(?:(\d{1,2}:\d{2})\s+)?(.+?)\s+v\s+(.+?)\s+(\d+)-(\d+)(?:\s+\((\d+)-(\d+)\))?\s*$")
    for line in source.decode("utf-8-sig").splitlines():
        if date_match := date_re.match(line):
            month, day, explicit_year = date_match.groups()
            year = int(explicit_year) if explicit_year else (2027 if MONTH[month] <= 6 else 2026)
            current_date = datetime(year, MONTH[month], int(day)).strftime("%d/%m/%Y")
            continue
        match = match_re.match(line)
        if not match or current_date is None:
            continue
        time_value, home_raw, away_raw, hg, ag, hthg, htag = match.groups()
        if home_raw not in TEAM_NAMES or away_raw not in TEAM_NAMES:
            raise ValueError(f"팀 이름 매핑이 없습니다: {home_raw} / {away_raw}")
        home, away = TEAM_NAMES[home_raw], TEAM_NAMES[away_raw]
        key = (current_date, home, away)
        if key in known:
            continue
        row = {field: "" for field in fields}
        values = dict(Div="SP1", Date=current_date, Time=time_value or "", HomeTeam=home,
                      AwayTeam=away, FTHG=hg, FTAG=ag,
                      FTR="H" if int(hg) > int(ag) else ("A" if int(hg) < int(ag) else "D"))
        if hthg is not None:
            values.update(HTHG=hthg, HTAG=htag,
                          HTR="H" if int(hthg) > int(htag) else ("A" if int(hthg) < int(htag) else "D"))
        row.update({key: value for key, value in values.items() if key in row})
        rows.append(row)
        known.add(key)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def download(url: str, attempts: int = 5) -> bytes:
    error = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "fc-barcelona-dashboard/1.0"})
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read()
        except Exception as exc:  # network errors must fail the workflow, not corrupt data
            error = exc
            if attempt + 1 < attempts:
                time.sleep(min(15 * (2 ** attempt), 60))
    raise RuntimeError(f"결과 다운로드 {attempts}회 실패: {error}") from error


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    args = parser.parse_args()

    old = args.target.read_bytes()
    source = download(args.url)
    new = merge_openfootball(old, source) if args.url.endswith(".txt") else source
    old_count, new_count = validate_update(old, new)
    if new == old:
        print(f"변경 없음: {old_count}경기")
        return
    temp = args.target.with_suffix(".csv.tmp")
    temp.write_bytes(new)
    temp.replace(args.target)
    print(f"결과 갱신: {old_count} → {new_count}경기")


if __name__ == "__main__":
    main()
