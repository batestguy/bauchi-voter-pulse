"""Turn a raw capture into the publishable demo: trim, burn captions, add music, encode.

Everything that has to line up - caption windows, the music arc, the trim - is
derived from the shot log `record_demo.mjs` wrote while it drove the browser. Nothing
here hard-codes a timestamp, because a take drifts by seconds between runs and a
caption that lands half a second late reads as a mistake.

Usage:
    python tools/build_demo.py desktop --trim 5.0
    python tools/build_demo.py phone   --trim 5.0
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_music import build as build_music
from make_music import events_from_shots

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "demo"

FONT = Path("C:/Windows/Fonts/segoeuib.ttf")

# Brand colours, straight from the stylesheet.
GOLD = "0xF0A500"
INK = "0x0B1A2A"

# One caption per recorded shot. Keyed by the prefix of the shot label the recorder
# writes, so a renamed shot fails here rather than silently losing its caption.
#
# `None` means this shot gets no caption: the video returns to the home page for the
# language toggle, and there is nothing to say twice. The stretch stays uncaptioned
# rather than inheriting the previous line.
CAPTIONS = {
    "home hero": "A visual record of Bauchi's public needs.",
    "the delivery story": "Need, achievement, promise, result.",
    "atlas map": "20 local government areas. One map.",
    "atlas selected": "Pick an area: its evidence, in the panel.",
    "achievements": "Every record carries the source behind it.",
    "poll form": "One question. No name, no phone, no voter ID.",
    "poll dashboard": "Zero means nobody has answered yet, not 'no'.",
    "home returned": None,
    "language switched": "English and Hausa.",
    "end card": "batestguy.github.io/bauchi-voter-pulse",
}

# Layout per delivery. The vertical cut is not a crop of the landscape: cropping
# 1920x1080 to 9:16 keeps the middle 607px and the caption dies with it. It is a
# separate phone-viewport capture, scaled to fit and padded on the brand navy.
LAYOUTS = {
    "desktop": {"pre": "null", "fontsize": 46, "margin_v": 62, "bar_h": 92},
    "phone": {
        "pre": "scale=-2:1920,pad=1080:1920:(ow-iw)/2:0:color=0x0B1A2A",
        "fontsize": 44,
        "margin_v": 150,
        "bar_h": 92,
    },
}


def ffmpeg_bin(name: str) -> str:
    """Find ffmpeg/ffprobe without trusting PATH.

    `winget` installed the binary but its command alias did not materialise, so the
    shim on PATH is a dead end. Look inside the package directory instead.
    """
    found = shutil.which(name)
    if found and Path(found).exists():
        return found
    root = Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    for pkg in sorted(root.glob("Gyan.FFmpeg*")):
        for exe in pkg.rglob(f"{name}.exe"):
            return str(exe)
    raise SystemExit(f"{name} not found; install it with: winget install Gyan.FFmpeg")


def probe_duration(video: Path) -> float:
    out = subprocess.run(
        [ffmpeg_bin("ffprobe"), "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(video)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def drawtext_chain(captions, font_size: int, margin_v: int, bar_h: int) -> str:
    """A caption bar plus one drawtext per caption, each gated to its own window.

    Two escapes matter here, and both fail as a parse error rather than as a wrong
    picture:

    - a colon separates filter options, so the drive letter in `fontfile` has to be
      written `C\\:` or the whole chain is rejected;
    - the caption text is arbitrary copy, so a colon, comma or apostrophe in it would
      otherwise be read as filter syntax.
    """
    chain = []
    font = FONT.as_posix().replace(":", r"\:")
    for start, end, text in captions:
        label = text.replace("\\", "\\\\").replace(":", r"\:").replace("'", "’").replace(",", r"\,")
        enable = f"between(t,{start:.2f},{end:.2f})"
        chain.append(
            f"drawbox=x=0:y=ih-{margin_v}-{bar_h}:w=iw:h={bar_h + margin_v}:"
            f"color={INK}@0.62:t=fill:enable='{enable}'"
        )
        chain.append(
            f"drawtext=fontfile='{font}':text='{label}':"
            f"fontsize={font_size}:fontcolor={GOLD}:x=(w-text_w)/2:"
            f"y=h-{margin_v}-{bar_h // 2}-text_h/2:enable='{enable}'"
        )
    return ",".join(chain)


def build(take: str, trim: float | None) -> None:
    raw_dir = OUT / f"raw-{take}"
    videos = sorted(raw_dir.glob("*.webm"))
    if not videos:
        raise SystemExit(f"no capture in {raw_dir}; run: node tools/record_demo.mjs {take}")
    raw = videos[0]

    shots = OUT / f"shots-{take}.json"
    marks = json.loads(shots.read_text(encoding="utf-8"))

    # The head of the capture is the page loading: a blank frame, then the hero with
    # its portrait half-drawn. The first cut is the first frame worth keeping, so the
    # trim is that mark - no magic number, and it moves with however slow the network
    # was on the day.
    trim = marks[0]["at"] if trim is None else float(trim)
    duration = round(probe_duration(raw) - trim, 2)
    print(f"{take}: raw {probe_duration(raw):.2f}s, trim {trim:.2f}s -> {duration:.2f}s")

    # Captions: a window runs from its shot's cut to the next cut, in the trimmed
    # timeline. Every caption must map to a recorded shot or the build stops, and a
    # shot mapped to None is left uncaptioned rather than given its neighbour's line.
    captions = []
    for i, m in enumerate(marks):
        if not any(m["label"].startswith(k) for k in CAPTIONS):
            raise SystemExit(f"no caption written for shot {m['label']!r}")
        text = next(v for k, v in CAPTIONS.items() if m["label"].startswith(k))
        start = max(0.0, m["at"] - trim)
        end = (marks[i + 1]["at"] - trim) if i + 1 < len(marks) else duration
        if text is None:
            print(f"  (no caption) {start:6.2f}-{min(end, duration):6.2f}  {m['label']}")
            continue
        captions.append((start, min(end, duration), text))
    for start, end, text in captions:
        print(f"  caption {start:6.2f}-{end:6.2f}  {text}")

    events = events_from_shots(shots, trim, duration)
    music_path = OUT / f"music-{take}.wav"
    samples = build_music(duration, events)
    pcm = (samples.clip(-1, 1) * 32767).astype("<i2").tobytes()
    music_path.write_bytes(b"RIFF" + (36 + len(pcm)).to_bytes(4, "little") + b"WAVEfmt ")
    import wave

    with wave.open(str(music_path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(48_000)
        fh.writeframes(pcm)

    cfg = LAYOUTS[take]
    out_path = OUT / f"demo-{take}.mp4"
    # `pre` comes first: the caption is sized for the delivered frame, so the
    # phone cut is scaled and padded to 1080x1920 before anything is drawn on it.
    vf = f'{cfg["pre"]},' + drawtext_chain(captions, cfg["fontsize"], cfg["margin_v"], cfg["bar_h"])
    cmd = [
        ffmpeg_bin("ffmpeg"), "-y", "-v", "error",
        "-ss", f"{trim}", "-i", str(raw), "-i", str(music_path),
        "-filter_complex", f"[0:v]{vf}[v]",
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "slow", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", "-t", f"{duration}",
        str(out_path),
    ]
    print("ffmpeg:", " ".join(cmd[:8]), "...")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(f"ffmpeg failed with exit code {result.returncode}")
    print(f"\nwrote {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("take", choices=sorted(LAYOUTS))
    ap.add_argument("--trim", type=float, default=None,
                    help="head trim; defaults to the first recorded cut, which is where the capture starts being worth keeping")
    args = ap.parse_args()
    build(args.take, args.trim)


if __name__ == "__main__":
    main()