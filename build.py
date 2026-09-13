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
import re
import pathlib

HERE = pathlib.Path(__file__).parent
SRC = HERE / "src"
OUT = HERE / "site"

# ── Edit these when the domain and contact details are settled ────────────
DOMAIN = "https://savidorhr.com"
COMPANY = "SavidorHR"
EMAIL = "hello@savidorhr.com"
EMAIL_INV = "invest@savidorhr.com"
PHONE = "+234 000 000 0000"

# Reachable, but deliberately absent from the nav, the sitemap and the preview.
UNLISTED = {"thanks"}

NAV = [
    ("product", "Product", "product.html"),
    ("modules", "Modules", "modules.html"),
    ("pricing", "Pricing", "pricing.html"),
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


LOGO_MARK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"'
             ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
             '<polyline points="5 12.5 10 17.5 19 7.5"/></svg>')


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
    """The single source of truth for what modules exist: the cards themselves."""
    src = (SRC / "pages" / "modules.html").read_text(encoding="utf-8")
    cards = re.findall(r'<div class="mod-card[^"]*" data-in="(\w+)">.*?<h4>(.*?)</h4>', src, re.S)
    by_fam = {}
    for fam, name in cards:
        by_fam.setdefault(fam, []).append(name.strip())
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
    <a class="logo" {home}><span class="logo-m">{LOGO_MARK}</span>Savidor<i>HR</i></a>
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
        a("investors", "Investors", "investors.html"),
        a("contact", "Contact", "contact.html"),
        f'<li><a href="mailto:{EMAIL}">Support</a></li>',
    ])
    return f"""
<footer class="ftr">
  <div class="wrap">
    <div class="ftr-grid">
      <div class="ftr-about">
        <a class="logo" href="{'#' if preview else 'index.html'}"><span class="logo-m">{LOGO_MARK}</span>Savidor<i>HR</i></a>
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

  /* ── Module family filter ───────────────────────────────────────────
     Hiding with a class rather than an inline style keeps the transition,
     and the note above the grid explains the family you just picked. */
  var chips=document.querySelectorAll("[data-fam]");
  var note=document.getElementById("famNote");
  if(chips.length){
    chips.forEach(function(c){
      c.addEventListener("click",function(){
        var f=c.getAttribute("data-fam");
        chips.forEach(function(x){x.classList.toggle("on",x===c);});

        document.querySelectorAll("[data-in]").forEach(function(card){
          var show=(f==="all"||card.getAttribute("data-in")===f);
          card.classList.toggle("hide",!show);
          if(show && !card.classList.contains("in")) card.classList.add("in");
        });

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


# The lowest tier each module is included in. Everything above inherits it.
# Keys must match the module card headings exactly; build fails loudly if not.
TIER_MIN = {
    "Requisitions": "core", "Procurement and vendor quotes": "ops",
    "Site budgets": "ops", "Implementation tracking": "ops",
    "Leave": "core", "Employee lifecycle": "ops", "Appraisals": "core",
    "Attendance and policies": "ops", "Recruitment and job portal": "ent",
    "Offer letters": "ent", "Staff broadcasts": "ops",
    "CRM and leads": "ent", "Guided calling": "ent", "Deals and pipeline": "ent",
    "Market demand": "ent", "Revenue outlook": "ent", "Sales activities": "ent",
    "Sale commissions": "ent", "Client portfolios": "ent",
    "Work reports": "core", "Monthly performance": "ops",
    "IT devices and CUG lines": "ops", "Pool car booking": "ops",
    "Management meeting": "ent",
    "Audit log": "core", "Root console": "ent", "Oversight analytics": "ops",
    "Social media monitor": "ent",
}
TIER_ORDER = ["core", "ops", "ent"]
FAM_TITLES = {"spend": "Spend and approvals", "people": "People",
              "revenue": "Revenue and CRM", "ops": "Operations", "gov": "Governance"}


def tier_table():
    """One accordion per family, with a tick per tier. Generated from the module
    cards and TIER_MIN together, so the table cannot list a module that does not
    exist or quietly omit a new one."""
    by_fam = modules_by_family()
    known = {n for names in by_fam.values() for n in names}
    missing = known - set(TIER_MIN)
    if missing:
        raise SystemExit(f"  ! TIER_MIN is missing: {sorted(missing)}")
    stale = set(TIER_MIN) - known
    if stale:
        raise SystemExit(f"  ! TIER_MIN names modules that no longer exist: {sorted(stale)}")

    tick = '<svg class="tk"><use href="#i-check"/></svg>'
    out = []
    for fam, title in FAM_TITLES.items():
        names = by_fam.get(fam, [])
        if not names:
            continue
        rows = ""
        for n in names:
            lo = TIER_ORDER.index(TIER_MIN[n])
            cells = "".join(
                f"<td>{tick}</td>" if i >= lo else '<td class="no">Add on</td>'
                for i in range(3))
            rows += f"<tr><td><b>{n}</b></td>{cells}</tr>"
        out.append(
            f'<details class="cmp-group"{" open" if fam == "spend" else ""}>'
            f"<summary>{title} <span>{len(names)} modules</span></summary>"
            f'<div class="cmp-scroll"><table class="cmp">'
            f"<thead><tr><th></th><th>Core</th><th>Operations</th><th>Enterprise</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></div></details>")
    return "\n".join(out)


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


def document(meta, body, slug):
    noindex = ('\n<meta name="robots" content="noindex,follow">'
               if meta.get("noindex") else "")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{meta.get('title', COMPANY)}</title>
<meta name="description" content="{meta.get('desc', '')}">
<link rel="canonical" href="{DOMAIN}/{'' if slug == 'index' else slug + '.html'}">{noindex}
<meta name="theme-color" content="#A24212">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{COMPANY}">
<meta property="og:url" content="{DOMAIN}/{'' if slug == 'index' else slug + '.html'}">
<meta property="og:title" content="{meta.get('title', COMPANY)}">
<meta property="og:description" content="{meta.get('desc', '')}">
<meta property="og:image" content="{DOMAIN}/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="site.css">
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


def main():
    OUT.mkdir(exist_ok=True)
    css = (SRC / "site.css").read_text(encoding="utf-8")
    (OUT / "site.css").write_text(css, encoding="utf-8")
    (OUT / "favicon.svg").write_text(
        (SRC / "favicon.svg").read_text(encoding="utf-8"), encoding="utf-8")

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
        body = body.replace("<!--TIER_TABLE-->", tier_table())
        frags[slug] = (meta, body)
        (OUT / f"{slug}.html").write_text(document(meta, body, slug), encoding="utf-8")
        print(f"  wrote site/{slug}.html")

    # Single-file preview: every page, switched client side.
    parts = []
    for slug, (meta, body) in frags.items():
        if slug in UNLISTED:
            continue
        parts.append(f'<div class="page" id="page-{slug}"{" hidden" if slug != "index" else ""}>'
                     f"<main>{body.strip()}</main></div>")
    preview = (f"<title>{COMPANY}</title>\n"
               '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
               'family=Plus+Jakarta+Sans:wght@600;700;800&family=Inter:wght@400;500;600;700&'
               'family=JetBrains+Mono:wght@400;500&display=swap">\n'
               f"<style>\n{css}\n</style>\n{sprite()}\n{header('index', True)}\n"
               + "\n".join(parts) + f"\n{footer(True)}\n{SCRIPT}\n{PREVIEW_SCRIPT}\n")
    (HERE / "_preview.html").write_text(preview, encoding="utf-8")
    print(f"  wrote _preview.html ({len(preview):,} chars)")

    # Search engines. Regenerated from DOMAIN so they cannot drift.
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n", encoding="utf-8")
    urls = "".join(
        f"  <url><loc>{DOMAIN}/{'' if s == 'index' else s + '.html'}</loc>"
        f"<priority>{'1.0' if s == 'index' else '0.8'}</priority></url>\n"
        for s in order if s in frags and s not in UNLISTED
    )
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n", encoding="utf-8")
    print("  wrote site/robots.txt, site/sitemap.xml, site/favicon.svg")


if __name__ == "__main__":
    main()
