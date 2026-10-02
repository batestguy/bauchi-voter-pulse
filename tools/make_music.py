"""Generate the demo's instrumental track.

Why generated rather than downloaded: the requirement was no copyright, and the
only way to be certain of that is for the audio to have no third-party author.
Everything below is synthesised from oscillators on this machine, so there is no
licence to clear, no attribution to carry, and nothing that a rights claim could
attach to.

**The arc is read from the recorded shot log, never from a plan.** A take recorded
today put the atlas click at 14.8s and yesterday's at 12.6s, because page loads
drift. Hard-coded timings would have put the bell under the wrong shot and nobody
would have noticed until the video was published.

    0.0        pad only        the hero, unhurried
    delivery   pulse enters    the story starts moving
    atlas hit  bell accent     the one moment the video asks you to notice
    form       pulse continues the form being filled
    dashboard  hush            the empty poll. The music stops arguing on purpose
    Hausa      pulse returns   back to business
    end card   resolve         one chord with a long tail

Usage:
    python tools/make_music.py build/demo/music.wav \
        --shots build/demo/shots-desktop.json --trim 4.2 --duration 33
"""

from __future__ import annotations

import argparse
import json
import math
import wave
from pathlib import Path

import numpy as np

SR = 48_000
BPM = 84.0
BEAT = 60.0 / BPM
BAR = 4 * BEAT

# i - VI - III - VII, voiced low and open. Not a hook; this is a bed.
CHORDS = [
    (220.00, 261.63, 329.63),  # Am
    (174.61, 220.00, 261.63),  # F
    (261.63, 329.63, 392.00),  # C
    (196.00, 246.94, 293.66),  # G
]

# Which recorded shot each musical event belongs to.
EVENT_SHOTS = {
    "pulse_in": "the delivery story",
    "bell": "atlas selected",
    "hush_in": "poll dashboard",
    "pulse_back": "language switched",
    "resolve": "end card",
}


def adsr(n: int, attack: float, release: float, sustain: float = 1.0) -> np.ndarray:
    a = max(1, int(attack * SR))
    r = max(1, int(release * SR))
    s = max(0, n - a - r)
    return np.concatenate([np.linspace(0, sustain, a), np.full(s, sustain), np.linspace(sustain, 0, r)])[:n]


