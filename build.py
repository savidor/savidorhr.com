#!/usr/bin/env python3
"""
build.py — assembles the SavidorHR marketing site.

Sources live in  src/ :
    site.css          the whole design system
    pages/*.html      one fragment per page, with a small header comment

Outputs to  site/ :
    index.html, product.html, modules.html, crm.html,
    investors.html, contact.html, site.css
    Upload that whole folder to your host. No build step needed on the server.

Also writes  _preview.html , a single file containing every page with
client-side switching, so the whole site can be previewed from one link.

Run:  python3 marketing/build.py
"""
import collections
import hashlib
import json
import re
import pathlib

CSS_NAME = "site.css"  # replaced with the fingerprinted name at build time
FONT_TAGS = ""         # preload links, filled in once the fonts are hashed

HERE = pathlib.Path(__file__).parent
SRC = HERE / "src"
OUT = HERE / "site"

# ── Edit these when the domain and contact details are settled ────────────
DOMAIN = "https://savidorhr.com"
COMPANY = "SavidorHR"
EMAIL = "hello@savidorhr.com"
EMAIL_INV = "invest@savidorhr.com"
PHONE = "+234 000 000 0000"

# ── Search ───────────────────────────────────────────────────────────────
# Where the company is, in the terms a search engine understands. The city
# and country are a real ranking signal for "HR software Nigeria" and the
# like, and they are true, so they are stated in the markup rather than only
# in the footer prose.
CITY = "Lagos"
REGION = "Lagos State"
COUNTRY = "NG"
LOCALE = "en-NG"

# Deliberately no <meta name="keywords">. Google has ignored it since 2009
# and stuffing it is a spam signal, not a ranking one. Keywords earn their
# place in titles, headings, body copy, link text and alt text instead.

# Reachable, but deliberately absent from the nav, the sitemap and the preview.
UNLISTED = {"thanks"}

# ── News and insights ────────────────────────────────────────────────────
# Articles live in src/insights/ and are published under /insights/. This is
# the part of a marketing site that earns search traffic over time: the
# product pages answer "is this the right tool", articles answer the
# questions people type long before they know a tool exists.
INSIGHTS_DIR = HERE / "src" / "insights"
INSIGHTS_OUT = "insights"

NAV = [
    ("product", "Product", "product.html"),
    ("modules", "Modules", "modules.html"),
    ("pricing", "Pricing", "pricing.html"),
    ("insights", "Insights", "insights.html"),
    ("investors", "Investors", "investors.html"),
]

# Nav items that open a mega panel. CRM is deliberately absent from NAV: it is
# the flagship card inside the Modules panel, so it is reachable without
# spending a top-level slot on one module out of twenty eight.
MEGA_ITEMS = {"product", "modules"}

# The Product panel, in columns. Each entry is (label, href-with-anchor).
PRODUCT_COLS = [
    ("How it works", [
        ("How a request moves", "product.html#how"),
        ("The routing engine", "product.html#routing"),
        ("Roles and permissions", "product.html#builtin"),
    ]),
    ("Built in", [
        ("Audit trail on every view", "product.html#builtin"),
        ("Email and push notification", "product.html#builtin"),
        ("Works on the phone in the field", "product.html#builtin"),
        ("Break glass administration", "product.html#builtin"),
    ]),
    ("Getting live", [
        ("Deployment in weeks", "product.html#deploy"),
        ("Migration from what you have", "product.html#builtin"),
        ("Talk to an engineer", "contact.html"),
    ]),
]

# ── Icon sprite. Stroke icons at 24x24, currentColor, so one set restyles. ──
ICONS = {
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "check-c": '<circle cx="12" cy="12" r="10"/><polyline points="16 10 11 15 8 12"/>',
    "doc": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
           '<polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/>'
           '<line x1="9" y1="17" x2="13" y2="17"/>',
    "cart": '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/>'
            '<path d="M1 1h4l2.7 13.4a2 2 0 0 0 2 1.6h9.7a2 2 0 0 0 2-1.6L23 6H6"/>',
    "wallet": '<path d="M21 12V7H5a2 2 0 0 1 0-4h14v4"/><path d="M3 5v14a2 2 0 0 0 2 2h16v-5"/>'
              '<path d="M18 12a2 2 0 0 0 0 4h4v-4z"/>',
    "chart": '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>'
             '<line x1="6" y1="20" x2="6" y2="14"/>',
    "cal": '<rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/>'
           '<line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
             '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "award": '<circle cx="12" cy="8" r="6"/><path d="M15.5 13.5 17 22l-5-3-5 3 1.5-8.5"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "case": '<rect x="2" y="7" width="20" height="14" rx="2"/>'
            '<path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>',
    "mail": '<path d="M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/>'
            '<polyline points="22 6 12 13 2 6"/>',
    "mega": '<path d="M3 11v2a1 1 0 0 0 1 1h3l5 4V6L7 10H4a1 1 0 0 0-1 1z"/>'
            '<path d="M16 8a5 5 0 0 1 0 8"/><path d="M19 5a9 9 0 0 1 0 14"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/>'
              '<circle cx="12" cy="12" r="2"/>',
    "laptop": '<rect x="3" y="4" width="18" height="12" rx="2"/><line x1="2" y1="20" x2="22" y2="20"/>',
    "car": '<path d="M5 17H3v-5l2-5h14l2 5v5h-2"/><circle cx="7.5" cy="17" r="2"/>'
           '<circle cx="16.5" cy="17" r="2"/><line x1="9.5" y1="17" x2="14.5" y2="17"/>',
    "screen": '<rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/>'
              '<line x1="12" y1="17" x2="12" y2="21"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>',
    "lock": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "eye": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    "share": '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>'
             '<line x1="8.6" y1="10.5" x2="15.4" y2="6.5"/><line x1="8.6" y1="13.5" x2="15.4" y2="17.5"/>',
    "db": '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.7-4 3-9 3s-9-1.3-9-3"/>'
          '<path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/>',
    "bell": '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>'
            '<path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
    "arrow": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    "menu": '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/>'
            '<line x1="3" y1="18" x2="21" y2="18"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "layers": '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/>'
              '<polyline points="2 12 12 17 22 12"/>',
    "route": '<circle cx="6" cy="19" r="3"/><circle cx="18" cy="5" r="3"/>'
             '<path d="M9 19h4a4 4 0 0 0 4-4V9"/>',
    "build": '<path d="M14.7 6.3a4 4 0 0 1 5 5L8.5 22.5 2 24l1.5-6.5z"/><line x1="12" y1="9" x2="18" y2="15"/>',
}


# Set in the <head>, before anything paints. Everything that starts hidden
# for the sake of an animation is gated behind this class, so a visitor with
# JavaScript off is served the finished page rather than an empty one. It has
# to run here and not with the rest of the script at the end of the body, or
# the hidden things would flash visible during the parse and then disappear.
JS_FLAG = '<script>document.documentElement.className+=" js";</script>'


ARROW_S = ('<svg class="ar" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
           'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
           '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>')


def sprite():
    """One hidden SVG holding every icon, referenced by <use>."""
    syms = "".join(
        f'<symbol id="i-{k}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{v}</symbol>'
        for k, v in ICONS.items()
    )
    return f'<svg width="0" height="0" style="position:absolute" aria-hidden="true">{syms}</svg>'


# The brand mark: three nodes joined into a triangle, which is the shape an
# approval chain makes. It paints its own colours rather than inheriting
# currentColor, because the three nodes differ, so it must sit on a white
# tile (.logo-m) on every ground, light or dark.
LOGO_MARK = (
    '<svg viewBox="0 0 24 24" aria-hidden="true">'
    '<path d="M12 6.6 6.9 16.4H17.1Z" fill="none" stroke="#5B6B8C"'
    ' stroke-width="1.5" stroke-linejoin="round" opacity=".92"/>'
    '<circle cx="12" cy="6.6" r="2.75" fill="#F5B33F"/>'
    '<circle cx="6.9" cy="16.4" r="2.75" fill="#16A55F"/>'
    '<circle cx="17.1" cy="16.4" r="2.75" fill="#2E63D5"/>'
    '</svg>')


# Mega menu columns. Operations and Governance share one column so the panel
# stays four columns wide next to the featured card.
MEGA_COLS = [
    ("Spend and approvals", ["spend"]),
    ("People",              ["people"]),
    ("Revenue and CRM",     ["revenue"]),
    ("Operations and governance", ["ops", "gov"]),
]

CARET = ('<svg class="caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
         'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
         '<polyline points="6 9 12 15 18 9"/></svg>')


def modules_by_family():
    by_fam = {}
    for m in MODULES:
        by_fam.setdefault(m.fam, []).append(m.name)
    return by_fam


def _mega_href(href, preview):
    """In the single-file preview there are no separate pages, so every link
    collapses to the page-switching attribute and anchors are dropped."""
    slug = href.split("#")[0].replace(".html", "")
    if slug == "index":
        slug = "index"
    return f'href="#" data-page="{slug}"' if preview else f'href="{href}"'


def mega_shell(cols, feat, foot):
    return (f'<div class="mega"><div class="wrap mega-in">{cols}{feat}</div>'
            f'<div class="mega-foot"><div class="wrap">{foot}</div></div></div>')


