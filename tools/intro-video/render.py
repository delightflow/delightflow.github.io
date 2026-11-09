# intro-v2.html 을 Playwright 로 프레임 캡처한 뒤 ffmpeg 로 MP4·WebM·poster 를 만든다
"""사용법: python tools/intro-video/render.py [프레임 임시 폴더]

결과: media/delightflow-intro-v2.mp4, .webm, -poster.jpg
"""
import pathlib
import shutil
import subprocess
import sys

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = pathlib.Path(__file__).resolve().parent / "intro-v2.html"
OUT = ROOT / "media"
FPS = 30
FRAMES = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".frames"

# 색 범위를 limited(tv)·bt709 로 명시한다. 태그가 없으면 Chrome 에서 WebM 디코드 오류가 난 사례가 있다.
COLOR = [
    "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
    "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
]


def capture() -> None:
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(SRC.as_uri() + "?capture=1")
        page.wait_for_timeout(500)
        total = int(page.evaluate("window.DURATION") * FPS)
        for i in range(total):
            page.evaluate(f"window.render({i / FPS})")
            page.screenshot(path=str(FRAMES / f"f{i:04d}.png"))
            if i % 150 == 0:
                print(f"frame {i}/{total}", flush=True)
        browser.close()


def encode() -> None:
    src = ["-framerate", str(FPS), "-i", str(FRAMES / "f%04d.png")]
    run = lambda args: subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], check=True)
    run([*src, *COLOR, "-c:v", "libx264", "-preset", "slow", "-crf", "24", "-profile:v", "high",
         "-movflags", "+faststart", "-an", str(OUT / "delightflow-intro-v2.mp4")])
    run([*src, *COLOR, "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "38", "-row-mt", "1",
         "-deadline", "good", "-cpu-used", "2", "-an", str(OUT / "delightflow-intro-v2.webm")])
    # 포스터: 첫 장면 워드마크가 다 올라온 시점(3초)
    run(["-i", str(FRAMES / f"f{3 * FPS:04d}.png"), "-q:v", "4", str(OUT / "delightflow-intro-v2-poster.jpg")])


if __name__ == "__main__":
    capture()
    encode()
    print("done")
