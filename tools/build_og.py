#!/usr/bin/env python3
"""
build_og.py — renders the social preview card to src/og.png.

Not part of the build. Run it by hand when the wording or the brand changes,
then commit the result, the same arrangement as the fonts and the images.

og.jpg is what WhatsApp, LinkedIn and X show when somebody shares a link. It
was referenced in every page head and never existed, so every share so far
has gone out as a bare grey box. In a market where links move through
WhatsApp more than anywhere else, that is the most expensive missing file on
the site.

Needs Chrome, which is also what takes the screenshot.
"""
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "src" / "og.jpg"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# 1200x630 is the size every platform crops from. Anything important stays
# well inside the middle, because the crop differs per platform.
HTML = """<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:"Jak";src:url("FONT_JAK") format("woff2");font-weight:200 800;}
@font-face{font-family:"Int";src:url("FONT_INT") format("woff2");font-weight:100 900;}
*{margin:0;padding:0;box-sizing:border-box;}
body{width:1200px;height:630px;overflow:hidden;position:relative;
  background:linear-gradient(152deg,#3D73DC 0%,#2A57C4 30%,#1B3C96 62%,#0F1B61 100%);
  font-family:"Int",sans-serif;}
.ph{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;
  object-position:center 40%;mix-blend-mode:luminosity;opacity:.5;}
.scrim{position:absolute;inset:0;
  background:radial-gradient(110% 90% at 32% 50%,rgba(10,18,62,.9) 0%,
    rgba(12,24,80,.7) 48%,rgba(14,32,100,.5) 100%),
    linear-gradient(180deg,rgba(10,18,62,.45),rgba(10,18,62,.6));}
.dots{position:absolute;inset:0;opacity:.5;
  background:radial-gradient(circle at 1px 1px,rgba(255,255,255,.13) 1px,transparent 0) 0 0/34px 34px;}
.in{position:relative;padding:64px 72px;height:100%;display:flex;
  flex-direction:column;justify-content:space-between;}
.brand{display:flex;align-items:center;gap:14px;}
.tile{width:56px;height:56px;border-radius:14px;background:#fff;
  display:grid;place-items:center;box-shadow:0 8px 22px -8px rgba(5,12,45,.7);}
.tile svg{width:34px;height:34px;}
.name{font-family:"Jak",sans-serif;font-weight:800;font-size:2rem;
  letter-spacing:-.03em;color:#fff;}
.name i{font-style:normal;color:#5CE8B0;}
h1{font-family:"Jak",sans-serif;font-weight:800;font-size:3.9rem;line-height:1.08;
  letter-spacing:-.032em;color:#fff;max-width:19ch;}
h1 span{color:#5CE8B0;}
p{margin-top:20px;font-size:1.34rem;line-height:1.5;color:rgba(255,255,255,.85);
  max-width:40ch;}
.foot{display:flex;align-items:center;gap:12px;font-size:1.1rem;font-weight:600;
  color:rgba(255,255,255,.82);}
.dot{width:6px;height:6px;border-radius:50%;background:#5CE8B0;}
</style></head><body>
<img class="ph" src="IMG_SRC"><div class="scrim"></div><div class="dots"></div>
<div class="in">
  <div class="brand"><span class="tile">LOGO</span>
    <span class="name">Savidor<i>HR</i></span></div>
  <div>
    <h1>HR and approvals,<br><span>finally on one system.</span></h1>
    <p>Leave, appraisals, requisitions and procurement, routed through the
      approval chain your company already uses.</p>
  </div>
  <div class="foot"><span class="dot"></span>Built in Lagos, for Nigerian companies</div>
</div></body></html>"""


def main():
    logo = None
    build = (ROOT / "build.py").read_text()
    start = build.index("LOGO_MARK = (")
    logo = "".join(
        line.strip().strip("'\"")
        for line in build[start:build.index("\n\n", start)].splitlines()[1:]
        if line.strip().startswith(("'", '"'))
    ).replace("')", "")

    img = sorted((ROOT / "src" / "img").glob("boardroom-1600.webp"))
    if not img:
        sys.exit("  ! run tools/build_images.py first")

    fonts = ROOT / "src" / "fonts"
    html = (HTML
            .replace("IMG_SRC", img[0].as_uri())
            .replace("FONT_JAK", (fonts / "jakarta-latin.woff2").as_uri())
            .replace("FONT_INT", (fonts / "inter-latin.woff2").as_uri())
            .replace("LOGO", logo))
    tmp = ROOT / ".og.html"
    tmp.write_text(html, encoding="utf-8")
    shot = ROOT / ".og.png"
    subprocess.run([
        CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        "--allow-file-access-from-files", "--force-device-scale-factor=1",
        "--virtual-time-budget=6000", "--window-size=1200,630",
        f"--screenshot={shot}", tmp.as_uri(),
    ], capture_output=True)
    tmp.unlink()
    if not shot.exists():
        sys.exit("  ! Chrome produced no screenshot")
    # A photographic card is four times the size as PNG as it is as JPEG, and
    # this file is fetched by a chat app on a phone before a link will even
    # render a preview.
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "82",
                    str(shot), "--out", str(OUT)], capture_output=True)
    shot.unlink()
    print(f"  wrote {OUT.relative_to(ROOT)}  {OUT.stat().st_size/1024:.0f}KB")


if __name__ == "__main__":
    main()
