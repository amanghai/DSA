#!/usr/bin/env python3
"""Check a GENERATED video against its source take and its prompt (the gate after the generation).

verify_prompt.py only checks the prompt text. What goes wrong happens after the model has run:
the clip ends early or mid-word, a whip never happens (or comes out as a hard cut), a position
looks like the source framing, the original audio is replaced, the resolution drops, the first
frames freeze. This script measures those, so you hear about them before spending more credits.

Usage:
    python qa_result.py <generated.mp4> --source <source.mp4> [--prompt <prompt.txt>]
                        [--whips 0.8,2.1,3.4] [--words <source>.json] [--json]

Checks (each prints PASS, WARN, FAIL or INFO):
  duration    generated length against the source ("Video timing must be exactly the same");
              FAIL if the clip ends before the last spoken word finishes (mid-word), using the
              Whisper cache beats.py wrote next to the source (<source stem>.json).
  whips       a whip is a short burst in which most of the frame changes at once (a camera
              move), not a hard cut and not a super animating. Each block start in the prompt
              that carries a "Whip the camera" line must have a burst within half a second;
              a hard cut at that time is reported as such. After the landing the framing must
              differ from the framing before the whip (the contrast rule).
  audio       is it still the original audio? Loudness envelope and spectral shape compared
              with the source after aligning the offset. A replaced or re-voiced track fails.
  resolution  smaller than the source, or under 1080 on the short side, or another aspect.
  freeze      the clip starting or ending on a held frame, or a mid-clip freeze the source
              does not have.

Not checked: the text of the supers and where they sit in the frame (a script cannot read them);
look at the frames for the safe zone. The thresholds below are starting values calibrated on
synthetic clips only: tune them after real runs.
Exit code: 0 when nothing FAILs (warnings allowed), 1 on any FAIL, 2 when it cannot run.
Needs ffmpeg and ffprobe on PATH. Standard library only.
"""
import argparse
import array
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

QA = {
    "duration_tol_s": 0.25, "duration_fail_s": 0.75,
    "whip_cells_frac": 0.5, "whip_cell_diff": 10, "whip_gap_frames": 2, "whip_min_frames": 2,
    "whip_radius_s": 0.5, "whip_tol_s": 0.25, "whip_long_s": 1.0, "whip_change_min": 6.0,
    "cut_min_score": 0.10, "cut_spike_ratio": 3.0,
    "audio_env_corr_min": 0.90, "audio_shape_corr_min": 0.85, "audio_warn_corr_min": 0.70, "audio_lag_warn_s": 0.15,
    "min_short_side_px": 1080,
    "still_diff": 0.35, "moving_diff": 0.75, "still_min_frames": 5,
    "lead_freeze_s": 0.20, "trail_freeze_s": 0.50, "mid_freeze_s": 1.00,
}
GRID_W, GRID_H, ANALYSIS_FPS = 18, 32, 30

BLOCK_HEAD = re.compile(r"^From \[(\d+(?:\.\d+)?)s\] to \[(\d+(?:\.\d+)?)s\]\s*$")
POSITION = re.compile(r"^((?:Instantly snap|Whip|Keep) the camera .+)$")


def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def run(cmd, binary=False):
    r = subprocess.run(cmd, capture_output=True)
    if not binary:
        r.stdout = r.stdout.decode("utf-8", "replace")
        r.stderr = r.stderr.decode("utf-8", "replace")
    return r


# ---------- probe and per-frame series ----------
def probe(path):
    r = run(["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,width,height,avg_frame_rate,duration", "-of", "json", str(path)])
    if r.returncode:
        die(f"ffprobe failed on {path}: {r.stderr.strip()[:300]}")
    j = json.loads(r.stdout)
    v = next((s for s in j["streams"] if s.get("codec_type") == "video"), None)
    a = next((s for s in j["streams"] if s.get("codec_type") == "audio"), None)
    if not v:
        die(f"no video stream in {path}")
    num, _, den = (v.get("avg_frame_rate") or "30/1").partition("/")
    fps = float(num) / float(den) if float(den or 0) else 30.0
    dur = float(j["format"]["duration"])
    return {"duration": dur, "width": v["width"], "height": v["height"], "fps": fps or 30.0,
            "has_audio": a is not None, "audio_duration": float(a.get("duration") or dur) if a else None}


