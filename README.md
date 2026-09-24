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
  insights/*.html one fragment per article
  og.jpg          the social share card, generated
tools/          not part of the build
  build_fonts.py  regenerates src/fonts, run by hand
  build_images.py regenerates src/img, run by hand
  build_og.py     regenerates src/og.jpg, run by hand
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

### The module picker

"Interested in" is a `<select multiple>` with an optgroup per family. The page
script builds a custom panel over it and writes selections back into that
select, so there is no second copy of the module list to drift and the native
control is what submits. With JavaScript off the native select is what the
visitor gets, which is why it is hidden by the `js` class rather than by an
attribute.

A family row selects or clears its whole family and shows a dash when only
part of it is chosen. A fully chosen family collapses to one chip rather than
four. "The whole system" and "Not sure yet" are exclusive: choosing either
clears everything else, and choosing a module clears them.

On a phone the panel becomes a bottom sheet, and the script moves it to
`<body>` while it is open. That is not decoration: `position:fixed` resolves
against the nearest transformed ancestor, the form card carries the scroll
reveal transform, and without the move the sheet rendered about 1800px down
the page instead of at the bottom of the screen.

A multiple select submits repeated values for one name, so
`netlify/functions/submission-created.mjs` joins arrays with ", " rather than
letting `String()` produce "A,B,C".

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

## Search

The site is written to be found for the terms it genuinely serves: HR software
in Nigeria, leave management, approval and requisition workflow, HR management
system, CRM. **Nothing targets payroll**, because there is no payroll module,
and ranking for a promise the product does not keep costs more in bounces than
the position is worth.

There is deliberately no `<meta name="keywords">`. Google has ignored it since
2009 and stuffing it is a spam signal rather than a ranking one. Terms earn
their place in titles, headings, body copy, link text and alt text.

Each page carries JSON-LD in its head, built in `build.py`: an Organization
with the Lagos address, a SoftwareApplication on the product pages, a
BreadcrumbList, and a FAQPage wherever the page has an FAQ. **The FAQ schema is
lifted out of the rendered markup**, not kept in a second list, because a
FAQPage whose answers have drifted from the visible ones is exactly what
Google issues manual actions for. No aggregateRating or review is emitted;
inventing either is the fastest route to a structured data penalty.

### The one thing that matters more than any of it

`savidorhr.com` must serve this site. At the time of writing it is parked on
Hostinger, and the parking page carries
`<meta name="robots" content="noindex, nofollow, noarchive, nosnippet">`.
Every canonical tag here points at that domain, so a crawler that reaches the
Netlify address is sent to a page that tells it not to index. **Until the DNS
is moved, none of the rest of this has any effect.** In Netlify, add the
domain under *Domain management*, then repoint the nameservers at Hostinger.

## Social preview image

`src/og.jpg` is generated by `tools/build_og.py` and published to the web root,
and `build.py` refuses to build without it rather than shipping a head that
points at a 404. It is JPEG rather than PNG because the same card is four
times the size as PNG, and it is fetched by a chat app on a phone before a
link will render a preview at all.

Regenerate it after a wording or brand change:

```
python3 tools/build_og.py
```

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

**A photograph has to depict what its box says.** That rule outranks
variety. Where a box makes a claim no photograph can show, it carries no
photograph at all: "Twenty eight modules, five families" and "The parts
nobody remembers to ask for" are plain navy bands for that reason, and a
decorative picture there would be worse than the gap.

The consequence is that repetition now tracks the message. Every call to
action that says "configured live on the call" carries the same photograph of
somebody on a call, because it is one component saying one thing. That is not
the fault the earlier set had, which was the same boardroom behind five
unrelated claims.

**One photograph per slot, and each depicts its subject.** The set drifted
into five uses of the same boardroom, which a reader notices long before they
notice the point being made. Nothing now appears more than twice across the
site, nothing appears twice on one page, and the article covers show what the
article is about: a hand signing an approval form, an empty chair at a desk
somebody has left, colleagues evaluating something together. An article cover
shown as a thumbnail on the insights hub is the same article, not a repeat.

If you add a page, check the reuse before you ship it:

```
python3 - <<'EOF'
import re, pathlib, collections
use = collections.defaultdict(list)
for f in sorted(list(pathlib.Path('src/pages').glob('*.html'))
                + list(pathlib.Path('src/insights').glob('*.html'))):
    t = f.read_text()
    for m in re.findall(r'data-photo="([a-z0-9-]+)"', t): use[m].append(f.stem)
    for m in re.findall(r'^cover: (\S+)', t, re.M):      use[m].append(f.stem)
for k in sorted(use, key=lambda k: -len(use[k])):
    print(f'{k:<14} x{len(use[k])}  {", ".join(use[k])}')
EOF
```

**These are launch ready.** The backbone is one photographer's Lagos series, so
the set reads as one shoot rather than a scrapbook, and every photograph is of
Black professionals, which is who this product sells to. Swap in photographs of
your own people and sites when you have them, but nothing here is a placeholder.

**Photographs submerged in the navy.** The blue panels, the page hero and
the six inner page heroes all use one mechanism, taken from the brand's own
social graphics: the photograph supplies only luminance and the navy supplies
every hue, which is what `mix-blend-mode:luminosity` does and why it is a
real duotone rather than a picture under a blue sheet. Put `navy-ph` on the
section and `navy-bg` on the photograph; `build.py` pairs the scrim element
to it automatically, so the two can never be separated by an edit.

The scrim is what holds the headline's contrast, and it is not decorative.
Measured against the live backdrop, white text sits at 9.1:1 on the home
hero and 9.5 to 10.5:1 on the bands, and the mint accent words at 5.5:1,
against a 4.5:1 requirement. If you lift `opacity` on `.navy-bg`, re-measure
rather than trusting the eye: a photograph with a bright window in it can
move the worst pixel a long way.

**Amber marks, green acts.** Also from the social graphics: on the navy
bands the icon tiles are amber and only buttons are green, so an icon and a
button never carry the same signal. The five family hues still apply to the
module grid, which is not on a navy band. The override has to be written at
`nth-child` weight, because that is how the family hues are set.

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

## News and insights

Articles are fragments in `src/insights/`, with the same header as a page plus
`date`, `heading`, `summary`, `topic` and `cover`. The topic drives the filter
on the hub; the cover names a photograph from the manifest.

**Reading time, heading anchors and the contents rail are derived from the
prose**, in `prepare()`, not written into the header. An edit to the body
cannot leave any of the three stale, which is why nobody has to remember to
update a table of contents. `build.py` renders each to
`site/insights/<slug>.html`, builds the hub at `site/insights.html`, adds both
to the sitemap with `lastmod`, and emits Article schema per piece.

The hub leads with the newest piece at full width, then filters the rest by
topic. Article pages carry a cover in the same navy duotone as the bands, a
contents rail that marks the section you are actually in rather than the last
link you clicked, and share buttons with **WhatsApp first**, because that is
how links move in this market and burying it behind a generic share icon
loses the share.

**Write article markup as though the page sat at the site root.** They are
published a level down, and `reroot()` lifts every relative URL by one. Writing
`../` yourself gets it lifted twice and 404s, which is exactly what happened on
the first pass.

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

- Google Analytics is the only third party request on the site. Fonts and
  photographs are all served from our own origin, so that tag is the single
  outside connection a visitor makes. It is set by `GA_ID` in `build.py`, and
  emptying that constant removes the tag from every page, which is what a fork
  or a local experiment should do. The snippet is Google's own, unedited, and it
  sits directly after the two `<meta>` declarations rather than literally first:
  a script ahead of `charset` is parsed before the browser knows the encoding of
  the bytes it is reading, and the charset has to land inside the first 1024.
- Motion carries no information anywhere on the site, so
  `prefers-reduced-motion` turns all of it off rather than merely shortening it.
  Anything that starts hidden for the sake of an animation is gated behind a
  `js` class set in the `<head>`, so JavaScript being off gives you the finished
  page rather than a blank one.
- Light theme only, which is the convention for this category. Every colour is
  painted explicitly, so it does not inherit a dark background anywhere.
- `robots.txt` and `sitemap.xml` are generated from `DOMAIN`, so they cannot
  drift out of sync with the real address.
