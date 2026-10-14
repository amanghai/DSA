#!/usr/bin/env python3
"""Nazakat Telecom 16:9 reel builder (GenZ style).

Full-frame landscape footage (no square panel) with 16:9 punch-in crops, speed ramps, beat zoom
punches, flash + RGB-split glitch transitions, colour-emoji stickers, word-by-word pop captions
(current word in yellow), original synthesized music ducked under the customer's real speech,
sound effects and a contact end card. Exports 1920x1080 or true 4K (3840x2160).

Usage:  python make_wide.py examples/iphone18_genz_16x9.json [--res 4k|1080] [--seconds N] [--out file.mp4]
   or:  python make_reel.py examples/iphone18_genz_16x9.json --format 16x9 ...
Plan times may be numbers (reel seconds) or segment marks such as "drop", "speech+2.5" or "end".
"""
import argparse, json, os, re, sys
from PIL import ImageFont
from make_reel import ROOT, FONT_BLACK, FONT_XBOLD, SFX, RED, YEL, run, probe

sys.path.insert(0, os.path.join(ROOT, "tools"))
import stickers  # noqa: E402

FPS = 30
FR = 1 / FPS


def atempo(speed):
    out = []
    while speed > 2.0:
        out.append("atempo=2.0"); speed /= 2.0
    out.append(f"atempo={speed:.4f}")
    return ",".join(out)