def mega_modules(preview):
    """Built from the module cards, so a new module appears in the navigation
    the moment its card is added to the Modules page."""
    by_fam = modules_by_family()
    href = _mega_href("modules.html", preview)
    crm = _mega_href("crm.html", preview)

    cols = ""
    for title, keys in MEGA_COLS:
        names = [n for k in keys for n in by_fam.get(k, [])]
        links = "".join(f"<a {href}>{n}</a>" for n in names)
        cols += f'<div class="mega-col"><h6>{title}</h6>{links}</div>'

    total = sum(len(v) for v in by_fam.values())
    feat = (f'<a class="mega-feat" {crm}>'
            f'<span class="mega-tag">Flagship</span>'
            f'<b>CRM and guided calling</b>'
            f'<p>The queue decides who is called next, the script branches on what they '
            f'actually said, and no call ends without a dated next step.</p>'
            f'<span class="mega-go">Look inside {ARROW_S}</span></a>')
    foot = (f'<span>{total} modules, one permission model. Switch on what you need now.</span>'
            f'<a {href}>Browse all {total} {ARROW_S}</a>')
    return mega_shell(cols, feat, foot)


def mega_product(preview):
    """How the system works, as opposed to what is in it."""
    cols = ""
    for title, items in PRODUCT_COLS:
        links = "".join(f'<a {_mega_href(h, preview)}>{l}</a>' for l, h in items)
        cols += f'<div class="mega-col mega-col-wide"><h6>{title}</h6>{links}</div>'

    demo = _mega_href("contact.html", preview)
    feat = (f'<a class="mega-feat" {demo}>'
            f'<span class="mega-tag">Forty minutes</span>'
            f'<b>Bring us your worst process</b>'
            f'<p>The one with the exception everybody works around. We will configure it '
            f'live on the call, against your own approval chain.</p>'
            f'<span class="mega-go">Book a walkthrough {ARROW_S}</span></a>')
    foot = (f'<span>Approval chains are settings, not code. No developer needed to change them.</span>'
            f'<a {_mega_href("product.html", preview)}>How it works {ARROW_S}</a>')
    return mega_shell(cols, feat, foot)


MEGA_PANELS = {"modules": mega_modules, "product": mega_product}


def header(active, preview):
    def link(slug, label, href):
        h = f'href="#" data-page="{slug}"' if preview else f'href="{href}"'
        cls = ' class="on"' if slug == active else ""
        return f"<a {h}{cls}>{label}</a>"

    home = 'href="#" data-page="index"' if preview else 'href="index.html"'
    contact = 'href="#" data-page="contact"' if preview else 'href="contact.html"'
    parts = []
    for slug, label, href in NAV:
        if slug in MEGA_ITEMS:
            h = f'href="#" data-page="{slug}"' if preview else f'href="{href}"'
            cls = ' class="on"' if slug == active else ""
            panel = MEGA_PANELS[slug](preview)
            parts.append(f'<div class="nav-item has-mega">'
                         f'<a {h}{cls}>{label}{CARET}</a>{panel}</div>')
        else:
            parts.append(link(slug, label, href))
    nav = "".join(parts)
    def mlink(slug, label, href):
        h = f'href="#" data-page="{slug}"' if preview else f'href="{href}"'
        cls = ' class="on"' if slug == active else ""
        return f"<a {h}{cls}>{label}</a>"

    mnav = "".join(mlink(s, l, h) for s, l, h in NAV)
    return f"""
<header class="hdr">
  <div class="wrap hdr-in">
    <a class="logo" {home}><span class="logo-m">{LOGO_MARK}</span><span class="logo-t">Savidor<i>HR</i></span></a>
    <nav class="nav">{nav}</nav>
    <div class="hdr-cta">
      <a class="btn btn-s" {contact}>Contact sales</a>
      <a class="btn btn-p" {contact}>Book a demo</a>
    </div>
    <button class="burger" id="burger" aria-label="Open menu" aria-expanded="false">
      <svg><use href="#i-menu"/></svg>
    </button>
  </div>
  <div class="hdr-bar" id="hdrBar"></div>
  <div class="wrap"><div class="mnav" id="mnav">{mnav}
    <div class="mnav-cta">
      <a class="btn btn-p" {contact}>Book a demo</a>
      <a class="btn btn-s" {contact}>Contact sales</a>
    </div>
  </div></div>
</header>"""


def footer(preview):
    def a(slug, label, href):
        h = f'href="#" data-page="{slug}"' if preview else f'href="{href}"'
        return f"<li><a {h}>{label}</a></li>"

    prod = "".join([
        a("product", "How it works", "product.html"),
        a("modules", "All 28 modules", "modules.html"),
        a("crm", "CRM and calling", "crm.html"),
        a("pricing", "Pricing", "pricing.html"),
    ])
    comp = "".join([
        # Linked from the footer as well as the nav, so every page on the site
        # passes authority to the articles rather than only the top level.
        a("insights", "News and insights", "insights.html"),
        a("investors", "Investors", "investors.html"),
        a("contact", "Contact", "contact.html"),
        f'<li><a href="mailto:{EMAIL}">Support</a></li>',
    ])
    return f"""
<footer class="ftr">
  <div class="wrap">
    <div class="ftr-grid">
      <div class="ftr-about">
        <a class="logo" href="{'#' if preview else 'index.html'}"><span class="logo-m">{LOGO_MARK}</span><span class="logo-t">Savidor<i>HR</i></span></a>
        <p>Workforce and approval infrastructure for African enterprise. Built in Lagos.</p>
      </div>
      <div><h5>Product</h5><ul>{prod}</ul></div>
      <div><h5>Modules</h5><ul>
        <li><a {'href="#" data-page="modules"' if preview else 'href="modules.html"'}>Spend and approvals</a></li>
        <li><a {'href="#" data-page="modules"' if preview else 'href="modules.html"'}>People</a></li>
        <li><a {'href="#" data-page="crm"' if preview else 'href="crm.html"'}>Revenue and CRM</a></li>
        <li><a {'href="#" data-page="modules"' if preview else 'href="modules.html"'}>Governance</a></li>
      </ul></div>
      <div><h5>Company</h5><ul>{comp}</ul></div>
      <div><h5>Get in touch</h5><ul>
        <li><a href="mailto:{EMAIL}">{EMAIL}</a></li>
        <li><a href="mailto:{EMAIL_INV}">{EMAIL_INV}</a></li>
        <li><a href="tel:{PHONE.replace(' ', '')}">{PHONE}</a></li>
      </ul></div>
    </div>
    <div class="ftr-btm">
      <div>&copy; 2026 {COMPANY}. All rights reserved.</div>
      <div>Lagos, Nigeria</div>
    </div>
  </div>
</footer>"""


