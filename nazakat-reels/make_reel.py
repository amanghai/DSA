#!/usr/bin/env python3
"""Nazakat Telecom reel builder.

Turns one landscape phone video + a JSON plan into a branded 9:16 reel:
square footage panel with beat-synced zoom pulses, pop-in headline text,
customer-review badge, optional captions, original synthesized music,
sound effects and a contact end card. Exports 1080x1920 or true 4K (2160x3840).

Usage:  python make_reel.py examples/iphone18_testimonial.json [--res 4k|1080] [--out file.mp4]
Needs:  ffmpeg + ffprobe on PATH, Python 3.9+, pip install pillow numpy scipy
"""
import argparse, json, os, subprocess, sys
from PIL import ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
# ffmpeg runs with cwd=ROOT and every filter path is relative, so Windows drive
# letters ("C:") never end up inside a filter string.
FONT_BLACK = "assets/fonts/Montserrat-Black.ttf"
FONT_XBOLD = "assets/fonts/Montserrat-ExtraBold.ttf"
SFX = {"impact": "assets/sfx/hook-impact.wav", "swish": "assets/sfx/zoom-swish.wav",
       "pop": "assets/sfx/ui-pop.wav", "shutter": "assets/sfx/camera-shutter.wav"}
RED, YEL = "0xD32F2F", "0xFFD54F"


