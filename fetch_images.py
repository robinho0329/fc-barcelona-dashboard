"""위키미디어 커먼즈에서 대시보드용 이미지를 받는다.

커먼즈가 짧은 간격 요청에 429를 자주 돌려줘, 요청 사이를 넉넉히 띄우고
실패하면 간격을 늘려 재시도한다. 저작자·라이선스는 credits.json에 남긴다.

  python fetch_images.py legends   # 레전드 인물
  python fetch_images.py clasico   # 엘클라시코 갤러리
  python fetch_images.py           # 둘 다
"""
import json
import logging
import re
import sys
import time
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent
UA = {"User-Agent": "BarcaDashboard/1.0 (educational portfolio project)"}
API = "https://commons.wikimedia.org/w/api.php"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("images")

MESSI = ("Lionel Messi in a La Liga match at Camp Nou, Barcelona "
         "( Ank Kumar, Infosys Limited) ")

# 커먼즈 파일명 -> 저장 키. 후보를 여러 개 두고 먼저 성공하는 것을 쓴다.
# 바르사 시절 사진을 우선한다. 커먼즈에 해당 시기 자유 라이선스 사진이
# 없는 선수(스토이치코프 1990~98, 수아레스 미라몬테스 1954~61)는 어쩔 수 없이
# 후대 사진을 쓰고, 페이지 캡션에 시기가 다르다고 밝힌다.
LEGENDS = {
    # Anefo(네덜란드 국립기록보관소) CC0. 바르사 유니폼을 입은 경기·훈련 사진.
    "cruyff": ["PSV tegen Barcelona (in Tilburg) 2-1, Cruijff (l) en Nordquist (r), "
               "Bestanddeelnr 927-9067.jpg",
               "Feyenoord tegen Barcelona 0-0, Europacup Johan Cruijff springt over "
               "keeper Eddy Treijtel, Bestanddeelnr 927-5354.jpg",
               "Barcelona traint voor wedstrijd tegen Feyenoord Cruijff en Reixach, "
               "Bestanddeelnr 927-5349.jpg",
               "Het elftal van Barcelona, Bestanddeelnr 928-0927.jpg"],
    "ronaldinho": ["Ronaldinhotaking a set piece54.jpg",
                   "Barcelona Ronaldinho Free Kick.jpg",
                   "Ronaldinho 11feb2007.jpg"],
    "puyol": ["Puyol 2010 02 02.jpg", "Carles Puyol 18abr2007.jpg",
              "Puyol tackle.jpg"],
}

# 홈 페이지용 — 바르사 전성기의 경기 중 사진을 쓴다.
# 기존 messi.jpg는 2018 월드컵 아르헨티나 대표팀, cruyff.jpg는 1974 네덜란드
# 대표팀 사진이라 클럽 페이지에 맞지 않았다.
HOME = {
    "messi": [MESSI + "03.jpg", MESSI + "07.jpg", MESSI + "10.jpg",
              MESSI + "01.jpg", "Lionel Messi, 2011.jpg"],
    "cruyff": ["PSV tegen Barcelona (in Tilburg) 2-1, Cruijff (l) en Nordquist (r), "
               "Bestanddeelnr 927-9067.jpg",
               "Feyenoord tegen Barcelona 0-0, Europacup Johan Cruijff springt over "
               "keeper Eddy Treijtel, Bestanddeelnr 927-5354.jpg",
               "Cruijff in de aanval met achter hem Hulshof, Bestanddeelnr 928-0906.jpg",
               "Johan Cruijff in actie, Bestanddeelnr 928-0907.jpg"],
}

CLASICO = {
    "sunyol": ["A Josep Sunyol.JPG",
               "37 Centenari de Josep Sunyol, Rambla 133.jpg",
               "TUMBA DE JOSEP SUÑOL i GARRIGA.jpg"],
    "di_stefano": ["Alfredo Di Stéfano 1959.jpg", "Alfredo Di Stefano.jpg",
                   "Alfredo Di Stéfano.jpg"],
    "figo": ["Luis Figo 2004.jpg", "Luís Figo.jpg", "Figo.jpg"],
    "bernabeu": ["Santiago Bernabéu Stadium 2019.jpg",
                 "Estadio Santiago Bernabéu 2017.jpg",
                 "Santiago Bernabeu Stadium.jpg"],
    "coronacion": ["Copa de la coronacion.jpg", "FC Barcelona B 1902.jpg"],
    "franco": ["Francisco Franco 1959 (cropped).jpg",
               "Francisco Franco circa 1939.jpg", "Francisco Franco 1930.jpg"],
}