SCRIPT = """
<script>
(function(){
  var b=document.getElementById("burger"), m=document.getElementById("mnav");
  if(b&&m){b.addEventListener("click",function(){
    var o=m.classList.toggle("open");
    b.classList.toggle("x",o);
    b.setAttribute("aria-expanded",o?"true":"false");
    b.setAttribute("aria-label",o?"Close menu":"Open menu");
  });}

  /* ── Header on scroll ───────────────────────────────────────────────
     Three behaviours: it compacts and gains a shadow once you leave the top,
     it slides away when you scroll down and returns the moment you scroll up,
     and a thin bar tracks how far through the page you are. */
  var hdr=document.querySelector(".hdr"), bar=document.getElementById("hdrBar");
  var last=0, ticking=false;
  var still=window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function onScroll(){
    var y=window.pageYOffset||document.documentElement.scrollTop||0;
    if(y<0) y=0;
    hdr.classList.toggle("scrolled", y>16);

    /* Never retract while the mobile menu is open, or the menu goes with it. */
    var menuOpen = m && m.classList.contains("open");
    if(!still && !menuOpen){
      if(y>260 && y>last+5) hdr.classList.add("up");
      else if(y<last-5 || y<=260) hdr.classList.remove("up");
    } else {
      hdr.classList.remove("up");
    }

    if(bar){
      var d=document.documentElement;
      var max=d.scrollHeight-d.clientHeight;
      bar.style.transform="scaleX("+(max>0?Math.min(y/max,1):0)+")";
    }
    last=y; ticking=false;
  }
  if(hdr){
    window.addEventListener("scroll",function(){
      if(!ticking){ ticking=true; window.requestAnimationFrame(onScroll); }
    },{passive:true});
    window.addEventListener("resize",onScroll,{passive:true});
    onScroll();
  }

  /* ── Reveal on arrival ──────────────────────────────────────────────
     Cards fade up as you reach them instead of landing as one wall. The
     stagger is capped so a filter showing twenty eight cards never leaves
     the last one waiting seconds to appear. */
  var reveals=document.querySelectorAll(".reveal");
  function showAll(){ reveals.forEach(function(el){ el.classList.add("in"); }); }
  if(reveals.length){
    if(still || !("IntersectionObserver" in window)){
      showAll();
    } else {
      var io=new IntersectionObserver(function(entries){
        entries.forEach(function(e){
          if(!e.isIntersecting) return;
          var sibs=Array.prototype.slice.call(e.target.parentNode.children);
          var i=sibs.indexOf(e.target);
          e.target.style.transitionDelay=Math.min(i,8)*55+"ms";
          e.target.classList.add("in");
          io.unobserve(e.target);
        });
      },{rootMargin:"0px 0px -40px 0px",threshold:.08});
      reveals.forEach(function(el){ io.observe(el); });
    }
  }

  /* ── Module explorer ────────────────────────────────────────────────
     One module open at a time, with the frame on the right following the
     selection. Everything it needs is on the button's data attributes, so
     there is no module list duplicated in JavaScript. */
  var exp=document.getElementById("explorer");
  if(exp){
    var expTitle=document.getElementById("expTitle");
    var expCrumb=document.getElementById("expCrumb");
    var pills=exp.querySelectorAll(".tp");
    var mocks=exp.querySelectorAll(".exp-mock");
    var order=["core","ops","ent"];

    function pick(btn){
      exp.querySelectorAll(".exp-item").forEach(function(b){
        var on=(b===btn);
        b.classList.toggle("on",on);
        b.setAttribute("aria-expanded",on?"true":"false");
      });
      expTitle.textContent=btn.getAttribute("data-name");
      expCrumb.textContent=btn.getAttribute("data-famlabel");

      var lo=order.indexOf(btn.getAttribute("data-tier"));
      pills.forEach(function(p){
        p.classList.toggle("in", order.indexOf(p.getAttribute("data-t"))>=lo);
      });

      var nm=btn.getAttribute("data-name");
      mocks.forEach(function(m){
        m.classList.toggle("on", m.getAttribute("data-mod")===nm);
      });
    }

    exp.querySelectorAll(".exp-item").forEach(function(b){
      b.addEventListener("click",function(){ pick(b); });
    });
    var first=exp.querySelector(".exp-item.on")||exp.querySelector(".exp-item");
    if(first) pick(first);
  }

  /* ── Module family filter ───────────────────────────────────────────
     Hiding with a class rather than an inline style keeps the transition,
     and the note above the grid explains the family you just picked. */
  var chips=document.querySelectorAll(".chip[data-fam]");
  var note=document.getElementById("famNote");
  if(chips.length){
    chips.forEach(function(c){
      c.addEventListener("click",function(){
        var f=c.getAttribute("data-fam");
        chips.forEach(function(x){x.classList.toggle("on",x===c);});

        document.querySelectorAll(".exp-group").forEach(function(g){
          g.classList.toggle("hide", !(f==="all"||g.getAttribute("data-in")===f));
        });
        /* If the filter hid whatever was open, open the first one still showing
           so the frame never describes a module you can no longer see. */
        if(exp){
          var cur=exp.querySelector(".exp-item.on");
          if(!cur||cur.closest(".exp-group").classList.contains("hide")){
            var next=exp.querySelector(".exp-group:not(.hide) .exp-item");
            if(next) next.click();
          }
        }

        if(note){
          var txt=note.getAttribute("data-"+f);
          if(txt && !still){
            note.classList.add("swap");
            setTimeout(function(){ note.textContent=txt; note.classList.remove("swap"); },220);
          } else if(txt){
            note.textContent=txt;
          }
        }
      });
    });
  }

  /* ── Numbers that count up ──────────────────────────────────────────
     A figure sitting still reads as a label. The same figure arriving at
     its value reads as a measurement, which is what these are. The
     original text is kept on the node, so the animation can never leave a
     half counted number behind if it is interrupted. */
  function countUp(el){
    var raw = el.getAttribute("data-n");
    if(raw === null){ raw = el.textContent; el.setAttribute("data-n", raw); }
    var m = raw.match(/^(\\D*?)([\\d,]+(?:\\.\\d+)?)(.*)$/);
    if(!m){ return; }
    var pre = m[1], body = m[2], post = m[3];
    var target = parseFloat(body.replace(/,/g, ""));
    if(!isFinite(target)) return;
    var dp = (body.split(".")[1] || "").length;
    var grouped = body.indexOf(",") > -1;
    el.classList.add("count");

    /* Under a second and a half, or it stops being a flourish and starts
       being something the reader is waiting for. */
    var dur = 1100, t0 = 0;
    function frame(ts){
      if(!t0) t0 = ts;
      var p = Math.min((ts - t0) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      var v = (target * eased).toFixed(dp);
      if(grouped) v = (+v).toLocaleString("en-US", {
        minimumFractionDigits: dp, maximumFractionDigits: dp });
      el.textContent = pre + v + post;
      if(p < 1) requestAnimationFrame(frame);
      else el.textContent = raw;
    }
    requestAnimationFrame(frame);
  }

  var figures = document.querySelectorAll(".stat b, .mini b, .pb-fact b");
  if(figures.length && !still && "IntersectionObserver" in window){
    var fio = new IntersectionObserver(function(es){
      es.forEach(function(e){
        if(!e.isIntersecting) return;
        countUp(e.target);
        fio.unobserve(e.target);
      });
    }, {threshold:.6});
    figures.forEach(function(el){ fio.observe(el); });
  }

  /* ── The signature chain signs itself ───────────────────────────────
     The rows arrive in the order a real request collects its signatures.
     It is the one piece of motion on the page that is worth more than
     decoration, which is exactly why the same table is readable in full
     the instant it lands for anyone who has motion turned off. */
  var seqs = document.querySelectorAll(".seq");
  if(seqs.length){
    if(still || !("IntersectionObserver" in window)){
      seqs.forEach(function(s){ s.classList.add("go"); });
    } else {
      var sio = new IntersectionObserver(function(es){
        es.forEach(function(e){
          if(!e.isIntersecting) return;
          e.target.classList.add("go");
          sio.unobserve(e.target);
        });
      }, {threshold:.25});
      seqs.forEach(function(s){ sio.observe(s); });
    }
  }

  /* ── Photographs drift as you pass them ─────────────────────────────
     Bound to the scroll handler already running rather than a second
     listener, and written as a transform so it never triggers layout. */
  var plx = Array.prototype.slice.call(document.querySelectorAll(".plx"));
  function parallax(){
    if(still || !plx.length) return;
    var vh = window.innerHeight || 800;
    plx.forEach(function(el){
      var r = el.parentNode.getBoundingClientRect();
      if(r.bottom < -80 || r.top > vh + 80) return;
      /* -1 well below the fold, +1 well above it. */
      var t = ((vh - r.top) / (vh + r.height)) * 2 - 1;
      el.style.transform = "translate3d(0," + (t * -5.5).toFixed(2) + "%,0)";
    });
  }
  if(plx.length && !still){
    window.addEventListener("scroll", function(){
      if(!ticking){ ticking = true; requestAnimationFrame(function(){
        parallax(); ticking = false; }); }
    }, {passive:true});
    window.addEventListener("resize", parallax, {passive:true});
    parallax();
  }

  /* ── The hero mockup follows the pointer ────────────────────────────
     Two degrees, no more. Enough that the screenshot reads as an object
     held in front of you, little enough that nobody notices it happening.
     Touch pointers are excluded: there is no hover there to justify it,
     and the handler would only fire on a tap. */
  var tilt = document.querySelector(".tilt");
  var fine = window.matchMedia && window.matchMedia("(hover:hover) and (pointer:fine)").matches;
  if(tilt && fine && !still){
    var inner = tilt.querySelector(".tilt-in");
    var pending = false, px = 0, py = 0;
    tilt.addEventListener("mousemove", function(e){
      var r = tilt.getBoundingClientRect();
      px = (e.clientX - r.left) / r.width - .5;
      py = (e.clientY - r.top) / r.height - .5;
      tilt.classList.add("live-tilt");
      if(pending) return;
      pending = true;
      requestAnimationFrame(function(){
        inner.style.transform =
          "rotateY(" + (px * 4).toFixed(2) + "deg) rotateX(" +
          (-py * 2.6).toFixed(2) + "deg) translateZ(0)";
        pending = false;
      });
    }, {passive:true});
    tilt.addEventListener("mouseleave", function(){
      tilt.classList.remove("live-tilt");
      inner.style.transform = "";
    });
  }
})();
</script>"""

PREVIEW_SCRIPT = """
<script>
(function(){
  var pages=document.querySelectorAll(".page");
  function go(slug){
    pages.forEach(function(p){p.hidden = (p.id !== "page-"+slug);});
    document.querySelectorAll("[data-page]").forEach(function(a){
      a.classList.toggle("on", a.getAttribute("data-page")===slug && a.closest(".nav"));
    });
    window.scrollTo({top:0,behavior:"instant"});
    var mn=document.getElementById("mnav"); if(mn) mn.classList.remove("open");
  }
  document.addEventListener("click",function(e){
    var a=e.target.closest("[data-page]");
    if(!a) return;
    e.preventDefault();
    go(a.getAttribute("data-page"));
  });
  go("index");
})();
</script>"""


# Family keys on the module cards, in the order they should appear in a form.
FAMILIES = [
    ("spend",   "Spend and approvals"),
    ("people",  "People"),
    ("revenue", "Revenue"),
    ("ops",     "Operations"),
    ("gov",     "Governance"),
]

# The icon each family wears wherever it is named, so the home page grid, the
# Modules hero and the mega menu never disagree about which glyph means what.
FAM_ICONS = {"spend": "wallet", "people": "users", "revenue": "target",
             "ops": "layers", "gov": "shield"}


def family_chips():
    """The glass chips in the Modules page hero, counted from the catalogue.

    The module count is hand-maintained in prose in several places and has
    shipped wrong before, so anything that can be counted is counted here
    rather than typed into the page.
    """
    by_fam = modules_by_family()
    out = []
    for key, label in FAMILIES:
        n = len(by_fam.get(key, []))
        if not n:
            continue
        out.append(f'<span class="hchip"><svg><use href="#i-{FAM_ICONS[key]}"/></svg>'
                   f'{label} <b>{n}</b></span>')
    return "\n      ".join(out)


def module_options():
    """Build the contact form's module list from the module cards themselves,
    so the form can never list a module the Modules page does not, or miss one."""
    by_fam = modules_by_family()

    out = ['<option selected>The whole system</option>',
           '<option>Not sure yet, please advise</option>']
    for key, label in FAMILIES:
        if key not in by_fam:
            continue
        out.append(f'<optgroup label="{label}">')
        out += [f"<option>{n}</option>" for n in by_fam[key]]
        out.append("</optgroup>")
    return "\n                ".join(out)


