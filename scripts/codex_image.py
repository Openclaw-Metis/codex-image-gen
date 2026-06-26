#!/usr/bin/env python3
"""codex-image-gen helper.

Three subcommands cover the reliable-landing problem for images produced by an
interactive Codex `image_gen` turn:

  verify  <path> [--ratio W:H] [--tol 0.02]
      Confirm a file is a decodable raster image and (optionally) within tolerance
      of a target aspect ratio. Exit 0 = PASS, 1 = FAIL.

  locate  [--since EPOCH] [--root DIR] [--copy-to PATH]
      Find the newest image written by Codex under the generated_images cache
      (default ~/.codex/generated_images/**). With --since, only files modified at
      or after that epoch are considered (use the baseline you snapshotted before
      driving Codex). Optionally copy the winner to a stable path.

  recover [--out PATH] [--sessions DIR]
      Deep fallback: extract the largest base64 blob from the newest Codex session
      rollout JSONL and decode it to PATH. Use only when no file landed in the
      cache or the requested output path.

All paths default to this machine's Codex layout but are overridable so the skill
stays portable across hosts.
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import shutil
import sys
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
DEFAULT_CACHE = HOME / ".codex" / "generated_images"
DEFAULT_SESSIONS = HOME / ".codex" / "sessions"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
# A base64 run long enough to be a real image payload, not an id/hash.
B64_RUN = re.compile(rb"[A-Za-z0-9+/]{20000,}={0,2}")


def _dims(path: Path):
    """Return (width, height) using PIL, falling back to ffprobe."""
    try:
        from PIL import Image  # type: ignore

        with Image.open(path) as im:
            return im.size
    except Exception:
        pass
    import subprocess

    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path),
        ],
        capture_output=True, text=True,
    )
    w, h = (out.stdout.strip().split(",") + ["0", "0"])[:2]
    return int(w), int(h)


def cmd_verify(args) -> int:
    path = Path(args.path)
    if not path.is_file() or path.stat().st_size == 0:
        print(f"FAIL: not a readable non-empty file: {path}")
        return 1
    try:
        w, h = _dims(path)
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: could not decode image dimensions: {e}")
        return 1
    if not w or not h:
        print(f"FAIL: zero dimension: {w}x{h}")
        return 1
    ratio = w / h
    line = f"{path}: {w}x{h}  ratio={ratio:.4f}  size={path.stat().st_size}B"
    if args.ratio:
        tw, th = (int(x) for x in args.ratio.split(":"))
        target = tw / th
        ok = abs(ratio - target) <= args.tol
        print(f"{line}  target {args.ratio}={target:.4f}  {'PASS' if ok else 'FAIL (out of tolerance)'}")
        return 0 if ok else 1
    print(f"{line}  PASS")
    return 0


def _candidate_images(root: Path, since: float):
    for p in root.rglob("*"):
        if p.suffix.lower() in IMAGE_SUFFIXES and p.is_file():
            if p.stat().st_mtime >= since:
                yield p


def cmd_locate(args) -> int:
    root = Path(args.root)
    if not root.exists():
        print(f"FAIL: cache root not found: {root}")
        return 1
    newest = max(_candidate_images(root, args.since), key=lambda p: p.stat().st_mtime, default=None)
    if newest is None:
        print(f"FAIL: no image under {root} newer than since={args.since}")
        return 1
    if args.copy_to:
        dst = Path(args.copy_to)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(newest, dst)
        print(f"{dst}")
    else:
        print(f"{newest}")
    return 0


def cmd_recover(args) -> int:
    sessions = Path(args.sessions)
    rollouts = sorted(sessions.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not rollouts:
        print(f"FAIL: no rollout-*.jsonl under {sessions}")
        return 1
    rollout = rollouts[0]
    data = rollout.read_bytes()
    blobs = B64_RUN.findall(data)
    if not blobs:
        print(f"FAIL: no base64 image blob in newest rollout: {rollout}")
        return 1
    blob = max(blobs, key=len)
    try:
        raw = base64.b64decode(blob + b"=" * (-len(blob) % 4))
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: base64 decode failed: {e}")
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    print(f"{out}  ({len(raw)}B recovered from {rollout.name})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="codex-image-gen helper")
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verify", help="verify a raster image + optional aspect ratio")
    v.add_argument("path")
    v.add_argument("--ratio", help="target aspect ratio, e.g. 9:16")
    v.add_argument("--tol", type=float, default=0.02, help="ratio tolerance (default 0.02)")
    v.set_defaults(func=cmd_verify)

    l = sub.add_parser("locate", help="find newest Codex-generated image in the cache")
    l.add_argument("--since", type=float, default=0.0, help="epoch baseline; only files >= this mtime")
    l.add_argument("--root", default=str(DEFAULT_CACHE))
    l.add_argument("--copy-to", help="copy the winner to this path")
    l.set_defaults(func=cmd_locate)

    r = sub.add_parser("recover", help="extract image from newest rollout base64 (deep fallback)")
    r.add_argument("--out", required=True, help="output PNG path")
    r.add_argument("--sessions", default=str(DEFAULT_SESSIONS))
    r.set_defaults(func=cmd_recover)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