def run(cmd):
    subprocess.run(cmd, check=True, cwd=ROOT)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation:stream_tags=rotate",
                          "-of", "json", path], capture_output=True, text=True, check=True).stdout
    st = json.loads(out)["streams"][0]
    w, h = st["width"], st["height"]
    rot = int(st.get("tags", {}).get("rotate", 0) or 0)
    for sd in st.get("side_data_list", []):
        rot = int(sd.get("rotation", rot) or rot)
    if abs(rot) % 180 == 90:  # ffmpeg auto-rotates on decode
        w, h = h, w
    return w, h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--res", choices=["1080", "4k"])
    ap.add_argument("--out")
    args = ap.parse_args()
    plan_path = os.path.abspath(args.plan)
    P = json.load(open(plan_path, encoding="utf-8"))
    base = os.path.dirname(plan_path)
    src = os.path.abspath(os.path.join(base, P["source"]))
    out = os.path.abspath(args.out or os.path.join(base, P.get("output", "reel.mp4")))
    res = args.res or P.get("resolution", "1080")
    S = 2 if res == "4k" else 1
    OW, OH = 1080 * S, 1920 * S
    def px(v): return int(round(v * S))

    work = os.path.join(ROOT, "work"); os.makedirs(f"{work}/txt", exist_ok=True); os.makedirs(f"{work}/segs", exist_ok=True)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    SW, SH = probe(src)
    brand = P["brand"]

    # ---------- timeline ----------
    segs = P["segments"]
    starts, t = [], 0.0
    for s in segs:
        starts.append(t); t += (s["to"] - s["from"]) / s.get("speed", 1)
    VID_END = t
    END = P.get("endcard_seconds", 5.0)
    TOTAL = VID_END + END
    def T(v): return VID_END if v == "end" else float(v)
    print("segment starts:", [round(x, 2) for x in starts], f"video_end={VID_END:.2f} total={TOTAL:.2f}")

    # ---------- stage 1: per-segment square panel clips ----------
    PY, PS = px(600), px(1080)
    lst = []
    for i, s in enumerate(segs):
        cx, cy, cs = P["crops"][s.get("crop", "two")]
        size = int(cs * SH) // 2 * 2
        x = min(max(0, int(cx * SW)), SW - size); y = min(max(0, int(cy * SH)), SH - size)
        name = f"s{i:02d}.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s['from']}", "-t", f"{s['to'] - s['from']}", "-i", src, "-an",
             "-vf", f"setpts=(PTS-STARTPTS)/{s.get('speed', 1)},fps=30,crop={size}:{size}:{x}:{y},"
                    f"scale={PS}:{PS}:flags=lanczos,setsar=1",
             "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-pix_fmt", "yuv420p", f"work/segs/{name}"])
        lst.append(f"file '{name}'")
    open(f"{work}/segs/list.txt", "w").write("\n".join(lst))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "work/segs/list.txt", "-c", "copy", "work/panel.mp4"])

    # ---------- speech track (real customer audio) ----------
    speech = P.get("speech")
    if speech:
        parts, fs = [], []
        for j, (a, b) in enumerate(speech["ranges"]):
            fs.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,afade=t=out:st={b - a - 0.06}:d=0.06[p{j}]")
            parts.append(f"[p{j}]")
        fs.append("".join(parts) + f"concat=n={len(parts)}:v=0:a=1,highpass=f=90,lowpass=f=12000,afftdn=nr=10,"
                  "acompressor=threshold=-24dB:ratio=3:attack=5:release=120,loudnorm=I=-16:TP=-2:LRA=8[sp]")
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", ";".join(fs), "-map", "[sp]",
             "-ar", "48000", "-ac", "2", "work/speech.wav"])
    SP_AT = T(speech["at"]) if speech else 0

    # ---------- music ----------
    sections = [[T(a), T(b), k] for a, b, k in P["music_sections"]] + [[VID_END, TOTAL, "out"]]
    run([sys.executable, "tools/music.py", "work/music.wav", f"{TOTAL:.3f}", json.dumps(sections)])

    # ---------- text helpers ----------
    tcount = [0]
    def tf(text):
        tcount[0] += 1
        p = f"work/txt/t{tcount[0]:03d}.txt"
        open(os.path.join(ROOT, p), "w", encoding="utf-8").write(text)
        return p

    def fit(text, font, maxw, maxsize):
        s = maxsize
        while s > 30 and ImageFont.truetype(os.path.join(ROOT, font), px(s)).getlength(text) > px(maxw): s -= 2
        return px(s)

    def txt(text, font, y, s, e, color="white", maxsize=104, box=None, pop=True, plain=False, x=None, maxw=None):
        size = fit(text, font, maxw or (680 if box else 720), maxsize)
        if pop and s > 0:
            p = f"min(1,(t-{s:.3f})/0.22)"
            fsz = f"'{size}*(0.55+0.45*{p}+0.22*sin(PI*{p}))'"
        else:
            fsz = str(size)
        o = [f"fontfile={font}", f"textfile={tf(text)}", f"fontsize={fsz}", f"fontcolor={color}",
             f"x={x if x is not None else '(w-text_w)/2'}", f"y={px(y)}-text_h/2",
             f"enable='between(t,{s:.3f},{e - 0.034:.3f})'"]
        if box: o += ["box=1", f"boxcolor={box}", f"boxborderw={px(20)}"]
        elif not plain: o += [f"borderw={px(5)}", "bordercolor=black@0.6", "shadowx=0", f"shadowy={px(6)}", "shadowcolor=black@0.45"]
        return "drawtext=" + ":".join(o)

    # ---------- stage 2: compose ----------
    full = "+".join(f"between(it,{a},{b})" for a, b, k in sections if k == "full") or "0"
    fx_cfg = P.get("motion", {})
    pulse = f"0.05*exp(-mod(it,0.5)*9)*({full})"
    terms = [pulse]
    if "push" in fx_cfg:  # slow zoom-in during a build-up: [from, to]
        a, b = fx_cfg["push"]; terms.append(f"0.15*max(0,min(1,(it-{a})/{b - a}))*between(it,{a},{b})")
    if speech:
        terms.append(f"0.06*max(0,min(1,(it-{SP_AT})/{max(0.1, VID_END - SP_AT)}))*gte(it,{SP_AT})")
    shake = "0"
    if "shake" in fx_cfg:
        a = fx_cfg["shake"]; shake = f"{px(12)}*sin(it*90)*exp(-(it-{a})*7)*between(it,{a},{a + 0.5})"

    f = []
    f.append("[0:v]setpts=PTS-STARTPTS,fps=30,split[vbg][vfg0]")
    f.append(f"[vfg0]scale={int(PS * 1.5)}:{int(PS * 1.5)}:flags=lanczos[vfg]")
    f.append(f"[vbg]scale=-2:{OH},crop={OW}:{OH},boxblur={px(30)}:3,eq=brightness=-0.25:saturation=1.3[bg]")
    f.append(f"[vfg]zoompan=z='1+{'+'.join(terms)}':x='iw/2-(iw/zoom/2)+{shake}':y='ih/2-(ih/zoom/2)':d=1:s={PS}x{PS}:fps=30,"
             "eq=contrast=1.06:saturation=1.15,unsharp=5:5:0.5[pan]")
    f.append(f"[bg][pan]overlay=0:{PY}:shortest=1[c0]")
    # round logos rendered once (geq per frame is slow at 4K)
    ls, lb = px(124), px(480)
    for name, d in (("logo_s", ls), ("logo_b", lb)):
        run(["ffmpeg", "-v", "error", "-y", "-i", "assets/logo.jpg", "-vf",
             f"scale={d}:{d},format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lte(hypot(X-{d/2},Y-{d/2}),{d/2 - 2}),255,0)'",
             "-frames:v", "1", f"work/{name}.png"])
    logo_from = P.get("logo_bug_from", 2)
    f.append(f"[c0][1:v]overlay=W-w-{px(28)}:{PY + px(24)}:shortest=1:enable='gte(t,{logo_from})'[c1]")

    fx = [f"drawbox=x=0:y={PY - px(6)}:w={OW}:h={px(6)}:color={RED}:t=fill",
          f"drawbox=x=0:y={PY + PS}:w={OW}:h={px(6)}:color={RED}:t=fill",
          f"drawbox=x=0:y={PY - px(6)}:w='{OW}*t/{VID_END:.3f}':h={px(6)}:color={YEL}:t=fill"]
    for b in P["beats"]:
        s, e, l1, l2 = T(b[0]), T(b[1]), b[2], b[3]
        pill = b[4] if len(b) > 4 else ""
        first = s == 0
        fx.append(txt(l1, FONT_BLACK, 300, s, e, pop=not first))
        fx.append(txt(l2, FONT_BLACK, 410, s if first else s + 0.1, e, color=YEL, pop=not first))
        if pill:
            fx.append(txt(pill, FONT_XBOLD, 518, s if first else s + 0.2, e, box=RED, maxsize=46, pop=False))
    if "badge" in P:
        bd = P["badge"]; a, b = T(bd["from"]), T(bd["to"])
        fx.append(txt(bd["text"], FONT_XBOLD, 670, a, b, box="black@0.6", maxsize=34, pop=False, x=str(px(80))))
        fx.append(f"drawbox=x={px(58)}:y={PY + px(62)}:w={px(14)}:h={px(14)}:color=0xFF3B30:t=fill:"
                  f"enable='between(t,{a:.3f},{b:.3f})*lt(mod(t,1),0.6)'")
    for c in P.get("captions", []):  # [from, to, text] in reel time, inside panel bottom
        fx.append(txt(c[2], FONT_XBOLD, 1540, T(c[0]), T(c[1]), box="black@0.65", maxsize=50, pop=False, maxw=860))
    fx.append(txt(brand["address"], FONT_XBOLD, 1750, 0, VID_END, maxsize=38, pop=False))
    fx.append(txt("  |  ".join(brand["phones"]), FONT_BLACK, 1815, 0, VID_END, color=YEL, maxsize=44, pop=False))
    for c in P.get("flashes", []):
        fx.append(f"drawbox=x=0:y=0:w={OW}:h={OH}:color=white@0.75:t=fill:enable='between(t,{c - 0.001:.3f},{c + 0.066:.3f})'")
    f.append("[c1]" + ",".join(fx) + "[c2]")

    E = VID_END
    f.append(f"color=c=0xF5F5F5:s={OW}x{OH}:r=30:d={TOTAL}[white]")
    f.append(f"[white][2:v]overlay=(W-w)/2:{px(330)}:shortest=1[ec0]")
    ec = [txt(f"Since {brand['since']}", FONT_XBOLD, 280, E + 0.1, TOTAL, color="0x555555", maxsize=40, pop=False, plain=True)]
    if brand.get("product_line"):
        ec.append(txt(brand["product_line"], FONT_BLACK, 880, E + 0.3, TOTAL, color="0x111111", maxsize=50, plain=True))
    ec += [txt(brand["street"], FONT_XBOLD, 960, E + 0.5, TOTAL, color="0x333333", maxsize=42, pop=False, plain=True),
           txt(brand["city"], FONT_BLACK, 1030, E + 0.6, TOTAL, color=RED, maxsize=72, plain=True),
           txt("Call / WhatsApp", FONT_XBOLD, 1150, E + 0.8, TOTAL, box=RED, maxsize=44, pop=False)]
    for k, ph in enumerate(brand["phones"]):
        ec.append(txt(ph, FONT_BLACK, 1250 + 90 * k, E + 0.95 + 0.1 * k, TOTAL, color="0x111111", maxsize=76, plain=True))
    f.append("[ec0]" + ",".join(ec) + "[endc]")
    f.append(f"[c2][endc]overlay=0:0:enable='gte(t,{E:.3f})',format=yuv420p[vout]")

    # inputs: 0 panel (no audio), 1 small logo, 2 big logo, 3 music, 4 speech?, then sfx
    inputs = ["-i", "work/panel.mp4", "-loop", "1", "-i", "work/logo_s.png", "-loop", "1", "-i", "work/logo_b.png",
              "-i", "work/music.wav"]
    duck = f"if(between(t,{SP_AT},{VID_END}),0.14,0.8)" if speech else "0.8"
    f.append(f"[3:a]aresample=48000,volume='{duck}':eval=frame[mus]")
    mix = ["[mus]"]
    nxt = 4
    if speech:
        inputs += ["-i", "work/speech.wav"]
        f.append(f"[{nxt}:a]aresample=48000,adelay={int(SP_AT * 1000)}:all=1[sp]"); mix.append("[sp]"); nxt += 1
    for j, (kind, at, *g) in enumerate(P.get("sfx", [])):
        inputs += ["-i", SFX[kind]]
        at = T(at); gain = g[0] if g else 0.5
        f.append(f"[{nxt}:a]aresample=48000,volume={gain},adelay={int(at * 1000)}:all=1[x{j}]"); mix.append(f"[x{j}]"); nxt += 1
    f.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{TOTAL},"
             "loudnorm=I=-14:TP=-1.5:LRA=9,alimiter=limit=0.8:level=disabled[aout]")

    crf = "18" if S == 2 else "17"
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(f), "-map", "[vout]", "-map", "[aout]",
         "-t", f"{TOTAL:.3f}", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", crf,
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out])
    print("wrote", out)


if __name__ == "__main__":
    main()
