#!/usr/bin/env python3
"""Isolate ONE ghanta strike and shape it to <=1.5s with a natural damped decay.

Fixes vs extract_strikes: peak threshold low enough to see every strike (so the
cut window never swallows a neighbor), then an exponential damp (hand-on-bell
feel) + raised-cosine tail so it reaches silence smoothly by ~1.45s.
"""
import numpy as np, subprocess, os, wave
from scipy.signal import butter, sosfilt

SR = 24000
RAW = "/private/tmp/claude-503/-Users-sscilab-mbharchive/c318795d-df4e-41f9-b611-be460ca86e0f/scratchpad/bells_raw"
OUT = "/Users/sscilab/mbharchive/kss_samples/bells_real"

def decode(path):
    p = subprocess.run(["ffmpeg", "-v", "quiet", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True)
    return np.frombuffer(p.stdout, dtype=np.float32).copy()

def envelope(y, win_ms=15):
    w = int(SR * win_ms / 1000)
    return np.sqrt(np.convolve(y**2, np.ones(w)/w, mode="same"))

def short_bell(src, name, tau, length=1.45):
    y = decode(os.path.join(RAW, src))
    y = sosfilt(butter(2, 35, "highpass", fs=SR, output="sos"), y).astype(np.float32)
    env = envelope(y)
    # find ALL strikes: low threshold, 0.8s min separation
    thresh = env.max() * 0.10
    peaks, i, sep = [], 0, int(0.8 * SR)
    while i < len(env):
        if env[i] > thresh:
            j = min(i + sep, len(env))
            peaks.append(i + int(np.argmax(env[i:j]))); i = j
        else: i += 1
    # pick the strike with the largest gap to its successor (cleanest isolation)
    gaps = [(peaks[n+1] - p if n+1 < len(peaks) else len(y) - p, p) for n, p in enumerate(peaks)]
    iso, p = max(gaps)
    # onset
    start = p
    while start > 0 and env[start] > env[p] * 0.05: start -= 1
    start = max(0, start - int(0.015 * SR))
    n = int(length * SR)
    end = min(start + n, start + iso - int(0.1 * SR), len(y))
    seg = y[start:end].copy()
    t = np.arange(len(seg)) / SR
    seg *= np.exp(-t / tau)                              # damped-bell decay
    fo = int(0.12 * SR)                                  # raised-cosine landing to zero
    if len(seg) > fo:
        seg[-fo:] *= 0.5 * (1 + np.cos(np.linspace(0, np.pi, fo)))
    fi = int(0.004 * SR); seg[:fi] *= np.linspace(0, 1, fi)
    seg = seg / np.max(np.abs(seg)) * 0.9
    with wave.open(os.path.join(OUT, name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((seg * 32767).astype("<i2").tobytes())
    print(f"{name}: {len(seg)/SR:.2f}s (strike at t={p/SR:.1f}s of source, isolation {iso/SR:.1f}s, tau={tau})")

short_bell("horst_ghanta.mp3", "bell_ghanta_1.5s_soft.wav", tau=0.45)   # gentler damp
short_bell("horst_ghanta.mp3", "bell_ghanta_1.5s_tight.wav", tau=0.30)  # drier, quicker damp
