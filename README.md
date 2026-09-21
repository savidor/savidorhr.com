# SavidorHR marketing site

Static marketing site, built by a small Python script and hosted on Netlify.
No database and no server-side code beyond one function that emails form submissions.

```
netlify.toml    build + headers + redirects
netlify/        the form notification function
src/            source you edit
  site.css        the whole design system
  favicon.svg     browser tab icon
  fonts/*.woff2   the two self-hosted webfonts, subset
  img/*.webp      the photographs, cropped and sized
  img/manifest.json  what build.py reads to write the <img> tags
  img/CREDITS.md  where each photograph came from, generated
  pages/*.html    one fragment per page
tools/          not part of the build
  build_fonts.py  regenerates src/fonts, run by hand
  build_images.py regenerates src/img, run by hand
build.py        assembles everything
site/           build output, what Netlify publishes
_preview.html   all six pages in one file, for sharing a preview link
```

## Deploying

Hosted on Netlify, built from this repo. Every push to `main` rebuilds and
publishes automatically.

**Netlify settings** (already declared in `netlify.toml`, nothing to type):

| Setting | Value |
|---|---|
| Build command | `python3 build.py` |
| Publish directory | `site` |
| Functions directory | `netlify/functions` |

**One-time setup in the Netlify dashboard**

1. *Add new site → Import an existing project* → GitHub → this repo.
2. *Site configuration → Environment variables*, add:

   | Variable | Value |
   |---|---|
   | `BREVO_API_KEY` | a Brevo v3 API key (free plan: 300 emails/day) |
   | `NOTIFY_TO` | where enquiries should land |
   | `NOTIFY_FROM` | the sender address verified in Brevo |

   To use Resend instead, set `RESEND_API_KEY` rather than `BREVO_API_KEY`.
   The function picks up whichever is present.
3. *Domain management* → add `savidorhr.com` and follow the DNS steps.
   HTTPS is issued automatically.

To work on it locally: edit files in `src/`, run `python3 build.py`, open
`site/index.html`. Commit and push to publish.

## The contact form