# ── The module catalogue ──────────────────────────────────────────────────────
# The single source of truth. The Modules page, the mega menu, the contact
# form's dropdown and the pricing comparison all read from here, so a module
# added once shows up in all four. This data used to be scraped back out of
# the page markup with a regex, which broke the moment a card gained a class.
M = collections.namedtuple("M", "fam icon name tier desc")

MODULES = [
    M("spend", "doc", "Requisitions", "core",
      "Every request carries its site, its budget line and its full signature history. Returned requests carry the reason back to the raiser, never a silent rejection."),
    M("spend", "cart", "Procurement and vendor quotes", "ops",
      "Where a site's chain includes a Procurement Officer, a line item with fewer than two vendor quotes blocks the whole requisition from advancing."),
    M("spend", "wallet", "Site budgets", "ops",
      "Approved spend commits against its site before money moves. Approving past a ceiling is allowed, but it notifies the Managing Director automatically."),
    M("spend", "build", "Implementation tracking", "ops",
      "Opens the moment the CFO releases payment. A milestone needs photographic or documentary evidence, and a rejected one reopens the original spend."),
    M("people", "cal", "Leave", "core",
      "Nightly accrual, live balances and a two stage approval that stops at the Executive Director. HR sees every application read only, by policy."),
    M("people", "users", "Employee lifecycle", "ops",
      "Onboarding to exit with documents, confirmation, disciplinary record and deactivation. Account status stays separate from employment status."),
    M("people", "award", "Appraisals", "core",
      "Self assessment, supervisor scoring and a Managing Director verdict on one form, covering confirmation, promotion and salary increment."),
    M("people", "clock", "Attendance and policies", "ops",
      "Daily presence against the published holiday calendar. Leave is resolved first, so a person on approved absence is never marked absent."),
    M("people", "case", "Recruitment and job portal", "ent",
      "Publish a role, collect applications on a public portal, shortlist and interview in one place. Everything after the application stays inside your permissions."),
    M("people", "mail", "Offer letters", "ent",
      "Generated from the approved role and grade, issued for signature and tracked to acceptance. An accepted offer creates the employee record automatically."),
    M("people", "mega", "Staff broadcasts", "ops",
      "HR notices, policy nuggets and company announcements by email, push and in app sticker, with delivery tracked per person."),
    M("revenue", "target", "CRM and leads", "ent",
      "Capture, qualify and convert with duplicate detection on the full international phone number. Leads from paid social arrive by signed webhook and route themselves."),
    M("revenue", "mega", "Guided calling", "ent",
      "The queue serves one lead at a time and the script branches on what the person actually said. No call can end without a dated next step."),
    M("revenue", "layers", "Deals and pipeline", "ent",
      "Stages carry their own odds and every move is kept, so stuck deals and slow stages are visible. A deal lost always records why."),
    M("revenue", "case", "Market demand", "ent",
      "Locations, property types and budgets captured during calls, ranked against what you have available. Demand you cannot meet is counted too."),
    M("revenue", "wallet", "Revenue outlook", "ent",
      "Signed money with real instalment dates, kept separate from weighted forecast. Leadership reads both and the two are never added together."),
    M("revenue", "zap", "Sales activities", "ent",
      "Register an event, raise its marketing spend, then file the report that justifies it. No further budget is released while a report is outstanding."),
    M("revenue", "chart", "Sale commissions", "ent",
      "A won lead becomes a commission request that walks its own approval chain to the CFO for payment. Rates are configuration, changed once and applied everywhere."),
    M("revenue", "db", "Client portfolios", "ent",
      "What each client bought, what they have paid and what is still outstanding, with handover and title documents on the same record."),
    M("ops", "doc", "Work reports", "core",
      "Daily and weekly reports route to the supervisor and escalate when late. Weekly rolls into monthly, quarterly and yearly without re entering a line."),
    M("ops", "layers", "Monthly performance", "ops",
      "Heads of department declare projections, blockers and the support they need. An unresolved blocker carries forward into next month automatically."),
    M("ops", "laptop", "IT devices and CUG lines", "ops",
      "Assignment, acknowledgement, maintenance history and closed user group control. An unacknowledged device stays flagged until the holder signs for it."),
    M("ops", "car", "Pool car booking", "ops",
      "Book a vehicle and driver against a trip. Mileage and fuel close out on return, so a trip cannot be quietly left open."),
    M("ops", "screen", "Management meeting", "ent",
      "Any format uploaded becomes one uniform deck, presented in a synchronised boardroom where every screen follows the chair."),
    M("gov", "shield", "Audit log", "core",
      "Every view, decision and override in one immutable trail. Page views are logged as well as actions, so who looked is answerable too."),
    M("gov", "lock", "Root console", "ent",
      "Break glass administration behind a PIN, rate limited and logged against itself. Anything that writes needs confirmation typed by hand."),
    M("gov", "eye", "Oversight analytics", "ops",
      "Read only cross department reporting for the Executive Director and Managing Director. Leadership reads everything and approves nothing here."),
    M("gov", "share", "Social media monitor", "ent",
      "Connected business accounts, reach and engagement in one view, with access tokens encrypted at rest and never readable off the server."),
]

TIER_ORDER = ["core", "ops", "ent"]
FAM_TITLES = {"spend": "Spend and approvals", "people": "People",
              "revenue": "Revenue and CRM", "ops": "Operations", "gov": "Governance"}


def tier_table():
    """One accordion per family, with a tick per tier, straight from MODULES."""
    tick = '<svg class="tk"><use href="#i-check"/></svg>'
    out = []
    for fam, title in FAM_TITLES.items():
        mods = [m for m in MODULES if m.fam == fam]
        if not mods:
            continue
        rows = ""
        for m in mods:
            lo = TIER_ORDER.index(m.tier)
            cells = "".join(
                f"<td>{tick}</td>" if i >= lo else '<td class="no">Add on</td>'
                for i in range(3))
            rows += f"<tr><td><b>{m.name}</b></td>{cells}</tr>"
        out.append(
            f'<details class="cmp-group"{" open" if fam == "spend" else ""}>'
            f"<summary>{title} <span>{len(mods)} modules</span></summary>"
            f'<div class="cmp-scroll"><table class="cmp">'
            f"<thead><tr><th></th><th>Core</th><th>Operations</th><th>Enterprise</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></div></details>")
    return "\n".join(out)


# ── One illustrative frame per module ────────────────────────────────────
# Held as data, not markup: (heading, badge, mini stats, rows). A cell is a
# plain string, "n:" for the emphasised first column, "m:" for a figure, or
# "b:<kind>:<text>" for a badge. Every name and number here is invented; see
# the style rules about never putting real client data in a demo.
NAIRA = "&#8358;"

