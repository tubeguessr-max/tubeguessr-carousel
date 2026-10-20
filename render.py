"""Builds the three slides as HTML (TikTok-style text) and screenshots them to JPEG."""
import html
import json
import shutil
from pathlib import Path

from PIL import Image, ImageOps
from playwright.sync_api import sync_playwright

import config

try:  # lets Pillow open iPhone HEIC photos, even ones renamed to .jpg
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

ROOT = Path(__file__).parent
W, H = config.WIDTH, config.HEIGHT
OFFSET_Y = (H - 1440) // 2  # keeps the layout centred if you change HEIGHT
GREEN = "#5DB75D"

BASE_CSS = """
@font-face { font-family: 'TikTok Sans'; src: url('TikTokSans.ttf'); font-weight: 300 900; }
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: __W__px; height: __H__px; overflow: hidden; background: #000; }
body { position: relative;
       font-family: 'TikTok Sans', 'Proxima Nova', 'Helvetica Neue', Arial, 'Noto Sans', sans-serif;
       font-weight: __FW__; -webkit-font-smoothing: antialiased; }
.bg { position: absolute; left: 0; top: 0; width: 100%; height: 100%; object-fit: cover; }
.layer { position: absolute; left: 0; right: 0; text-align: center; }
/* multi-line text: every line gets its own rounded highlight, like TikTok's text tool */
.wrap { width: 800px; margin: 0 auto; line-height: 1.18; }
.hl { background: #fff; color: #000; padding: .06em .4em; border-radius: .22em;
      -webkit-box-decoration-break: clone; box-decoration-break: clone; }
/* single-line boxes and pills */
.box { display: table; margin: 0 auto; background: #fff; color: #000; border-radius: .2em;
       padding: .17em .45em; line-height: 1.2; white-space: nowrap; }
.appstore { position: absolute; left: 50%; transform: translateX(-50%); width: auto; height: auto; }
""".replace("__W__", str(W)).replace("__H__", str(H)).replace("__FW__", str(config.FONT_WEIGHT))


def _page(body: str) -> str:
    return (
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        + BASE_CSS
        + "</style></head><body>"
        + body
        + "</body></html>"
    )


def _y(px: int) -> int:
    return px + OFFSET_Y


def _text(s: str) -> str:
    """Escape text; a literal newline becomes a forced line break."""
    return html.escape(s).replace("\n", "<br>")


def slide1_html(hook: str) -> str:
    return _page(
        f'<img class="bg" src="bg1.jpg">'
        f'<div class="layer" style="top:{_y(380)}px"><div class="wrap" style="font-size:56px">'
        f'<span class="hl">{_text(hook)}</span></div></div>'
        f'<div class="layer" style="top:{_y(755)}px"><div class="box" style="font-size:76px">—&gt;</div></div>'
    )


def slide2_html(station_lines: list, line_styles: dict) -> str:
    n = len(station_lines)
    # Pill size shrinks when a station has many lines, so everything still fits above the swipe box.
    fs = min(72, int(717 / (2.173 + 2.207 * n)))
    gap = round(fs * 0.667)
    top = 220 if n <= 4 else 170
    pills = "".join(
        f'<div class="box" style="font-size:{fs}px;margin-top:{0 if i == 0 else gap}px;'
        f'background:{line_styles[name]["bg"]};color:{line_styles[name]["fg"]}">{_text(name)}</div>'
        for i, name in enumerate(station_lines)
    )
    return _page(
        f'<img class="bg" src="bg2.jpg">'
        f'<div class="layer" style="top:{_y(top)}px">'
        f'<div class="box" style="font-size:62px">I’m at a station with</div>'
        f'<div style="height:{round(fs * 1.38)}px"></div>{pills}'
        f'<div style="height:{round(fs * 1.46)}px"></div>'
        f'<div class="box" style="font-size:72px">Where am I??</div></div>'
        f'<div class="layer" style="top:{_y(1170)}px">'
        f'<div class="box" style="font-size:28px;padding:.08em .7em;border-radius:.25em">'
        f"Swipe for the answer —&gt;</div></div>"
    )


def slide3_html(station: str, has_appstore: bool) -> str:
    answer = station + "!"
    fs = min(84, int(1630 / len(answer)))  # long names shrink to fit
    appstore = (
        f'<img class="appstore" src="app-store.png" style="top:{_y(800)}px">' if has_appstore else ""
    )
    return _page(
        f'<img class="bg" src="bg3.jpg">'
        f'<div class="layer" style="top:{_y(125)}px">'
        f'<div class="box" style="font-size:{fs}px;background:{GREEN};color:#fff">{_text(answer)}</div></div>'
        f'<div class="layer" style="top:{_y(300)}px"><div class="wrap" style="font-size:56px">'
        f'<span class="hl">Too easy? Want to test<br>your knowledge more?</span></div></div>'
        f'<div class="layer" style="top:{_y(515)}px"><div class="wrap" style="font-size:56px">'
        f'<span class="hl">Download TubeGuessr on<br>the App Store to play<br>more 😎</span></div></div>'
        + appstore
    )


def _find_appstore():
    """Any png/jpg/webp in assets/ is used, whatever it is called."""
    folder = ROOT / "assets"
    if not folder.exists():
        return None
    for p in sorted(folder.iterdir()):
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            return p
    return None


def prepare_background(src: Path, dest: Path) -> None:
    """Fix phone-photo rotation, crop to the slide size, save as JPEG."""
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        im = ImageOps.fit(im, (W, H), method=Image.LANCZOS, centering=(0.5, 0.5))
        im.save(dest, "JPEG", quality=95)


def render_all(backgrounds: list, station: str, station_lines: list, hook: str, workdir: Path) -> list:
    """backgrounds: three image paths. Returns the three rendered slide JPEG paths."""
    workdir.mkdir(parents=True, exist_ok=True)
    line_styles = json.loads((ROOT / "data" / "lines.json").read_text(encoding="utf-8"))

    for i, src in enumerate(backgrounds, 1):
        prepare_background(Path(src), workdir / f"bg{i}.jpg")

    font = ROOT / "fonts" / "TikTokSans.ttf"
    if font.exists():
        shutil.copy(font, workdir / "TikTokSans.ttf")
    else:
        print("WARNING: fonts/TikTokSans.ttf not found, falling back to a system font.")

    appstore = _find_appstore()
    has_appstore = appstore is not None
    if has_appstore:
        with Image.open(appstore) as im:
            im = ImageOps.contain(im.convert("RGBA"), (606, 590), method=Image.LANCZOS)
            im.save(workdir / "app-store.png", "PNG")
        print("Using App Store image:", appstore.name)
    else:
        print("WARNING: no image found in assets/, slide 3 will have no App Store image.")

    pages = [slide1_html(hook), slide2_html(station_lines, line_styles), slide3_html(station, has_appstore)]
    outputs = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        for i, content in enumerate(pages, 1):
            html_file = workdir / f"slide{i}.html"
            html_file.write_text(content, encoding="utf-8")
            page.goto(html_file.resolve().as_uri())
            page.evaluate("document.fonts.ready")
            out = workdir / f"slide{i}.jpg"
            page.screenshot(path=str(out), type="jpeg", quality=config.JPEG_QUALITY)
            outputs.append(out)
        browser.close()
    return outputs
