"""assets/_inbox/ 에 넣은 사진을 대시보드 자산으로 반영한다.

사용자가 직접 고른 사진을 쓰기 위한 경로다. 파일명 앞부분으로 대상을 정하며
(messi / cruyff / ronaldinho / puyol ...), 확장자는 무엇이든 된다.

  1) assets/_inbox/ 에 파일을 넣는다  (예: messi.jpg, puyol.png)
  2) python apply_inbox.py

레전드 페이지와 홈 페이지가 함께 쓰는 인물은 양쪽에 복사한다.
"""
import json
import logging
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
INBOX = ROOT / "assets" / "_inbox"
ASSETS = ROOT / "assets"
LEGENDS = ASSETS / "legends"
CLASICO = ASSETS / "clasico"
ERAS_DIR = ASSETS / "eras"
MVP_DIR = ASSETS / "mvp"
MSN_DIR = ASSETS / "msn"
MASIA_DIR = ASSETS / "masia"

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("inbox")

# 키 -> 저장할 자산 폴더 목록. 여러 페이지가 함께 쓰는 인물은 양쪽에 넣는다.
#   legends = 레전드 카드,  home = 홈 페이지,  clasico = 엘클라시코 갤러리
TARGETS = {
    "messi": ["legends", "home"],
    "cruyff": ["legends", "home"],
    "ronaldinho": ["legends"],
    "puyol": ["legends"],
    "xavi": ["legends"],
    "iniesta": ["legends"],
    "kubala": ["legends"],
    "guardiola": ["legends"],
    "stoichkov": ["legends"],
    "suarez": ["legends"],
    "camp_nou": ["home"],
    # 삼각편대 2기 (MSN) — 선수별 사진
    "msn_messi": ["msn"], "msn_suarez": ["msn"], "msn_neymar": ["msn"],
    # 삼각편대 1기 (MVP) — 선수별 사진
    "mvp_messi": ["mvp"], "mvp_villa": ["mvp"], "mvp_pedro": ["mvp"],
    # 라 마시아 대표 선수 (바르사 유니폼 사진으로 넣을 것)
    "yamal": ["masia"], "cubarsi": ["masia"], "gavi": ["masia"],
    "pedri": ["masia"], "fermin": ["masia"], "busquets": ["masia"],
    # 역사·시대 분석 카드
    "era_dreamteam": ["eras"], "era_transition": ["eras"],
    "era_rijkaard": ["eras"], "era_pep": ["eras"],
    "era_msn": ["eras"], "era_post": ["eras"], "era_rebuild": ["eras"],
    # 엘클라시코 갤러리
    "figo": ["clasico"],
    "sunyol": ["clasico"],
    "franco": ["clasico"],
    "di_stefano": ["clasico"],
    "coronacion": ["clasico"],
    "bernabeu": ["clasico"],
}

STORE = {"legends": LEGENDS, "home": ASSETS, "clasico": CLASICO,
         "eras": ERAS_DIR, "masia": MASIA_DIR, "mvp": MVP_DIR, "msn": MSN_DIR}
MAX_W = 900
MAX_W_WIDE = 1200  # 시대 카드처럼 가로로 쓰는 이미지


# 반입 키와 실제 파일명이 다른 경우. mvp_messi 는 legends/messi 와 겹치지
# 않게 키를 나눴을 뿐, 저장은 mvp/messi.jpg 로 해야 페이지가 읽는다.
FILENAME = {"mvp_messi": "messi", "mvp_villa": "villa", "mvp_pedro": "pedro",
            "msn_messi": "messi", "msn_suarez": "suarez",
            "msn_neymar": "neymar"}


def save_as(src: Path, dest: Path) -> None:
    """JPEG로 통일해 저장. 폭이 크면 줄인다."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGB")
    w, h = im.size
    if w > MAX_W:
        im = im.resize((MAX_W, int(h * MAX_W / w)), Image.LANCZOS)
    im.save(dest, "JPEG", quality=88, optimize=True)


def note_source(store: Path, key: str, filename: str) -> None:
    """출처를 '사용자 제공'으로 남긴다. 커먼즈 항목은 건드리지 않는다."""
    p = store / "credits.json"
    meta = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    name = FILENAME.get(key, key)
    rel = f"{name}.jpg" if store == ASSETS else f"{store.name}/{name}.jpg"
    meta[key] = {"file": rel, "license": "사용자 제공", "artist": "사용자 제공",
                 "source": f"직접 전달한 파일 ({filename})"}
    p.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    files = [f for f in sorted(INBOX.iterdir())
             if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}] \
        if INBOX.exists() else []
    if not files:
        sys.exit(f"{INBOX} 에 이미지가 없습니다. 파일을 넣고 다시 실행하세요.")

    applied = 0
    for f in files:
        # 파일명이 그대로 키다. 예전에는 '_' 앞만 잘라 썼는데 era_dreamteam 처럼
        # 밑줄이 든 키가 'era'로 잘려 버렸다. 이제는 전체 이름으로 먼저 찾고,
        # 없을 때만 구분자 앞부분으로 한 번 더 본다.
        stem = f.stem.lower().strip()
        key = stem if stem in TARGETS else stem.split("_")[0].split("-")[0].strip()
        if key not in TARGETS:
            log.warning("건너뜀 %-22s — 대상 이름이 아닙니다 (%s)",
                        f.name, ", ".join(TARGETS))
            continue
        dests = TARGETS[key]
        for d in dests:
            store = STORE[d]
            save_as(f, store / f"{FILENAME.get(key, key)}.jpg")
            note_source(store, key, f.name)
        log.info("반영 %-14s <- %-26s (%s)", key, f.name, " + ".join(dests))
        applied += 1

    log.info("\n%d개 반영 완료. 브라우저를 새로고침하면 바로 보입니다.", applied)


if __name__ == "__main__":
    main()
