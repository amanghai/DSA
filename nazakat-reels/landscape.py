#!/usr/bin/env python3
"""16:9 GenZ mode for make_reel.py (plan "format": "16:9").

Full-frame landscape edit at 1920x1080 or true 4K (3840x2160): 16:9 punch-in crops, smooth speed
ramps, beat-synced zoom punches, flash + RGB-split glitch hits, emoji stickers, word-by-word pop
captions and a brand end card. drawtext cannot draw colour emoji, so every text/sticker/end-card
graphic is drawn with Pillow and composited into ONE RGBA overlay track (an ffconcat list of PNG
states); ffmpeg only overlays that single stream on the footage.

Plan times may be numbers (reel seconds), "end" (footage end) or "@id", "@id.end", "@id+0.5"
referring to a segment tagged with "id".
"""
import hashlib, json, math, os, re, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from make_reel import ROOT, FONT_BLACK, FONT_XBOLD, SFX, run, probe

FPS = 30
POPF = 6  # pop-in animation length in frames
SAFE = 0.05  # title-safe margin
COLORS = {"white": (255, 255, 255), "yellow": (255, 213, 79), "red": (211, 47, 47), "black": (0, 0, 0)}
EMOJI_FONTS = ["C:/Windows/Fonts/seguiemj.ttf", "/System/Library/Fonts/Apple Color Emoji.ttc",
               "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"]


def rgb(c):
    if isinstance(c, (list, tuple)): return tuple(c)
    if c.startswith("#"): return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    return COLORS[c]


def is_emoji(ch):
    c = ord(ch)
    return (c in (0x200D, 0xFE0F, 0x20E3) or 0x1F000 <= c <= 0x1FAFF or 0x2600 <= c <= 0x27BF
            or 0x2B00 <= c <= 0x2BFF or 0x2300 <= c <= 0x23FF)


def split_runs(text):
    runs = []
    for ch in text:
        e = is_emoji(ch)
        if runs and runs[-1][0] == e: runs[-1][1] += ch
        else: runs.append([e, ch])
    return runs


