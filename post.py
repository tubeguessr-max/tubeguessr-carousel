"""Sends the rendered slides to your TikTok drafts through PostPeer."""
import json
import os
import sys
import time
from pathlib import Path

import requests

API_URL = "https://api.postpeer.dev/v1/posts"


def _wait_until_public(urls: list) -> None:
    """The slides are pushed to GitHub moments before this runs; wait until the URLs resolve."""
    for url in urls:
        for attempt in range(12):
            try:
                if requests.head(url, timeout=15, allow_redirects=True).status_code == 200:
                    break
            except requests.RequestException:
                pass
            time.sleep(5)
        else:
            raise SystemExit("Slide not reachable at %s (is the repo public?)" % url)


def send_draft(meta_path: Path, base_url: str) -> None:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    urls = ["%s/%s" % (base_url.rstrip("/"), name) for name in meta["files"]]
    _wait_until_public(urls)

    payload = {
        "content": meta["title"][:90],
        "platforms": [
            {
                "platform": "tiktok",
                "accountId": os.environ["POSTPEER_ACCOUNT_ID"],
                "platformSpecificData": {"draft": True, "photoCoverIndex": 0, "description": meta["description"]},
            }
        ],
        "mediaItems": [{"type": "image", "url": u} for u in urls],
        "publishNow": True,
    }
    resp = requests.post(
        API_URL,
        headers={"x-access-key": os.environ["POSTPEER_API_KEY"], "Content-Type": "application/json"},
        json=payload,
        timeout=120,
    )
    print(resp.status_code, resp.text[:500])
    if not resp.ok:
        sys.exit(1)
