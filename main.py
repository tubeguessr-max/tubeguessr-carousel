"""TubeGuessr daily carousel.

  python main.py check                 validate the data files
  python main.py render                pick images (from images/slide1-3 in this repo, or Google Drive
                                       if DRIVE_FOLDER_SLIDE1 is set), render slides into ./out
  python main.py render --local DIR    same, but pick images from a local folder (for testing)
  python main.py post                  send ./out to your TikTok drafts via PostPeer
"""
import argparse
import json
import os
import random
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import config

ROOT = Path(__file__).parent
OUT = ROOT / "out"


def load_data():
    read = lambda name: json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))
    return read("stations.json"), read("lines.json"), read("hooks.json")


def cmd_check(_args):
    stations, lines, hooks = load_data()
    problems = [
        "%s: unknown line '%s' (add it to data/lines.json)" % (s, l)
        for s, ls in stations.items()
        for l in ls
        if l not in lines
    ]
    if problems:
        raise SystemExit("\n".join(problems))
    print("OK: %d stations, %d lines, %d hooks" % (len(stations), len(lines), len(hooks)))


def _local_backgrounds(folder: Path) -> list:
    files = [p for p in folder.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    if not files:
        raise SystemExit("No images in %s" % folder)
    return [random.choice(files) for _ in range(3)]


def _repo_backgrounds() -> list:
    """Pick one random image from each of images/slide1, images/slide2, images/slide3 in this repo."""
    picks = []
    for n in (1, 2, 3):
        folder = ROOT / "images" / ("slide%d" % n)
        files = [p for p in folder.glob("*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")] if folder.exists() else []
        if not files:
            raise SystemExit("No jpg/png/webp images found in images/slide%d/ - add some and commit them." % n)
        picks.append(random.choice(files))
    print("Backgrounds:", ", ".join(p.name for p in picks))
    return picks


def cmd_render(args):
    from render import render_all

    stations, _lines, hooks = load_data()
    station = random.choice(list(stations))
    hook = random.choice(hooks)
    print("Station: %s | Hook: %s" % (station, hook))

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if args.local:
            backgrounds = _local_backgrounds(Path(args.local))
        elif not os.environ.get("DRIVE_FOLDER_SLIDE1"):
            backgrounds = _repo_backgrounds()  # default: images stored in this repo
        else:
            from drive import pick_images

            folders = [os.environ["DRIVE_FOLDER_SLIDE1"], os.environ["DRIVE_FOLDER_SLIDE2"], os.environ["DRIVE_FOLDER_SLIDE3"]]
            backgrounds = pick_images(folders, tmp / "picked")
        slides = render_all(backgrounds, station, stations[station], hook, tmp / "work")

        if OUT.exists():
            shutil.rmtree(OUT)
        OUT.mkdir()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        names = []
        for i, slide in enumerate(slides, 1):
            name = "%s-%d.jpg" % (stamp, i)  # unique names stop GitHub's cache serving yesterday's image
            shutil.copy(slide, OUT / name)
            names.append(name)
    (OUT / "meta.json").write_text(
        json.dumps({"files": names, "caption": config.CAPTION, "station": station, "hook": hook}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Rendered:", ", ".join(names))


def cmd_post(_args):
    from post import send_draft

    send_draft(OUT / "meta.json", os.environ["IMAGE_BASE_URL"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(func=cmd_check)
    r = sub.add_parser("render")
    r.add_argument("--local", help="folder of test images instead of Google Drive")
    r.set_defaults(func=cmd_render)
    sub.add_parser("post").set_defaults(func=cmd_post)
    args = parser.parse_args()
    args.func(args)
