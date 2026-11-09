# 메인 랜딩을 로컬 정적 서버로 띄워 데스크톱·375px·reduced-motion 에서 동작을 점검하고 스크린샷을 남긴다
"""사용법: python tools/check_landing.py [스크린샷 폴더]

점검 항목: 콘솔 오류 0, 가로 스크롤 없음, 서비스 카드 실제 URL, 소개 영상 지연 로드·재생,
MP4/WebM 각각 디코드, reduced-motion 시 히어로 인터랙션·자동재생 꺼짐.
"""
import functools
import http.server
import pathlib
import sys
import threading

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHOTS = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".shots"
SERVICES = ["https://inventips.net/", "https://marknser.com/", "https://nextip.ai/", "https://www.patentwith.com/"]
failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        failures.append(msg)


def serve() -> str:
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(Quiet, directory=str(ROOT))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{httpd.server_address[1]}/"


def decode_ok(page, src: str) -> bool:
    return page.evaluate(
        """src => new Promise(res => {
            const v = document.createElement('video'); v.muted = true; v.src = src;
            v.onerror = () => res(false);
            v.oncanplay = () => v.play().then(() => setTimeout(() => res(!v.error && v.currentTime > 0), 600)).catch(() => res(false));
            setTimeout(() => res(false), 8000);
        })""",
        src,
    )


def run_view(browser, url: str, name: str, viewport: dict, reduced: bool = False) -> None:
    ctx = browser.new_context(viewport=viewport, reduced_motion="reduce" if reduced else "no-preference")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(1800)
    tag = f"[{name}]"

    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    check(overflow <= 0, f"{tag} 가로 스크롤 없음 (넘침 {overflow}px)")
    hrefs = page.eval_on_selector_all(".service-card", "els => els.map(e => e.href)")
    check(hrefs == SERVICES, f"{tag} 서비스 카드 URL {hrefs}")
    far = page.eval_on_selector("video.lazy-video", "v => v.getBoundingClientRect().top > innerHeight + 300")
    if far:
        check(page.eval_on_selector("video.lazy-video", "v => !v.currentSrc"), f"{tag} 화면에서 먼 소개 영상은 처음에 로드하지 않음")
    live = page.eval_on_selector("[data-hero]", "h => h.classList.contains('is-live')")
    hero_paused = page.eval_on_selector(".hero-video", "v => v.paused")
    if reduced:
        check(not live and hero_paused, f"{tag} reduced-motion: 히어로 인터랙션 꺼짐·배경 영상 정지")
    else:
        check(live, f"{tag} 히어로 인터랙션 활성")
    page.screenshot(path=str(SHOTS / f"{name}-hero.png"))

    if not reduced and viewport["width"] > 900:
        page.mouse.move(viewport["width"] * 0.8, viewport["height"] * 0.3)
        page.wait_for_timeout(700)
        tx = page.eval_on_selector("[data-hero]", "h => parseFloat(h.style.getPropertyValue('--tx'))")
        check(tx > 0.2, f"{tag} 커서 이동이 --tx 에 반영 ({tx})")
        page.screenshot(path=str(SHOTS / f"{name}-hero-cursor.png"))

    page.locator(".intro-film").scroll_into_view_if_needed()
    page.wait_for_timeout(2500)
    state = page.eval_on_selector("video.lazy-video", "v => ({src: v.currentSrc, t: v.currentTime, paused: v.paused, err: v.error && v.error.code})")
    check(bool(state["src"]) and not state["err"], f"{tag} 소개 영상 지연 로드 {state}")
    if reduced:
        check(state["paused"], f"{tag} reduced-motion: 소개 영상 자동재생 안 함")
    else:
        check(state["t"] > 0 and not state["paused"], f"{tag} 소개 영상 재생 중")
    page.screenshot(path=str(SHOTS / f"{name}-about.png"))
    page.screenshot(path=str(SHOTS / f"{name}-full.png"), full_page=True)
    check(not errors, f"{tag} 콘솔 오류 없음 {errors}")
    ctx.close()


def main() -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    url = serve()
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")  # H.264 디코드는 정식 Chrome 이 필요
        except Exception:
            browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        for f in ["media/delightflow-intro-v2.webm", "media/delightflow-intro-v2.mp4"]:
            check(decode_ok(page, url + f), f"{f} 디코드·재생")
        page.close()
        run_view(browser, url, "desktop", {"width": 1440, "height": 900})
        run_view(browser, url, "mobile", {"width": 375, "height": 812})
        run_view(browser, url, "reduced", {"width": 1440, "height": 900}, reduced=True)
        browser.close()
    print(f"\n{len(failures)} failure(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