MOCKS = {
 # ── Spend and approvals ──
 "Requisitions": ("Signature chain", ("warn", "CFO review"), [], [
   ("n:Raised", "Adaeze Nwankwo", "b:ok:Signed"),
   ("n:Supervisor", "Bayo Fashola", "b:ok:Signed"),
   ("n:Executive Director", "Chiamaka Eze", "b:ok:Signed"),
   ("n:CFO", "Damilola Ajayi", "b:warn:Reviewing")]),
 "Procurement and vendor quotes": ("Line items", ("err", "Blocked"), [], [
   ("n:Perimeter fencing", "3 quotes", "b:ok:Cleared"),
   ("n:Survey drone", "1 quote", "b:err:Needs 2"),
   ("n:Generator parts", "2 quotes", "b:ok:Cleared"),
   ("n:Site signage", "0 quotes", "b:err:Needs 2")]),
 "Site budgets": ("Committed against budget", ("warn", "1 over"), [], [
   ("n:Harmattan Heights", "m:" + NAIRA + "82m of 100m", "b:ok:82%"),
   ("n:Cedarline Court", "m:" + NAIRA + "47m of 60m", "b:ok:78%"),
   ("n:Meridian Motors", "m:" + NAIRA + "31m of 28m", "b:err:MD notified")]),
 "Implementation tracking": ("Milestones", ("info", "Evidence required"), [], [
   ("n:Site cleared", "Photos attached", "b:ok:Accepted"),
   ("n:Foundation poured", "Photos attached", "b:ok:Accepted"),
   ("n:Block work", "No evidence", "b:warn:Awaiting"),
   ("n:Roofing", "Photos attached", "b:err:Rejected")]),

 # ── People ──
 "Leave": ("Entitlement", ("ok", "Approved"), [("14", "Days left"), ("6", "Taken"), ("20", "Accrued")], [
   ("n:Applied", "Adaeze Nwankwo, 4 days", "b:ok:Signed"),
   ("n:Supervisor", "Bayo Fashola", "b:ok:Signed"),
   ("n:Executive Director", "Chiamaka Eze", "b:ok:Final")]),
 "Employee lifecycle": ("Record", ("ok", "Confirmed"), [], [
   ("n:Onboarded", "12 March", "b:ok:Complete"),
   ("n:Documents", "6 of 6 filed", "b:ok:Complete"),
   ("n:Confirmation", "After 6 months", "b:ok:Confirmed"),
   ("n:Disciplinary", "None on record", "b:mute:Clear")]),
 "Appraisals": ("Cycle", ("info", "With the MD"), [("4.2", "Overall"), ("3", "Of 4 done"), ("H1", "Period")], [
   ("n:Self assessment", "Adaeze Nwankwo", "b:ok:Submitted"),
   ("n:Supervisor score", "Bayo Fashola", "b:ok:Scored"),
   ("n:MD verdict", "Confirmation and increment", "b:warn:Pending")]),
 "Attendance and policies": ("Today", ("ok", "Reconciled"), [("41", "Present"), ("4", "On leave"), ("2", "Absent")], [
   ("n:Adaeze Nwankwo", "08:42", "b:ok:Present"),
   ("n:Bayo Fashola", "Approved absence", "b:info:On leave"),
   ("n:Uche Madu", "No record", "b:err:Absent")]),
 "Recruitment and job portal": ("Open role", ("info", "Shortlisting"), [("38", "Applied"), ("6", "Shortlisted"), ("2", "Interviewed")], [
   ("n:Site Engineer", "Posted 4 days ago", "b:ok:Live"),
   ("n:Sales Consultant", "Posted 2 weeks ago", "b:warn:Closing"),
   ("n:Accounts Officer", "Draft", "b:mute:Unposted")]),
 "Offer letters": ("Issued", ("warn", "Awaiting signature"), [], [
   ("n:Ifeoma Balogun", "Site Engineer", "b:ok:Accepted"),
   ("n:Tari Georgewill", "Sales Consultant", "b:warn:Sent"),
   ("n:Uche Madu", "Accounts Officer", "b:err:Declined")]),
 "Staff broadcasts": ("Delivery", ("ok", "Sent"), [("47", "Recipients"), ("44", "Opened"), ("3", "Unread")], [
   ("n:Email", "47 delivered", "b:ok:Complete"),
   ("n:Push", "41 delivered", "b:ok:Complete"),
   ("n:In app sticker", "Shown on sign in", "b:ok:Active")]),

 # ── Revenue and CRM ──
 "CRM and leads": ("Intake", ("info", "Deduplicated"), [("146", "Open"), ("23", "This week"), ("4", "Merged")], [
   ("n:Sade Martins", "Paid social", "b:ok:Qualified"),
   ("n:Tari Georgewill", "Walk in", "b:warn:New"),
   ("n:Northgate Ltd", "Referral", "b:ok:Qualified"),
   ("n:Duplicate number", "Matched on +234", "b:mute:Merged")]),
 "Guided calling": ("Next in queue", ("warn", "Promised callback"), [("1", "Served"), ("3rd", "Attempt"), ("14", "Day ladder")], [
   ("n:Lead", "Ifeoma Balogun", "b:ok:Qualified"),
   ("n:Promised", "Today, 2:00pm", "b:warn:Due"),
   ("n:Last attempt", "No answer, 11:00am", "b:mute:Logged"),
   ("n:Next if missed", "Friday, 4:00pm", "b:info:Scheduled")]),
 "Deals and pipeline": ("Stages", ("ok", "22% win rate"), [("146", "Open"), (NAIRA + "318m", "Weighted"), ("9", "Stuck")], [
   ("n:Sade Martins", "m:" + NAIRA + "68,000,000", "b:ok:Negotiation 75%"),
   ("n:Northgate Ltd", "m:" + NAIRA + "120,000,000", "b:warn:Proposal 50%"),
   ("n:Uche Madu", "m:" + NAIRA + "34,000,000", "b:mute:Qualification 10%")]),
 "Market demand": ("Requested against stock", ("err", "Unmet demand"), [], [
   ("n:Lekki and Ajah", "62 asked", "b:ok:We have stock"),
   ("n:Ikoyi", "38 asked", "b:err:No stock"),
   ("n:Outside Lagos", "21 asked", "b:err:No stock"),
   ("n:Undecided", "17 asked", "b:mute:Nurturing")]),
 "Revenue outlook": ("Money", ("ok", "Committed"), [(NAIRA + "418m", "Signed"), (NAIRA + "96m", "Due 30 days"), (NAIRA + "12m", "Overdue")], [
   ("n:Meridian Group", "Instalment 3 of 6", "b:ok:Paid"),
   ("n:Cedarline Court", "Instalment 2 of 4", "b:warn:Due Friday"),
   ("n:Harmattan Heights", "Instalment 1 of 8", "b:err:Overdue")]),
 "Sales activities": ("Event", ("err", "Report outstanding"), [], [
   ("n:Open day, Lekki", "m:" + NAIRA + "1,800,000", "b:ok:Report filed"),
   ("n:Radio campaign", "m:" + NAIRA + "2,400,000", "b:err:No report"),
   ("n:Estate tour", "Budget requested", "b:mute:Held")]),
 "Sale commissions": ("Commission chain", ("info", "With the CFO"), [], [
   ("n:Raised", "Adaeze Nwankwo", "b:ok:Signed"),
   ("n:Sales Manager", "Bayo Fashola", "b:ok:Signed"),
   ("n:Executive Director", "Chiamaka Eze", "b:ok:Signed"),
   ("n:CFO, payment", "m:" + NAIRA + "1,240,000", "b:warn:Releasing")]),
 "Client portfolios": ("Client record", ("warn", "Outstanding"), [], [
   ("n:Bought", "Harmattan Heights, 3 bed", "b:ok:Allocated"),
   ("n:Paid", "m:" + NAIRA + "52,000,000", "b:ok:Cleared"),
   ("n:Outstanding", "m:" + NAIRA + "16,000,000", "b:warn:2 instalments"),
   ("n:Title documents", "Handover pack", "b:ok:On file")]),

 # ── Operations ──
 "Work reports": ("This week", ("warn", "2 late"), [], [
   ("n:Projects", "Filed Monday", "b:ok:On time"),
   ("n:Facilities", "3 days late", "b:err:Escalated"),
   ("n:Sales", "Filed Monday", "b:ok:On time"),
   ("n:Rolls into", "Monthly, then quarterly", "b:mute:Automatic")]),
 "Monthly performance": ("Declarations", ("warn", "Blocker carried"), [], [
   ("n:Projections", "5 of 6 heads filed", "b:ok:Filed"),
   ("n:Blockers", "Vendor lead times", "b:err:Carried forward"),
   ("n:Support asked", "2 extra site staff", "b:warn:With the ED")]),
 "IT devices and CUG lines": ("Assignment", ("warn", "Unacknowledged"), [("64", "Devices"), ("58", "Signed for"), ("12", "CUG lines")], [
   ("n:Laptop, Meridian", "Adaeze Nwankwo", "b:ok:Acknowledged"),
   ("n:Laptop, Cedarline", "Uche Madu", "b:err:Unsigned"),
   ("n:CUG line 0803", "Bayo Fashola", "b:ok:Active")]),
 "Pool car booking": ("Trip", ("ok", "Closed out"), [], [
   ("n:Vehicle", "Meridian Motors, Hilux", "b:ok:Returned"),
   ("n:Driver", "Uche Madu", "b:ok:Assigned"),
   ("n:Mileage", "218 km", "b:ok:Logged"),
   ("n:Fuel", "m:" + NAIRA + "34,000", "b:ok:Reconciled")]),
 "Management meeting": ("Boardroom", ("info", "Live"), [("14", "Slides"), ("9", "In the room"), ("1", "Chair")], [
   ("n:Uploaded", "Mixed formats", "b:ok:Normalised"),
   ("n:Deck", "One uniform deck", "b:ok:Ready"),
   ("n:Screens", "Following the chair", "b:info:Synced")]),

 # ── Governance ──
 "Audit log": ("Trail", ("mute", "Immutable"), [], [
   ("n:Viewed", "REQ-2026-0412", "Chiamaka Eze"),
   ("n:Approved", "REQ-2026-0412", "Damilola Ajayi"),
   ("n:Override", "Budget ceiling", "b:warn:Flagged"),
   ("n:Exported", "Payroll summary", "Ikenna Obi")]),
 "Root console": ("Break glass", ("err", "PIN required"), [], [
   ("n:Access", "PIN, rate limited", "b:warn:Challenged"),
   ("n:Confirmation", "Typed by hand", "b:err:Required"),
   ("n:Snapshot", "Table copied first", "b:ok:Taken"),
   ("n:Logged", "Against itself", "b:ok:Recorded")]),
 "Oversight analytics": ("Leadership view", ("mute", "Read only"), [("5", "Departments"), ("0", "Actions"), ("12", "Reports")], [
   ("n:Spend by site", "Rolling 90 days", "b:ok:Current"),
   ("n:Headcount", "By arm and grade", "b:ok:Current"),
   ("n:Approvals", "Median 3.2 days", "b:ok:Current")]),
 "Social media monitor": ("Connected accounts", ("ok", "Tokens encrypted"), [("3", "Accounts"), ("48k", "Reach"), ("6.1%", "Engagement")], [
   ("n:Instagram", "Business account", "b:ok:Connected"),
   ("n:Facebook", "Page linked", "b:ok:Connected"),
   ("n:Access tokens", "AES-GCM at rest", "b:mute:Never readable")]),
}


def _cell(c):
    if c.startswith("b:"):
        _, kind, txt = c.split(":", 2)
        return f'<td><span class="badge b-{kind}">{txt}</span></td>'
    if c.startswith("n:"):
        return f'<td class="n">{c[2:]}</td>'
    if c.startswith("m:"):
        return f'<td class="m">{c[2:]}</td>'
    return f"<td>{c}</td>"


def render_mock(name):
    """Build one module's frame body. Fails loudly rather than rendering an
    empty panel, which is the bug this replaced: five family panels meant
    every module in a family showed the same picture."""
    if name not in MOCKS:
        raise SystemExit(f"  ! No MOCKS entry for module {name!r}")
    heading, badge, minis, rows = MOCKS[name]
    b = f'<span class="badge b-{badge[0]}">{badge[1]}</span>' if badge else ""
    mini = ""
    if minis:
        mini = '<div class="mini">' + "".join(
            f"<div><b>{v}</b><span>{l}</span></div>" for v, l in minis) + "</div>"
    body = "".join("<tr>" + "".join(_cell(c) for c in r) + "</tr>" for r in rows)
    return (f'<div class="app-h"><h5>{heading}</h5>{b}</div>{mini}'
            f'<div class="t-scroll"><table class="t"><tbody>{body}</tbody></table></div>')