class Gfx:
    """Pillow text renderer: Montserrat with black outline + soft shadow, colour emoji stickers."""

    def __init__(self, S):
        self.S = S
        self.fonts = {}
        self.efont = next((p for p in EMOJI_FONTS if os.path.exists(p)), None)
        if not self.efont: print("warning: no colour emoji font found, emoji will be dropped")

    def font(self, path, size):
        k = (path, size)
        if k not in self.fonts: self.fonts[k] = ImageFont.truetype(os.path.join(ROOT, path), size)
        return self.fonts[k]

    def emoji(self, run, size):
        if not self.efont: return None
        try:
            ef, scale = ImageFont.truetype(self.efont, size), 1.0
        except OSError:  # bitmap emoji fonts only load at their native size
            for native in (109, 160):
                try: ef, scale = ImageFont.truetype(self.efont, native), size / native; break
                except OSError: continue
            else: return None
        n = ef.size
        tmp = Image.new("RGBA", (int(ef.getlength(run) * 1.3) + 20, int(n * 1.7)), (0, 0, 0, 0))
        ImageDraw.Draw(tmp).text((10, int(n * 1.3)), run, font=ef, embedded_color=True, anchor="ls")
        bb = tmp.getbbox()
        if not bb: return None
        tmp = tmp.crop(bb)
        if scale != 1.0: tmp = tmp.resize((max(1, round(tmp.width * scale)), max(1, round(tmp.height * scale))), Image.LANCZOS)
        o = max(2, size // 16)  # white sticker outline so dark emoji read on any footage
        a = Image.new("L", (tmp.width + 2 * o, tmp.height + 2 * o), 0); a.paste(tmp.getchannel("A"), (o, o))
        a = a.filter(ImageFilter.MaxFilter(2 * o + 1))
        out = Image.new("RGBA", a.size, (255, 255, 255, 255)); out.putalpha(a); out.alpha_composite(tmp, (o, o))
        return out

    def line(self, parts, size, font=FONT_BLACK, stroke=0.09, shadow=True):
        """parts: [(text, color), ...] drawn on one baseline."""
        f = self.font(font, size)
        sw = max(2, round(size * stroke)) if stroke else 0
        asc, desc = f.getmetrics()
        items, x = [], 0.0
        for text, color in parts:
            for emo, r in split_runs(text):
                if emo:
                    im = self.emoji(r, int(size * 0.92))
                    if im is None: continue  # never ship empty boxes
                    items.append((x, None, im)); x += im.width + size * 0.04
                else:
                    items.append((x, rgb(color), r)); x += f.getlength(r)
        pad = sw + max(4, size // 8)
        W, H = int(math.ceil(x)) + 2 * pad, asc + desc + 2 * pad
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        base = pad + asc
        for x0, col, p in items:
            if col is None:
                img.alpha_composite(p, (int(pad + x0), max(0, int(base - p.height + size * 0.12))))
            else:
                d.text((pad + x0, base), p, font=f, fill=col, stroke_width=sw, stroke_fill=(0, 0, 0), anchor="ls")
        if shadow:
            off = max(2, round(size * 0.06))
            sh = Image.new("RGBA", img.size, (0, 0, 0, 255))
            sh.putalpha(img.getchannel("A").point(lambda v: int(v * 0.55)))
            sh = sh.filter(ImageFilter.GaussianBlur(max(1, off * 0.8)))
            out = Image.new("RGBA", (W, H + off), (0, 0, 0, 0)); out.alpha_composite(sh, (0, off)); out.alpha_composite(img)
            img = out
        bb = img.getbbox()
        return img.crop(bb) if bb else img

    def stack(self, imgs, gap, align="center"):
        W = max(i.width for i in imgs); H = sum(i.height for i in imgs) + gap * (len(imgs) - 1)
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0)); y = 0
        for i in imgs:
            x = {"center": (W - i.width) // 2, "left": 0, "right": W - i.width}[align]
            out.alpha_composite(i, (x, y)); y += i.height + gap
        return out

    def pill(self, text, size, bg, fg="white", font=FONT_XBOLD):
        t = self.line([(text, fg)], size, font, stroke=0, shadow=False)
        px_, py_ = int(size * 0.55), int(size * 0.32)
        out = Image.new("RGBA", (t.width + 2 * px_, t.height + 2 * py_), (0, 0, 0, 0))
        ImageDraw.Draw(out).rounded_rectangle([0, 0, out.width - 1, out.height - 1], radius=out.height // 2, fill=rgb(bg))
        out.alpha_composite(t, (px_, py_))
        return out

    def circle_logo(self, path, d, ring=0, ring_color=(255, 255, 255)):
        src = Image.open(os.path.join(ROOT, path)).convert("RGBA")
        s = min(src.size); src = src.crop(((src.width - s) // 2, (src.height - s) // 2, (src.width + s) // 2, (src.height + s) // 2))
        inner = d - 2 * ring
        src = src.resize((inner * 4, inner * 4), Image.LANCZOS)
        m = Image.new("L", src.size, 0); ImageDraw.Draw(m).ellipse([0, 0, src.width - 1, src.height - 1], fill=255)
        src.putalpha(m); src = src.resize((inner, inner), Image.LANCZOS)
        out = Image.new("RGBA", (d * 4, d * 4), (0, 0, 0, 0))
        if ring: ImageDraw.Draw(out).ellipse([0, 0, d * 4 - 1, d * 4 - 1], fill=ring_color + (255,))
        out = out.resize((d, d), Image.LANCZOS); out.alpha_composite(src, (ring, ring))
        return out


def pop_scale(p):
    return 0.5 + 0.5 * p + 0.22 * math.sin(math.pi * p)


def comp(canvas, img, x, y):
    """alpha_composite that clips at the canvas edges (pop overshoot can poke outside)."""
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(canvas.width, x + img.width), min(canvas.height, y + img.height)
    if x1 <= x0 or y1 <= y0: return
    canvas.alpha_composite(img.crop((x0 - x, y0 - y, x1 - x, y1 - y)), (x0, y0))


def build(P, plan_path, args):
    base = os.path.dirname(plan_path)
    src = os.path.abspath(os.path.join(base, P["source"]))
    out = os.path.abspath(args.out or os.path.join(base, P.get("output", "reel_16x9.mp4")))
    res = args.res or P.get("resolution", "1080")
    S = 2 if res == "4k" else 1
    OW, OH = 1920 * S, 1080 * S
    def px(v): return int(round(v * S))

    work = os.path.join(ROOT, "work")
    for d in ("l_segs", "l_ovl"): os.makedirs(f"{work}/{d}", exist_ok=True)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    SW, SH = probe(src)
    brand = P["brand"]

    # ---------- timeline (in whole frames so every clip lines up exactly) ----------
    pieces, ids, t_fr = [], {}, 0
    for s in P["segments"]:
        a, b = s["from"], s["to"]
        speeds = s.get("ramp") or [s.get("speed", 1.0)] * 2
        n = len(speeds) - 1
        seg_start = t_fr
        for k in range(n):
            pa, pb = a + (b - a) * k / n, a + (b - a) * (k + 1) / n
            v0, v1 = speeds[k], speeds[k + 1]
            D = pb - pa
            dur = D / v0 if abs(v1 - v0) < 1e-6 else D / (v1 - v0) * math.log(v1 / v0)
            nf = max(1, int(round(dur * FPS)))
            pieces.append(dict(src_from=pa, D=D, v0=v0, v1=v1, nf=nf, start=t_fr, crop=s.get("crop", "full")))
            t_fr += nf
        if "id" in s: ids[s["id"]] = (seg_start / FPS, t_fr / FPS)
        s["_start"], s["_end"] = seg_start / FPS, t_fr / FPS
    VID_END = t_fr / FPS
    END = P.get("endcard_seconds", 4.5)
    TOTAL = VID_END + END
    NF = int(round(TOTAL * FPS))

    def T(v):
        if isinstance(v, (int, float)): return float(v)
        if v == "end": return VID_END
        m = re.fullmatch(r"@(\w+)(\.end)?([+-][\d.]+)?", v)
        if not m: raise ValueError(f"bad time {v!r}")
        a, b = ids[m.group(1)]
        return (b if m.group(2) else a) + float(m.group(3) or 0)

    def src2reel(t):  # only constant-speed segments carry speech
        for s in P["segments"]:
            if "ramp" not in s and s["from"] <= t < s["to"]:
                return s["_start"] + (t - s["from"]) / s.get("speed", 1.0)
        return None

    print("segments:", [(s.get("id", ""), round(s["_start"], 2)) for s in P["segments"]], f"video_end={VID_END:.2f} total={TOTAL:.2f}")
    if args.plan_only: return

    # ---------- stage 1: footage clips (full frame or 16:9 punch-in, smooth speed ramps) ----------
    lst = []
    for i, p in enumerate(pieces):
        c = P["crops"].get(p["crop"], [0, 0, 1]) if p["crop"] != "full" else [0, 0, 1]
        ch = int(c[2] * SH) // 2 * 2; cw = min(SW, int(ch * 16 / 9)) // 2 * 2
        x = min(max(0, int(c[0] * SW)), SW - cw); y = min(max(0, int(c[1] * SH)), SH - ch)
        D, v0, v1 = p["D"], p["v0"], p["v1"]
        if abs(v1 - v0) < 1e-6:
            pts = f"(PTS-STARTPTS)/{v0}"
        else:  # speed changes linearly v0 -> v1 over the source span: out_t = D/k * ln(1 + k*s/(D*v0))
            k = v1 - v0
            pts = f"'({D}/({k}))*log(1+({k})*(PTS-STARTPTS)*TB/({D}*{v0}))/TB'"
        vf = f"setpts={pts},fps={FPS},"
        if cw < SW or ch < SH: vf += f"crop={cw}:{ch}:{x}:{y},"
        vf += f"scale={OW}:{OH}:flags=lanczos,setsar=1,tpad=stop_mode=clone:stop_duration=0.5"
        cmd = ["-ss", f"{p['src_from']:.3f}", "-t", f"{D + 0.05:.3f}", "-i", src, "-an", "-vf", vf, "-frames:v", str(p["nf"]),
               "-c:v", "libx264", "-crf", "10", "-preset", "veryfast", "-pix_fmt", "yuv420p"]
        # cache by parameters so a short --only test and the full render share the 4K clips
        name = "p" + hashlib.sha1(json.dumps([cmd, os.path.getmtime(src)]).encode()).hexdigest()[:12] + ".mp4"
        if not os.path.exists(f"{work}/l_segs/{name}"):
            run(["ffmpeg", "-v", "error", "-y", *cmd, f"work/l_segs/{name}.part.mp4"])
            os.replace(f"{work}/l_segs/{name}.part.mp4", f"{work}/l_segs/{name}")
        lst.append(f"file '{name}'")
    open(f"{work}/l_segs/list.txt", "w").write("\n".join(lst))
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "work/l_segs/list.txt", "-c", "copy", "work/l_panel.mp4"])

    # ---------- speech (real customer audio) ----------
    speech = P.get("speech")
    SP_AT = SP_END = 0
    if speech:
        fs, parts, L = [], [], 0.0
        for j, (a, b) in enumerate(speech["ranges"]):
            fs.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d=0.04,afade=t=out:st={b - a - 0.06}:d=0.06[p{j}]")
            parts.append(f"[p{j}]"); L += b - a
        fs.append("".join(parts) + f"concat=n={len(parts)}:v=0:a=1,highpass=f=90,lowpass=f=12000,afftdn=nr=10,"
                  "acompressor=threshold=-24dB:ratio=3:attack=5:release=120,loudnorm=I=-16:TP=-2:LRA=8[sp]")
        run(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex", ";".join(fs), "-map", "[sp]",
             "-ar", "48000", "-ac", "2", "work/l_speech.wav"])
        SP_AT = T(speech["at"]); SP_END = SP_AT + L

    # ---------- music (faster variant, beat grid anchored on the drop) ----------
    M = P["music"]
    bpm = M.get("bpm", 128); BEAT = 60 / bpm
    anchor = T(M["anchor"]) if "anchor" in M else 0.0
    sections = [[T(a), T(b), k] for a, b, k in M["sections"]] + [[VID_END, TOTAL, "out"]]
    run([sys.executable, "tools/music.py", "work/l_music.wav", f"{TOTAL:.3f}", json.dumps(sections), str(bpm), f"{anchor:.4f}"])

    # ---------- overlay graphics (Pillow) ----------
    G = Gfx(S)
    els = []  # dict(img, x, y, f0, f1, pop)

    def place(img, pos, align="center", safe=True):
        cx, cy = pos[0] * OW, pos[1] * OH
        mx, my = SAFE * OW, SAFE * OH
        if safe and (img.width > OW - 2 * mx or img.height > OH - 2 * my):
            k = min((OW - 2 * mx) / img.width, (OH - 2 * my) / img.height)
            img = img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)
        x = {"center": cx - img.width / 2, "left": cx, "right": cx - img.width}[align]
        y = cy - img.height / 2
        if safe:
            x = min(max(x, mx), OW - mx - img.width); y = min(max(y, my), OH - my - img.height)
        return img, int(x), int(y)

    def add(img, pos, a, b, pop=True, align="center", safe=True):
        img, x, y = place(img, pos, align, safe)
        f0, f1 = int(round(a * FPS)), int(round(b * FPS))
        if f1 > f0: els.append(dict(img=img, x=x, y=y, f0=f0, f1=f1, pop=pop))

    def text_img(it):
        size = px(it.get("size", 80))
        font = FONT_XBOLD if it.get("font") == "xbold" else FONT_BLACK
        lines = it["text"].split("\n")
        cols = it.get("color", "white")
        cols = cols if isinstance(cols, list) else [cols] * len(lines)
        if it.get("style") == "pill":
            img = G.pill(it["text"], size, it.get("bg", "red"), cols[0], font)
        else:
            img = G.stack([G.line([(l, cols[i % len(cols)])], size, font) for i, l in enumerate(lines)],
                          gap=-int(size * 0.12), align=it.get("align", "center"))
        if it.get("rotate"): img = img.rotate(it["rotate"], resample=Image.BICUBIC, expand=True)
        return img

    lg = P.get("logo")
    if lg:
        d = px(lg.get("size", 110))
        add(G.circle_logo("assets/logo.jpg", d, ring=max(2, d // 28)), lg.get("pos", [0.93, 0.12]),
            T(lg.get("from", 0)), T(lg.get("to", "end")))

    for it in P.get("texts", []):
        add(text_img(it), it["pos"], T(it["t"][0]), T(it["t"][1]), pop=it.get("pop", True), align=it.get("align", "center"))

    cap = P.get("captions")
    if cap:  # word-by-word: whole chunk white with black outline, the current word yellow
        words = []  # [reel start, reel end, word]; a trailing "/" or punctuation ends a chunk
        for s_, e_, w in cap["words"]:
            a, b = src2reel(s_), src2reel(max(s_, e_ - 0.01))
            if a is None or b is None: continue
            words.append([a, b + 0.01, w.strip()])
        chunks, cur = [], []
        for w in words:
            if cur and (len(cur) >= cap.get("max_words", 4) or w[0] - cur[-1][1] > 0.45 or cur[-1][2][-1:] in "/.,?!"):
                chunks.append(cur); cur = []
            cur.append(w)
        if cur: chunks.append(cur)
        for ch in chunks:
            for w in ch: w[2] = w[2].strip(" /.,?!").upper()
        size = px(cap.get("size", 66)); hl = cap.get("highlight", "#FFD54F")
        for ci, ch in enumerate(chunks):
            nxt = chunks[ci + 1][0][0] if ci + 1 < len(chunks) else 1e9
            hold = min(ch[-1][1] + 0.35, nxt)
            for wi, w in enumerate(ch):
                parts = []
                for wj, w2 in enumerate(ch):
                    parts.append((w2[2] + (" " if wj < len(ch) - 1 else ""), hl if wj == wi else "white"))
                b = ch[wi + 1][0] if wi + 1 < len(ch) else hold
                add(G.line(parts, size, FONT_BLACK, stroke=0.11), cap.get("pos", [0.5, 0.86]), w[0], b, pop=(wi == 0))

    # end card: red background, round logo left, brand column right, items pop in one by one
    E = VID_END
    bg = Image.new("RGBA", (OW, OH), rgb("red") + (255,))
    dr = ImageDraw.Draw(bg)
    dr.rectangle([0, OH - px(22), OW, OH], fill=rgb("yellow") + (255,))
    dr.polygon([(OW * 0.36, 0), (OW * 0.44, 0), (OW * 0.30, OH), (OW * 0.22, OH)], fill=(190, 38, 38, 255))
    add(bg, [0.5, 0.5], E, TOTAL, pop=False, safe=False)
    add(G.circle_logo("assets/logo.jpg", px(560), ring=px(14)), [0.25, 0.5], E + 0.05, TOTAL)
    col, k = 0.68, 0
    rows = []
    if brand.get("name"): rows.append((G.line([(brand["name"], "white")], px(88)), 0.20))
    rows.append((G.line([(f"Since {brand['since']}", "yellow")], px(44), FONT_XBOLD, stroke=0.06), 0.29))
    if brand.get("product_line"): rows.append((G.line([(brand["product_line"], "white")], px(52)), 0.38))
    rows += [(G.line([(brand["street"], "white")], px(46), FONT_XBOLD, stroke=0.06), 0.47),
             (G.line([(brand["city"], "yellow")], px(96)), 0.56),
             (G.pill("Call / WhatsApp", px(42), "black"), 0.67)]
    for j, ph in enumerate(brand["phones"]):
        rows.append((G.line([(ph, "white")], px(78)), 0.77 + 0.095 * j))
    for img, yy in rows:
        if img.width > px(900): img = img.resize((px(900), int(img.height * px(900) / img.width)), Image.LANCZOS)
        add(img, [col, yy], E + 0.15 + 0.1 * k, TOTAL); k += 1

    # composite one PNG per distinct overlay state, list them in an ffconcat with durations
    def sig(f):
        return tuple((i, min(f - e["f0"], POPF) if e["pop"] else POPF)
                     for i, e in enumerate(els) if e["f0"] <= f < e["f1"])
    runs_ = []
    for f in range(NF):
        s = sig(f)
        if runs_ and runs_[-1][0] == s: runs_[-1][1] += 1
        else: runs_.append([s, 1])
    names, lines = {}, ["ffconcat version 1.0"]
    for s, n in runs_:
        if s not in names:
            canvas = Image.new("RGBA", (OW, OH), (0, 0, 0, 0))
            for i, kf in s:
                e = els[i]; img = e["img"]
                if kf < POPF:
                    sc = pop_scale((kf + 1) / POPF)
                    img = img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.BILINEAR)
                comp(canvas, img, e["x"] + (e["img"].width - img.width) // 2, e["y"] + (e["img"].height - img.height) // 2)
            names[s] = f"o{len(names):04d}.png"
            canvas.save(f"{work}/l_ovl/{names[s]}", compress_level=1)
        lines += [f"file '{names[s]}'", f"duration {n / FPS:.6f}"]
    lines.append(f"file '{names[runs_[-1][0]]}'")  # concat demuxer needs the last file repeated
    open(f"{work}/l_ovl/list.ffconcat", "w").write("\n".join(lines) + "\n")
    print(f"overlay: {len(names)} states over {NF} frames")

    # ---------- stage 2: compose ----------
    full = "+".join(f"between(it,{a:.3f},{b:.3f})" for a, b, k in sections if k == "full") or "0"
    off = anchor % BEAT
    terms = [f"0.035*exp(-mod(it+{BEAT - off:.4f},{BEAT:.4f})*10)*({full})"]  # beat pulse, grid shares the music's
    fxc = P.get("fx", {})
    for a in fxc.get("punches", []):
        a = T(a); terms.append(f"0.13*exp(-(it-{a:.3f})*5)*between(it,{a:.3f},{a + 1.2:.3f})")
    for a, b in fxc.get("push", []):
        a, b = T(a), T(b); terms.append(f"0.16*max(0,min(1,(it-{a:.3f})/{b - a:.3f}))*between(it,{a:.3f},{b:.3f})")
    shake = "+".join(f"{px(16)}*sin(it*95)*exp(-(it-{T(a):.3f})*8)*between(it,{T(a):.3f},{T(a) + 0.5:.3f})"
                     for a in fxc.get("shake", [])) or "0"
    v = [f"[0:v]setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={END + 0.5},"
         f"zoompan=z='1+{'+'.join(terms)}':x='iw/2-(iw/zoom/2)+{shake}':y='ih/2-(ih/zoom/2)':d=1:s={OW}x{OH}:fps={FPS},"
         "eq=contrast=1.05:saturation=1.12,unsharp=5:5:0.4"]
    gl = [T(a) for a in fxc.get("glitch", [])]
    if gl:
        en = "+".join(f"between(t,{a - 0.001:.3f},{a + 0.13:.3f})" for a in gl)
        v.append(f"rgbashift=rh={-px(14)}:bh={px(14)}:gv={px(4)}:edge=smear:enable='{en}'")
    for a in fxc.get("flashes", []):
        a = T(a); v.append(f"drawbox=x=0:y=0:w={OW}:h={OH}:color=white@0.8:t=fill:enable='between(t,{a - 0.001:.3f},{a + 0.066:.3f})'")
    f = [",".join(v) + "[base]", f"[1:v]fps={FPS},format=rgba[ovl]",
         f"[base][ovl]overlay=0:0:eof_action=repeat,format=yuv420p[vout]"]

    inputs = ["-i", "work/l_panel.mp4", "-f", "concat", "-safe", "0", "-i", "work/l_ovl/list.ffconcat", "-i", "work/l_music.wav"]
    duck = f"if(between(t,{SP_AT:.3f},{SP_END:.3f}),0.16,0.85)" if speech else "0.85"
    f.append(f"[2:a]aresample=48000,volume='{duck}':eval=frame[mus]")
    mix, nxt = ["[mus]"], 3
    if speech:
        inputs += ["-i", "work/l_speech.wav"]
        f.append(f"[{nxt}:a]aresample=48000,adelay={int(SP_AT * 1000)}:all=1[sp]"); mix.append("[sp]"); nxt += 1
    for j, (kind, at, *g) in enumerate(P.get("sfx", [])):
        inputs += ["-i", SFX[kind]]
        f.append(f"[{nxt}:a]aresample=48000,volume={g[0] if g else 0.5},adelay={int(T(at) * 1000)}:all=1[x{j}]")
        mix.append(f"[x{j}]"); nxt += 1
    f.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{TOTAL},"
             "loudnorm=I=-15:TP=-2:LRA=9,alimiter=limit=0.79:level=disabled[aout]")

    span = ["-t", f"{TOTAL:.3f}"]
    if args.only:
        a, b = (float(x) for x in args.only.split(":")); span = ["-ss", f"{a}", "-to", f"{b}"]
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(f), "-map", "[vout]", "-map", "[aout]",
         *span, "-r", str(FPS),
         "-c:v", "libx264", "-preset", "medium", "-crf", "18" if S == 2 else "17",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", out])
    print("wrote", out)
