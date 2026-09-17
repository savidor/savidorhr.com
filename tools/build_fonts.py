#!/usr/bin/env python3
"""Rebuild the self-hosted webfonts in src/fonts/.

Not part of the normal build. Run it only when the fonts need refreshing:

    python3 -m venv /tmp/fontenv
    /tmp/fontenv/bin/pip install "fonttools[woff]" brotli
    /tmp/fontenv/bin/python tools/build_fonts.py

Why self-hosted at all: loading from fonts.googleapis.com costs two extra
DNS and TLS handshakes, and the font URLs are not even known until that
render-blocking stylesheet comes back. Serving them from our own origin lets
the HTML preload them immediately.

Why subset: the only character on the whole site outside Latin-1 is the naira
sign, and Google ships it inside a latin-ext file that carries the whole of
Latin Extended-A and B, IPA and more. That file is 83KB for Inter. Subsetting
it to the one glyph we use takes it to about 2KB.

The latin files are cut to a deliberately generous western set rather than to
exactly the characters present today, so ordinary copy edits cannot silently
drop a glyph out of the font.
"""
import io
import pathlib
import re
import subprocess
import sys

from fontTools.ttLib import TTFont
from fontTools import subset

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "Chrome/120 Safari/537.36")

FAMILIES = {
    "inter":   "Inter:wght@400..800",
    "jakarta": "Plus+Jakarta+Sans:wght@600..800",
}

# ASCII, Latin-1, the punctuation a marketing site actually uses, and nothing
# else. Deliberately wider than what the pages contain today.
WESTERN = (
    list(range(0x0020, 0x007F)) + list(range(0x00A0, 0x0100)) +
    [0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026,
     0x2039, 0x203A, 0x2122, 0x2190, 0x2191, 0x2192, 0x2193, 0x2212]
)
NAIRA = [0x20A6]

OUT = pathlib.Path(__file__).parent.parent / "src" / "fonts"


def fetch_subset_urls(query):
    """Return {subset_name: woff2 url} from the Google Fonts css2 endpoint."""
    css = subprocess.run(
        ["curl", "-fsS", "--max-time", "30", "-A", UA,
         f"https://fonts.googleapis.com/css2?family={query}&display=swap"],
        capture_output=True, text=True, check=True).stdout
    found = {}
    for name, body in re.findall(r"/\*\s*([a-z-]+)\s*\*/\s*@font-face\s*\{(.*?)\}",
                                 css, re.S):
        m = re.search(r"url\((https://[^)]+\.woff2)\)", body)
        if m:
            found[name] = m.group(1)
    return found


def cut(url, codepoints, dest):
    raw = subprocess.run(["curl", "-fsS", "--max-time", "60", url],
                         capture_output=True, check=True).stdout
    font = TTFont(io.BytesIO(raw))
    if "fvar" not in font:
        sys.exit(f"{dest.name}: expected a variable font, got a static one")

    opts = subset.Options()
    opts.layout_features = ["*"]      # keep kerning and ligatures
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    opts.recalc_bounds = True

    sub = subset.Subsetter(options=opts)
    sub.populate(unicodes=codepoints)
    sub.subset(font)

    font.flavor = "woff2"
    font.save(dest)
    return dest.stat().st_size


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    for slug, query in FAMILIES.items():
        urls = fetch_subset_urls(query)
        for name, codepoints, want in (("latin", WESTERN, "latin"),
                                       ("naira", NAIRA, "latin-ext")):
            if want not in urls:
                sys.exit(f"{slug}: Google did not serve a {want} subset")
            dest = OUT / f"{slug}-{name}.woff2"
            size = cut(urls[want], codepoints, dest)
            total += size
            print(f"  {dest.name:24} {size/1024:6.1f} KB")
    print(f"  {'total':24} {total/1024:6.1f} KB")


if __name__ == "__main__":
    main()
