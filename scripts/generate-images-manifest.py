#!/usr/bin/env python3
import argparse
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".avif"}
ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "images"
MANIFEST_PATH = IMAGES_DIR / "images.json"


def git_last_modified_iso(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", rel],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def file_modified_iso(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
    except Exception:
        return ""


def is_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in IMAGE_EXTS


def collect_entries() -> List[Dict[str, str]]:
    if not IMAGES_DIR.exists():
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    entries = []
    for path in IMAGES_DIR.iterdir():
        if not is_image(path):
            continue
        rel = path.relative_to(ROOT).as_posix()
        entries.append(
            {
                "name": path.name,
                "path": rel,
                "lastModified": git_last_modified_iso(path) or file_modified_iso(path),
            }
        )

    entries.sort(key=lambda item: (item["lastModified"] or "9999-12-31T23:59:59Z", item["name"]))
    return entries


def write_manifest(entries: List[Dict[str, str]]) -> bool:
    payload = json.dumps(entries, ensure_ascii=False, indent=2) + "\n"
    previous = MANIFEST_PATH.read_text(encoding="utf-8") if MANIFEST_PATH.exists() else ""
    if payload == previous:
        return False

    MANIFEST_PATH.write_text(payload, encoding="utf-8")
    return True


def build_manifest() -> bool:
    entries = collect_entries()
    changed = write_manifest(entries)
    if changed:
        print(f"Wrote {MANIFEST_PATH} with {len(entries)} items.")
    return changed


def watch_manifest(interval: float) -> None:
    print(f"Watching {IMAGES_DIR} every {interval:.1f}s for changes...")
    # Initial write so file is always up to date when watch starts.
    build_manifest()

    last_snapshot: Dict[str, Tuple[int, int]] = {}
    while True:
        snapshot: Dict[str, Tuple[int, int]] = {}
        if IMAGES_DIR.exists():
            for path in IMAGES_DIR.iterdir():
                if not is_image(path):
                    continue
                stat = path.stat()
                snapshot[path.name] = (stat.st_mtime_ns, stat.st_size)

        if snapshot != last_snapshot:
            build_manifest()
            last_snapshot = snapshot

        time.sleep(interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate images/images.json manifest.")
    parser.add_argument("--watch", action="store_true", help="Watch images/ and auto-update manifest.")
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Polling interval in seconds when --watch is enabled (default: 1.0).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.watch:
        watch_manifest(max(0.2, args.interval))
        return

    build_manifest()


if __name__ == "__main__":
    main()
