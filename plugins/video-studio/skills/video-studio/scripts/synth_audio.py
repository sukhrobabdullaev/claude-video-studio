"""Synthesize an original music bed + SFX kit. No downloads, no licensing questions.

Outputs (48 kHz mono WAV): music_bed.wav, whoosh_up.wav, whoosh_down.wav, riser.wav,
tick.wav, thud.wav. The bed is deliberately plain — air under a voice, not a melody.
If the user provides a real track, use that instead.

    synth_audio.py --out edit/audio --duration 70
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 48_000


def env(n, attack, decay, floor=0.0):
    e = np.zeros(n)
    a = min(int(attack * SR), n)
    e[:a] = np.linspace(0, 1, a, endpoint=False) ** 0.6
    d = min(int(decay * SR), n - a)
    if d > 0:
        e[a:a + d] = np.exp(-np.linspace(0, 5, d)) * (1 - floor) + floor
        e[a + d:] = floor
    return e


def lowpass(x, cutoff):
    c = np.broadcast_to(np.asarray(cutoff, float), x.shape)
    al = np.clip(1 - np.exp(-2 * np.pi * c / SR), 1e-5, 1)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(x.size):
        acc += al[i] * (x[i] - acc)
        y[i] = acc
    return y


def norm(x, peak):
    m = np.abs(x).max()
    return x * peak / m if m else x


def music(duration, bpm, seed):
    n = int(duration * SR)
    beat = 60 / bpm
    bar = beat * 4
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (196.0, 246.94, 329.63), (196.0, 246.94, 293.66)]
    roots = [110.0, 87.31, 98.0, 98.0]
    pad, bass = np.zeros(n), np.zeros(n)
    b = 0
    while b * bar < duration:
        st = int(b * bar * SR)
        m = min(int(bar * SR), n - st)
        if m <= 0:
            break
        tt = np.arange(m) / SR
        e = env(m, 0.55, bar * 0.9, 0.18)
        for f in chords[b % 4]:
            pad[st:st + m] += (np.sin(2 * np.pi * f * tt) * 0.6 + np.sin(2 * np.pi * f * 1.004 * tt) * 0.4
                               + np.sin(4 * np.pi * f * tt) * 0.12) * e
        r = roots[b % 4]
        bass[st:st + m] += (np.sin(2 * np.pi * r * tt) + 0.25 * np.sin(np.pi * r * tt)) * env(m, 0.03, bar * 0.75, 0.05)
        b += 1
    pad = lowpass(pad, 1800.0) * 0.30
    bass = lowpass(bass, 220.0) * 0.55
    hats = np.zeros(n)
    rng = np.random.default_rng(seed)
    k = 0
    while k * beat / 2 < duration:
        if k % 2:
            i = int(k * beat / 2 * SR)
            ln = int(0.045 * SR)
            if i + ln < n:
                hats[i:i + ln] += rng.normal(0, 1, ln) * env(ln, 0.001, 0.035) * (0.5 if k % 4 == 1 else 0.3)
        k += 1
    hats = (hats - lowpass(hats, 6000.0)) * 0.12
    mix = np.tanh((pad + bass + hats) * 1.2) / 1.2
    mix = norm(mix, 0.22)
    fade = int(1.5 * SR)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)
    return mix


def whoosh(dur, up, seed):
    n = int(dur * SR)
    x = np.random.default_rng(seed).normal(0, 1, n)
    y = lowpass(x, np.linspace(400, 5200, n) if up else np.linspace(5200, 400, n)) * env(n, dur * 0.35, dur * 0.6)
    return norm(y, 0.5)


def riser(dur, seed):
    n = int(dur * SR)
    noise = lowpass(np.random.default_rng(seed).normal(0, 1, n), np.linspace(600, 7000, n)) * 0.6
    tone = np.sin(2 * np.pi * np.cumsum(np.linspace(180, 620, n)) / SR) * 0.35
    return norm((noise + tone) * np.linspace(0, 1, n) ** 1.8, 0.5)


def tick(seed):
    n = int(0.05 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * 1250 * t) * env(n, 0.001, 0.022)
    air = lowpass(np.random.default_rng(seed).normal(0, 1, n), 9000.0) * env(n, 0.0005, 0.012) * 0.5
    return norm(body + air, 0.4)


def thud():
    n = int(0.3 * SR)
    return norm(np.sin(2 * np.pi * np.cumsum(np.linspace(95, 48, n)) / SR) * env(n, 0.004, 0.16), 0.55)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--duration", type=float, default=70, help="bed length, s (mix.py loops if short)")
    ap.add_argument("--bpm", type=float, default=84)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    kit = {
        "music_bed.wav": music(a.duration, a.bpm, a.seed),
        "whoosh_up.wav": whoosh(0.5, True, a.seed + 1),
        "whoosh_down.wav": whoosh(0.45, False, a.seed + 2),
        "riser.wav": riser(1.2, a.seed + 3),
        "tick.wav": tick(a.seed + 4),
        "thud.wav": thud(),
    }
    for name, x in kit.items():
        sf.write(a.out / name, x.astype(np.float32), SR)
        print(f"  {name:16s} {len(x) / SR:6.2f}s  peak {20 * np.log10(np.abs(x).max()):6.1f} dBFS")


if __name__ == "__main__":
    main()
