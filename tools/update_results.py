"""Download and validate the current La Liga results CSV atomically."""
from __future__ import annotations

import argparse
import csv
import io
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = ROOT / "data" / "raw" / "SP1_2627.csv"
DEFAULT_URL = "https://www.football-data.co.uk/mmz4281/2627/SP1.csv"
KEY = ("Date", "HomeTeam", "AwayTeam")
REQUIRED = (*KEY, "Div", "FTHG", "FTAG", "FTR")


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

    new = download(args.url)
    old = args.target.read_bytes()
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
