#!/usr/bin/env python3
"""
build_images.py — regenerates src/img from the photo manifest below.

Not part of the build. Run it by hand when a photo changes, the way
tools/build_fonts.py is run, then commit what it writes.

Every photograph on the site is served from our own origin. Hotlinking the
stock library would have undone the whole point of self-hosting the fonts:
two more DNS and TLS handshakes, on the largest files the page downloads,
against a host whose cache headers and uptime are not ours to set.

What it does per photo:
  1. downloads the source once into a scratch cache
  2. crops to the target aspect around a focal point, so faces are never
     cut in half by a centre crop that knows nothing about the subject
  3. writes one WebP per width in the srcset
  4. writes a 20px wide placeholder, base64 in the manifest, so a slot
     shows the photo's own colours while the real file arrives

Needs cwebp and sips, both already present on macOS with libwebp installed:
    brew install webp

Outputs src/img/*.webp and src/img/manifest.json. build.py reads the
manifest, fingerprints each file into site/img/ and writes the markup.
"""
import base64
import json
import pathlib
import subprocess
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "src" / "img"
CACHE = HERE.parent / ".photo-cache"

# Every photo is from Pexels, whose licence allows commercial use with no
# attribution. The source URL is recorded anyway so any one of them can be
# traced back, re-downloaded at a different size, or replaced.
#
#   focal  (x, y) as a fraction of the source, the point a crop keeps.
#   aspect target width/height. The crop is the largest box of that shape
#          that fits, positioned on the focal point and clamped to the edges.
#   zoom   how much of that largest box to actually take, 1 being all of it.
#          The face crops need this: the widest possible square around a head
#          is most of the photograph, which at 44px on screen is an unreadable
#          smudge of a whole person rather than a face.
#   widths the srcset, largest first.
PHOTOS = {
    # The backbone is one photographer's Lagos series (Ninthgrid): same city,
    # same light, same styling, so the set looks shot rather than scavenged.
    # Everything here is a photograph of Black professionals, which is the
    # audience this product sells to.
    "boardroom": dict(
        pexels=30688596, aspect=16 / 9, focal=(0.50, 0.52), widths=[1600, 1100, 700],
        alt="A management team around a boardroom table in a Lagos office",
        page="https://www.pexels.com/photo/business-meeting-in-lagos-office-setting-30688596/",
    ),
    "huddle": dict(
        pexels=30689114, aspect=3 / 2, focal=(0.52, 0.52), widths=[1000, 640],
        alt="Three colleagues looking at the same laptop screen",
        page="https://www.pexels.com/photo/team-collaboration-meeting-in-lagos-office-30689114/",
    ),
    # The testimonial block is out of the site for now, so the two photographs
    # that served it are not generated. Uncomment both to bring it back: a
    # portrait crop of the huddle for the panel, and the face of the man in
    # that same photograph for the avatar beside the quote.
    #
    # "huddle-p": dict(
    #     pexels=30689114, aspect=4 / 5, focal=(0.47, 0.50), widths=[680, 420],
    #     alt="Three colleagues looking at the same laptop screen",
    #     page="https://www.pexels.com/photo/team-collaboration-meeting-in-lagos-office-30689114/",
    # ),
    "talking": dict(
        pexels=30688593, aspect=16 / 9, focal=(0.50, 0.48), widths=[1400, 900, 600],
        alt="Colleagues talking in the break area of a Lagos office",
        page="https://www.pexels.com/photo/casual-office-meeting-in-lagos-nigeria-30688593/",
    ),
    "desk-m": dict(
        pexels=30678211, aspect=3 / 2, focal=(0.36, 0.48), widths=[1000, 640],
        alt="A director working from his laptop",
        page="https://www.pexels.com/photo/professional-man-working-on-laptop-in-lagos-office-30678211/",
    ),
    "reviewing": dict(
        pexels=5668845, aspect=3 / 2, focal=(0.62, 0.42), widths=[1000, 640],
        alt="A manager looking up from her laptop in a glass walled office",
        page="https://www.pexels.com/photo/thoughtful-black-businesswoman-working-on-project-in-office-5668845/",
    ),
    "callcentre": dict(
        pexels=7709242, aspect=3 / 2, focal=(0.58, 0.46), widths=[1000, 640],
        alt="A consultant on a call at her desk, headset on",
        page="https://www.pexels.com/photo/woman-in-black-blazer-sitting-on-chair-7709242/",
    ),
    "portrait-w": dict(
        pexels=12373136, aspect=4 / 5, focal=(0.55, 0.45), widths=[760, 480],
        alt="A director standing outside her office building",
        page="https://www.pexels.com/photo/portrait-of-a-woman-in-a-suit-12373136/",
    ),
    "lagos": dict(
        pexels=32656347, aspect=16 / 9, focal=(0.50, 0.46), widths=[1200, 800, 560],
        q=60,
        alt="The Lagos skyline looking out towards the water",
        page="https://www.pexels.com/photo/aerial-view-of-lagos-cityscape-with-ocean-horizon-32656347/",
    ),

    # Faces, square, for the avatars beside an approval or a quote. Each is
    # cropped from a photograph already on the site, so the people in the
    # product screenshots are the same people in the scenes around them.
    "face-1": dict(pexels=12373136, aspect=1, focal=(0.555, 0.272), zoom=0.36,
                   widths=[160, 96], alt="Portrait", page=""),
    # "face-2": dict(pexels=30689114, aspect=1, focal=(0.657, 0.241), zoom=0.26,
    #                widths=[160, 96], alt="Portrait", page=""),
    "face-3": dict(pexels=7709242, aspect=1, focal=(0.634, 0.468), zoom=0.46,
                   widths=[160, 96], alt="Portrait", page=""),
    "face-4": dict(pexels=5668845, aspect=1, focal=(0.712, 0.285), zoom=0.40,
                   widths=[160, 96], alt="Portrait", page=""),
}

