"""페이지가 실제로 그려지는지 훑는다.

    python tools/smoke.py              # 떠 있는 서버를 찾아 검사
    python tools/smoke.py --port 8501  # 포트 지정

tools/audit.py 가 데이터를 보는 반면 이쪽은 **화면**을 본다.
200 만 확인하면 안 된다 — Streamlit 은 페이지가 예외로 죽어도 200 을 준다.
그래서 응답 본문이 아니라 **렌더된 뒤의 상태**를 봐야 하는데, 헤드리스로는
거기까지 못 간다. 대신 여기서는 그 직전까지를 자동으로 잡는다.

  1) app.py 의 st.navigation 에 등록된 페이지를 읽어 목록을 만든다
     (목록을 손으로 적으면 페이지를 늘렸을 때 조용히 빠진다)
  2) 각 페이지 모듈을 **임포트해 실제로 실행**한다. 예외가 나면 잡힌다.
  3) HTTP 200 도 함께 확인한다.

브라우저에서만 드러나는 것(CSS 가 무시됐다, 라벨이 겹친다, 이미지가
안 떴다)은 여전히 사람이 봐야 한다. barca-qa 의 2층을 보라.
"""
import argparse
import re
import sys
import traceback
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def pages() -> list[tuple[str, str]]:
    """app.py 에 등록된 (모듈경로, URL슬러그) 목록."""
    src = (ROOT / "app.py").read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r'st\.Page\(\s*"([^"]+)"[^)]*?(default=True)?\s*\)', src):
        path, is_default = m.group(1), bool(m.group(2))
        slug = "" if is_default else Path(path).stem
        out.append((path, slug))
    return out


def run_module(path: str) -> str | None:
    """페이지를 실제로 실행해 예외를 잡는다. 정상이면 None."""
    import streamlit as st
    from streamlit.testing.v1 import AppTest
    try:
        at = AppTest.from_file(str(ROOT / path), default_timeout=120)
        at.run()
        if at.exception:
            return "; ".join(str(e.message)[:200] for e in at.exception)
        return None
    except Exception:                       # noqa: BLE001 - 무엇이든 보고해야 한다
        return traceback.format_exc(limit=3)[-400:]


def find_port(given: int | None) -> int | None:
    for p in ([given] if given else [8501, 8502, 8503, 8533]):
        try:
            if requests.get(f"http://localhost:{p}", timeout=3).status_code == 200:
                return p
        except requests.RequestException:
            continue
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=None)
    ap.add_argument("--no-http", action="store_true", help="HTTP 확인을 건너뛴다")
    args = ap.parse_args()

    plist = pages()
    print(f"등록된 페이지 {len(plist)}개\n")

    fails = []

    print("=== 실행 (예외 검사) ===")
    for path, slug in plist:
        err = run_module(path)
        name = slug or "/"
        print(f"  [{'X ' if err else 'OK'}] {name:14s} {path}")
        if err:
            print(f"        {err.splitlines()[-1][:160]}")
            fails.append(f"{name}: {err.splitlines()[-1][:160]}")

    if not args.no_http:
        port = find_port(args.port)
        if port is None:
            print("\n=== HTTP ===\n  떠 있는 서버가 없어 건너뛴다.")
        else:
            print(f"\n=== HTTP (포트 {port}) ===")
            for _, slug in plist:
                url = f"http://localhost:{port}/{slug}"
                try:
                    code = requests.get(url, timeout=10).status_code
                except requests.RequestException as e:
                    code = f"연결 실패 {e.__class__.__name__}"
                ok = code == 200
                print(f"  [{'OK' if ok else 'X '}] {slug or '/':14s} {code}")
                if not ok:
                    fails.append(f"{slug or '/'}: HTTP {code}")

    print("\n" + "=" * 52)
    print("실패:", fails if fails else "없음")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
