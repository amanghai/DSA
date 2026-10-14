#!/usr/bin/env python3
"""Text + colour-emoji sticker PNGs for the 16:9 reel (ffmpeg drawtext cannot draw colour emoji).
Text uses Montserrat; emoji use Windows' Segoe UI Emoji (seguiemj.ttf). If that font is missing
the emoji are dropped (never drawn as tofu boxes)."""
import os
from PIL import Image, ImageDraw, ImageFont

EMOJI_FONTS = [r"C:\Windows\Fonts\seguiemj.ttf", "/System/Library/Fonts/Apple Color Emoji.ttc",
               "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"]
STYLES = {  # background, text colour, outline colour (None = no outline)
    "white": ((255, 255, 255, 255), (17, 17, 17, 255), None),
    "yellow": ((255, 213, 79, 255), (17, 17, 17, 255), None),
    "red": ((211, 47, 47, 255), (255, 255, 255, 255), None),
    "outline": (None, (255, 255, 255, 255), (0, 0, 0, 255)),
}


def is_emoji(ch):
    o = ord(ch)
    return o >= 0x1F000 or 0x2600 <= o <= 0x27BF or 0x2B00 <= o <= 0x2BFF or o in (0xFE0F, 0x200D, 0x20E3)


def runs(text):
    out = []
    for ch in text:
        e = is_emoji(ch)
        if out and out[-1][0] == e: out[-1][1] += ch
        else: out.append([e, ch])
    return out


def emoji_font(size):
    for p in EMOJI_FONTS:
        if os.path.exists(p):
            try:
                # Segoe UI Emoji is a COLR font; 109 is the size bitmap fonts like Noto need
                return ImageFont.truetype(p, size if p.endswith("seguiemj.ttf") else 109)
            except OSError:
                continue
    return None


def render(text, font_path, size, style="white", out=None, rotate=0.0, pad=None, maxw=None):
    """Render one line of text (may contain emoji) to an RGBA PNG; returns (path, w, h)."""
    bg, fg, ol = STYLES[style]
    while True:
        font = ImageFont.truetype(font_path, size)
        efont = emoji_font(int(size * 1.2))
        parts = [(e, s) for e, s in runs(text) if not (e and efont is None)]
        stroke = max(2, size // 9) if ol else 0
        widths = []
        for e, s in parts:
            s2 = s.replace("\uFE0F", "") if e else s
            widths.append(int((efont if e else font).getlength(s2)) + (size // 10 if e else 0))
        tw = sum(widths)
        if not maxw or tw + 2 * stroke <= maxw or size <= 20: break
        size = int(size * 0.94)
    asc, desc = font.getmetrics()
    th = asc + desc
    px_, py_ = pad if pad else ((int(size * 0.55), int(size * 0.28)) if bg else (stroke + 4, stroke + 4))
    W, H = tw + 2 * px_ + 2 * stroke, th + 2 * py_ + 2 * stroke
    im = Image.new("RGBA", (W + 24, H + 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if bg:
        d.rounded_rectangle([14, 16, 14 + W, 16 + H], radius=int(size * 0.35), fill=(0, 0, 0, 110))  # shadow
        d.rounded_rectangle([6, 6, 6 + W, 6 + H], radius=int(size * 0.35), fill=bg)
    x = 6 + px_ + stroke
    y = 6 + py_ + stroke
    for (e, s), w in zip(parts, widths):
        if e:
            s2 = s.replace("\uFE0F", "")
            eh = efont.getbbox(s2)
            ey = y + (th - (eh[3] - eh[1])) // 2 - eh[1]
            d.text((x + size // 20, ey), s2, font=efont, embedded_color=True)
        else:
            d.text((x, y), s, font=font, fill=fg, stroke_width=stroke, stroke_fill=ol)
        x += w
    if rotate:
        im = im.rotate(rotate, resample=Image.BICUBIC, expand=True)
    im = im.crop(im.getbbox())
    if out:
        im.save(out)
    return out, im.width, im.height


if __name__ == "__main__":
    import sys
    p, w, h = render(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else "white", sys.argv[5] if len(sys.argv) > 5 else "sticker.png")
    print(p, w, h)
