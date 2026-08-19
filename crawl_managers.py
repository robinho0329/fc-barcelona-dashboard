"""Transfermarkt 감독 이력에서 바르셀로나 역대 감독과 사진을 받는다.

이력 페이지 한 장에 이름·생년월일·부임일·이임일·재임일수와 포트레이트가
모두 들어 있어 HTML 요청은 1건이면 된다. 사진은 CDN에서 따로 받는다.

성적(경기·승무패·승점)은 여기서 가져오지 않는다. TM 표의 수치는 대회를
모두 합친 값이라, 이 대시보드가 쓰는 라리가 원본과 기준이 어긋난다.
build_managers.py가 재임 기간과 경기 날짜를 맞춰 직접 집계한다.

  python crawl_managers.py
"""
import json
import logging
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import sys

EPL = Path(r"D:\workspace\EPL project")
sys.path.insert(0, str(EPL))
from crawlers.base_agent import BaseCrawlerAgent  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets" / "managers"
INDEX = ROOT / "data" / "processed" / "managers_raw.json"
OUT.mkdir(parents=True, exist_ok=True)
INDEX.parent.mkdir(parents=True, exist_ok=True)

URL = ("https://www.transfermarkt.com/fc-barcelona/mitarbeiterhistorie"
       "/verein/131/personalie_id/Trainer")
IMG_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Referer": "https://www.transfermarkt.com/",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("managers")


class TMAgent(BaseCrawlerAgent):
    def __init__(self):
        super().__init__(source_name="transfermarkt", min_interval=5.0)


def parse(soup: BeautifulSoup) -> list[dict]:
    """이력 표에서 감독 한 명당 한 건씩 뽑는다.

    표가 한 감독을 여러 행에 걸쳐 그리므로, 부임일(dd/mm/yyyy)이 들어 있는
    행만 실제 재임 기록으로 본다.
    """
    out = []
    for tr in soup.select("table.items tbody tr"):
        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        dates = [t for t in tds if re.fullmatch(r"\d{2}/\d{2}/\d{4}", t)]
        if len(dates) < 2:  # 생년월일 + 부임일이 있어야 재임 행
            continue
        img = tr.find("img")
        src = (img.get("data-src") or img.get("src") or "") if img else ""
        m = re.search(r"/portrait/[a-z]+/(\d+)-", src)
        if not m:
            continue
        name = (img.get("title") or img.get("alt") or "").strip()
        appointed = dates[1]
        left = dates[2] if len(dates) > 2 else ""
        out.append({
            "name": name, "tm_id": m.group(1), "born": dates[0],
            "appointed": appointed, "left": left,
            "img": re.sub(r"/portrait/(small|medium|header)/", "/portrait/big/", src),
        })
    # 같은 감독이 두 번 부임하면 두 건 다 남긴다. 완전 중복만 제거.
    seen, uniq = set(), []
    for r in out:
        key = (r["tm_id"], r["appointed"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq


def download(url: str, dest: Path) -> bool:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=IMG_HEADERS, timeout=30)
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 200 and len(r.content) > 1200:
            dest.write_bytes(r.content)
            return True
        if r.status_code == 404:
            return False
        time.sleep(2 * (attempt + 1))
    return False


def main() -> None:
    agent = TMAgent()
    try:
        soup = agent.fetch(URL)
    finally:
        agent.close()
    if not soup:
        raise SystemExit("감독 이력 페이지 응답 없음")

    rows = parse(soup)
    log.info("재임 기록 %d건 · 감독 %d명", len(rows), len({r["tm_id"] for r in rows}))

    got = 0
    for r in rows:
        dest = OUT / f"{r['tm_id']}.jpg"
        if not dest.exists() and download(r["img"], dest):
            got += 1
            time.sleep(0.35)
        r["file"] = dest.name if dest.exists() else ""

    INDEX.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    mb = sum(f.stat().st_size for f in OUT.glob("*.jpg")) / 1024 / 1024
    log.info("사진 신규 %d장 · 총 %d장 · %.1fMB", got, len(list(OUT.glob("*.jpg"))), mb)
    for r in rows[:6]:
        log.info("  %-26s %s ~ %s", r["name"], r["appointed"], r["left"] or "현재")


if __name__ == "__main__":
    main()
