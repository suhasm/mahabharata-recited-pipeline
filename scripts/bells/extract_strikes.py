#!/usr/bin/env python3
"""Extract the single cleanest bell strike from each raw recording.

Pipeline: decode->mono 24k, high-pass 35Hz (rumble), find strike peaks,
pick the one with the longest uncontaminated decay, cut onset->decay floor,
micro fade-in, gentle fade-out, normalize.
"""
import numpy as np, subprocess, os, wave
from scipy.signal import butter, sosfilt

SR = 24000
RAW = "/private/tmp/claude-503/-Users-sscilab-mbharchive/c318795d-df4e-41f9-b611-be460ca86e0f/scratchpad/bells_raw"
OUT = "/Users/sscilab/mbharchive/kss_samples/bells_real"
os.makedirs(OUT, exist_ok=True)

def decode(path):
    p = subprocess.run(["ffmpeg", "-v", "quiet", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True)
    return np.frombuffer(p.stdout, dtype=np.float32).copy()

def envelope(y, win_ms=20):
    w = int(SR * win_ms / 1000)
    e = np.sqrt(np.convolve(y**2, np.ones(w)/w, mode="same"))
    return e

def extract(name, fname):
    y = decode(os.path.join(RAW, fname))
    sos = butter(2, 35, "highpass", fs=SR, output="sos")
    y = sosfilt(sos, y).astype(np.float32)
    env = envelope(y)
    peak_thresh = env.max() * 0.35
    min_sep = int(1.5 * SR)
    # candidate strike peaks
    peaks = []
    i = 0
    while i < len(env):
        if env[i] > peak_thresh:
            j = min(i + min_sep, len(env))
            k = i + int(np.argmax(env[i:j]))
            peaks.append(k)
            i = j
        else:
            i += 1
    # score each: decay run-length before floor or next strike
    best = None
    for n, p in enumerate(peaks):
        nxt = peaks[n+1] - int(0.15*SR) if n+1 < len(peaks) else len(y)
        noise = np.median(env)
        floor = max(env[p] * 0.004, noise * 1.6)
        end = p
        while end < nxt and env[end] > floor:
            end += 1
        score = (end - p) + env[p]/env.max()*SR  # decay length, tie-break on loudness
        if best is None or score > best[2]:
            best = (p, end, score)
    p, end, _ = best
    # onset: walk back to 5% of peak env
    start = p
    while start > 0 and env[start] > env[p] * 0.05:
        start -= 1
    start = max(0, start - int(0.02*SR))
    end = min(end + int(0.05*SR), len(y))
    seg = y[start:end].copy()
    seg = seg[:int(12*SR)]                      # cap at 12s
    fi = int(0.005*SR); seg[:fi] *= np.linspace(0, 1, fi)
    fo = min(int(0.25*SR), len(seg)); seg[-fo:] *= np.linspace(1, 0, fo)
    seg = seg / np.max(np.abs(seg)) * 0.9
    with wave.open(os.path.join(OUT, name), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((seg * 32767).astype("<i2").tobytes())
    print(f"{name}: {len(seg)/SR:.1f}s  (from {len(peaks)} strikes in source, used t={p/SR:.1f}s)")

extract("real_indian_temple_himachal.wav", "ganiket_indian_temple.mp3")
extract("real_ghanta_mallet.wav", "horst_ghanta.mp3")
extract("real_bonsho_japan.wav", "vurca_bonsho.mp3")
extract("real_drilbu_tibetan.wav", "tenzin_drilbu.mp3")
