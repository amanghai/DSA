"""Two alternative Dhanteras 2026 styles (v2): 'luxury' (black & gold) and 'bright' (saffron/magenta).

python3 make_post_v2.py --fonts /tmp/fonts --style luxury|bright
"""
import argparse
import pathlib
import random

from playwright.sync_api import sync_playwright

from make_post import CHROMIUM, HERE, data_uri, diya_svg, font_face, mandala_svg


def fonts_css(fonts: pathlib.Path) -> str:
    return "\n".join([
        font_face(fonts, "Yatra One", "yatra-one",
                  ["yatra-one-devanagari-400-normal.woff2", "yatra-one-latin-400-normal.woff2"]),
        font_face(fonts, "Great Vibes", "great-vibes", ["great-vibes-latin-400-normal.woff2"]),
        font_face(fonts, "Cinzel", "cinzel", ["cinzel-latin-400-normal.woff2", "cinzel-latin-700-normal.woff2"]),
        font_face(fonts, "Cinzel Decorative", "cinzel-decorative", ["cinzel-decorative-latin-900-normal.woff2"]),
        font_face(fonts, "Montserrat", "montserrat",
                  ["montserrat-latin-500-normal.woff2", "montserrat-latin-700-normal.woff2",
                   "montserrat-latin-900-normal.woff2"]),
    ])


def sparkles(n: int, color: str, seed: int, area=(1080, 1350)) -> str:
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        x, y = rnd.randint(20, area[0] - 20), rnd.randint(20, area[1] - 20)
        s = rnd.choice([3, 4, 5, 7, 10])
        o = rnd.uniform(.35, .95)
        out.append(f'<div class="spark" style="left:{x}px;top:{y}px;width:{s}px;height:{s}px;opacity:{o:.2f};background:{color}"></div>')
    return "".join(out)


def falling_coins(seed: int) -> str:
    rnd = random.Random(seed)
    spots = [(70, 330), (960, 300), (130, 560), (930, 600), (60, 860), (990, 900), (210, 220), (850, 170)]
    out = []
    for x, y in spots:
        s = rnd.randint(46, 78)
        out.append(f'<div class="fcoin" style="left:{x}px;top:{y}px;width:{s}px;height:{s}px;'
                   f'transform:rotate({rnd.randint(-40, 40)}deg) scaleX({rnd.uniform(.45, 1):.2f})">₹</div>')
    return "".join(out)


