#!/usr/bin/env python3
"""Original synthesized music bed (no samples, no third-party audio) for the Nazakat reel.
120 BPM, A minor. Sections are passed as JSON: [[start, end, kind], ...] with kind in
full | break | light | out. Usage: music.py OUT.wav TOTAL_SECONDS SECTIONS_JSON"""
import json, sys
import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

SR = 48000
BPM = 120
BEAT = 60 / BPM
out_path, total, sections = sys.argv[1], float(sys.argv[2]), json.loads(sys.argv[3])
N = int(total * SR) + SR
rng = np.random.default_rng(7)

def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)
def hp(x, f): return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x)
def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)

def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    click = rng.standard_normal(n) * np.exp(-t * 400) * 0.25
    return (np.sin(ph) * np.exp(-t * 7) + click) * 0.95

def clap():
    n = int(0.25 * SR); t = np.arange(n) / SR
    nz = hp(lp(rng.standard_normal(n), 6000), 900)
    e = np.exp(-t * 18) + 0.6 * np.exp(-((t - 0.012) % 0.011) * 300) * (t < 0.035)
    return nz * e * 0.45

def hat(open_=False):
    n = int((0.18 if open_ else 0.045) * SR); t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000) * np.exp(-t * (14 if open_ else 90)) * 0.22

def saw(freq, n):
    t = np.arange(n) / SR
    return 2 * ((t * freq) % 1) - 1

def note(m): return 440 * 2 ** ((m - 69) / 12)

PROG = [(57, [69, 72, 76]), (53, [65, 69, 72]), (48, [67, 72, 76]), (55, [67, 71, 74])]  # Am F C G

def kind_at(t):
    for s, e, k in sections:
        if s <= t < e: return k
    return "out"

mix = np.zeros(N)
def add(sig, at, g=1.0):
    i = int(at * SR)
    if i >= N: return
    j = min(N, i + len(sig)); mix[i:j] += sig[: j - i] * g

duck = np.ones(N)
step = BEAT / 2
t = 0.0; k8 = 0
while t < total:
    kd = kind_at(t)
    bar = int(t / (BEAT * 4)); root, chord = PROG[bar % 4]
    on_beat = k8 % 2 == 0
    if kd in ("full",) and on_beat:
        add(kick(), t, 1.0)
        i = int(t * SR); m = int(0.18 * SR)
        duck[i:i + m] = np.minimum(duck[i:i + m], 0.35 + 0.65 * np.linspace(0, 1, m))
    if kd in ("full", "light") and on_beat and (k8 // 2) % 2 == 1:
        add(clap(), t, 0.9 if kd == "full" else 0.5)
    if kd in ("full", "light", "break") and not on_beat:
        add(hat(), t, 1.0 if kd != "break" else 0.6)
    if kd == "full" and k8 % 8 == 7:
        add(hat(True), t, 0.8)
    if kd in ("full", "light"):
        n = int(step * SR * 0.9)
        b = lp(saw(note(root - 12), n), 900) * env(n, 0.004, 0.18) * (0.42 if kd == "full" else 0.25)
        add(b, t)
    t += step; k8 += 1

# pads: one chord per bar, everywhere except "out" tail fades
bar_len = BEAT * 4
b = 0
while b * bar_len < total:
    s = b * bar_len; kd = kind_at(s)
    root, chord = PROG[b % 4]
    n = int(bar_len * SR)
    tt = np.arange(n) / SR
    pad = sum(saw(note(m) * (1 + d), n) for m in chord for d in (-0.003, 0.003))
    pad = lp(pad, 1800 if kd == "full" else 1100) * np.minimum(1, tt / 0.08) * np.minimum(1, (bar_len - tt) / 0.1)
    add(pad, s, {"full": 0.05, "light": 0.045, "break": 0.06, "out": 0.05}[kd])
    # pluck arp on full sections
    if kd == "full":
        for q, m in enumerate(chord * 3 + chord[:2]):
            if q >= 8: break
            nn = int(0.22 * SR)
            pl = lp(saw(note(m + 12), nn), 3500) * env(nn, 0.002, 0.08)
            add(pl, s + q * step, 0.09)
    b += 1

mix *= duck  # sidechain feel: everything dips briefly under each kick

# risers into each "full" that follows a "break", and impacts at section starts
for idx, (s, e, kd) in enumerate(sections):
    if kd == "full" and idx > 0 and sections[idx - 1][2] == "break":
        rs = sections[idx - 1][0]; n = int((s - rs) * SR)
        tt = np.arange(n) / SR
        nz = rng.standard_normal(n)
        sweep = np.zeros(n)
        for c in range(0, n, 2400):
            frac = c / n
            seg = nz[c:c + 2400]
            sweep[c:c + 2400] = hp(seg, 300 + 6000 * frac ** 2)
        tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * (tt / tt[-1]) ** 2) / SR)
        add((sweep * 0.12 + tone * 0.05) * (tt / tt[-1]) ** 1.5, rs)
    if kd in ("full", "out"):
        n = int(1.2 * SR); tt = np.arange(n) / SR
        boom = np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-tt * 6)) / SR) * np.exp(-tt * 2.5)
        add(boom, s, 0.55)

mix *= 0.85

# fade tail
ft = int(total * SR); fl = int(1.5 * SR)
mix[ft - fl:ft] *= np.linspace(1, 0, fl)
mix[ft:] = 0
mix = mix[:ft]
mix /= np.max(np.abs(mix)) + 1e-9
mix *= 0.89
st = np.stack([mix, np.roll(mix, 24) * 0.98], axis=1)
wavfile.write(out_path, SR, (st * 32767).astype(np.int16))
print("music", out_path, f"{total:.2f}s")
