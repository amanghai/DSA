"""Dhanteras 2026 Instagram post for Nazakat Telecom x A&H Teleservices.

Usage:
    python3 make_post.py                       # no showroom photo, text badge for A&H
    python3 make_post.py --photo showroom.jpg --ah-logo ah_logo.png

Renders 1080x1350 (Instagram 4:5 portrait) PNG + JPG via Playwright/Chromium.
Fonts come from @fontsource npm packages (see README).
"""
import argparse
import base64
import mimetypes
import pathlib

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
CHROMIUM = "/opt/pw-browsers/chromium"


def data_uri(path: pathlib.Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def font_face(fonts_dir: pathlib.Path, family: str, pkg: str, files: list[str]) -> str:
    rules = []
    for f in files:
        p = fonts_dir / "node_modules/@fontsource" / pkg / "files" / f
        rules.append(
            f"@font-face{{font-family:'{family}';src:url('{data_uri(p)}') format('woff2');"
            f"font-weight:{f.split('-')[-2]};}}"
        )
    return "\n".join(rules)


def diya_svg(scale: float = 1.0) -> str:
    w, h = 150 * scale, 120 * scale
    return f"""
<svg class="diya" width="{w}" height="{h}" viewBox="0 0 150 120">
  <defs>
    <radialGradient id="glow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#fff6c9" stop-opacity=".95"/>
      <stop offset="35%" stop-color="#ffc93c" stop-opacity=".55"/>
      <stop offset="100%" stop-color="#ff8a00" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="flame" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#fffbe6"/>
      <stop offset="45%" stop-color="#ffd23f"/>
      <stop offset="100%" stop-color="#ff6a00"/>
    </linearGradient>
    <linearGradient id="clay" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#e0742a"/>
      <stop offset="100%" stop-color="#7a2a0c"/>
    </linearGradient>
    <linearGradient id="rim" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#b8860b"/>
      <stop offset="50%" stop-color="#ffe38a"/>
      <stop offset="100%" stop-color="#b8860b"/>
    </linearGradient>
  </defs>
  <circle cx="75" cy="38" r="40" fill="url(#glow)"/>
  <path d="M75 8 C86 26 88 40 75 54 C62 40 64 26 75 8Z" fill="url(#flame)"/>
  <path d="M10 62 Q75 66 140 62 Q130 108 75 110 Q20 108 10 62Z" fill="url(#clay)"/>
  <path d="M10 62 Q75 72 140 62" stroke="url(#rim)" stroke-width="6" fill="none" stroke-linecap="round"/>
  <path d="M30 84 Q75 94 120 84" stroke="#ffd36b" stroke-width="2.5" fill="none" stroke-dasharray="2 7" stroke-linecap="round"/>
</svg>"""


def coin_stack(n: int, w: int = 110) -> str:
    coins = "".join(
        f'<div class="coin" style="bottom:{i*13}px"></div>' for i in range(n)
    )
    return f'<div class="stack" style="width:{w}px;height:{n*13+40}px">{coins}</div>'


def mandala_svg() -> str:
    petals = []
    for ring, (r, count, size) in enumerate([(150, 16, 46), (260, 24, 56), (380, 32, 62), (500, 40, 66)]):
        for i in range(count):
            a = 360 / count * i + (ring % 2) * (180 / count)
            petals.append(
                f'<ellipse cx="0" cy="-{r}" rx="{size*0.32:.1f}" ry="{size}" '
                f'transform="rotate({a:.2f})" />'
            )
    circles = "".join(f'<circle r="{r}" />' for r in (90, 200, 320, 445, 570))
    return f"""
<svg class="mandala" viewBox="-620 -620 1240 1240">
  <g fill="none" stroke="#f5c451" stroke-width="2">{circles}{''.join(petals)}</g>
</svg>"""


def bunting() -> str:
    flowers = []
    for i in range(28):
        x = 20 + i * 39
        y = 22 + 18 * (1 - ((i % 14 - 6.5) / 6.5) ** 2)
        color = "#ff9f1c" if i % 2 else "#ffd23f"
        flowers.append(
            f'<circle cx="{x}" cy="{y:.1f}" r="17" fill="{color}"/>'
            f'<circle cx="{x}" cy="{y:.1f}" r="7" fill="#d9480f" opacity=".55"/>'
        )
    leaves = "".join(
        f'<path d="M{20 + i*78 + 19} 30 q10 34 0 54 q-10 -20 0 -54z" fill="#2b8a3e"/>'
        for i in range(14)
    )
    return f"""
<svg class="bunting" viewBox="0 0 1080 110" width="1080" height="110">
  <path d="M0 18 Q540 70 1080 18" stroke="#c99a2e" stroke-width="3" fill="none"/>
  {leaves}
  {''.join(flowers)}
</svg>"""


def build_html(photo: str | None, ah_logo: str | None, nazakat_logo: str, fonts_css: str) -> str:
    ah_block = (
        f'<img class="logo" src="{ah_logo}" alt="A&H Teleservices">'
        if ah_logo
        else """<div class="logo ah-badge">
                 <div class="ah-mono">A<span>&amp;</span>H</div>
                 <div class="ah-name">TELESERVICES</div>
               </div>"""
    )

    if photo:
        centre = f"""
        <div class="arch-wrap">
          <div class="arch"><img src="{photo}" alt="Nazakat Telecom showroom"></div>
          <div class="arch-cap">Hamare showroom mein aapka swagat hai</div>
        </div>
        <p class="blessing small">Maa Lakshmi aur Bhagwan Dhanvantari aapke ghar laayein<br>
           <b>sukh, samriddhi aur arogya</b></p>"""
    else:
        centre = f"""
        <div class="centre-art">
          {coin_stack(5)}
          <div class="kalash-glow"></div>
          {coin_stack(7, 120)}
          {coin_stack(4)}
        </div>
        <p class="blessing">Maa Lakshmi aur Bhagwan Dhanvantari<br>aapke ghar laayein
           <b>sukh, samriddhi<br>aur arogya</b></p>"""

    diyas = "".join(diya_svg(1.0 if i in (0, 4) else 1.15 if i in (1, 3) else 1.3) for i in range(5))

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
{fonts_css}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1350px;overflow:hidden;background:#1d0208}}
.post{{position:relative;width:1080px;height:1350px;overflow:hidden;
  background:radial-gradient(ellipse 85% 60% at 50% 42%,#7d1026 0%,#4a0716 45%,#1d0208 100%);
  font-family:'Montserrat',sans-serif;color:#fff}}
.post::after{{content:"";position:absolute;inset:0;pointer-events:none;
  box-shadow:inset 0 0 0 14px #1d0208, inset 0 0 0 17px #d4a537, inset 0 0 0 24px #1d0208, inset 0 0 0 25px #8a6a1f}}
.mandala{{position:absolute;width:1240px;height:1240px;left:-80px;top:-60px;opacity:.10}}
.bokeh{{position:absolute;border-radius:50%;filter:blur(2px);
  background:radial-gradient(circle,#ffd86b 0%,rgba(255,190,60,.25) 45%,transparent 70%)}}
.bunting{{position:absolute;top:22px;left:0}}
.logos{{position:absolute;top:104px;left:0;right:0;display:flex;justify-content:center;align-items:center;gap:34px}}
.logo{{width:188px;height:188px;border-radius:50%;object-fit:cover;background:#f4f1ec;
  box-shadow:0 0 0 5px #d4a537,0 0 0 9px #5a0b1a,0 0 0 11px #8a6a1f,0 10px 30px rgba(0,0,0,.5)}}
.plus{{font-family:'Cinzel Decorative',serif;font-size:58px;color:#f5c451;text-shadow:0 0 18px rgba(255,200,80,.6)}}
.ah-badge{{display:flex;flex-direction:column;align-items:center;justify-content:center;
  background:radial-gradient(circle at 35% 30%,#fff8e7,#f1e3c2)}}
.ah-mono{{font-family:'Cinzel Decorative',serif;font-weight:900;font-size:64px;line-height:1;color:#7d1026;letter-spacing:-1px}}
.ah-mono span{{color:#b8860b;font-size:46px;margin:0 2px}}
.ah-name{{font-family:'Cinzel',serif;font-weight:700;font-size:16px;letter-spacing:2.5px;color:#4a0716;margin-top:6px}}
.title{{position:absolute;top:322px;left:0;right:0;text-align:center}}
.hindi{{font-family:'Yatra One',serif;font-size:150px;line-height:1.05;
  background:linear-gradient(180deg,#fff3c4 0%,#ffd34d 38%,#e0a21b 62%,#fff0b0 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;
  filter:drop-shadow(0 4px 0 #6b1408) drop-shadow(0 0 22px rgba(255,190,60,.45))}}
.eng{{font-family:'Great Vibes',cursive;font-size:96px;color:#fff;margin-top:-18px;
  text-shadow:0 0 18px rgba(255,210,120,.7),0 3px 0 #6b1408}}
.date{{font-family:'Cinzel',serif;font-weight:700;font-size:24px;letter-spacing:6px;color:#f5c451;margin-top:6px}}
.date:before,.date:after{{content:"";display:inline-block;width:70px;height:2px;margin:0 18px 7px;
  background:linear-gradient(90deg,transparent,#f5c451)}}
.date:after{{transform:scaleX(-1)}}
.centre{{position:absolute;top:668px;left:0;right:0;display:flex;flex-direction:column;align-items:center}}
.centre-art{{display:flex;align-items:flex-end;gap:26px;height:170px;position:relative}}
.kalash-glow{{position:absolute;left:50%;top:40%;width:420px;height:200px;transform:translate(-50%,-50%);
  background:radial-gradient(ellipse,rgba(255,206,90,.45),transparent 70%);z-index:0}}
.stack{{position:relative;z-index:1}}
.coin{{position:absolute;left:0;width:100%;height:34px;border-radius:50%;
  background:linear-gradient(180deg,#fff0a8 0%,#f2c230 40%,#b8860b 100%);
  box-shadow:0 5px 0 #8a6408,0 7px 10px rgba(0,0,0,.45)}}
.coin:last-child::after{{content:"₹";position:absolute;left:50%;top:50%;transform:translate(-50%,-55%) scaleY(.6);
  font:900 34px 'Montserrat';color:#a8740a}}
.blessing{{margin-top:30px;text-align:center;font-family:'Cinzel',serif;font-weight:400;font-size:33px;line-height:1.45;color:#ffe9b5}}
.blessing b{{font-weight:700;color:#ffd34d}}
.blessing.small{{font-size:26px;margin-top:18px}}
.arch-wrap{{display:flex;flex-direction:column;align-items:center;margin-top:-20px}}
.arch{{width:520px;height:330px;border-radius:260px 260px 18px 18px;overflow:hidden;
  box-shadow:0 0 0 6px #d4a537,0 0 0 11px #4a0716,0 0 0 13px #8a6a1f,0 0 50px rgba(255,190,60,.45)}}
.arch img{{width:100%;height:100%;object-fit:cover}}
.arch-cap{{margin-top:-22px;z-index:2;background:linear-gradient(90deg,#b8860b,#ffd34d,#b8860b);color:#4a0716;
  font:700 19px 'Montserrat';letter-spacing:1px;padding:9px 24px;border-radius:30px}}
.diyas{{position:absolute;bottom:162px;left:0;right:0;display:flex;justify-content:center;align-items:flex-end;gap:38px}}
.footer{{position:absolute;bottom:38px;left:40px;right:40px;height:110px;border-radius:16px;
  background:linear-gradient(180deg,rgba(255,215,110,.16),rgba(255,215,110,.06));
  border:1.5px solid rgba(245,196,81,.55);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:6px}}
.footer .brand{{font-family:'Cinzel',serif;font-weight:700;font-size:27px;letter-spacing:3px;color:#ffd34d}}
.footer .brand span{{color:#ffe9b5;font-weight:400}}
.footer .addr{{font-size:19px;letter-spacing:.6px;color:#ffe9b5;font-weight:500}}
/* layout when a showroom photo is present */
.with-photo .logos{{top:96px}}
.with-photo .logo{{width:200px;height:200px}}
.with-photo .title{{top:316px}}
.with-photo .hindi{{font-size:124px}}
.with-photo .eng{{font-size:80px;margin-top:-14px}}
.with-photo .date{{font-size:21px;margin-top:2px}}
.with-photo .centre{{top:600px}}
.with-photo .arch-wrap{{margin-top:0}}
.with-photo .arch{{width:600px;height:340px;border-radius:300px 300px 16px 16px}}
.with-photo .blessing.small{{font-size:23px;margin-top:16px;line-height:1.35}}
.with-photo .diyas{{bottom:158px;gap:44px}}
.with-photo .diyas svg{{transform:scale(.78);transform-origin:bottom center;margin:0 -16px}}
</style></head><body><div class="post{' with-photo' if photo else ''}">
  {mandala_svg()}
  <div class="bokeh" style="width:90px;height:90px;left:70px;top:420px;opacity:.5"></div>
  <div class="bokeh" style="width:60px;height:60px;right:90px;top:520px;opacity:.55"></div>
  <div class="bokeh" style="width:40px;height:40px;left:160px;top:640px;opacity:.6"></div>
  <div class="bokeh" style="width:110px;height:110px;right:40px;top:300px;opacity:.35"></div>
  <div class="bokeh" style="width:50px;height:50px;left:60px;top:880px;opacity:.45"></div>
  <div class="bokeh" style="width:70px;height:70px;right:120px;top:900px;opacity:.4"></div>
  {bunting()}
  <div class="logos">
    <img class="logo" src="{nazakat_logo}" alt="Nazakat Telecom">
    <div class="plus">&amp;</div>
    {ah_block}
  </div>
  <div class="title">
    <div class="hindi">शुभ धनतेरस</div>
    <div class="eng">Happy Dhanteras</div>
    <div class="date">6 NOV 2026</div>
  </div>
  <div class="centre">{centre}</div>
  <div class="diyas">{diyas}</div>
  <div class="footer">
    <div class="brand">NAZAKAT TELECOM <span>·</span> A&amp;H TELESERVICES</div>
    <div class="addr">Defence Road, Mamun Cantt, Pathankot &nbsp;•&nbsp; Since 1992</div>
  </div>
</div></body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo", type=pathlib.Path)
    ap.add_argument("--ah-logo", type=pathlib.Path)
    ap.add_argument("--logo", type=pathlib.Path, default=HERE / "assets/nazakat_logo.jpg")
    ap.add_argument("--fonts", type=pathlib.Path, required=True, help="dir containing node_modules/@fontsource")
    ap.add_argument("--out", type=pathlib.Path, default=HERE / "output/dhanteras_2026_post")
    args = ap.parse_args()

    fonts_css = "\n".join([
        font_face(args.fonts, "Yatra One", "yatra-one",
                  ["yatra-one-devanagari-400-normal.woff2", "yatra-one-latin-400-normal.woff2"]),
        font_face(args.fonts, "Great Vibes", "great-vibes", ["great-vibes-latin-400-normal.woff2"]),
        font_face(args.fonts, "Cinzel", "cinzel",
                  ["cinzel-latin-400-normal.woff2", "cinzel-latin-700-normal.woff2"]),
        font_face(args.fonts, "Cinzel Decorative", "cinzel-decorative",
                  ["cinzel-decorative-latin-900-normal.woff2"]),
        font_face(args.fonts, "Montserrat", "montserrat",
                  ["montserrat-latin-500-normal.woff2", "montserrat-latin-700-normal.woff2",
                   "montserrat-latin-900-normal.woff2"]),
    ])

    html = build_html(
        data_uri(args.photo) if args.photo else None,
        data_uri(args.ah_logo) if args.ah_logo else None,
        data_uri(args.logo),
        fonts_css,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM if pathlib.Path(CHROMIUM).exists() else None)
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
        page.set_content(html)
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(400)
        png = args.out.with_suffix(".png")
        page.screenshot(path=str(png))
        browser.close()

    from PIL import Image
    img = Image.open(png).convert("RGB")
    img.resize((1080, 1350), Image.LANCZOS).save(args.out.with_suffix(".jpg"), quality=95)
    print("wrote", png, args.out.with_suffix(".jpg"))


if __name__ == "__main__":
    main()