# 시대 카드용 — 인물 증명사진이 아니라 그 시대를 떠올리게 하는 장면으로.
# 커먼즈에 바르사 우승 순간 사진이 많지 않아, 없는 시대는 캄 노우·클라시코
# 같은 그 시기 실제 경기 장면으로 대신한다.
ERAS = {
    "era_dreamteam": ["Celebración Barcelona Copa de Europa 1992.jpg"],
    "era_transition": ["F.C. Barcelona. Camp Nou 2006 - panoramio.jpg",
                       "Camp Nou - Home Ground of FC Barcelona.jpg"],
    "era_rijkaard": ["LFP - Barcelona vs Mallorca pre-match - Oct 3rd 2010.jpg",
                     "Barca medals.jpg"],
    "era_pep": ["2010-11-29 Clasico05 (5221488999).jpg",
                "2010-11-29 Clasico11 (5222092056).jpg"],
    "era_msn": ["Festa culé, Barcelona-Juventus. Champions league 2015, Berlin.JPG",
                "Barça Party - Champions League Final 2015 , Barcelona-Juventus.JPG",
                "Barcelona fans - Champions league 2015 Berlin.JPG"],
    "era_post": ["Barcelona BW 2019-10-07 10-48-36.jpg",
                 "Camp Nou, La Liga match (Ank Kumar) 10.jpg",
                 "Camp Nou - Home Ground of FC Barcelona.jpg"],
    "era_rebuild": ["Stadium of Football Club FC Barcelona - Camp Nou.jpg",
                    "Camp Nou - Home Ground of FC Barcelona.jpg",
                    "2014. Camp Nou. Més que un club. Barcelona B40.jpg"],
}


def commons_file(title: str, width: int = 760) -> dict | None:
    r = requests.get(API, headers=UA, timeout=45, params={
        "action": "query", "format": "json", "titles": f"File:{title}",
        "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": width})
    r.raise_for_status()
    for pg in (r.json().get("query", {}).get("pages", {}) or {}).values():
        ii = (pg.get("imageinfo") or [{}])[0]
        if ii.get("thumburl"):
            return ii
    return None


def save(key: str, title: str, out: Path, max_w: int = 640) -> dict | None:
    """한 후보를 받아 저장.

    upload.wikimedia.org는 연속 요청에 429를 IP 단위로 오래 건다. 429를 만나면
    분 단위로 물러섰다가 다시 시도한다. 썸네일이 막히면 원본으로도 시도한다.
    """
    ii = commons_file(title)
    if not ii:
        return None

    img = None
    for url in (ii.get("thumburl"), ii.get("url")):
        if not url:
            continue
        for wait in (0, 75, 180, 360):
            if wait:
                log.info("      429 — %ds 대기 후 재시도", wait)
                time.sleep(wait)
            try:
                r = requests.get(url, headers=UA, timeout=180)
            except requests.RequestException as exc:
                log.info("      %s — %s", title[:36], type(exc).__name__)
                continue
            if r.status_code == 200:
                img = r
                break
            if r.status_code != 429:
                log.info("      %s — HTTP %d", title[:36], r.status_code)
                break
        if img:
            break
    if not img:
        return None

    p = out / f"{key}.jpg"
    p.write_bytes(img.content)
    im = Image.open(p).convert("RGB")
    w, h = im.size
    if w > max_w:
        im = im.resize((max_w, int(h * max_w / w)), Image.LANCZOS)
    im.save(p, "JPEG", quality=84, optimize=True)

    em = ii.get("extmetadata", {})
    return {
        "file": f"{out.name}/{key}.jpg",
        "license": (em.get("LicenseShortName", {}) or {}).get("value", "?"),
        "artist": re.sub(r"<[^>]+>", "", (em.get("Artist", {}) or {}).get("value", "?")).strip()[:44],
        "source": f"https://commons.wikimedia.org/wiki/File:{title}",
    }


def run(group: str, wants: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    cred_path = out / "credits.json"
    meta = json.loads(cred_path.read_text(encoding="utf-8")) if cred_path.exists() else {}

    for key, titles in wants.items():
        if key in meta and (out / f"{key}.jpg").exists():
            log.info("  건너뜀 %s (이미 있음)", key)
            continue
        got = None
        for round_ in range(3):
            for title in titles:
                time.sleep(25 + round_ * 20)  # 429 회피 — 넉넉히 띄운다
                try:
                    got = save(key, title, out)
                except requests.RequestException as exc:
                    log.info("      %s — %s", title[:40], type(exc).__name__)
                    got = None
                if got:
                    break
            if got:
                break
        if got:
            meta[key] = got
            log.info("  OK %-12s %5.0fKB  %-16s %s", key,
                     (out / f"{key}.jpg").stat().st_size / 1024,
                     got["license"], got["artist"][:28])
        else:
            log.warning("  X  %-12s — 후보 %d개 모두 실패", key, len(titles))
        cred_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info("[%s] 완료 — %d개 보유", group, len(meta))


def main() -> None:
    groups = sys.argv[1:] or ["legends", "clasico", "home", "eras"]
    if "legends" in groups:
        run("legends", LEGENDS, ROOT / "assets" / "legends")
    if "clasico" in groups:
        run("clasico", CLASICO, ROOT / "assets" / "clasico")
    if "home" in groups:
        run("home", HOME, ROOT / "assets")
    if "eras" in groups:
        run("eras", ERAS, ROOT / "assets" / "eras")


if __name__ == "__main__":
    main()
