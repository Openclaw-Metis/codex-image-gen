"""Regression tests for codex_image.py (stdlib only).

Run: python scripts/test_codex_image.py
"""

from __future__ import annotations

import base64
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("codex_image", HERE / "codex_image.py")
codex_image = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(codex_image)


def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(sys, "argv", ["codex_image.py", *argv]), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = codex_image.main()
    return code, out.getvalue(), err.getvalue()


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.img = Path(self.tmp.name) / "a.png"
        self.img.write_bytes(b"x" * 10)

    def tearDown(self):
        self.tmp.cleanup()

    def test_landscape_16x9_within_tolerance_passes(self):
        # Size observed from a real Windows run on 2026-10-20.
        with mock.patch.object(codex_image, "_dims", return_value=(1672, 941)):
            code, out, _ = run_cli("verify", str(self.img), "--ratio", "16:9")
        self.assertEqual(code, 0)
        self.assertIn("PASS", out)

    def test_square_against_9x16_fails(self):
        with mock.patch.object(codex_image, "_dims", return_value=(1024, 1024)):
            code, out, _ = run_cli("verify", str(self.img), "--ratio", "9:16")
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)

    def test_missing_file_fails(self):
        code, out, _ = run_cli("verify", str(Path(self.tmp.name) / "nope.png"))
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)

    def test_file_older_than_baseline_is_stale(self):
        # A leftover from an earlier run must not pass as this run's image.
        past = time.time() - 600
        os.utime(self.img, (past, past))
        with mock.patch.object(codex_image, "_dims", return_value=(1672, 941)):
            code, out, _ = run_cli("verify", str(self.img), "--ratio", "16:9", "--since", str(time.time() - 60))
            self.assertEqual(code, 1)
            self.assertIn("stale", out)
            code, _, _ = run_cli("verify", str(self.img), "--ratio", "16:9", "--since", str(past - 1))
        self.assertEqual(code, 0)


class LocateRecoverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_locate_ignores_files_older_than_baseline(self):
        cache = self.root / "generated_images" / "thread"
        cache.mkdir(parents=True)
        old = cache / "old.png"
        old.write_bytes(b"old")
        past = time.time() - 600
        os.utime(old, (past, past))
        baseline = time.time() - 60
        code, out, _ = run_cli("locate", "--since", str(baseline), "--root", str(self.root / "generated_images"))
        self.assertEqual(code, 1)
        new = cache / "exec-new.png"
        new.write_bytes(b"new")
        dst = self.root / "out" / "final.png"
        code, out, _ = run_cli("locate", "--since", str(baseline), "--root",
                               str(self.root / "generated_images"), "--copy-to", str(dst))
        self.assertEqual(code, 0)
        self.assertEqual(dst.read_bytes(), b"new")

    def test_recover_decodes_largest_blob_from_newest_rollout(self):
        payload = b"\x89PNG" + bytes(range(256)) * 100
        blob = base64.b64encode(payload).decode()
        sessions = self.root / "sessions" / "2026" / "10" / "20"
        sessions.mkdir(parents=True)
        (sessions / "rollout-1.jsonl").write_text('{"result":"%s"}\n' % blob, encoding="utf-8")
        out_png = self.root / "recovered.png"
        code, out, _ = run_cli("recover", "--out", str(out_png), "--sessions", str(self.root / "sessions"))
        self.assertEqual(code, 0)
        self.assertEqual(out_png.read_bytes(), payload)

    def test_copy_to_and_out_are_no_clobber_without_overwrite(self):
        cache = self.root / "generated_images"
        cache.mkdir()
        (cache / "exec-new.png").write_bytes(b"new")
        dst = self.root / "keep.png"
        dst.write_bytes(b"user file")
        code, out, _ = run_cli("locate", "--root", str(cache), "--copy-to", str(dst))
        self.assertEqual(code, 1)
        self.assertIn("--overwrite", out)
        self.assertEqual(dst.read_bytes(), b"user file")

        sessions = self.root / "sessions"
        sessions.mkdir()
        (sessions / "rollout-1.jsonl").write_text(base64.b64encode(b"z" * 30000).decode(), encoding="utf-8")
        code, _, _ = run_cli("recover", "--out", str(dst), "--sessions", str(sessions))
        self.assertEqual(code, 1)
        self.assertEqual(dst.read_bytes(), b"user file")

        code, _, _ = run_cli("locate", "--root", str(cache), "--copy-to", str(dst), "--overwrite")
        self.assertEqual(code, 0)
        self.assertEqual(dst.read_bytes(), b"new")


class FindCliTests(unittest.TestCase):
    """Regression for the 2026-10-20 Windows failure: no codex on PATH, only the desktop-app bundle."""

    def test_prefers_codex_on_path(self):
        with mock.patch.object(codex_image.shutil, "which", return_value="/usr/local/bin/codex"), \
                mock.patch.object(codex_image, "_desktop_app_cli") as bundled:
            code, out, err = run_cli("find-cli")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "/usr/local/bin/codex")
        self.assertNotIn("--no-daemon", err)
        bundled.assert_not_called()

    def test_falls_back_to_desktop_app_bundle_and_flags_no_daemon(self):
        exe = Path("C:/Program Files/WindowsApps/OpenAI.Codex_1.0_x64__x/app/resources/codex.exe")
        with mock.patch.object(codex_image.shutil, "which", return_value=None), \
                mock.patch.object(codex_image, "_desktop_app_cli", return_value=exe):
            code, out, err = run_cli("find-cli")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), str(exe))
        self.assertIn("--no-daemon", err)

    def test_reports_failure_when_no_cli_exists(self):
        with mock.patch.object(codex_image.shutil, "which", return_value=None), \
                mock.patch.object(codex_image, "_desktop_app_cli", return_value=None):
            code, out, _ = run_cli("find-cli")
        self.assertEqual(code, 1)
        self.assertIn("FAIL", out)

    def test_desktop_app_lookup_is_windows_only(self):
        with mock.patch.object(codex_image.os, "name", "posix"), \
                mock.patch.object(codex_image.subprocess, "run") as run:
            self.assertIsNone(codex_image._desktop_app_cli())
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