def build(args):
    plan_path = os.path.abspath(args.plan)
    P = json.load(open(plan_path, encoding="utf-8"))
    base = os.path.dirname(plan_path)
    src = os.path.abspath(os.path.join(base, P["source"]))
    out = os.path.abspath(args.out or os.path.join(base, P.get("output", "reel_16x9.mp4")))
    S = 2 if (args.res or P.get("resolution", "1080")) == "4k" else 1
    OW, OH = 1920 * S, 1080 * S
    MX, MY = 96, 54  # 5% title-safe margins (1080p units)
    def px(v): return int(round(v * S))

    for d in ("txt", "segs", "stk"): os.makedirs(os.path.join(ROOT, "work", "wide", d), exist_ok=True)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    SW, SH = probe(src)
    brand = P["brand"]

    # ---------- timeline: ramps become equal-source-length chunks; frame counts keep sync ----------
    chunks, marks, t = [], {}, 0.0
    for s in P["segments"]:
        if "mark" in s: marks[s["mark"]] = t
        speeds = s.get("ramp", [s.get("speed", 1.0)])
        L = (s["to"] - s["from"]) / len(speeds)
        for k, sp in enumerate(speeds):
            n = max(1, round(L / sp * FPS))
            chunks.append(dict(src=s["from"] + k * L, len=L, speed=sp, frames=n, start=t, crop=s.get("crop", "wide"),
                               audio=bool(s.get("audio")), ambient=float(s.get("ambient", 0))))
            t += n / FPS
    VID_END = t
    TOTAL = VID_END + P.get("endcard_seconds", 5.0)
    marks["end"] = VID_END

    def T(v):
        if isinstance(v, (int, float)): return float(v)
        m = re.fullmatch(r"([a-z_][a-z0-9_]*)\s*([+-]\s*[0-9.]+)?", v.strip())
        if not m or m.group(1) not in marks: sys.exit(f"unknown time/mark: {v!r} (marks: {', '.join(marks)})")
        return marks[m.group(1)] + (float(m.group(2).replace(" ", "")) if m.group(2) else 0.0)
    print("marks:", {k: round(v, 2) for k, v in marks.items()}, f"total={TOTAL:.2f}")
    LIMIT = min(TOTAL, args.seconds) if getattr(args, "seconds", None) else TOTAL

    # ---------- stage 1: 16:9 crops per chunk ----------
    lst = []
    for i, c in enumerate(chunks):
        cx, cy, cw = P["crops"][c["crop"]]
        w = int(cw * SW) // 2 * 2; h = int(w * 9 / 16) // 2 * 2
        x = min(max(0, int(cx * SW)), SW - w); y = min(max(0, int(cy * SH)), SH - h)
        name = f"w{i:02d}.mp4"
        cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{c['src']:.3f}", "-t", f"{c['len'] + 0.5:.3f}", "-i", src, "-an",
               "-vf", f"setpts=(PTS-STARTPTS)/{c['speed']},fps={FPS},crop={w}:{h}:{x}:{y},"
                      f"scale={OW}:{OH}:flags=lanczos,setsar=1",
               "-frames:v", str(c["frames"]), "-c:v", "libx264", "-crf", "13", "-preset", "fast", "-pix_fmt", "yuv420p",
               f"work/wide/segs/{name}"]
        key = os.path.join(ROOT, "work/wide/segs", name + ".cmd")  # skip clips already cut with the same settings
        if not (os.path.exists(key) and open(key, encoding="utf-8").read() == repr(cmd)
                and os.path.getsize(os.path.join(ROOT, "work/wide/segs", name)) > 0):
            run(cmd)
            open(key, "w", encoding="utf-8").write(repr(cmd))
        lst.append(f"file '{name}'")
    open(os.path.join(ROOT, "work/wide/segs/list.txt"), "w").write("\n".join(lst))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "work/wide/segs/list.txt", "-c", "copy",
         "work/wide/footage.mp4"])

    # ---------- real audio: customer speech + optional low ambient under the unboxing ----------
    def merged(kind):  # contiguous chunks (same source flow, same speed) become one audio piece
        out_ = []
        for c in chunks:
            if not c[kind]: continue
            p = out_[-1] if out_ else None
            if p and p["speed"] == c["speed"] and abs(p["src"] + p["len"] - c["src"]) < 1e-3 \
                    and abs(p["start"] + p["frames"] * FR - c["start"]) < 1e-3:
                p["len"] += c["len"]; p["frames"] += c["frames"]
            else:
                out_.append(dict(c))
        return out_

    def audio_track(pieces, gain_key, post, name):
        fs, labels = [], []
        for j, c in enumerate(pieces):
            d = c["frames"] * FR
            g = 1.0 if gain_key == "audio" else c["ambient"]
            fs.append(f"[0:a]atrim={c['src']:.3f}:{c['src'] + c['len']:.3f},asetpts=PTS-STARTPTS,{atempo(c['speed'])},"
                      f"atrim=0:{d:.3f},afade=t=in:d=0.04,afade=t=out:st={max(0, d - 0.06):.3f}:d=0.06,volume={g},"
                      f"adelay={int(round(c['start'] * 1000))}:all=1[q{j}]")
            labels.append(f"[q{j}]")
        fs.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,apad,atrim=0:{TOTAL:.3f}{post}[o]")
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", ";".join(fs), "-map", "[o]",
             "-ar", "48000", "-ac", "2", f"work/wide/{name}"])

    speech = merged("audio")
    if speech:
        audio_track(speech, "audio", ",highpass=f=90,lowpass=f=12000,afftdn=nr=10,"
                    "acompressor=threshold=-24dB:ratio=3:attack=5:release=120,loudnorm=I=-13:TP=-2:LRA=7", "speech.wav")
    ambient = merged("ambient")
    if ambient:  # phone mics record the counter quietly: normalise, then sit well under the music
        audio_track(ambient, "ambient", ",highpass=f=120,afftdn=nr=8,loudnorm=I=-20:TP=-6,volume=0.5", "ambient.wav")

    # ---------- music ----------
    sections = [[T(a), T(b), k] for a, b, k in P["music_sections"]] + [[VID_END, TOTAL, "out"]]
    bpm = P.get("bpm", 128)
    run([sys.executable, "tools/music.py", "work/wide/music.wav", f"{TOTAL:.3f}", json.dumps(sections), str(bpm)])

    # ---------- drawtext helper ----------
    tcount = [0]
    def tf(text):
        tcount[0] += 1
        p = f"work/wide/txt/t{tcount[0]:03d}.txt"
        open(os.path.join(ROOT, p), "w", encoding="utf-8").write(text)
        return p

    def fsize(text, font, maxw, size):
        while size > 20 and ImageFont.truetype(os.path.join(ROOT, font), px(size)).getlength(text) > px(maxw): size -= 2
        return px(size)

    def dt(text, font, y, s, e, color="white", size=60, x=None, box=None, pop=True, outline=True, maxw=1728):
        sz = fsize(text, font, maxw, size)
        if pop and s > 0:
            p = f"min(1,(t-{s:.3f})/0.2)"
            fz = f"'{sz}*(0.6+0.4*{p}+0.2*sin(PI*{p}))'"
        else:
            fz = str(sz)
        o = [f"fontfile={font}", f"textfile={tf(text)}", f"fontsize={fz}", f"fontcolor={color}",
             f"x={x if x is not None else '(w-text_w)/2'}", f"y={px(y)}-text_h/2",
             f"enable='between(t,{s:.3f},{e - FR:.3f})'"]
        if box: o += ["box=1", f"boxcolor={box}", f"boxborderw={px(18)}"]
        elif outline: o += [f"borderw={px(5)}", "bordercolor=black"]
        return "drawtext=" + ":".join(o)

    # ---------- inputs ----------
    inputs = ["-i", "work/wide/footage.mp4"]
    def add_input(*a):
        inputs.extend(a); return sum(1 for v in inputs if v == "-i") - 1

    ls, lb = px(150), px(600)
    for name, d in (("logo_s", ls), ("logo_b", lb)):
        run(["ffmpeg", "-v", "error", "-y", "-i", "assets/logo.jpg", "-vf",
             f"scale={d}:{d},format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-{d/2},Y-{d/2}),{d/2 - 2}),255,0)'",
             "-frames:v", "1", f"work/wide/{name}.png"])
    i_ls = add_input("-loop", "1", "-framerate", str(FPS), "-t", f"{VID_END:.3f}", "-i", "work/wide/logo_s.png")
    i_lb = add_input("-loop", "1", "-framerate", str(FPS), "-t", f"{TOTAL:.3f}", "-i", "work/wide/logo_b.png")

    # ---------- video: zoom punches, beat pulses, push-ins ----------
    beat = 60 / bpm
    full = "+".join(f"between(it,{a:.3f},{b:.3f})" for a, b, k in sections if k == "full") or "0"
    terms = [f"0.03*exp(-mod(it,{beat:.4f})*10)*({full})"]
    for p in P.get("punches", []):
        p = T(p); terms.append(f"0.12*exp(-(it-{p:.3f})*7)*gte(it,{p:.3f})")
    for a, b in P.get("pushes", []):
        a, b = T(a), T(b); terms.append(f"0.18*max(0,min(1,(it-{a:.3f})/{b - a:.3f}))*between(it,{a:.3f},{b:.3f})")
    f = [f"[0:v]setpts=PTS-STARTPTS,fps={FPS},zoompan=z='1+{'+'.join(terms)}':x='iw/2-(iw/zoom/2)':"
         f"y='ih/2-(ih/zoom/2)':d=1:s={OW}x{OH}:fps={FPS},eq=contrast=1.05:saturation=1.12,unsharp=5:5:0.4,"
         f"tpad=stop_mode=clone:stop_duration={TOTAL - VID_END + 1:.3f}[v0]"]  # main stream must outlast the end card
    lf = T(P.get("logo_bug_from", 0))
    f.append(f"[v0][{i_ls}:v]overlay={px(MX)}:{px(MY)}:enable='between(t,{lf:.3f},{VID_END - FR:.3f})'[v1]")

    # ---------- word-by-word pop captions (current word yellow) ----------
    cap = []
    def reel_time(ts):
        for c in chunks:
            if c["audio"] and c["speed"] == 1 and c["src"] - 1e-3 <= ts <= c["src"] + c["len"] + 1e-3:
                return c["start"] + ts - c["src"]
        return None
    words = [(reel_time(a), reel_time(b) or reel_time(a) + 0.2, w) for a, b, w in P.get("words", [])]
    words = [w for w in words if w[0] is not None]
    groups = []
    for w in words:
        g = groups[-1] if groups else None
        if g and len(g) < 4 and w[0] - g[-1][1] < 0.4 and w[1] - g[0][0] < 2.4 and sum(len(x[2]) for x in g) + len(w[2]) < 24:
            g.append(w)
        else:
            groups.append([w])
    cs = P.get("caption_style", {})
    CY, CSZ = cs.get("y", 905), cs.get("size", 72)
    for gi, g in enumerate(groups):
        g0 = g[0][0]
        nxt = groups[gi + 1][0][0] if gi + 1 < len(groups) else 1e9
        g1 = min(nxt, g[-1][1] + 0.6)
        sz = fsize(" ".join(x[2] for x in g), FONT_BLACK, 1728, CSZ)
        font = ImageFont.truetype(os.path.join(ROOT, FONT_BLACK), sz)
        sp = font.getlength(" ") * 1.8  # room for the popped (bigger) word
        widths = [font.getlength(x[2]) for x in g]
        left = (OW - (sum(widths) + sp * (len(g) - 1))) / 2
        asc, desc = font.getmetrics(); half = (asc + desc) / 2
        for k, (ws, we, word) in enumerate(g):
            cxw = left + sum(widths[:k]) + sp * k + widths[k] / 2
            tfile = tf(word)
            common = [f"fontfile={FONT_BLACK}", f"textfile={tfile}", "y_align=font", f"borderw={px(6)}", "bordercolor=black"]
            cap.append("drawtext=" + ":".join(common + [f"fontsize={sz}", "fontcolor=white", f"x={cxw - widths[k] / 2:.1f}",
                                                         f"y={px(CY) - half:.1f}", f"enable='between(t,{g0:.3f},{g1 - FR:.3f})'"]))
            hi_end = g[k + 1][0] if k + 1 < len(g) else g1
            pk = f"(1+0.2*sin(PI*min(1,(t-{ws:.3f})/0.16)))"
            cap.append("drawtext=" + ":".join(common + [f"fontsize='{sz}*{pk}'", f"fontcolor={YEL}", f"x={cxw:.1f}-text_w/2",
                                                         f"y='{px(CY)}-{half:.1f}*{pk}'",
                                                         f"enable='between(t,{ws:.3f},{hi_end - FR:.3f})'"]))
    f.append("[v1]" + (",".join(cap) if cap else "null") + "[v2]")

    # ---------- end card ----------
    E = VID_END
    f.append(f"color=c={RED}:s={OW}x{OH}:r={FPS}:d={TOTAL:.3f}[red]")
    f.append(f"[red][{i_lb}:v]overlay={px(150)}:(H-h)/2:shortest=1[ec0]")
    X0 = str(px(840)); RW = 1824 - 840
    ec = [dt(f"SINCE {brand['since']}", FONT_XBOLD, 200, E + 0.1, TOTAL, color=YEL, size=44, x=X0, pop=False, outline=False, maxw=RW)]
    if brand.get("product_line"):
        ec.append(dt(brand["product_line"], FONT_BLACK, 290, E + 0.25, TOTAL, size=64, x=X0, outline=False, maxw=RW))
    ec += [dt(brand["street"], FONT_XBOLD, 385, E + 0.4, TOTAL, size=50, x=X0, pop=False, outline=False, maxw=RW),
           dt(brand["city"], FONT_BLACK, 490, E + 0.5, TOTAL, color=YEL, size=124, x=X0, outline=False, maxw=RW),
           dt("Call / WhatsApp", FONT_XBOLD, 625, E + 0.7, TOTAL, color=RED, size=44, x=str(px(858)), box="white", pop=False, maxw=RW)]
    for k, ph in enumerate(brand["phones"]):
        ec.append(dt(ph, FONT_BLACK, 745 + 120 * k, E + 0.85 + 0.12 * k, TOTAL, size=100, x=X0, outline=False, maxw=RW))
    f.append("[ec0]" + ",".join(ec) + "[endc]")
    f.append(f"[v2][endc]overlay=0:0:enable='gte(t,{E:.3f})'[v3]")

    # ---------- emoji stickers (meme lines, hook) ----------
    last = "v3"
    for j, st in enumerate(P.get("stickers", [])):
        s, e = T(st["at"]), T(st["to"])
        pth = f"work/wide/stk/s{j:02d}.png"
        _, w, h = stickers.render(st["text"], os.path.join(ROOT, FONT_BLACK), px(st.get("size", 64)), st.get("style", "white"),
                                  os.path.join(ROOT, pth), st.get("rot", 0), maxw=px(1728))
        X = min(max(st.get("x", 0.5) * OW, px(MX) + w / 2), OW - px(MX) - w / 2)
        Y = min(max(st.get("y", 0.72) * OH, px(MY) + h / 2), OH - px(MY) - h / 2)
        k = add_input("-loop", "1", "-framerate", str(FPS), "-t", f"{e + 0.2:.3f}", "-i", pth)
        if s > 0:
            f.append(f"[{k}:v]format=rgba,fade=t=in:st={s:.3f}:d=0.12:alpha=1[k{j}]")
            yexp = f"{Y - h / 2:.1f}+{px(60)}*exp(-(t-{s:.3f})*11)*cos((t-{s:.3f})*26)"
        else:
            f.append(f"[{k}:v]format=rgba[k{j}]")
            yexp = f"{Y - h / 2:.1f}"
        f.append(f"[{last}][k{j}]overlay=x={X - w / 2:.1f}:y='{yexp}':enable='between(t,{s:.3f},{e - FR:.3f})'[st{j}]")
        last = f"st{j}"

    # ---------- flash + RGB-split glitch transitions ----------
    fx = []
    for g in P.get("glitches", []):
        g = T(g)
        fx.append(f"rgbashift=rh=-{px(22)}:bh={px(22)}:rv={px(6)}:enable='between(t,{g:.3f},{g + 2 * FR:.3f})'")
        fx.append(f"rgbashift=rh={px(12)}:bh=-{px(12)}:gv=-{px(8)}:enable='between(t,{g + 3 * FR:.3f},{g + 5 * FR:.3f})'")
    for c in P.get("flashes", []):
        c = T(c)
        fx.append(f"drawbox=x=0:y=0:w={OW}:h={OH}:color=white@0.8:t=fill:enable='between(t,{c - 0.001:.3f},{c + 2 * FR:.3f})'")
    # quick tests cut inside the graph: output-side -t left ffmpeg idling after the last frame
    f.append(f"[{last}]" + ",".join(fx + ["format=yuv420p", f"trim=0:{LIMIT:.3f}"]) + "[vout]")

    # ---------- audio mix ----------
    i_mus = add_input("-i", "work/wide/music.wav")
    duck = "0.62"
    if speech:
        iv = [(c["start"], c["start"] + c["frames"] * FR) for c in speech]
        parts = "+".join(f"min(1,max(0,(t-{a - 0.25:.3f})/0.25))*min(1,max(0,({b + 0.3:.3f}-t)/0.3))" for a, b in iv)
        duck = f"0.62-0.5*min(1,{parts})"
    f.append(f"[{i_mus}:a]aresample=48000,volume='{duck}':eval=frame[mus]")
    mix = ["[mus]"]
    if speech:
        k = add_input("-i", "work/wide/speech.wav"); f.append(f"[{k}:a]aresample=48000[sp]"); mix.append("[sp]")
    if ambient:
        k = add_input("-i", "work/wide/ambient.wav"); f.append(f"[{k}:a]aresample=48000[amb]"); mix.append("[amb]")
    for j, (kind, at, *g) in enumerate(P.get("sfx", [])):
        k = add_input("-i", SFX[kind])
        f.append(f"[{k}:a]aresample=48000,volume={g[0] if g else 0.5},adelay={int(T(at) * 1000)}:all=1[x{j}]")
        mix.append(f"[x{j}]")
    f.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{TOTAL:.3f},"
             f"loudnorm=I=-14:TP=-1.5:LRA=9,alimiter=limit=0.8:level=disabled,atrim=0:{LIMIT:.3f}[aout]")

    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(f), "-map", "[vout]", "-map", "[aout]",
         "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18" if S == 2 else "17",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out])
    print("wrote", out, f"({LIMIT:.2f}s)")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--res", choices=["1080", "4k"])
    ap.add_argument("--seconds", type=float, help="only render the first N seconds (quick test)")
    ap.add_argument("--out")
    build(ap.parse_args(argv))


if __name__ == "__main__":
    main()
