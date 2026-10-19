"""Picks random images from Google Drive folders (read-only service account)."""
import io
import json
import os
import random
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]


def _service():
    info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _list_images(svc, folder_id: str) -> list:
    types = " or ".join("mimeType='%s'" % t for t in IMAGE_TYPES)
    query = "'%s' in parents and trashed=false and (%s)" % (folder_id, types)
    files, token = [], None
    while True:
        resp = svc.files().list(
            q=query,
            fields="nextPageToken, files(id, name)",
            pageSize=1000,
            pageToken=token,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files += resp.get("files", [])
        token = resp.get("nextPageToken")
        if not token:
            return files


def _download(svc, file_id: str, dest: Path) -> None:
    request = svc.files().get_media(fileId=file_id, supportsAllDrives=True)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    dest.write_bytes(buf.getvalue())


def pick_images(folder_ids: list, dest_dir: Path) -> list:
    """One random image per folder id (in order). If two slides share a folder, they get different images."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    svc = _service()
    cache = {}
    used = set()
    paths = []
    for i, folder_id in enumerate(folder_ids, 1):
        if folder_id not in cache:
            cache[folder_id] = _list_images(svc, folder_id)
        files = cache[folder_id]
        if not files:
            raise SystemExit("No jpg/png/webp images found in Drive folder for slide %d (%s)." % (i, folder_id))
        fresh = [f for f in files if f["id"] not in used] or files
        choice = random.choice(fresh)
        used.add(choice["id"])
        dest = dest_dir / ("pick%d%s" % (i, Path(choice["name"]).suffix.lower() or ".jpg"))
        _download(svc, choice["id"], dest)
        print("Slide %d background: %s" % (i, choice["name"]))
        paths.append(dest)
    return paths
