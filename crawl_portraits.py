"""Transfermarkt에서 바르셀로나 선수 증명사진(포트레이트)을 받는다.

시즌 스쿼드 페이지 한 장에 그 시즌 선수 전원의 이름·TM id·포트레이트 URL이
들어 있어, HTML 요청은 시즌당 1건이면 된다. 이미지는 CDN에서 받으므로
Cloudflare 우회가 필요 없고 빠르다.

  python crawl_portraits.py            # 전 시즌
  python crawl_portraits.py 2010 2015  # 연도 범위
"""
import json
import logging
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

EPL = Path(r"D:\workspace\EPL project")
sys.path.insert(0, str(EPL))
from crawlers.base_agent import BaseCrawlerAgent  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets" / "portraits"
INDEX = ROOT / "data" / "processed" / "portraits.json"
OUT.mkdir(parents=True, exist_ok=True)

TM = "https://www.transfermarkt.com"
BARCA_ID = 131
SQUAD_URL = TM + "/fc-barcelona/kader/verein/{cid}/saison_id/{year}/plus/1"
IMG_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"),
    "Referer": TM + "/",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("portraits")


class TMAgent(BaseCrawlerAgent):
    def __init__(self):
        super().__init__(source_name="transfermarkt", min_interval=5.0)


def slug(name: str) -> str:
    """FBref 이름과 맞추기 위한 정규화 키. 발음기호를 벗기고 소문자로."""
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", "", n.lower()).strip()


def parse_squad(soup: BeautifulSoup) -> list[dict]:
    """스쿼드 표에서 (이름, TM id, 포트레이트 URL)을 뽑는다.

    포트레이트는 목록에서 작은 이미지로 나오지만 URL의 /small/ 을 /big/ 으로
    바꾸면 증명사진 크기가 나온다.
    """
    out = []
    for img in soup.select("img.bilderrahmen-fixed, img[data-src*='portrait']"):
        src = img.get("data-src") or img.get("src") or ""
        if "portrait" not in src:
            continue
        name = (img.get("title") or img.get("alt") or "").strip()
        pid = ""
        m = re.search(r"/portrait/[a-z]+/(\d+)-", src)
        if m:
            pid = m.group(1)
        if not name or not pid:
            continue
        big = re.sub(r"/portrait/(small|medium|header)/", "/portrait/big/", src)
        out.append({"name": name, "tm_id": pid, "url": big})
    # 같은 선수가 여러 번 잡히면 첫 건만
    seen, uniq = set(), []
    for p in out:
        if p["tm_id"] in seen:
            continue
        seen.add(p["tm_id"])
        uniq.append(p)
    return uniq


def download(url: str, dest: Path) -> bool:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=IMG_HEADERS, timeout=30)
        except requests.RequestException:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 200 and len(r.content) > 1500:
            dest.write_bytes(r.content)
            return True
        if r.status_code == 404:
            return False
        time.sleep(2 * (attempt + 1))
    return False


def main() -> None:
    years = range(1993, 2026)
    if len(sys.argv) == 3:
        years = range(int(sys.argv[1]), int(sys.argv[2]) + 1)

    index = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {}
    agent = TMAgent()
    t0 = time.time()
    new_players = 0

    for i, year in enumerate(years, 1):
        url = SQUAD_URL.format(cid=BARCA_ID, year=year)
        try:
            soup = agent.fetch(url)
        except Exception as exc:  # noqa: BLE001 — 한 시즌 실패로 멈추지 않는다
            log.error("%d — %s: %s", year, type(exc).__name__, exc)
            continue
        if not soup:
            log.warning("%d — 응답 없음", year)
            continue

        squad = parse_squad(soup)
        got = 0
        for p in squad:
            key = slug(p["name"])
            if not key:
                continue
            dest = OUT / f"{p['tm_id']}.jpg"
            if not dest.exists() and download(p["url"], dest):
                got += 1
                time.sleep(0.35)  # CDN도 예의는 지킨다
            if dest.exists():
                entry = index.setdefault(key, {"name": p["name"], "tm_id": p["tm_id"],
                                               "file": dest.name, "seasons": []})
                season = f"{year}/{str(year + 1)[-2:]}"
                if season not in entry["seasons"]:
                    entry["seasons"].append(season)
                if key not in index:
                    new_players += 1

        INDEX.parent.mkdir(parents=True, exist_ok=True)
        INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
        rate = (time.time() - t0) / i
        log.info("[%d/%d] %d/%02d — 스쿼드 %d명 · 신규 사진 %d · 누적 %d명 · 남은 %.0f분",
                 i, len(list(years)), year, (year + 1) % 100, len(squad), got,
                 len(index), rate * (len(list(years)) - i) / 60)

    total_mb = sum(f.stat().st_size for f in OUT.glob("*.jpg")) / 1024 / 1024
    log.info("완료 — 선수 %d명 · 사진 %d장 · %.1fMB · %.1f분",
             len(index), len(list(OUT.glob("*.jpg"))), total_mb, (time.time() - t0) / 60)


if __name__ == "__main__":
    main()
