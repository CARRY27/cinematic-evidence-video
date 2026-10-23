#!/usr/bin/env python3
"""Verify technical properties of one or two rendered video files.

This checks exported files, not visual quality or factual correctness.
Requires ffprobe; --full-decode also requires ffmpeg. Python 3.9+.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Optional


def ratio(value: object) -> Optional[Fraction]:
    """Read an ffprobe ratio such as 30/1 or 9:16, ignoring unknown values."""
    if not isinstance(value, str) or value in {"", "N/A", "0/0", "0:0"}:
        return None
    try:
        parsed = Fraction(value.replace(":", "/"))
    except (ValueError, ZeroDivisionError):
        return None
    return parsed if parsed > 0 else None


def probe(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"File does not exist: {path}")
    command = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration,size:stream=index,codec_type,codec_name,width,height,"
        "avg_frame_rate,r_frame_rate,nb_frames,sample_aspect_ratio,display_aspect_ratio",
        "-of", "json", str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(f"ffprobe failed for {path}: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if not video:
        raise ValueError(f"No video stream: {path}")
    width, height = video.get("width"), video.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        raise ValueError(f"Invalid video dimensions: {path}")
    frame_rate = ratio(video.get("avg_frame_rate")) or ratio(video.get("r_frame_rate"))
    display_ratio = ratio(video.get("display_aspect_ratio"))
    if display_ratio is None:
        pixel_ratio = ratio(video.get("sample_aspect_ratio")) or Fraction(1, 1)
        display_ratio = Fraction(width, height) * pixel_ratio
    frames = video.get("nb_frames")
    try:
        duration = float(data["format"]["duration"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Missing or invalid duration: {path}") from error
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError(f"Missing or invalid duration: {path}")
    return {
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "duration_seconds": duration,
        "video": {
            "codec": video.get("codec_name"),
            "width": width,
            "height": height,
            "fps": float(frame_rate) if frame_rate is not None else None,
            "frames": int(frames) if isinstance(frames, str) and frames.isdigit() else None,
            "display_aspect_ratio": f"{display_ratio.numerator}:{display_ratio.denominator}",
            "display_aspect_ratio_value": float(display_ratio),
        },
        "has_audio": any(stream.get("codec_type") == "audio" for stream in streams),
    }


def decode(path: Path) -> None:
    command = [
        "ffmpeg", "-hide_banner", "-v", "error", "-xerror", "-i", str(path),
        "-map", "0:v:0", "-map", "0:a?", "-f", "null", "-",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(f"Video/audio decode failed for {path}: {result.stderr.strip()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("master", type=Path, help="Rendered master video")
    parser.add_argument("--review", type=Path, help="Optional review export to compare")
    parser.add_argument("--width", type=int, help="Expected master width")
    parser.add_argument("--height", type=int, help="Expected master height")
    parser.add_argument("--review-width", type=int, help="Expected review width")
    parser.add_argument("--review-height", type=int, help="Expected review height")
    parser.add_argument("--fps", type=float, help="Expected master frames per second")
    parser.add_argument("--frames", type=int, help="Expected master frame count")
    parser.add_argument("--duration", type=float, help="Expected duration in seconds")
    parser.add_argument("--tolerance", type=float, default=0.15,
                        help="Allowed duration difference in seconds (default: 0.15)")
    parser.add_argument("--require-audio", action="store_true", help="Require an audio stream in each file")
    parser.add_argument("--full-decode", action="store_true",
                        help="Decode the primary video and all audio streams in each file")
    args = parser.parse_args()
    if args.tolerance < 0:
        parser.error("--tolerance must be nonnegative")
    failures: list[str] = []
    report: dict = {"ok": False, "files": {}, "failures": failures}
    try:
        master = probe(args.master)
        report["files"]["master"] = master
        if args.review:
            review = probe(args.review)
            report["files"]["review"] = review
        else:
            review = None
        if args.full_decode:
            for item in (args.master, args.review):
                if item is not None:
                    decode(item)
            report["video_audio_full_decode"] = "passed"
    except (ValueError, OSError, json.JSONDecodeError, ZeroDivisionError) as error:
        failures.append(str(error))
    else:
        video = master["video"]
        for key, expected in (("width", args.width), ("height", args.height),
                              ("frames", args.frames)):
            if expected is not None and video[key] != expected:
                failures.append(f"master {key}: expected {expected}, got {video[key]}")
        if args.fps is not None and (video["fps"] is None or abs(video["fps"] - args.fps) > 0.001):
            failures.append(f"master fps: expected {args.fps}, got {video['fps']}")
        if args.duration is not None and abs(master["duration_seconds"] - args.duration) > args.tolerance:
            failures.append(f"master duration: expected {args.duration}, got {master['duration_seconds']}")
        if args.require_audio and not master["has_audio"]:
            failures.append("master has no audio stream")
        if review:
            review_video = review["video"]
            for key, expected in (("width", args.review_width), ("height", args.review_height)):
                if expected is not None and review_video[key] != expected:
                    failures.append(f"review {key}: expected {expected}, got {review_video[key]}")
            if abs(master["duration_seconds"] - review["duration_seconds"]) > args.tolerance:
                failures.append("master and review durations differ")
            if video["fps"] is None or review_video["fps"] is None:
                failures.append("master or review frame rate could not be verified")
            elif abs(video["fps"] - review_video["fps"]) > 0.001:
                failures.append("master and review frame rates differ")
            if abs(video["display_aspect_ratio_value"] - review_video["display_aspect_ratio_value"]) > 0.001:
                failures.append("master and review display aspect ratios differ")
            if video["frames"] is not None and review_video["frames"] is not None:
                if video["frames"] != review_video["frames"]:
                    failures.append("master and review frame counts differ")
            if master["has_audio"] != review["has_audio"]:
                failures.append("master and review audio presence differs")
            if args.require_audio and not review["has_audio"]:
                failures.append("review has no audio stream")
    report["ok"] = not failures
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