TIER_LABEL = {"core": "Core", "ops": "Operations", "ent": "Enterprise"}


def module_explorer():
    """Left: every module as an accordion row, grouped by family and filtered by
    the chips. Right: a frame that follows the selection. One description is
    visible at a time instead of twenty eight stacked on top of each other."""
    items = ""
    for fam, title in FAM_TITLES.items():
        mods = [m for m in MODULES if m.fam == fam]
        items += f'<div class="exp-group" data-in="{fam}"><h6>{title}</h6>'
        for m in mods:
            first = ' aria-expanded="true" class="exp-item on"' if not items.count("exp-item") else ' aria-expanded="false" class="exp-item"'
            items += (
                f'<button type="button"{first} data-in="{m.fam}" '
                f'data-name="{m.name}" data-famlabel="{title}" data-tier="{m.tier}">'
                f'<span class="exp-ic"><svg><use href="#i-{m.icon}"/></svg></span>'
                f'<span class="exp-name">{m.name}</span>'
                f'<svg class="exp-ch" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                f'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
                f'<polyline points="6 9 12 15 18 9"/></svg></button>'
                f'<div class="exp-body"><p>{m.desc}</p></div>')
        items += "</div>"

    pills = "".join(f'<span class="tp" data-t="{k}">{v}</span>' for k, v in TIER_LABEL.items())
    mocks = "".join(f'<div class="exp-mock" data-mod="{m.name}">{render_mock(m.name)}</div>'
                    for m in MODULES)
    return f"""<div class="exp-grid" id="explorer">
  <div class="exp-list">{items}</div>
  <div class="exp-side">
    <div class="shot exp-shot">
      <div class="shot-bar"><div class="shot-dots"><i></i><i></i><i></i></div>
        <span class="exp-crumb" id="expCrumb">Spend and approvals</span></div>
      <div class="shot-in">
        <h4 class="exp-title" id="expTitle">Requisitions</h4>
        <div class="exp-tiers"><span class="tp-l">Included from</span>{pills}</div>
        <div class="exp-mocks">{mocks}</div>
      </div>
    </div>
  </div>
</div>"""


# ── Structured data ───────────────────────────────────────────────────────
# What the page is, in the vocabulary search engines actually parse. This is
# the part that earns a rich result rather than a blue link, and unlike copy
# it cannot be written persuasively: every claim here has to be checkable
# against the page it sits on, or it is a manual action waiting to happen.
#
# Deliberately absent: aggregateRating and review. Inventing either is the
# fastest way to a structured data penalty, and there are no real ones yet.

# Page titles and descriptions carry the search terms; these are the terms
# each page genuinely serves. Nothing here names payroll, because there is
# no payroll module and ranking for a promise the product does not keep
# costs more in bounces than the position is worth.
BREADCRUMB = {
    "product": "How it works",
    "modules": "Modules",
    "crm": "CRM and guided calling",
    "pricing": "Pricing",
    "investors": "Investors",
    "contact": "Book a demo",
    "insights": "News and insights",
}


def _org():
    return {
        "@type": "Organization",
        "@id": f"{DOMAIN}/#organization",
        "name": COMPANY,
        "url": f"{DOMAIN}/",
        "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/og.jpg"},
        "email": EMAIL,
        "address": {
            "@type": "PostalAddress",
            "addressLocality": CITY,
            "addressRegion": REGION,
            "addressCountry": COUNTRY,
        },
        "areaServed": {"@type": "Country", "name": "Nigeria"},
    }


def _software():
    """The product itself. `applicationCategory` is what puts it in the
    business-software bucket rather than being guessed from prose."""
    return {
        "@type": "SoftwareApplication",
        "@id": f"{DOMAIN}/#software",
        "name": COMPANY,
        "applicationCategory": "BusinessApplication",
        "applicationSubCategory": "Human Resources Management Software",
        "operatingSystem": "Web browser, iOS, Android",
        "url": f"{DOMAIN}/",
        "publisher": {"@id": f"{DOMAIN}/#organization"},
        "areaServed": {"@type": "Country", "name": "Nigeria"},
        "featureList": [
            "Leave management and entitlement accrual",
            "Requisition and procurement approval workflow",
            "Staff appraisals and performance reviews",
            "Attendance and employee lifecycle records",
            "Recruitment, job portal and offer letters",
            "CRM, guided calling and sales commissions",
            "Audit trail on every view and decision",
        ],
        # A real offer with no price is honest and still parseable: it says
        # the thing is sold and quoted, which is exactly the case.
        "offers": {
            "@type": "Offer",
            "priceCurrency": "NGN",
            "availability": "https://schema.org/InStock",
            "url": f"{DOMAIN}/pricing.html",
            "description": "Priced on headcount and the modules switched on. "
                           "Written quote within one working day.",
        },
    }


# Scoped to the `.faq` container on purpose. The pricing page's comparison
# table is built from <details> too, and an unscoped pattern swallowed the
# whole tier table into the first "question".
FAQ_BLOCK = re.compile(r'<div class="faq[^"]*"[^>]*>(.*?)</div>\s*</div>', re.S)
FAQ_RE = re.compile(
    r"<details[^>]*>\s*<summary>(.*?)</summary>\s*<p>(.*?)</p>", re.S)


def _faqs(body):
    """Lift the FAQ block straight out of the page.

    Read from the rendered markup rather than kept in a second list, because
    a FAQPage whose answers have drifted from the visible ones is the exact
    thing Google issues manual actions for.
    """
    out = []
    pairs = []
    for block in FAQ_BLOCK.findall(body):
        pairs += FAQ_RE.findall(block)
    for q, a in pairs:
        q = re.sub(r"<[^>]+>", "", q).strip()
        a = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", a)).strip()
        if q and a:
            out.append({"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": a}})
    return out


def json_ld(slug, meta, body):
    graph = [_org()]
    url = f"{DOMAIN}/{'' if slug == 'index' else slug + '.html'}"

    if slug == "index":
        graph.append({
            "@type": "WebSite",
            "@id": f"{DOMAIN}/#website",
            "url": f"{DOMAIN}/",
            "name": COMPANY,
            "inLanguage": LOCALE,
            "publisher": {"@id": f"{DOMAIN}/#organization"},
        })
    if slug in ("index", "product", "modules", "pricing"):
        graph.append(_software())

    if slug not in ("index",) and slug in BREADCRUMB:
        graph.append({
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home",
                 "item": f"{DOMAIN}/"},
                {"@type": "ListItem", "position": 2, "name": BREADCRUMB[slug],
                 "item": url},
            ],
        })

    faqs = _faqs(body)
    if faqs:
        graph.append({"@type": "FAQPage", "@id": f"{url}#faq",
                      "mainEntity": faqs})

    return ('<script type="application/ld+json">'
            + json.dumps({"@context": "https://schema.org", "@graph": graph},
                         separators=(",", ":"))
            + "</script>")


def parse(path):
    """Fragment header: <!-- title / desc / slug --> then the markup."""
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"\s*<!--(.*?)-->\s*(.*)", raw, re.S)
    meta, body = {}, raw
    if m:
        for line in m.group(1).strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        body = m.group(2)
    return meta, body


# ── Articles ──────────────────────────────────────────────────────────────
# Each file in src/insights/ carries the same header as a page, plus a date
# and a one line summary for the hub. They are published into a subfolder, so
# every relative URL in the shared header, footer, stylesheet link and photo
# srcset has to be lifted a level. That is done once, on the finished HTML,
# rather than by threading a prefix through every function that emits a path.
REL_ATTR = re.compile(r'(\s(?:href|src)=")(?!https?:|mailto:|tel:|#|/|data:)')
REL_SRCSET = re.compile(r'(\ssrcset=")([^"]+)(")')


def reroot(html, prefix="../"):
    """Article markup is written as if the page sat at the site root, and
    this lifts every relative URL by one level. Nothing upstream may write
    `../` itself, or it gets lifted twice and 404s."""
    html = REL_ATTR.sub(lambda m: m.group(1) + prefix, html)

    def fix_set(m):
        parts = []
        for cand in m.group(2).split(","):
            cand = cand.strip()
            if cand and not cand.startswith(("http", "/", "data:")):
                cand = prefix + cand
            parts.append(cand)
        return m.group(1) + ", ".join(parts) + m.group(3)

    return REL_SRCSET.sub(fix_set, html)


def read_articles():
    """Newest first. A missing date stops the build rather than sorting oddly."""
    arts = []
    if not INSIGHTS_DIR.exists():
        return arts
    for path in sorted(INSIGHTS_DIR.glob("*.html")):
        meta, body = parse(path)
        for key in ("title", "desc", "slug", "date", "summary", "heading"):
            if key not in meta:
                raise SystemExit(f"  ! {path.name} is missing '{key}:' in its header")
        meta["body"] = body
        arts.append(meta)
    arts.sort(key=lambda a: a["date"], reverse=True)
    return arts