The form on the contact page is a [Netlify Form](https://docs.netlify.com/forms/setup/)
named `walkthrough`. Netlify detects it by parsing the built HTML at deploy time,
so it must stay in `site/contact.html` with `data-netlify="true"` on it.

What happens on submit:

1. Netlify stores the submission (*Forms* in the dashboard) and screens it for
   spam using the `bot-field` honeypot.
2. That fires `netlify/functions/submission-created.mjs`, which sends a branded
   HTML email with `Reply-To` set to the enquirer, so replying goes straight
   back to them.
3. The visitor lands on `thanks.html`, which is built but kept out of the nav,
   the sitemap and the preview, and carries `noindex`.

If sending ever fails the function still returns 200 and logs the reason, because
the submission is already safely stored. Nothing is lost; check *Forms* in the
dashboard and the function log.

Adding a field to the form needs no code change: unknown fields appear in the
email automatically. Add a label to `LABELS` in the function to give it a nicer
heading.

## Before it goes live

Two things are placeholders.

| What | Where | Note |
|---|---|---|
| Domain and contact details | `build.py`, the constants block at the top | Change `DOMAIN`, `EMAIL`, `EMAIL_INV`, `PHONE`, then rebuild. They propagate to every page, the footer, the sitemap and the social tags. |
| Logo | `build.py`, `LOGO_MARK` | The three node triangle. It paints its own colours rather than inheriting `currentColor`, so it keeps a white tile on dark grounds. Also replace `src/favicon.svg` if you change it. |

**There is no testimonial section.** It was removed rather than shipped with an
invented quote. To bring it back once you have a real, attributed reference:
restore the `.quote q-photo` block in `src/pages/index.html` and uncomment
`huddle-p` and `face-2` in `tools/build_images.py`. The styles for it are still
in `site.css`. Use a photograph of the person actually being quoted, not one of
the stock faces, for the reason in `src/img/CREDITS.md`.

Investor traction figures on `investors.html` are intentionally blank. Fill them
only with numbers you can evidence.

## Social preview image

`og.png` is referenced in the page head but not included. Until you add a
1200x630 PNG at the web root, links shared on WhatsApp, LinkedIn and X will show
no preview image. Everything else works without it.

## Photography

Every photograph is **served from our own origin**, for the same reason the
fonts are. They are cropped, resized and converted by `tools/build_images.py`,
which is run by hand and whose output is committed under `src/img/`.

Pages never write a srcset. They write one tag naming a photo:

```html
<img data-photo="boardroom" sizes="(max-width:940px) 100vw, 660px">
```

`build.py` turns that into the full responsive tag: every width in the srcset,
the intrinsic size so nothing shifts as it loads, lazy loading, and the 20px
placeholder inlined as the image's own background so a slot shows the
photograph's colours rather than a white hole. Naming a photo the manifest does
not carry stops the build. Add `data-eager` to a photo that should be fetched
for the first paint; nothing currently needs it, because the hero is a mockup.

To change, add or recrop a photo, edit the `PHOTOS` table at the top of
`tools/build_images.py` and run it:

```
brew install webp        # once, for cwebp
python3 tools/build_images.py
```

Each entry takes the Pexels id, the target aspect, a focal point as a fraction
of the source, an optional `zoom` and `q`, and the widths to publish. The crop
is built around the focal point rather than the centre, which is what keeps
faces whole; the face crops would otherwise be a whole person at 44px. The
photographer's original upload is fetched, not Pexels' own 2400px re-encode,
because resizing something already compressed once is a second lossy pass for
nothing. Sources are cached in a gitignored `.photo-cache/`.

**These are launch ready.** The backbone is one photographer's Lagos series, so
the set reads as one shoot rather than a scrapbook, and every photograph is of
Black professionals, which is who this product sells to. Swap in photographs of
your own people and sites when you have them, but nothing here is a placeholder.

**Which photographs can carry a product card.** The `.duo-shot` pattern lays a
mockup over one corner of a photo, so it only suits photographs with an empty
corner: `reviewing` and `callcentre` (subject right, use `pop-l`), `desk-m`
(subject left), `portrait-w` (subject right, use `pop-l`). `boardroom`,
`huddle` and `talking` fill their frames edge to edge and are used whole, in a
band, a closing panel or a plain frame. Putting a card on one of those covers
the very people the photograph is there for.

Licence terms and the one real limit are in `src/img/CREDITS.md`, generated
alongside the images. The short version: free commercially, no attribution
needed, but **do not put one of these faces beside a named customer
testimonial** — the licence forbids implying that a person in the imagery
endorses the product. The home page testimonial is labelled illustrative for
that reason.

## Fonts

Inter and Plus Jakarta Sans are **served from our own origin**, not from Google.
Loading them from `fonts.googleapis.com` cost two extra DNS and TLS handshakes,
and the font URLs were not even known until that render-blocking stylesheet came
back. The old setup pulled up to 18 files totalling about 750KB. This one is
four files totalling 64KB, two of which the page preloads.

Both are variable fonts, so one file covers every weight. They are subset by
`tools/build_fonts.py`:

- `*-latin.woff2` covers ASCII, Latin-1 and common punctuation. Deliberately
  wider than what the pages contain today, so ordinary copy edits cannot
  silently drop a glyph.
- `*-naira.woff2` carries the single character U+20A6. The naira sign is the
  only character on the site outside Latin-1, and Google ships it inside a
  latin-ext file carrying the whole of Latin Extended plus IPA, 83KB for Inter
  alone. Its `unicode-range` means the browser fetches it only for pages that
  print a figure in naira.

To regenerate them:

```
python3 -m venv /tmp/fontenv
/tmp/fontenv/bin/pip install "fonttools[woff]" brotli
/tmp/fontenv/bin/python tools/build_fonts.py
```

`build.py` content-hashes each file into `site/fonts/` and fills the
`__FONT_*__` placeholders in `site.css`, so the URLs in the stylesheet are
generated. Editing them by hand does nothing.

Monospace is the system stack. A webfont there would have cost two more files
to set a handful of figures inside screenshot mockups.

## Notes

- Nothing is fetched from a third party origin. Fonts and photographs are both
  served from our own, which is what keeps the page to one connection.
- Motion carries no information anywhere on the site, so
  `prefers-reduced-motion` turns all of it off rather than merely shortening it.
  Anything that starts hidden for the sake of an animation is gated behind a
  `js` class set in the `<head>`, so JavaScript being off gives you the finished
  page rather than a blank one.
- Light theme only, which is the convention for this category. Every colour is
  painted explicitly, so it does not inherit a dark background anywhere.
- `robots.txt` and `sitemap.xml` are generated from `DOMAIN`, so they cannot
  drift out of sync with the real address.
