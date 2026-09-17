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
  pages/*.html    one fragment per page
tools/          not part of the build
  build_fonts.py  regenerates src/fonts, run by hand
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

Three things are placeholders.

| What | Where | Note |
|---|---|---|
| Domain and contact details | `build.py`, the constants block at the top | Change `DOMAIN`, `EMAIL`, `EMAIL_INV`, `PHONE`, then rebuild. They propagate to every page, the footer, the sitemap and the social tags. |
| Logo | `build.py`, `LOGO_MARK` | The three node triangle. It paints its own colours rather than inheriting `currentColor`, so it keeps a white tile on dark grounds. Also replace `src/favicon.svg` if you change it. |
| Testimonial | `src/pages/index.html`, the `.quote` block | Labelled "Illustrative customer quote". Replace with a real attributed one, or delete the section. |

Investor traction figures on `investors.html` are intentionally blank. Fill them
only with numbers you can evidence.

## Social preview image

`og.png` is referenced in the page head but not included. Until you add a
1200x630 PNG at the web root, links shared on WhatsApp, LinkedIn and X will show
no preview image. Everything else works without it.

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

- Fonts load from Google Fonts. The site renders correctly on the fallback stack
  if that is ever blocked.
- Light theme only, which is the convention for this category. Every colour is
  painted explicitly, so it does not inherit a dark background anywhere.
- `robots.txt` and `sitemap.xml` are generated from `DOMAIN`, so they cannot
  drift out of sync with the real address.
