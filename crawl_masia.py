"""라 마시아 — 바르사 B팀(FC Barcelona Atlètic)을 거친 선수를 찾는다.

유스 출신을 가려내는 가장 확실한 신호는 B팀 등록 이력이다. Transfermarkt
선수 프로필의 '유스 클럽' 항목은 입단 전 클럽만 적히는 경우가 있어(메시는
그란돌리·뉴웰스만 나온다) 그대로 쓰면 정작 라 마시아 상징 선수가 빠진다.

B팀 시즌 스쿼드를 훑으면 시즌당 요청 1건으로 명단을 얻는다.

  python crawl_masia.py            # 1990~2025
  python crawl_masia.py 2000 2025  # 연도 범위
"""
import json
import logging
import re
import sys
import time
import unicodedata
from pathlib import Path

EPL = Path(r"D:\workspace\EPL project")
sys.path.insert(0, str(EPL))
from crawlers.base_agent import BaseCrawlerAgent  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "processed" / "masia.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

B_TEAM_ID = 2464  # FC Barcelona Atlètic
URL = ("https://www.transfermarkt.com/fc-barcelona-atletic/kader/verein/{cid}"
       "/saison_id/{year}/plus/1")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("masia")


class TMAgent(BaseCrawlerAgent):
    def __init__(self):
        super().__init__(source_name="transfermarkt", min_interval=5.0)


def slug(name: str) -> str:
    """발음기호를 벗기고 소문자로. 다른 소스의 이름과 맞추기 위한 키."""
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"[^a-z ]", "", n.lower()).strip()


def parse_squad(soup) -> list[dict]:
    out, seen = [], set()
    for img in soup.select("img.bilderrahmen-fixed, img[data-src*='portrait']"):
        src = img.get("data-src") or img.get("src") or ""
        if "portrait" not in src:
            continue
        m = re.search(r"/portrait/[a-z]+/(\d+)-", src)
        name = (img.get("title") or img.get("alt") or "").strip()
        if not m or not name or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        out.append({"name": name, "tm_id": m.group(1)})
    return out


def main() -> None:
    years = range(1990, 2026)
    if len(sys.argv) == 3:
        years = range(int(sys.argv[1]), int(sys.argv[2]) + 1)
    years = list(years)

    index = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    agent = TMAgent()
    t0 = time.time()
    try:
        for i, year in enumerate(years, 1):
            try:
                soup = agent.fetch(URL.format(cid=B_TEAM_ID, year=year))
            except Exception as exc:  # noqa: BLE001 — 한 시즌 실패로 멈추지 않는다
                log.error("%d — %s: %s", year, type(exc).__name__, exc)
                continue
            if not soup:
                log.warning("%d — 응답 없음", year)
                continue
            squad = parse_squad(soup)
            season = f"{year}/{str(year + 1)[-2:]}"
            for p in squad:
                key = slug(p["name"])
                if not key:
                    continue
                e = index.setdefault(key, {"name": p["name"], "tm_id": p["tm_id"],
                                           "b_seasons": []})
                if season not in e["b_seasons"]:
                    e["b_seasons"].append(season)
            OUT.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
            rate = (time.time() - t0) / i
            log.info("[%d/%d] %s — B팀 %d명 · 누적 %d명 · 남은 %.0f분",
                     i, len(years), season, len(squad), len(index),
                     rate * (len(years) - i) / 60)
    finally:
        agent.close()

    log.info("완료 — B팀을 거친 선수 %d명 · %.1f분", len(index), (time.time() - t0) / 60)


if __name__ == "__main__":
    main()