def metadata_series(path, vf, key):
    r = run(["ffmpeg", "-v", "error", "-i", str(path), "-an", "-vf", vf, "-f", "null", "-"])
    out, t = [], None
    for line in r.stdout.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            t = float(m.group(1))
            continue
        m = re.search(re.escape(key) + r"=([\d.]+)", line)
        if m and t is not None:
            out.append((t, float(m.group(1))))
    return out


def scene_series(path):
    return metadata_series(path, "scale=270:-2,select='gte(scene,0)',metadata=print:key=lavfi.scene_score:file=-",
                           "lavfi.scene_score")


def motion_series(path):
    """Mean absolute difference with the previous frame at 270 px wide grey; the first frame counts 0."""
    s = metadata_series(path, "scale=270:-2,format=gray,tblend=all_mode=difference,signalstats,"
                              "metadata=print:key=lavfi.signalstats.YAVG:file=-", "lavfi.signalstats.YAVG")
    return [(0.0, 0.0)] + s


def grid_frames(path):
    """Every frame, resampled to ANALYSIS_FPS, as an 18 x 32 grey grid (one bytes object per frame)."""
    size = GRID_W * GRID_H
    r = run(["ffmpeg", "-v", "error", "-i", str(path), "-an", "-vf",
             f"fps={ANALYSIS_FPS},scale={GRID_W}:{GRID_H}:flags=area,format=gray", "-f", "rawvideo", "-"], binary=True)
    data = r.stdout
    return [data[i:i + size] for i in range(0, len(data) - size + 1, size)]