def pad(buf: np.ndarray, start: float, dur: float, freq: float, gain: float) -> None:
    """A soft, slightly detuned saw pair under a sine, so it moves without buzzing."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = adsr(n, 0.9, min(1.6, dur * 0.45), 0.72)

    voice = np.zeros(n)
    for detune in (-0.16, 0.17):
        f = freq * (1 + detune / 100)
        voice += np.sin(2 * np.pi * f * t) / 1.6
        # One octave and a fifth up, quieter: gives the pad an edge to cut through.
        voice += 0.16 * np.sin(2 * np.pi * f * 2 * t)
        voice += 0.07 * np.sin(2 * np.pi * f * 3 * t)
    # A touch of triangle content: sin(x) harmonics roll off, so this is enough.
    voice *= env
    i = int(start * SR)
    j = min(len(buf), i + n)
    if i < len(buf):
        buf[i:j] += voice[: j - i] * gain


def kick(buf: np.ndarray, start: float, gain: float) -> None:
    n = int(0.26 * SR)
    t = np.arange(n) / SR
    pitch = 118 * np.exp(-t * 26) + 44
    env = np.exp(-t * 15)
    sig = np.sin(2 * np.pi * np.cumsum(pitch) / SR) * env
    i = int(start * SR)
    j = min(len(buf), i + n)
    if i < len(buf):
        buf[i:j] += sig[: j - i] * gain


def hat(buf: np.ndarray, start: float, gain: float) -> None:
    """Noise burst. Deterministic, so the render is reproducible."""
    n = int(0.05 * SR)
    rng = np.random.default_rng(7)
    env = np.exp(-np.arange(n) / SR * 90)
    i = int(start * SR)
    j = min(len(buf), i + n)
    if i < len(buf):
        buf[i:j] += rng.standard_normal(n)[: j - i] * env * gain


def bell(buf: np.ndarray, start: float, gain: float = 0.20) -> None:
    """Two-operator FM. The accent under the atlas click, and nothing else gets one."""
    n = int(1.9 * SR)
    t = np.arange(n) / SR
    carrier = np.sin(2 * np.pi * 880 * t)
    mod = np.sin(2 * np.pi * 880 * 2.4 * t) * np.exp(-t * 7)
    env = np.exp(-t * 3.1)
    i = int(start * SR)
    j = min(len(buf), i + n)
    if i < len(buf):
        buf[i:j] += (carrier + 0.32 * mod) * env * gain


def build(duration: float, ev: dict[str, float]) -> np.ndarray:
    """`ev` carries the musical events in final-timeline seconds.

    The three layers are built separately and mixed at the end, because the hush needs
    to be a real dynamic drop and a pad that simply keeps playing at the same level
    hides it. Measuring the first render showed the beat-pulse ratio inside the
    "hush" at 1.03 against 1.10-1.40 elsewhere: inaudible. The pad is now ducked to
    a third under that stretch, the kick stops outright, and the pulse outside it is
    loud enough to hear.
    """
    PULSE_IN = ev["pulse_in"]
    BELL_AT = ev["bell"]
    HUSH_IN = ev["hush_in"]
    PULSE_BACK = ev["pulse_back"]
    RESOLVE_AT = ev["resolve"]

    n = int(duration * SR) + SR // 2
    pad_buf = np.zeros(n)
    pulse_buf = np.zeros(n)

    # Pad: one chord per two bars, overlapping so nothing is silent.
    chord_len = BAR * 2
    t = 0.0
    idx = 0
    while t < duration:
        for f in CHORDS[idx % len(CHORDS)]:
            pad(pad_buf, t, chord_len + 1.4, f, 0.115)
        t += chord_len
        idx += 1

    # Pulse: a kick on every beat, with an off-beat hat once the video is moving.
    #
    # The kick sits on the *absolute* beat grid, not on a grid that starts at the
    # cut. Two reasons, and the second is the one that caught out the first build:
    # a grid offset from zero by a fraction of a beat makes the track impossible to
    # measure against the timeline, because a 90 ms analysis window lands between
    # beats instead of on them. Locked to the timeline, the arrangement is
    # deterministic and can be checked rather than assumed.
    beat_index = math.ceil(PULSE_IN / BEAT)
    while beat_index * BEAT < duration - 0.1:
        at = beat_index * BEAT
        if not (HUSH_IN <= at < PULSE_BACK):
            kick(pulse_buf, at, 0.42)
            if beat_index % 2 == 1:
                hat(pulse_buf, at + BEAT / 2, 0.07)
        beat_index += 1

    # The duck on the pad, as a ramp rather than a step: a hard cut on a sustained
    # chord is audible as a click, which is the opposite of the effect wanted here.
    duck = np.ones(n)
    ramp = int(0.9 * SR)
    hi, lo = int(HUSH_IN * SR), int(PULSE_BACK * SR)
    if lo - hi > 2 * ramp:
        duck[hi : hi + ramp] = np.linspace(1.0, 0.30, ramp)
        duck[hi + ramp : lo - ramp] = 0.30
        duck[lo - ramp : lo] = np.linspace(0.30, 1.0, ramp)
    buf = pad_buf * duck + pulse_buf

    # Under the hush, one sustained tone so the quiet is musical rather than dead.
    if PULSE_BACK > HUSH_IN:
        hold_len = min(int((PULSE_BACK - HUSH_IN + 0.8) * SR), n - hi)
        if hold_len > 0:
            hold = adsr(hold_len, 1.5, 2.2, 0.9)
            ts = np.arange(hold_len) / SR
            tone = (np.sin(2 * np.pi * 220.0 * ts) + 0.4 * np.sin(2 * np.pi * 329.63 * ts)) * hold
            buf[hi : hi + hold_len] += tone * 0.10

    bell(buf, BELL_AT)

    # Resolve: one more chord, unamped, with a long release under the end card.
    if RESOLVE_AT < duration:
        for f in (220.00, 261.63, 329.63, 392.00):
            pad(buf, RESOLVE_AT, duration - RESOLVE_AT + 1.2, f, 0.10)

    buf = buf[: int(duration * SR)]

    # Gentle low-pass on the sum: one-pole, twice, ~3 kHz-ish corner. Takes the fizz
    # off the hats without touching the arrangement.
    a = math.exp(-2 * math.pi * 3200 / SR)
    for _ in range(2):
        out = np.empty_like(buf)
        acc = 0.0
        for i, x in enumerate(buf):
            acc = a * acc + (1 - a) * x
            out[i] = acc
        buf = out

    # Normalise to -14 dBFS peak, then a 40 ms fade in and a 1.6 s fade out.
    peak = float(np.max(np.abs(buf))) or 1.0
    buf *= (10 ** (-14 / 20)) / peak
    buf[: int(0.04 * SR)] *= np.linspace(0, 1, int(0.04 * SR))
    fade = int(1.6 * SR)
    if len(buf) > fade:
        buf[-fade:] *= np.linspace(1, 0, fade)
    return buf


def write_wav(path: Path, samples: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = np.clip(samples, -1.0, 1.0)
    data = (pcm * 32767).astype("<i2").tobytes()
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(SR)
        fh.writeframes(data)
    print(f"wrote {path} ({len(samples) / SR:.2f}s, peak {np.max(np.abs(pcm)):.3f})")


def events_from_shots(shots: Path, trim: float, duration: float) -> dict[str, float]:
    """Read the musical arc out of the recorded shot log.

    The take drifts: today's atlas click landed at 14.8s and yesterday's at 12.6s,
    because page loads do. Deriving the arc from the log is the only way the bell
    stays under the click.
    """
    marks = json.loads(shots.read_text(encoding="utf-8"))
    got: dict[str, float] = {}
    for key, needle in EVENT_SHOTS.items():
        for m in marks:
            if m["label"].startswith(needle):
                got[key] = round(max(0.0, m["at"] - trim), 2)
                break
        else:
            raise SystemExit(f"shot log has no shot starting {needle!r}; cannot place {key}")
    got["pulse_in"] = max(got["pulse_in"], 1.0)
    got["hush_in"] = min(got["hush_in"], duration - 1.0)
    got["pulse_back"] = min(got["pulse_back"], duration - 0.6)
    got["resolve"] = min(got["resolve"], duration - 0.4)
    return got


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", type=Path)
    ap.add_argument("--duration", type=float, default=34.0)
    ap.add_argument("--shots", type=Path, help="record_demo.mjs shot log")
    ap.add_argument("--trim", type=float, default=0.0, help="head trim already applied to the video")
    args = ap.parse_args()
    if args.shots:
        ev = events_from_shots(args.shots, args.trim, args.duration)
        print("arc:", json.dumps(ev))
    else:
        ev = {"pulse_in": 2.0, "bell": 9.8, "hush_in": 19.5, "pulse_back": 27.5, "resolve": 31.0}
    write_wav(args.out, build(args.duration, ev))


if __name__ == "__main__":
    main()