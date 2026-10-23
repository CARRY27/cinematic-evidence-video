"""Synthetic integration tests for the optional video verifier.

Run with: python3 -m unittest discover -s tests -v
The tests generate short color-and-tone MP4s; no project media is required.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_video.py"


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "ffmpeg and ffprobe are needed for integration tests")
class VerifyVideoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = tempfile.TemporaryDirectory()
        folder = Path(cls.temp_dir.name)
        cls.master = folder / "master.mp4"
        cls.review = folder / "review.mp4"
        cls.bad_review = folder / "bad_review.mp4"
        cls.make_video(cls.master, 320, 568, 10)
        cls.make_video(cls.review, 160, 284, 10)
        cls.make_video(cls.bad_review, 160, 280, 12)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp_dir.cleanup()

    @staticmethod
    def make_video(path: Path, width: int, height: int, fps: int) -> None:
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"color=c=blue:s={width}x{height}:r={fps}:d=1",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=16000:duration=1",
            "-shortest", "-c:v", "mpeg4", "-q:v", "5", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(path),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)

    @staticmethod
    def run_cli(*args: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            capture_output=True, text=True, check=False,
        )
        return result, json.loads(result.stdout)

    def test_matching_exports_and_full_decode_pass(self) -> None:
        result, report = self.run_cli(
            self.master, "--review", self.review, "--width", "320", "--height", "568",
            "--review-width", "160", "--review-height", "284", "--fps", "10",
            "--frames", "10", "--duration", "1", "--require-audio", "--full-decode",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(report["ok"])
        self.assertEqual(report["video_audio_full_decode"], "passed")
        self.assertEqual(report["files"]["master"]["video"]["display_aspect_ratio"], "40:71")

    def test_wrong_dimensions_fail(self) -> None:
        result, report = self.run_cli(self.master, "--width", "1080", "--height", "1920")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ok"])
        self.assertTrue(any("master width" in reason for reason in report["failures"]))
        self.assertTrue(any("master height" in reason for reason in report["failures"]))

    def test_mismatched_review_frame_rate_and_aspect_fail(self) -> None:
        result, report = self.run_cli(self.master, "--review", self.bad_review)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ok"])
        self.assertTrue(any("frame rates differ" in reason for reason in report["failures"]))
        self.assertTrue(any("aspect ratios differ" in reason for reason in report["failures"]))

    def test_missing_file_fails_as_json(self) -> None:
        missing = Path(self.temp_dir.name) / "missing.mp4"
        result, report = self.run_cli(missing)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(report["ok"])
        self.assertIn("File does not exist", report["failures"][0])


if __name__ == "__main__":
    unittest.main()