BASE_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1080px;height:1350px;overflow:hidden}
.post{position:relative;width:1080px;height:1350px;overflow:hidden;font-family:'Montserrat',sans-serif}
.dist{position:absolute;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:26px;
  background:#fff;border-radius:60px;padding:14px 38px;white-space:nowrap}
.dist .lbl{font:900 15px Montserrat;letter-spacing:2px;line-height:1.25;text-align:right;color:#5c0a2a}
.dist .vr{width:2px;height:52px;background:#e3d3b0}
.dist img.intex{height:40px}
.dist img.ambrane{height:36px}
.biz{display:flex;flex-direction:column;align-items:center;gap:8px}
.role{font:900 14px Montserrat;letter-spacing:2.5px;padding:5px 14px;border-radius:20px}
.spark{position:absolute;border-radius:50%;box-shadow:0 0 10px 2px rgba(255,220,130,.8)}
"""


def luxury(nt: str, ah: str, photo: str, intex: str, ambrane: str) -> str:
    return f"""<style>{BASE_CSS}
.post{{background:radial-gradient(ellipse 70% 55% at 50% 30%,#3a2a08 0%,#120d03 55%,#050402 100%)}}
.rays{{position:absolute;left:50%;top:-260px;width:1800px;height:1800px;transform:translateX(-50%);opacity:.22;
  background:repeating-conic-gradient(from 0deg,rgba(255,206,90,.55) 0deg 4deg,transparent 4deg 14deg);
  -webkit-mask:radial-gradient(circle,#000 0%,transparent 55%);mask:radial-gradient(circle,#000 0%,transparent 55%)}}
.mandala{{position:absolute;width:900px;height:900px;left:90px;top:-40px;opacity:.13}}
.fcoin{{position:absolute;border-radius:50%;display:flex;align-items:center;justify-content:center;
  font:900 30px Montserrat;color:#9a6a06;background:radial-gradient(circle at 35% 30%,#fff3b0,#f0bf2c 45%,#a9760a 100%);
  box-shadow:0 0 0 3px #c99312 inset,0 8px 18px rgba(0,0,0,.6),0 0 22px rgba(255,200,60,.35)}}
.frame{{position:absolute;inset:26px;border:2px solid rgba(232,190,90,.75);border-radius:6px}}
.frame::after{{content:"";position:absolute;inset:8px;border:1px solid rgba(232,190,90,.35)}}
.logos{{position:absolute;top:60px;left:50%;transform:translateX(-50%);display:flex;align-items:center;gap:26px;
  background:#fff;border-radius:120px;padding:12px 30px 12px 30px;box-shadow:0 0 0 3px #d9a93a,0 12px 40px rgba(0,0,0,.6)}}
.logos .role{{background:#1a1204;color:#ffd666}}
.logos img{{width:124px;height:124px;border-radius:50%;object-fit:cover}}
.logos .sep{{width:2px;height:96px;background:linear-gradient(#fff,#d9a93a,#fff)}}
.happy{{position:absolute;top:276px;width:100%;text-align:center;font:400 112px 'Great Vibes';color:#fff;
  text-shadow:0 0 30px rgba(255,210,120,.65)}}
.big{{position:absolute;top:368px;width:100%;text-align:center;font:900 132px 'Cinzel Decorative';letter-spacing:4px;
  background:linear-gradient(180deg,#fff7d1 0%,#ffd666 30%,#c8901a 58%,#ffe9a3 78%,#b8820f 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;filter:drop-shadow(0 6px 14px rgba(0,0,0,.7))}}
.hindi{{position:absolute;top:536px;width:100%;text-align:center;font:400 54px 'Yatra One';color:#ffd666;letter-spacing:2px}}
.hindi span{{display:inline-block;width:90px;height:2px;margin:0 22px 16px;background:linear-gradient(90deg,transparent,#d9a93a)}}
.hindi span:last-child{{transform:scaleX(-1)}}
.polaroid{{position:absolute;top:640px;left:50%;width:640px;padding:18px 18px 64px;background:#fffdf6;
  transform:translateX(-50%) rotate(-3deg);box-shadow:0 22px 50px rgba(0,0,0,.75),0 0 0 1px #e9dfc4}}
.polaroid img{{display:block;width:100%;height:292px;object-fit:cover;filter:saturate(1.1) contrast(1.05)}}
.polaroid .cap{{position:absolute;bottom:10px;left:0;right:0;text-align:center;font:400 44px 'Great Vibes';color:#5a3b05}}
.tape{{position:absolute;top:-16px;width:130px;height:36px;background:rgba(240,214,150,.85);box-shadow:0 2px 6px rgba(0,0,0,.3)}}
.cta{{position:absolute;bottom:222px;width:100%;text-align:center;font:700 30px 'Cinzel';color:#ffe39a;letter-spacing:1px}}
.cta b{{color:#fff}}
.addr{{position:absolute;bottom:46px;left:50%;transform:translateX(-50%);white-space:nowrap;font:500 20px Montserrat;color:#1a1204;
  background:linear-gradient(90deg,#b8820f,#ffe08a,#b8820f);padding:12px 34px;border-radius:40px;letter-spacing:.5px}}
.diya-l,.diya-r{{position:absolute;bottom:250px}}
.post .dist{{bottom:118px;box-shadow:0 0 0 3px #d9a93a,0 10px 30px rgba(0,0,0,.6)}}
.diya-l{{left:62px}} .diya-r{{right:62px}}
</style>
<div class="post">
  <div class="rays"></div>{mandala_svg()}
  {sparkles(70, '#ffe7a3', 7)}{falling_coins(3)}
  <div class="frame"></div>
  <div class="logos"><div class="biz"><img src="{nt}"><div class="role">RETAIL</div></div><div class="sep"></div>
    <div class="biz"><img src="{ah}"><div class="role">DISTRIBUTION</div></div></div>
  <div class="happy">Happy</div>
  <div class="big">DHANTERAS</div>
  <div class="hindi"><span></span>शुभ धनतेरस<span></span></div>
  <div class="polaroid"><div class="tape" style="left:40px;transform:rotate(-8deg)"></div>
    <div class="tape" style="right:40px;transform:rotate(7deg)"></div>
    <img src="{photo}"><div class="cap">Nazakat Telecom, Pathankot</div></div>
  <div class="diya-l">{diya_svg(1.0)}</div><div class="diya-r">{diya_svg(1.0)}</div>
  <div class="cta">Is Dhanteras, ghar laaiye <b>naya smartphone</b></div>
  <div class="dist"><div class="lbl">AUTHORISED<br>DISTRIBUTOR</div><div class="vr"></div>
    <img class="intex" src="{intex}"><div class="vr"></div><img class="ambrane" src="{ambrane}"></div>
  <div class="addr">📍 Defence Road, Mamun Cantt, Pathankot &nbsp;•&nbsp; Since 1992</div>
</div>"""


def garland(x: int, length: int) -> str:
    beads = []
    for i in range(length):
        c = "#ffd23f" if i % 2 else "#ff8c1a"
        beads.append(f'<circle cx="20" cy="{14 + i*26}" r="14" fill="{c}"/>'
                     f'<circle cx="20" cy="{14 + i*26}" r="5" fill="#c2410c" opacity=".5"/>')
    h = 14 + length * 26 + 30
    return (f'<svg class="garland" style="left:{x}px" width="40" height="{h}" viewBox="0 0 40 {h}">'
            f'<line x1="20" y1="0" x2="20" y2="{h-30}" stroke="#7c2d12" stroke-width="2"/>{"".join(beads)}'
            f'<path d="M20 {h-34} l-9 26 h18z" fill="#2f9e44"/></svg>')


def bright(nt: str, ah: str, photo: str, intex: str, ambrane: str) -> str:
    garlands = "".join(garland(x, n) for x, n in [(40, 9), (110, 6), (180, 4), (860, 4), (930, 6), (1000, 9)])
    return f"""<style>{BASE_CSS}
.post{{background:linear-gradient(160deg,#ff9a1f 0%,#ff5e3a 38%,#e8175d 72%,#a3135c 100%)}}
.mandala{{position:absolute;width:1300px;height:1300px;left:-110px;top:120px;opacity:.16}}
.mandala g{{stroke:#fff}}
.sun{{position:absolute;left:50%;top:520px;width:900px;height:900px;transform:translate(-50%,-50%);
  background:radial-gradient(circle,rgba(255,240,170,.55),transparent 60%)}}
.garland{{position:absolute;top:0}}
.hindi{{position:absolute;top:110px;width:100%;text-align:center;font:400 150px 'Yatra One';color:#fff;line-height:1.05;
  text-shadow:0 6px 0 #7a0a2e,0 12px 30px rgba(80,0,20,.5)}}
.eng{{position:absolute;top:268px;width:100%;text-align:center;font:400 96px 'Great Vibes';color:#ffe14d;
  text-shadow:0 4px 0 #7a0a2e}}
.tag{{position:absolute;top:400px;left:50%;transform:translateX(-50%);background:#fff;color:#c2185b;white-space:nowrap;
  font:900 24px Montserrat;letter-spacing:3px;padding:10px 28px;border-radius:40px;box-shadow:0 6px 0 #7a0a2e}}
.phone{{position:absolute;top:500px;left:50%;width:720px;height:390px;transform:translateX(-50%) rotate(-4deg);
  background:#111;border-radius:56px;padding:22px 30px;box-shadow:0 0 0 4px #3b3b3b,0 30px 60px rgba(60,0,20,.55)}}
.phone .scr{{width:100%;height:100%;border-radius:34px;overflow:hidden;position:relative}}
.phone img{{width:100%;height:100%;object-fit:cover}}
.phone .notch{{position:absolute;left:10px;top:50%;width:12px;height:12px;border-radius:50%;background:#2a2a2a;transform:translateY(-50%)}}
.phone .badge{{position:absolute;right:16px;top:14px;background:rgba(0,0,0,.6);color:#fff;font:700 15px Montserrat;
  padding:6px 12px;border-radius:20px}}
.msg{{position:absolute;top:930px;width:100%;text-align:center;font:700 32px Montserrat;color:#fff;line-height:1.35;
  text-shadow:0 3px 0 rgba(122,10,46,.6)}}
.msg b{{color:#ffe14d}}
.diyas{{position:absolute;top:1016px;width:100%;display:flex;justify-content:space-between;padding:0 40px}}
.post .dist{{top:1040px;box-shadow:0 6px 0 #7a0a2e}}
.diyas svg{{transform:scale(.8)}}
.bar{{position:absolute;bottom:0;left:0;right:0;height:196px;background:#5c0a2a;display:flex;align-items:center;
  justify-content:space-between;padding:0 50px;border-top:5px solid #ffd23f}}
.bar .role{{background:#ffd23f;color:#5c0a2a}}
.bar img{{width:118px;height:118px;border-radius:50%;object-fit:cover;box-shadow:0 0 0 4px #ffd23f}}
.bar .mid{{text-align:center;color:#fff}}
.bar .mid .n{{font:900 26px Montserrat;letter-spacing:2px;color:#ffe14d}}
.bar .mid .a{{font:500 19px Montserrat;margin-top:8px}}
</style>
<div class="post">
  {mandala_svg()}<div class="sun"></div>{sparkles(40, '#fff6c9', 11)}{garlands}
  <div class="hindi">शुभ धनतेरस</div>
  <div class="eng">Happy Dhanteras</div>
  <div class="tag">6 NOVEMBER 2026</div>
  <div class="phone"><div class="scr"><img src="{photo}"><div class="badge">📍 Pathankot</div></div><div class="notch"></div></div>
  <div class="msg">Is Dhanteras, ghar laaiye <b>naya smartphone</b><br>aur dher saari khushiyaan! 🪔</div>
  <div class="diyas">{diya_svg(1.0)}{diya_svg(1.0)}</div>
  <div class="dist"><div class="lbl">AUTHORISED<br>DISTRIBUTOR</div><div class="vr"></div>
    <img class="intex" src="{intex}"><div class="vr"></div><img class="ambrane" src="{ambrane}"></div>
  <div class="bar"><div class="biz"><img src="{nt}"><div class="role">RETAIL</div></div>
    <div class="mid"><div class="n">NAZAKAT TELECOM &amp; A&amp;H TELESERVICES</div>
      <div class="a">Defence Road, Mamun Cantt, Pathankot • Since 1992</div></div>
    <div class="biz"><img src="{ah}"><div class="role">DISTRIBUTION</div></div></div>
</div>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", type=pathlib.Path, required=True)
    ap.add_argument("--style", choices=["luxury", "bright"], required=True)
    ap.add_argument("--width", type=int, default=0, help="also export a hi-res JPG at this width (e.g. 3840 for 4K)")
    args = ap.parse_args()
    a = HERE / "assets"
    nt, ah, photo = (data_uri(a / "nazakat_logo.jpg"), data_uri(a / "ah_logo_circle.png"),
                     data_uri(a / "showroom_up.jpg"))
    intex, ambrane = data_uri(a / "intex_logo.svg"), data_uri(a / "ambrane_logo.svg")
    body = (luxury if args.style == "luxury" else bright)(nt, ah, photo, intex, ambrane)
    html = f"<!doctype html><html><head><meta charset='utf-8'><style>{fonts_css(args.fonts)}</style></head><body>{body}</body></html>"
    out = HERE / f"output/dhanteras_2026_{args.style}"
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROMIUM if pathlib.Path(CHROMIUM).exists() else None)
        page = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=2)
        page.set_content(html)
        page.evaluate("document.fonts.ready")
        page.wait_for_timeout(400)
        page.screenshot(path=str(out.with_suffix(".png")))
        b.close()
    from PIL import Image
    Image.open(out.with_suffix(".png")).convert("RGB").resize((1080, 1350), Image.LANCZOS).save(
        out.with_suffix(".jpg"), quality=95)
    print("wrote", out.with_suffix(".jpg"))
    if args.width:
        with sync_playwright() as p:
            b = p.chromium.launch(executable_path=CHROMIUM if pathlib.Path(CHROMIUM).exists() else None)
            page = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=args.width / 1080)
            page.set_content(html)
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(600)
            hi = out.with_name(out.name + f"_{args.width}px")
            page.screenshot(path=str(hi.with_suffix(".png")))
            b.close()
        Image.open(hi.with_suffix(".png")).convert("RGB").save(hi.with_suffix(".jpg"), quality=95)
        hi.with_suffix(".png").unlink()
        print("wrote", hi.with_suffix(".jpg"))


if __name__ == "__main__":
    main()