# The square face crops are a couple of kilobytes whatever quality they are
# set to, so they get the generous number. The scenery is what actually
# decides the weight of a page, and holds up fine at 74.
QUALITY = {1: 80}


def run(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"  ! {' '.join(args[:2])} failed\n{r.stderr.strip()}")
    return r.stdout


def source(pexels_id):
    """Download once, keep it in a gitignored cache for the next run."""
    CACHE.mkdir(exist_ok=True)
    path = CACHE / f"{pexels_id}.jpg"
    if not path.exists():
        # No size or compression parameters: this is the photographer's own
        # upload, around 4000px. Pexels' w=2400 copy has already been through a
        # lossy pass, and resizing that again is a second one for nothing.
        url = (f"https://images.pexels.com/photos/{pexels_id}/"
               f"pexels-photo-{pexels_id}.jpeg")
        print(f"  downloading {pexels_id}")
        req = urllib.request.Request(url, headers={"User-Agent": "savidorhr-build"})
        with urllib.request.urlopen(req, timeout=90) as r:
            path.write_bytes(r.read())
    return path


def dimensions(path):
    out = run("sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path))
    vals = [int(line.split(":")[1]) for line in out.splitlines() if ":" in line
            and line.strip().startswith("pixel")]
    return vals[0], vals[1]


def crop_box(w, h, aspect, focal, zoom=1.0):
    """A box of the target shape, centred on the focal point.

    Starts from the largest box of that shape that fits, takes `zoom` of it,
    then clamps to the edges so a focal point near a corner pulls the crop as
    far as it can go and then stops rather than running off the image.
    """
    if w / h > aspect:
        cw, ch = int(h * aspect), h
    else:
        cw, ch = w, int(w / aspect)
    cw, ch = max(1, int(cw * zoom)), max(1, int(ch * zoom))
    x = int(focal[0] * w - cw / 2)
    y = int(focal[1] * h - ch / 2)
    x = max(0, min(x, w - cw))
    y = max(0, min(y, h - ch))
    return x, y, cw, ch


def main():
    if not run("which", "cwebp").strip():
        sys.exit("  ! cwebp not found. brew install webp")
    OUT.mkdir(parents=True, exist_ok=True)

    manifest, written = {}, set()
    for name, spec in PHOTOS.items():
        src = source(spec["pexels"])
        w, h = dimensions(src)
        x, y, cw, ch = crop_box(w, h, spec["aspect"], spec["focal"],
                                spec.get("zoom", 1.0))
        # A photo can overrule the default. The cityscape needs it: a frame
        # full of small high contrast detail is the worst case for WebP, and
        # at the shared quality it alone weighed more than the other twelve
        # photographs put together.
        q = spec.get("q", QUALITY.get(spec["aspect"], 74))

        files = []
        for width in spec["widths"]:
            out = OUT / f"{name}-{width}.webp"
            run("cwebp", "-quiet", "-q", str(q), "-m", "6",
                "-crop", str(x), str(y), str(cw), str(ch),
                "-resize", str(width), "0", str(src), "-o", str(out))
            written.add(out.name)
            files.append({"w": width, "file": out.name,
                          "bytes": out.stat().st_size})

        # 20px wide, blurred up by CSS. Small enough to inline without
        # costing more than the request it saves.
        tiny = OUT / f".{name}-lqip.webp"
        run("cwebp", "-quiet", "-q", "26", "-crop", str(x), str(y), str(cw), str(ch),
            "-resize", "20", "0", str(src), "-o", str(tiny))
        lqip = ("data:image/webp;base64,"
                + base64.b64encode(tiny.read_bytes()).decode())
        tiny.unlink()

        manifest[name] = {
            "alt": spec["alt"], "source": spec["page"],
            "w": spec["widths"][0],
            "h": round(spec["widths"][0] / spec["aspect"]),
            "aspect": round(spec["aspect"], 4),
            "lqip": lqip, "files": files,
        }
        total = sum(f["bytes"] for f in files)
        print(f"  {name:<12} {cw}x{ch} crop  "
              f"{len(files)} files  {total/1024:6.1f}KB  lqip {len(lqip)}B")

    for stale in OUT.glob("*.webp"):
        if stale.name not in written:
            stale.unlink()
            print(f"  removed stale {stale.name}")

    (OUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_credits(manifest)
    grand = sum(f["bytes"] for m in manifest.values() for f in m["files"])
    print(f"\n  {len(manifest)} photos, {grand/1024:.0f}KB on disk, "
          f"manifest written")


def write_credits(manifest):
    """A record of where every photograph came from.

    The Pexels licence does not require attribution, so this is not a legal
    notice. It is so that a year from now anyone can trace a photograph back,
    fetch it at another size, or find the rest of the shoot it came from,
    without that knowledge living only in somebody's browser history.
    """
    rows = []
    for name in sorted(manifest):
        spec = manifest[name]
        if not spec["source"]:
            continue
        rows.append(f"| `{name}` | {spec['alt']} | <{spec['source']}> |")

    faces = ", ".join(f"`{n}`" for n in sorted(manifest) if not manifest[n]["source"])
    (OUT / "CREDITS.md").write_text(f"""# Photograph credits

Generated by `tools/build_images.py`. Do not edit by hand.

Every photograph on the site comes from [Pexels](https://www.pexels.com) under
the [Pexels licence](https://www.pexels.com/license/): free to use, including
commercially, modification allowed, **attribution not required**. This file
exists so each one can be traced back, not because credit is owed.

| Name | What it shows | Source |
|---|---|---|
{chr(10).join(rows)}

{faces} are square crops of the photographs above, for the avatars.

## The limits that do apply

The licence forbids four things. Three are not in play here: we do not sell
unaltered copies, we do not redistribute them to other stock sites, and the
logo is our own artwork rather than a stock photograph.

The fourth matters. **"Don't imply endorsement of your product by people or
brands on the imagery."** Putting one of these faces next to a named customer
testimonial would do exactly that, whether or not the name is real. The
testimonial on the home page is therefore labelled illustrative. Before it
carries a real customer's name it needs a photograph of that customer, or no
photograph at all.
""", encoding="utf-8")


if __name__ == "__main__":
    main()