def article_ld(a):
    url = f"{DOMAIN}/{INSIGHTS_OUT}/{a['slug']}.html"
    return ('<script type="application/ld+json">' + json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": a["heading"],
        "description": a["desc"],
        "datePublished": a["date"],
        "dateModified": a.get("updated", a["date"]),
        "inLanguage": LOCALE,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "author": {"@type": "Organization", "name": COMPANY, "url": f"{DOMAIN}/"},
        "publisher": {
            "@type": "Organization", "name": COMPANY,
            "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/og.jpg"},
        },
    }, separators=(",", ":")) + "</script>")


def pretty_date(iso):
    y, m, d = iso.split("-")
    months = ["January", "February", "March", "April", "May", "June", "July",
              "August", "September", "October", "November", "December"]
    return f"{int(d)} {months[int(m) - 1]} {y}"


def article_page(a, others):
    """One article, with a short list of the others underneath.

    The cross links are not decoration: a page with no route onward is a page
    search engines treat as a dead end, and a reader who finishes an article
    is the most likely person on the site to read a second one.
    """
    more = "".join(
        f'<a class="ins-more-item" href="{INSIGHTS_OUT}/{o["slug"]}.html">'
        f'<span class="ins-date">{pretty_date(o["date"])}</span>'
        f'<b>{o["heading"]}</b><p>{o["summary"]}</p></a>'
        for o in others[:3])
    return f"""
<article class="sec ins-article">
  <div class="wrap">
    <nav class="crumbs" aria-label="Breadcrumb">
      <a href="index.html">Home</a> <span>/</span>
      <a href="insights.html">Insights</a>
    </nav>
    <p class="ins-date">{pretty_date(a['date'])}</p>
    <h1 class="h1">{a['heading']}</h1>
    <p class="lead measure-w">{a['summary']}</p>
    <div class="ins-body">{a['body'].strip()}</div>

    <div class="ins-cta">
      <h2 class="h3">See it against your own approval chain</h2>
      <p>A forty minute walkthrough, configured live on the call.</p>
      <a class="btn btn-p btn-lg" href="contact.html">Book a demo</a>
    </div>
  </div>
</article>

<section class="sec-sm tint">
  <div class="wrap">
    <h2 class="h3" style="margin-bottom:24px;">More from SavidorHR</h2>
    <div class="ins-more">{more}</div>
  </div>
</section>
"""


def insights_hub(arts):
    cards = "".join(
        f'<a class="ins-card" href="{INSIGHTS_OUT}/{a["slug"]}.html">'
        f'<span class="ins-date">{pretty_date(a["date"])}</span>'
        f'<h2 class="h4">{a["heading"]}</h2><p>{a["summary"]}</p>'
        f'<span class="ins-read">Read it{ARROW_S}</span></a>'
        for a in arts)
    return f"""
<section class="phero band ondark navy-ph">
  <img data-photo="talking" class="navy-bg" sizes="100vw" data-eager>
  <div class="wrap rise">
    <span class="eyebrow">News and insights</span>
    <h1 class="h1">How Nigerian companies approve, hire and pay</h1>
    <p class="lead measure-w">
      Practical writing on approval chains, staff leave, procurement and
      choosing HR software in Nigeria. Written from what we see inside real
      companies, not from a keyword list.
    </p>
  </div>
</section>

<section class="sec">
  <div class="wrap">
    <div class="ins-grid">{cards}</div>
  </div>
</section>
"""


def document(meta, body, slug, ld=None):
    noindex = ('\n<meta name="robots" content="noindex,follow">'
               if meta.get("noindex") else "")
    return f"""<!doctype html>
<html lang="{LOCALE}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{JS_FLAG}
<title>{meta.get('title', COMPANY)}</title>
<meta name="description" content="{meta.get('desc', '')}">
<link rel="canonical" href="{DOMAIN}/{'' if slug == 'index' else slug + '.html'}">{noindex}
<meta name="theme-color" content="#2D60D0">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{COMPANY}">
<meta property="og:url" content="{DOMAIN}/{'' if slug == 'index' else slug + '.html'}">
<meta property="og:title" content="{meta.get('title', COMPANY)}">
<meta property="og:description" content="{meta.get('desc', '')}">
<meta property="og:image" content="{DOMAIN}/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{COMPANY}, HR and approval software for Nigerian companies">
<meta property="og:locale" content="en_NG">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{meta.get('title', COMPANY)}">
<meta name="twitter:description" content="{meta.get('desc', '')}">
<meta name="twitter:image" content="{DOMAIN}/og.jpg">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
{FONT_TAGS}
<link rel="stylesheet" href="{CSS_NAME}">
{ld if ld is not None else json_ld(slug, meta, body)}
</head>
<body>
{sprite()}
{header(slug, False)}
<main>
{body.strip()}
</main>
{footer(False)}
{SCRIPT}
</body>
</html>
"""


# ── Self-hosted webfonts ──────────────────────────────────────────────────────
# Built by tools/build_fonts.py and committed under src/fonts/. Loading them
# from Google cost two extra DNS and TLS handshakes, and the font URLs were not
# even known until that render-blocking stylesheet came back. Serving them from
# our own origin lets the HTML preload them on the first parse instead.
#
# Each file is fingerprinted for exactly the reason the stylesheet is: an
# unversioned asset behind a one year cache is how this site once served
# week-old CSS against fresh HTML and rendered unstyled.
FONTS = ["inter-latin", "inter-naira", "jakarta-latin", "jakarta-naira"]

# Only the two that carry actual text are preloaded, because those block first
# paint. The naira files are about 1KB each and the browser fetches them on
# demand through their unicode-range.
FONT_PRELOAD = ["inter-latin", "jakarta-latin"]


def install_fonts(css):
    """Publish src/fonts under hashed names and point the CSS at them.

    Returns the rewritten CSS and {name: published path}. Substitution happens
    before the stylesheet is hashed, so the CSS fingerprint covers the font
    URLs too and a font swap busts the stylesheet cache with it.
    """
    dest_dir = OUT / "fonts"
    dest_dir.mkdir(parents=True, exist_ok=True)

    published = {}
    for name in FONTS:
        src = SRC / "fonts" / f"{name}.woff2"
        if not src.exists():
            raise SystemExit(f"  ! missing {src}\n    Run tools/build_fonts.py")
        data = src.read_bytes()
        digest = hashlib.md5(data).hexdigest()[:10]
        out_name = f"{name}.{digest}.woff2"
        (dest_dir / out_name).write_bytes(data)
        published[name] = f"fonts/{out_name}"

    keep = {p.rsplit("/", 1)[-1] for p in published.values()}
    for stale in dest_dir.glob("*.woff2"):
        if stale.name not in keep:
            stale.unlink()

    for name, path in published.items():
        token = "__FONT_" + name.upper().replace("-", "_") + "__"
        if token not in css:
            raise SystemExit(f"  ! {token} is not referenced in src/site.css")
        css = css.replace(token, path)
    return css, published


# ── Photography ───────────────────────────────────────────────────────────────
# Regenerated by tools/build_images.py and committed under src/img/, the same
# arrangement as the fonts and for the same reason: nothing on a page should
# depend on a third party origin we do not control.
#
# Pages do not write out srcsets. They write one tag naming a photo:
#
#     <img data-photo="boardroom" sizes="100vw" class="ph-band">
#
# and this fills in the srcset, the intrinsic size, the lazy loading and the
# placeholder. Widths and file names live in the manifest, so adding a size to
# a photo changes no page.
IMAGES = {}


def install_images(manifest_path):
    """Publish src/img under hashed names, keyed by photo then width."""
    if not manifest_path.exists():
        raise SystemExit(f"  ! missing {manifest_path}\n"
                         f"    Run tools/build_images.py")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    dest_dir = OUT / "img"
    dest_dir.mkdir(parents=True, exist_ok=True)

    keep = set()
    for name, spec in manifest.items():
        for f in spec["files"]:
            src = manifest_path.parent / f["file"]
            if not src.exists():
                raise SystemExit(f"  ! manifest lists {f['file']}, which is "
                                 f"not in src/img. Run tools/build_images.py")
            data = src.read_bytes()
            digest = hashlib.md5(data).hexdigest()[:10]
            out_name = f"{src.stem}.{digest}.webp"
            (dest_dir / out_name).write_bytes(data)
            keep.add(out_name)
            f["url"] = f"img/{out_name}"

    for stale in dest_dir.glob("*.webp"):
        if stale.name not in keep:
            stale.unlink()
    return manifest


# Blocks that fade up as they are reached. Listed here rather than typed
# into every page: a rule about how the whole site behaves belongs in one
# place, and an element that should not do it says so with `no-reveal`.
REVEAL_AT = {"sec-head", "card", "stat", "tier", "quote", "cta", "ph-band",
             "feat-t", "mosaic", "form-card", "faq", "mod-card"}
CLASS_ATTR = re.compile(r'(<[a-z][a-z0-9]*\b[^>]*?\bclass=")([^"]*)(")')


def add_reveals(html):
    def one(m):
        classes = m.group(2).split()
        if ("reveal" in classes or "no-reveal" in classes
                or not REVEAL_AT.intersection(classes)):
            return m.group(0)
        return m.group(1) + " ".join(classes + ["reveal"]) + m.group(3)
    return CLASS_ATTR.sub(one, html)


# A marquee needs its list twice: the track slides exactly half its width,
# and the second copy is what is under the viewport as the first leaves it.
# Duplicating it here rather than in the page keeps one list to edit, and
# hides the copy from screen readers so the sectors are announced once.
MQ = re.compile(r"<!--MQ-->(.*?)<!--/MQ-->", re.S)


def fill_marquee(html):
    return MQ.sub(
        lambda m: (f'<div class="mq-set">{m.group(1)}</div>'
                   f'<div class="mq-set" aria-hidden="true">{m.group(1)}</div>'),
        html)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