def pick_cuts(series, fps, qa):
    scores = [s for _, s in series]
    half = max(3, int(fps / 2))
    cuts = []
    for i in range(2, len(scores) - 1):
        s = scores[i]
        if s < qa["cut_min_score"]:
            continue
        window = sorted(scores[max(0, i - half):i + half + 1])
        if s < qa["cut_spike_ratio"] * max(window[len(window) // 2], 0.01):
            continue
        if s < max(scores[max(0, i - 3):i + 4]):
            continue
        t = series[i][0]
        if cuts and t - cuts[-1][0] < 0.2:
            if s > cuts[-1][1]:  # two spikes this close are one cut: keep the stronger
                cuts[-1] = (round(t, 3), s)
            continue
        cuts.append((round(t, 3), s))
    return [t for t, _ in cuts]


# ---------- whips ----------
def whip_bursts(frames, qa):
    """Runs of frames in which most grid cells changed from the previous frame: a camera move.
    A super animating changes a small part of the grid, a still talking head almost none."""
    flags = []
    for i in range(1, len(frames)):
        a, b = frames[i - 1], frames[i]
        changed = sum(1 for x, y in zip(a, b) if abs(x - y) > qa["whip_cell_diff"])
        flags.append((i, changed / len(a)))
    bursts = []
    for i, frac in flags:
        if frac >= qa["whip_cells_frac"]:
            if bursts and i - bursts[-1][1] <= qa["whip_gap_frames"] + 1:
                bursts[-1][1] = i
            else:
                bursts.append([i, i])
    out = []
    for a, b in bursts:
        if b - a + 1 >= qa["whip_min_frames"]:
            out.append({"start": round(a / ANALYSIS_FPS, 3), "end": round((b + 1) / ANALYSIS_FPS, 3),
                        "a": a, "b": b})
    return out


def planned_whips(prompt_path):
    """Start time of every timeline block whose position line is a whip (a 'Keep the camera' block is a hold)."""
    lines = Path(prompt_path).read_text(encoding="utf-8-sig").replace("\r\n", "\n").split("\n")
    whips = []
    for i, line in enumerate(lines):
        m = BLOCK_HEAD.match(line.strip())
        if not m:
            continue
        for nxt in lines[i + 1:i + 5]:
            pm = POSITION.match(nxt.strip())
            if pm:
                if not pm.group(1).startswith("Keep"):
                    whips.append(float(m.group(1)))
                break
    return whips


def mean_diff(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / len(a)


def check_whips(bursts, planned, cuts, frames, qa):
    if not planned:
        return [("INFO", "whips", "no plan given (--prompt or --whips); bursts found at: "
                 + (", ".join(f"{b['start']:.2f}" for b in bursts) or "none"))]
    free = list(bursts)
    rows, levels, out = [], [], []
    for p in planned:
        near = min(free, key=lambda b: abs(b["start"] - p), default=None)
        if near is None or abs(near["start"] - p) > qa["whip_radius_s"]:
            hard = next((c for c in cuts if abs(c - p) <= qa["whip_radius_s"]), None)
            rows.append(f"{p:.1f} " + ("hard cut" if hard is not None else "missing"))
            levels.append("FAIL")
            continue
        free.remove(near)
        off = near["start"] - p
        rows.append(f"{p:.1f} {off:+.2f}")
        levels.append("PASS" if abs(off) <= qa["whip_tol_s"] else "WARN")
        if near["end"] - near["start"] > qa["whip_long_s"]:
            out.append(("WARN", "whips", f"the move at {near['start']:.2f} s lasts {near['end'] - near['start']:.2f} s: "
                        "a long float, not a split-second snap"))
        pre = frames[max(0, int(round((near["start"] - 0.2) * ANALYSIS_FPS)))]
        post = frames[min(len(frames) - 1, int(round((near["end"] + 0.3) * ANALYSIS_FPS)))]
        change = mean_diff(pre, post)
        if change < qa["whip_change_min"]:
            out.append(("WARN", "whips", f"after the move at {near['start']:.2f} s the framing barely differs from the "
                        f"framing before it (change {change:.1f}): a position that reads like the source shows no cut; "
                        "look at the frames"))
    status = "FAIL" if "FAIL" in levels else ("WARN" if "WARN" in levels else "PASS")
    text = (f"{len(planned)} planned, {len(bursts)} bursts found; offset of each planned whip in seconds: " + ", ".join(rows))
    if status == "FAIL":
        text += " (a hard cut means the generator read the move as an instant cut; missing means the camera never moved)"
    out.insert(0, (status, "whips", text))
    if free:
        out.append(("WARN", "whips", "unplanned burst(s) at " + ", ".join(f"{b['start']:.2f}" for b in free)
                    + " s: an extra camera move, or a super animating across most of the frame"))
    return out


# ---------- words ----------
def load_words(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return [(float(w["start"]), float(w["end"])) for seg in d.get("segments", []) for w in seg.get("words", [])]


# ---------- audio ----------
SR, WIN, HOP = 8000, 200, 160  # 25 ms windows every 20 ms at 8 kHz
BANDS = (150, 250, 350, 500, 650, 800, 1000, 1250, 1500, 1800, 2200, 2700, 3300, 3800)
FLOOR_DB = -50.0


def pcm(path):
    r = run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], binary=True)
    a = array.array("h")
    a.frombytes(r.stdout[:len(r.stdout) // 2 * 2])
    if sys.byteorder == "big":
        a.byteswap()
    return a


def audio_features(samples, stride):
    """Per-frame level in dB and, on active frames, the spectral shape: the log energy in 14 bands
    (Goertzel) with the frame mean removed, so only the timbre is left."""
    coeffs = [2.0 * math.cos(2.0 * math.pi * f / SR) for f in BANDS]
    env, shapes = [], {}
    for k in range(max((len(samples) - WIN) // HOP + 1, 0)):
        frame = samples[k * HOP:k * HOP + WIN]
        e = sum(x * x for x in frame) / WIN / (32768.0 ** 2)
        env.append(max(10 * math.log10(e + 1e-12), -90.0))
        if k % stride == 0 and env[-1] > FLOOR_DB:
            bands = []
            for c in coeffs:
                s1 = s2 = 0.0
                for x in frame:
                    s0 = x + c * s1 - s2
                    s2 = s1
                    s1 = s0
                bands.append(math.log10(s1 * s1 + s2 * s2 - c * s1 * s2 + 1.0))
            m = sum(bands) / len(bands)
            shapes[k] = [b - m for b in bands]
    return env, shapes


def pearson(x, y):
    n = len(x)
    if n < 3:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    sx, sy = sum((a - mx) ** 2 for a in x), sum((b - my) ** 2 for b in y)
    if sx <= 1e-12 or sy <= 1e-12:
        return 0.0
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / math.sqrt(sx * sy)


def compare_audio(src, gen, max_lag=20):
    ea, sa = src
    eb, sb = gen
    best_lag, best = 0, -2.0
    for lag in range(-max_lag, max_lag + 1):
        xs, ys = [], []
        for i in range(len(ea)):
            j = i + lag
            if 0 <= j < len(eb):
                xs.append(max(ea[i], -70.0))
                ys.append(max(eb[j], -70.0))
        r = pearson(xs, ys)
        if r > best:
            best_lag, best = lag, r
    shape = [pearson(va, sb[i + best_lag]) for i, va in sa.items() if (i + best_lag) in sb]
    return {"lag_s": round(best_lag * HOP / SR, 3), "env_corr": round(best, 3),
            "shape_corr": round(sum(shape) / len(shape), 3) if shape else 0.0, "frames": len(shape),
            "at_search_edge": abs(best_lag) >= max_lag - 1}


# ---------- still stretches ----------
def still_runs(series, fps, qa):
    """(start_s, end_s) of runs of near-identical frames, at least still_min_frames long."""
    d = [v for _, v in series]
    runs, i = [], 1
    while i < len(d):
        if d[i] < qa["still_diff"]:
            j = i
            while j < len(d) and d[j] < qa["still_diff"]:
                j += 1
            if j - i >= qa["still_min_frames"]:
                runs.append((series[i - 1][0], series[j - 1][0] + 1.0 / fps))
            i = j
        else:
            i += 1
    return runs


def motion_bounds(series, qa):
    """Index of the first and last moving frame."""
    d = [v for _, v in series]
    first = next((i for i in range(1, len(d))
                  if d[i] > qa["moving_diff"] and sorted(d[i:i + 3])[len(d[i:i + 3]) // 2] > qa["still_diff"]), 0)
    last = max([i for i in range(1, len(d)) if d[i] > qa["moving_diff"]] or [len(d) - 1])
    return first, last


# ---------- checks ----------
def check_duration(gi, si, words, qa):
    out = []
    diff = gi["duration"] - si["duration"]
    ad = abs(diff)
    status = "PASS" if ad <= qa["duration_tol_s"] else ("WARN" if ad <= qa["duration_fail_s"] else "FAIL")
    out.append((status, "duration", f"generated {gi['duration']:.2f} s, source {si['duration']:.2f} s ({diff:+.2f} s)"
                + ("" if status == "PASS" else ": the prompt asks for exactly the original timing; "
                   + ("it came back shorter" if diff < 0 else "it came back longer"))))
    if words:
        last_end = max(e for _, e in words)
        if gi["duration"] < last_end + 0.05:
            out.append(("FAIL", "duration", f"ends mid-word: the clip stops at {gi['duration']:.2f} s but the last "
                        f"spoken word ends at {last_end:.2f} s in the source transcript"))
    if gi["has_audio"] and gi["audio_duration"] is not None and gi["duration"] - gi["audio_duration"] > 0.3:
        out.append(("WARN", "duration", f"the audio track ends {gi['duration'] - gi['audio_duration']:.2f} s before the picture"))
    return out


def check_audio(src_audio, gen_audio, si, gi, qa):
    if not si["has_audio"]:
        return [("INFO", "audio", "the source has no audio track; nothing to compare")]
    if not gi["has_audio"]:
        return [("FAIL", "audio", "the generated video has no audio track (the original audio was dropped)")]
    if not src_audio[1]:
        return [("INFO", "audio", "the source audio is silent (nothing above the noise floor); nothing to compare")]
    c = compare_audio(src_audio, gen_audio)
    detail = f"envelope {c['env_corr']:.2f}, spectral shape {c['shape_corr']:.2f}, offset {c['lag_s']:+.2f} s"
    if c["env_corr"] >= qa["audio_env_corr_min"] and c["shape_corr"] >= qa["audio_shape_corr_min"]:
        out = [("PASS", "audio", f"original audio kept ({detail})")]
    elif c["env_corr"] >= qa["audio_warn_corr_min"] and c["shape_corr"] >= qa["audio_warn_corr_min"]:
        out = [("WARN", "audio", f"close but changed ({detail}): re-voiced, mixed or drifting; listen to it")]
    else:
        out = [("FAIL", "audio", f"the audio is not the original ({detail}): replaced or re-voiced, or the speech "
                "timing moved; lay the source audio back or regenerate")]
    if abs(c["lag_s"]) >= qa["audio_lag_warn_s"] and out[0][0] != "FAIL":
        out.append(("WARN", "audio", f"the audio sits {c['lag_s']:+.2f} s off the source"
                    + (" (at the search limit, it may be more)" if c["at_search_edge"] else "")))
    return out


def check_resolution(gi, si, qa):
    gs, ss = min(gi["width"], gi["height"]), min(si["width"], si["height"])
    target = min(ss, qa["min_short_side_px"])
    text = f"{gi['width']}x{gi['height']} (source {si['width']}x{si['height']})"
    out = []
    if gs < target:
        out.append(("WARN", "resolution", f"{text}: under {target} px on the short side; upscale before delivery"))
    else:
        out.append(("PASS", "resolution", text))
    ga, sa = gi["width"] / gi["height"], si["width"] / si["height"]
    if abs(ga - sa) / sa > 0.02:
        out.append(("WARN", "resolution", f"the aspect ratio changed ({ga:.3f} against {sa:.3f})"))
    return out


def check_freeze(gen_series, src_series, gi, si, qa):
    fps = gi["fps"]
    first, last = motion_bounds(gen_series, qa)
    lead = gen_series[first][0] if first else 0.0
    trail = gi["duration"] - (gen_series[last][0] + 1.0 / fps)
    out = []
    if lead >= qa["lead_freeze_s"]:
        out.append(("WARN", "freeze", f"the clip starts on a held frame for {lead:.2f} s (video models can hold the "
                    "first frame; the opening hold of this format should still show the speaker moving)"))
    if trail >= qa["trail_freeze_s"]:
        out.append(("WARN", "freeze", f"the clip ends on a held frame for {trail:.2f} s"))
    src_runs = still_runs(src_series, si["fps"], qa)
    mid = [(a, b) for a, b in still_runs(gen_series, fps, qa)
           if a > (gen_series[first][0] if first else 0) + 0.05 and b < gen_series[last][0] + 1.0 / fps - 0.05
           and b - a >= qa["mid_freeze_s"] and not any(a < sb + 0.3 and b > sa - 0.3 for sa, sb in src_runs)]
    for a, b in mid:
        out.append(("WARN", "freeze", f"a frozen stretch from {a:.2f} to {b:.2f} s that the source does not have"))
    if not out:
        out.append(("PASS", "freeze", "no held first or last frame, no frozen stretch the source lacks"))
    return out


def main():
    ap = argparse.ArgumentParser(description="QA of a generated kinetic-multicam video against its source and prompt.")
    ap.add_argument("generated", type=Path, help="the video the model returned")
    ap.add_argument("--source", type=Path, required=True, help="the original take that went into the generation")
    ap.add_argument("--prompt", type=Path, help="the delivered prompt (planned whips come from its timeline blocks)")
    ap.add_argument("--whips", help="planned whip times in seconds, comma separated (instead of --prompt)")
    ap.add_argument("--words", type=Path, help="Whisper JSON of the source (default: <source stem>.json next to it)")
    ap.add_argument("--json", action="store_true", help="print the result as JSON")
    a = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            die(f"{tool} not found on PATH (run scripts/check_env.py for the install command)")
    for p in (a.generated, a.source):
        if not p.exists():
            die(f"file not found: {p}")
    qa = QA

    gi, si = probe(a.generated), probe(a.source)
    words_path = a.words or a.source.with_suffix(".json")
    words = []
    if words_path.exists():
        try:
            words = load_words(words_path)
        except (ValueError, KeyError):
            words = []

    planned = []
    if a.whips:
        planned = [float(x) for x in a.whips.split(",") if x.strip()]
    elif a.prompt:
        planned = planned_whips(a.prompt)

    frames = grid_frames(a.generated)
    if len(frames) < 3:
        die("could not read frames from the generated video")
    bursts = whip_bursts(frames, qa)
    cuts = pick_cuts(scene_series(a.generated), gi["fps"], qa)
    gen_motion, src_motion = motion_series(a.generated), motion_series(a.source)

    results = []
    results += check_duration(gi, si, words, qa)
    results += check_whips(bursts, planned, cuts, frames, qa)
    if si["has_audio"] and gi["has_audio"]:
        results += check_audio(audio_features(pcm(a.source), 2), audio_features(pcm(a.generated), 1), si, gi, qa)
    else:
        results += check_audio(None, None, si, gi, qa)
    results += check_resolution(gi, si, qa)
    results += check_freeze(gen_motion, src_motion, gi, si, qa)

    n_fail = sum(1 for r in results if r[0] == "FAIL")
    n_warn = sum(1 for r in results if r[0] == "WARN")
    verdict = "FAIL" if n_fail else "PASS"
    if a.json:
        print(json.dumps({"generated": str(a.generated), "source": str(a.source), "planned_whips": planned,
                          "bursts": [{"start": b["start"], "end": b["end"]} for b in bursts], "hard_cuts": cuts,
                          "results": [{"status": s, "check": c, "detail": t} for s, c, t in results],
                          "verdict": verdict, "fails": n_fail, "warnings": n_warn}, ensure_ascii=False, indent=1))
    else:
        print(f"qa_result: {a.generated.name} against {a.source.name}")
        for s, c, t in results:
            print(f"[{s}] {c}: {t}")
        print(f"RESULT: {verdict} ({n_fail} fail, {n_warn} warning)")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
