#!/usr/bin/env python3
"""codex-image-gen helper.

Four subcommands cover finding the Codex CLI and the reliable-landing problem
for images produced by an interactive Codex `image_gen` turn:

  find-cli
      Print the Codex CLI to launch: `codex` on PATH first, otherwise (Windows)
      the copy bundled in the Codex desktop app package. A bundled copy needs
      `--no-daemon` for the interactive TUI; that note goes to stderr.
      Exit 0 = found, 1 = none.

  verify  <path> [--ratio W:H] [--tol 0.02] [--since EPOCH]
      Confirm a file is a decodable raster image and (optionally) within tolerance
      of a target aspect ratio. With --since, a file last modified before that
      epoch is a stale leftover and FAILs. Exit 0 = PASS, 1 = FAIL.

  locate  [--since EPOCH] [--root DIR] [--copy-to PATH [--overwrite]]
      Find the newest image written by Codex under the generated_images cache
      (default ~/.codex/generated_images/**). With --since, only files modified at
      or after that epoch are considered (use the baseline you snapshotted before
      driving Codex). Optionally copy the winner to a stable path.

  recover --out PATH [--overwrite] [--sessions DIR]
      Deep fallback: extract the largest base64 blob from the newest Codex session
      rollout JSONL and decode it to PATH. Use only when no file landed in the
      cache or the requested output path.

--copy-to and --out are no-clobber: an existing file is left alone and the
command FAILs unless --overwrite is passed (only after the user approved it).
All paths default to this machine's Codex layout but are overridable so the skill
stays portable across hosts.
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
DEFAULT_CACHE = HOME / ".codex" / "generated_images"
DEFAULT_SESSIONS = HOME / ".codex" / "sessions"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
# A base64 run long enough to be a real image payload, not an id/hash.
B64_RUN = re.compile(rb"[A-Za-z0-9+/]{20000,}={0,2}")
# The MSIX install folder embeds the app version, so it is resolved at run time.
DESKTOP_APP_PACKAGE = "OpenAI.Codex"
DESKTOP_APP_CLI = Path("app") / "resources" / "codex.exe"


def _desktop_app_cli() -> Path | None:
    """Return the codex.exe bundled in the Codex desktop app (Windows only)."""
    if os.name != "nt":
        return None
    try:
        out = subprocess.run(
            [
                "powershell", "-NoProfile", "-NonInteractive", "-Command",
                f"(Get-AppxPackage -Name '{DESKTOP_APP_PACKAGE}').InstallLocation",
            ],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    for line in out.stdout.splitlines():
        if line.strip():
            exe = Path(line.strip()) / DESKTOP_APP_CLI
            if exe.is_file():
                return exe
    return None


def cmd_find_cli(args) -> int:
    on_path = shutil.which("codex")
    if on_path:
        print(on_path)
        return 0
    bundled = _desktop_app_cli()
    if bundled:
        print(bundled)
        # Observed with codex-cli 0.163: without it the TUI exits with
        # "this CLI has no complete local package".
        print("note: Codex desktop app bundle; launch the interactive TUI with --no-daemon", file=sys.stderr)
        return 0
    where = "PATH or the Codex desktop app package" if os.name == "nt" else "PATH"
    print(f"FAIL: no Codex CLI found on {where}")
    return 1


def _dims(path: Path):
    """Return (width, height) using PIL, falling back to ffprobe."""
    try:
        from PIL import Image  # type: ignore

        with Image.open(path) as im:
            return im.size
    except Exception:
        pass
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path),
        ],
        capture_output=True, text=True,
    )
    w, h = (out.stdout.strip().split(",") + ["0", "0"])[:2]
    return int(w), int(h)


def _refuse_clobber(dst: Path, overwrite: bool) -> bool:
    """Print a FAIL line and return True when dst exists and overwriting was not approved."""
    if dst.exists() and not overwrite:
        print(f"FAIL: {dst} already exists; pass --overwrite only after the user approves replacing it")
        return True
    return False


def cmd_verify(args) -> int:
    path = Path(args.path)
    if not path.is_file() or path.stat().st_size == 0:
        print(f"FAIL: not a readable non-empty file: {path}")
        return 1
    if args.since is not None and path.stat().st_mtime < args.since:
        print(f"FAIL: stale file older than baseline since={args.since}: {path}")
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
        if _refuse_clobber(dst, args.overwrite):
            return 1
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(newest, dst)
        print(f"{dst}")
    else:
        print(f"{newest}")
    return 0


def cmd_recover(args) -> int:
    out = Path(args.out)
    if _refuse_clobber(out, args.overwrite):
        return 1
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
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(raw)
    print(f"{out}  ({len(raw)}B recovered from {rollout.name})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="codex-image-gen helper")
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("find-cli", help="print the Codex CLI to launch (PATH, else Windows desktop-app bundle)")
    f.set_defaults(func=cmd_find_cli)

    v = sub.add_parser("verify", help="verify a raster image + optional aspect ratio")
    v.add_argument("path")
    v.add_argument("--ratio", help="target aspect ratio, e.g. 9:16")
    v.add_argument("--tol", type=float, default=0.02, help="ratio tolerance (default 0.02)")
    v.add_argument("--since", type=float, help="epoch baseline; FAIL if the file is older")
    v.set_defaults(func=cmd_verify)

    l = sub.add_parser("locate", help="find newest Codex-generated image in the cache")
    l.add_argument("--since", type=float, default=0.0, help="epoch baseline; only files >= this mtime")
    l.add_argument("--root", default=str(DEFAULT_CACHE))
    l.add_argument("--copy-to", help="copy the winner to this path (no-clobber)")
    l.add_argument("--overwrite", action="store_true", help="replace an existing --copy-to file (user-approved)")
    l.set_defaults(func=cmd_locate)

    r = sub.add_parser("recover", help="extract image from newest rollout base64 (deep fallback)")
    r.add_argument("--out", required=True, help="output PNG path (no-clobber)")
    r.add_argument("--overwrite", action="store_true", help="replace an existing --out file (user-approved)")
    r.add_argument("--sessions", default=str(DEFAULT_SESSIONS))
    r.set_defaults(func=cmd_recover)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