ATTR = re.compile(r'([a-zA-Z-]+)(?:="([^"]*)")?')
IMG_TAG = re.compile(r"<img\b([^>]*?)/?>")


def expand_photos(html, slug=""):
    """Turn every <img data-photo="..."> into a full responsive tag.

    A name the manifest does not carry stops the build. A silently broken
    image is the kind of thing that ships and is noticed by a customer.
    """
    def one(m):
        attrs = {k: (v or "") for k, v in ATTR.findall(m.group(1))}
        name = attrs.pop("data-photo", "")
        if not name:
            return m.group(0)
        if name not in IMAGES:
            raise SystemExit(f"  ! {slug}: no photo named '{name}'. "
                             f"Known: {', '.join(sorted(IMAGES))}")

        spec = IMAGES[name]
        files = sorted(spec["files"], key=lambda f: f["w"])
        srcset = ", ".join(f"{f['url']} {f['w']}w" for f in files)

        # The hero photograph is wanted in the first paint, so it says so.
        # Everything else waits until it is nearly on screen.
        eager = "data-eager" in attrs
        attrs.pop("data-eager", None)

        cls = " ".join(x for x in ["ph", attrs.pop("class", "")] if x)
        alt = attrs.pop("alt", None)
        if alt is None:
            alt = spec["alt"]
        sizes = attrs.pop("sizes", "100vw")

        # The 20px placeholder sits behind the image as its own background, so
        # a slot shows the photograph's colours the moment the HTML lands and
        # never a white hole. Scaling it to cover is what blurs it; no filter
        # is involved, which matters because a filter would blur the real
        # image once it painted on top.
        style = (f"background-image:url({spec['lqip']})"
                 + (";" + attrs.pop("style") if attrs.get("style") else ""))
        attrs.pop("style", None)

        rest = "".join(f' {k}="{v}"' if v else f" {k}"
                       for k, v in attrs.items())

        # A navy background photo is never alone: it needs the scrim that
        # holds the headline's contrast. Pairing them here rather than in
        # every page means the two can never be separated by an edit.
        scrim = '<i class="navy-scrim" aria-hidden="true"></i>' if "navy-bg" in cls else ""

        return (
            f'<img class="{cls}" src="{files[-1]["url"]}" srcset="{srcset}" '
            f'sizes="{esc(sizes)}" width="{spec["w"]}" height="{spec["h"]}" '
            f'alt="{esc(alt)}" '
            + ('fetchpriority="high" decoding="async"' if eager
               else 'loading="lazy" decoding="async"')
            + f' style="{style}"{rest}>' + scrim)

    return IMG_TAG.sub(one, html)


def strip_css_comments(css):
    """Drop comments from the published stylesheet.

    src/site.css is commented heavily on purpose and stays that way; this only
    affects what ships. It is worth roughly a third of the compressed
    stylesheet, and the browser no longer parses past 25KB of prose.

    Whitespace is left alone. Collapsing it as well saved another 0.4KB
    compressed, which is not worth the chance of mangling a selector.
    """
    out = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    # A comment opener inside a quoted value would make the regex eat real
    # rules, so prove the declarations survived before shipping it.
    for anchor in (".hero{", ".band{", "@font-face{", ".phero{"):
        if anchor not in out.replace(" ", "").replace("\n", ""):
            raise SystemExit(f"  ! minifier lost {anchor}, shipping source instead")
    return re.sub(r"\n{2,}", "\n", out).strip() + "\n"


def main():
    OUT.mkdir(exist_ok=True)

    global IMAGES
    IMAGES = install_images(SRC / "img" / "manifest.json")
    shipped = sum(f["bytes"] for m in IMAGES.values() for f in m["files"])
    print(f"  published {len(IMAGES)} photos into site/img "
          f"({shipped / 1024:.0f}KB across every size)")

    css = (SRC / "site.css").read_text(encoding="utf-8")
    css, font_paths = install_fonts(css)
    css = strip_css_comments(css)

    global FONT_TAGS
    FONT_TAGS = "\n".join(
        f'<link rel="preload" href="{font_paths[n]}" as="font" '
        f'type="font/woff2" crossorigin>' for n in FONT_PRELOAD)

    # Fingerprint the stylesheet. Without this the filename never changes, so a
    # long Cache-Control header serves week-old CSS against freshly built HTML
    # and the site renders unstyled for anyone who visited before. The hash in
    # the name means the URL changes whenever the bytes do, which is what makes
    # the long cache safe rather than dangerous.
    global CSS_NAME
    digest = hashlib.md5(css.encode("utf-8")).hexdigest()[:10]
    CSS_NAME = f"site.{digest}.css"
    for stale in OUT.glob("site.*.css"):
        if stale.name != CSS_NAME:
            stale.unlink()
    (OUT / "site.css").unlink(missing_ok=True)
    (OUT / CSS_NAME).write_text(css, encoding="utf-8")
    (OUT / "favicon.svg").write_text(
        (SRC / "favicon.svg").read_text(encoding="utf-8"), encoding="utf-8")
    og = SRC / "og.jpg"
    if not og.exists():
        raise SystemExit("  ! src/og.jpg is missing. Run tools/build_og.py")
    (OUT / "og.jpg").write_bytes(og.read_bytes())

    order = ["index", "product", "modules", "crm", "pricing", "investors",
             "contact", "thanks"]
    frags = {}
    for slug in order:
        p = SRC / "pages" / f"{slug}.html"
        if not p.exists():
            print(f"  ! missing {p}")
            continue
        meta, body = parse(p)
        body = body.replace("<!--MODULE_OPTIONS-->", module_options())
        body = body.replace("<!--FAMILY_CHIPS-->", family_chips())
        body = body.replace("<!--MODULE_COUNT-->", str(len(MODULES)))
        body = body.replace("<!--TIER_TABLE-->", tier_table())
        body = body.replace("<!--MODULE_EXPLORER-->", module_explorer())
        body = expand_photos(body, slug)
        body = fill_marquee(body)
        body = add_reveals(body)
        frags[slug] = (meta, body)
        (OUT / f"{slug}.html").write_text(document(meta, body, slug), encoding="utf-8")
        print(f"  wrote site/{slug}.html")

    # ── News and insights ────────────────────────────────────────────
    arts = read_articles()
    if arts:
        hub_meta = {
            "title": "HR Insights for Nigerian Companies | SavidorHR",
            "desc": "Practical writing on approval chains, staff leave, "
                    "procurement and choosing HR software in Nigeria.",
        }
        hub_body = add_reveals(expand_photos(insights_hub(arts), "insights"))
        (OUT / "insights.html").write_text(
            document(hub_meta, hub_body, "insights"), encoding="utf-8")
        frags["insights"] = (hub_meta, hub_body)
        print("  wrote site/insights.html")

        (OUT / INSIGHTS_OUT).mkdir(exist_ok=True)
        for a in arts:
            others = [o for o in arts if o["slug"] != a["slug"]]
            body = add_reveals(article_page(a, others))
            html = document(a, body, f"{INSIGHTS_OUT}/{a['slug']}",
                            ld=article_ld(a))
            # Published a level down, so every relative URL moves with it.
            (OUT / INSIGHTS_OUT / f"{a['slug']}.html").write_text(
                reroot(html), encoding="utf-8")
            print(f"  wrote site/{INSIGHTS_OUT}/{a['slug']}.html")

    # Single-file preview: every page, switched client side.
    parts = []
    for slug, (meta, body) in frags.items():
        if slug in UNLISTED:
            continue
        parts.append(f'<div class="page" id="page-{slug}"{" hidden" if slug != "index" else ""}>'
                     f"<main>{body.strip()}</main></div>")
    # _preview.html sits at the repo root while the fonts are published inside
    # site/, so the relative URLs in the inlined CSS need one level added.
    preview_css = css.replace('url("fonts/', 'url("site/fonts/')
    # Same for the photographs, which the expanded tags reference by the
    # published path they have inside site/.
    parts = [re.sub(r"(?<![a-z/])img/([a-z0-9-]+\.[0-9a-f]{10}\.webp)",
                    r"site/img/\1", part) for part in parts]
    preview = (f"<title>{COMPANY}</title>\n{JS_FLAG}\n"
               f"<style>\n{preview_css}\n</style>\n{sprite()}\n{header('index', True)}\n"
               + "\n".join(parts) + f"\n{footer(True)}\n{SCRIPT}\n{PREVIEW_SCRIPT}\n")
    (HERE / "_preview.html").write_text(preview, encoding="utf-8")
    print(f"  wrote _preview.html ({len(preview):,} chars)")

    # Search engines. Regenerated from DOMAIN so they cannot drift.
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n", encoding="utf-8")
    urls = "".join(
        f"  <url><loc>{DOMAIN}/{'' if s == 'index' else s + '.html'}</loc>"
        f"<priority>{'1.0' if s == 'index' else '0.8'}</priority></url>\n"
        for s in order + ["insights"] if s in frags and s not in UNLISTED
    )
    # `lastmod` on the articles only. Claiming it for pages that did not
    # change is how a sitemap stops being believed.
    urls += "".join(
        f"  <url><loc>{DOMAIN}/{INSIGHTS_OUT}/{a['slug']}.html</loc>"
        f"<lastmod>{a.get('updated', a['date'])}</lastmod>"
        f"<priority>0.7</priority></url>\n"
        for a in arts
    )
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n", encoding="utf-8")
    print(f"  wrote site/robots.txt, site/sitemap.xml, site/favicon.svg, {CSS_NAME}")


if __name__ == "__main__":
    main()
