#!/usr/bin/env python3
"""Runs the actual documented ffmpeg commands on generated media, never downloads."""
import json
import hashlib
import argparse
import re
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, check=False)
    if result.returncode:
        raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def command_from_skill(name):
    text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    return shlex.split(re.search(r"`(ffmpeg -n [^`]+)`", text).group(1))


def probe(path, cwd):
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                           "-of", "json", str(path)], cwd))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, help="Optional directory for the synthetic result and preview")
    args = parser.parse_args()
    for executable in ("ffmpeg", "ffprobe"):
        if not shutil.which(executable):
            raise SystemExit(f"Missing required executable: {executable}")
    with tempfile.TemporaryDirectory(prefix="gta6-media-test-", dir=ROOT) as temp:
        folder = Path(temp)
        folder.resolve().relative_to(ROOT.resolve())
        run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
             "testsrc2=size=1920x1080:rate=10", "-f", "lavfi", "-i",
             "sine=frequency=440:sample_rate=48000", "-t", "2", "-c:v", "libx264",
             "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
             "quelle.mp4"], folder)
        clip = command_from_skill("clip-schneider")
        clip[-1] = "01-roh.mp4"
        clip[clip.index("-t") + 1] = "2"
        run(clip, folder)
        (folder / "01.ass").write_text("""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,96,&H00FFFFFF,&H0000FFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,6,0,2,60,60,480,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.20,0:00:01.80,Default,,0,0,0,,EIGENER TESTCLIP
""", encoding="utf-8")
        subtitles = [part.replace("<nr>", "01") for part in command_from_skill("untertitel")]
        run(subtitles, folder)
        for filename in ("01-roh.mp4", "01-fertig.mp4"):
            result = probe(filename, folder)
            video = next(s for s in result["streams"] if s["codec_type"] == "video")
            assert (video["width"], video["height"]) == (1080, 1920), video
            assert video["sample_aspect_ratio"] == "1:1", video
            assert video["pix_fmt"] == "yuv420p", video
            assert any(s["codec_type"] == "audio" for s in result["streams"]), result
            assert abs(float(result["format"]["duration"]) - 2) < 0.15, result
        frames = []
        for filename in ("01-roh.mp4", "01-fertig.mp4"):
            frames.append(run(["ffmpeg", "-v", "error", "-ss", "1", "-i", filename,
                               "-frames:v", "1", "-vf", "crop=960:200:60:1250",
                               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], folder))
        delta = sum(abs(a - b) > 45 for a, b in zip(*frames))
        assert delta > 1000, f"No substantial subtitle pixels: {delta}"
        # -n must prevent accidental replacement of the existing source render.
        output = folder / "01-roh.mp4"
        before = (output.stat().st_mtime_ns, hashlib.sha256(output.read_bytes()).digest())
        subprocess.run(clip, cwd=folder, capture_output=True, check=False)
        after = (output.stat().st_mtime_ns, hashlib.sha256(output.read_bytes()).digest())
        assert before == after, "Existing clip was overwritten"
        if args.artifacts:
            destination = args.artifacts.resolve()
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(folder / "01-fertig.mp4", destination / "synthetischer-testclip.mp4")
            run(["ffmpeg", "-v", "error", "-n", "-ss", "1", "-i", "01-fertig.mp4",
                 "-frames:v", "1", str(destination / "synthetischer-testclip.png")], folder)
            (destination / "ffprobe.json").write_text(
                json.dumps(probe("01-fertig.mp4", folder), indent=2), encoding="utf-8")
        print("PASS: actual clip and subtitle commands, 1080x1920, SAR 1:1, audio, duration, subtitle pixels, overwrite protection")


if __name__ == "__main__":
    main()
