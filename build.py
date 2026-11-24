#!/usr/bin/env python3
"""Build the front page for make.fun bounty news-image-20261123.

"The World in One Day", Monday 23 November 2026. Draws at 2x (2048x2048)
with Pillow, downscales once with LANCZOS to 1024x1024, quantizes to 256
colours (MEDIANCUT, no dither) and saves entry.png.

Every count on the page is computed from the story data below. A text
registry records every text bounding box; the build prints the overlap /
out-of-bounds problem list, which must be empty.

Deterministic: no randomness, no clock, no network. Fonts are loaded from
$FONT_DIR (default /usr/share/fonts/truetype).
"""

import json
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

S = 2                      # draw scale (2048 canvas for a 1024 page)
W = H = 1024
NBSP = "\u00a0"

# ---------------------------------------------------------------- colours
PAPER = (247, 244, 236)
INK = (20, 22, 28)
GREY = (96, 98, 106)
RULE = (205, 199, 186)
RED = (176, 22, 30)
NAVY = (16, 34, 64)
WHITE = (255, 255, 255)
CARDB = (222, 215, 202)
SHADOW = (228, 221, 207)
CAPSTRIP = (247, 244, 237)
BGBAR = (234, 229, 218)
NUMLINE = (30, 48, 84)
NUMSRC = (156, 174, 206)
NUMLBL = (226, 232, 242)
LEADBODY = (40, 44, 54)
UPD = (16, 96, 170)
ZEBRA = (248, 245, 238)
OCEAN = (222, 232, 242)
LANDC = (206, 197, 178)
UNK_FILL = (253, 246, 232)
UNK_OUT = (214, 160, 60)
UNK_TITLE = (150, 92, 6)
CONF = (24, 122, 64)
STATED = (176, 112, 8)
UNVER = (192, 54, 30)
CERT = {"CONFIRMED": CONF, "STATED": STATED, "UNVERIFIED": UNVER}

REGIONS = [
    ("EUROPE", "Europe", (34, 88, 166)),
    ("CAUCASUS", "Caucasus", (150, 56, 120)),
    ("MIDDLE EAST", "Middle East", (196, 96, 16)),
    ("AFRICA", "Africa", (40, 122, 72)),
    ("SOUTH ASIA", "South Asia", (150, 110, 30)),
    ("EAST ASIA", "East Asia", (180, 36, 60)),
    ("SOUTHEAST ASIA", "Southeast Asia", (18, 122, 132)),
    ("OCEANIA", "Oceania", (40, 140, 200)),
    ("AMERICAS", "Americas", (112, 60, 156)),
    ("WORLD", "World", (88, 88, 96)),
]
REGION = {key: (name, col) for key, name, col in REGIONS}

# ---------------------------------------------------------------- fonts
FONT_DIR = os.environ.get("FONT_DIR", "/usr/share/fonts/truetype")
_FONT_PATHS = {
    "serif_b": "liberation/LiberationSerif-Bold.ttf",
    "serif_i": "liberation/LiberationSerif-Italic.ttf",
    "sans_b": "liberation/LiberationSans-Bold.ttf",
    "cond": "dejavu/DejaVuSansCondensed.ttf",
    "cond_b": "dejavu/DejaVuSansCondensed-Bold.ttf",
}
_FONTS = {}


def font(key, size):
    """TrueType font for `key` at final-unit size `size` (canvas px = 2x)."""
    cache_key = (key, size)
    if cache_key not in _FONTS:
        path = os.path.join(FONT_DIR, _FONT_PATHS[key])
        _FONTS[cache_key] = ImageFont.truetype(path, round(2 * size))
    return _FONTS[cache_key]


def tlen(text, key, size):
    """Text width in final 1024-px units."""
    return font(key, size).getlength(text) / 2.0


# ---------------------------------------------------------------- data
TIMELINE = [
    ("09:00", "Brussels march"),
    ("13:00", "UN AI summit opens"),
    ("~13:30", "Drone fire in Kyiv"),
    ("13:57", "Nvidia rehires Huang"),
    ("14:35", "Merz warns Russia"),
    ("~16:30", "Burnham on EU deal"),
    ("21:00", "S&P 500 +4.7%"),
]

LEADS = [
    dict(n=1, pic="merkury", region="EUROPE", topic="Conflict",
         field="UKRAINE WAR", follow=True, place="KYIV \u2192 BENGHAZI",
         label="7 SEA DRONES", cert="CONFIRMED",
         headline="Kyiv says its sea drones sank a Russian warship",
         body="Zelensky: seven Ukrainian drones hit the corvette Merkury.",
         why="Far from home; Moscow warns of \u201cpainful consequences\u201d.",
         sources="Zelensky, Kyiv Independent, AJ", pin=(30.52, 50.45)),
    dict(n=2, pic="tankers3", region="MIDDLE EAST", topic="Conflict",
         field="IRAN WAR", follow=False, place="STRAIT OF HORMUZ",
         label="3 TANKERS", cert="STATED",
         headline="Iran vows \u201call means\u201d against the US blockade",
         body="IRGC says 3 tankers hit mines in Hormuz and caught fire.",
         why="Hormuz attacks near a wartime peak: 22+ this month (CNN).",
         sources="Iran FM, IRNA, Arab News", pin=(56.3, 26.6)),
    dict(n=3, pic="chart", region="AMERICAS", topic="Economy",
         field="MARKETS", follow=True, place="SANTA CLARA",
         label="+31.5%", cert="CONFIRMED",
         headline="Nvidia brings back Huang; its shares jump 31.5%",
         body="Back 11 days after he quit; about $950bn added in a day.",
         why="Record one-day gain for any company (NBC); S&P 500 +4.7%.",
         sources="NBC, Kiplinger, Fortune", pin=(-121.96, 37.35)),
]

CARDS = [
    dict(n=4, pic="scroll", region="CAUCASUS", topic="Diplomacy",
         field="PEACE", follow=False, place="YEREVAN", label="NEW DRAFT",
         cert="CONFIRMED", sources="Reuters, H\u00fcrriyet",
         headline="Armenia drafts a constitution with no land claims, aiding peace",
         pin=(44.51, 40.18)),
    dict(n=5, pic="tower", region="MIDDLE EAST", topic="Conflict",
         field="YEMEN", follow=False, place="HODEIDAH", label="17 KILLED",
         cert="STATED", sources="Houthis, Ahram",
         headline="Houthis: Saudi strikes on Hodeidah telecom sites kill 17, cut internet",
         pin=(42.95, 14.8)),
    dict(n=6, pic="fire2", region="SOUTHEAST ASIA", topic="Disaster",
         field="FIRE", follow=True, place="SERANG, INDONESIA",
         label="24 DEAD", cert="CONFIRMED", sources="Basarnas, AJ",
         headline="Indonesia factory fire toll rises to 24; about 30 workers still missing",
         pin=(106.15, -6.12)),
    dict(n=7, pic="noflight", region="EUROPE", topic="Labour",
         field="STRIKE", follow=False, place="BRUSSELS", label="NO FLIGHTS",
         cert="CONFIRMED", sources="VRT, AFP",
         headline="Belgian strike grounds all Brussels flights; police tear-gas marchers",
         pin=(4.35, 50.85)),
    dict(n=8, pic="village", region="AFRICA", topic="Conflict",
         field="NIGERIA", follow=False, place="NIGER STATE",
         label="64 KILLED", cert="STATED", sources="Reuters",
         headline="Fulani say 64 killed in Niger State reprisals for a village head\u2019s murder",
         pin=(4.5, 10.0)),
    dict(n=9, pic="health", region="AFRICA", topic="Health",
         field="POLICY", follow=False, place="ADDIS ABABA",
         label="HEALTH SUMMIT", cert="CONFIRMED", sources="AU, Africa CDC",
         headline="African leaders open Addis health summit, seek less reliance on aid",
         pin=(38.75, 9.0)),
    dict(n=10, pic="ai", region="WORLD", topic="Tech & AI",
         field="UN", follow=False, place="BARBADOS", label="AI SAFETY",
         cert="CONFIRMED", sources="UN News",
         headline="Guterres asks nations for a global AI risk framework within a year",
         pin=(-59.6, 13.1)),
    dict(n=11, pic="train", region="SOUTH ASIA", topic="Diplomacy",
         field="INDIA\u2013NEPAL", follow=False, place="NEW DELHI",
         label="8 PACTS", cert="CONFIRMED", sources="The Hindu, DH",
         headline="India and Nepal sign 8 pacts and launch a direct Ayodhya\u2013Janakpur train",
         pin=(77.21, 28.61)),
    dict(n=12, pic="music", region="OCEANIA", topic="Culture",
         field="MUSIC", follow=False, place="MELBOURNE", label="DIES AT 83",
         cert="CONFIRMED", sources="Reuters, 7News",
         headline="Australian TV music legend Molly Meldrum, who boosted AC/DC, dies",
         pin=(144.96, -37.81)),
    dict(n=13, pic="oil", region="WORLD", topic="Economy",
         field="OIL", follow=False, place="MARKETS", label="3-MONTH LOW",
         cert="CONFIRMED", sources="Reuters, Investing",
         headline="Oil drops over 3% to a three-month low as Mideast supply rises",
         pin=None),
]

LIST = [
    dict(n=14, region="EUROPE", topic="Conflict", follow=False,
         place="Kyiv", text="drone debris sets fires; 5 hurt",
         source="Klitschko, KI", cert="CONFIRMED", pin=(30.52, 50.45)),
    dict(n=15, region="EUROPE", topic="Security", follow=False,
         place="Berlin", text="Merz: Russian \u201cprovocations\u201d",
         source="Reuters, DW", cert="CONFIRMED", pin=(13.4, 52.52)),
    dict(n=16, region="EUROPE", topic="Politics", follow=False,
         place="London", text="Burnham: EU return needs vote",
         source="Politico, Sky", cert="CONFIRMED", pin=(-0.13, 51.51)),
    dict(n=17, region="EUROPE", topic="Diplomacy", follow=False,
         place="Brussels", text="22nd Russia sanctions plan",
         source="EU, Reuters", cert="CONFIRMED", pin=(4.35, 50.85)),
    dict(n=18, region="EUROPE", topic="Environment", follow=True,
         place="Ankara", text="Erdo\u011fan: COP31 laid groundwork",
         source="Reuters", cert="STATED", pin=(32.85, 39.93)),
    dict(n=19, region="EUROPE", topic="Conflict", follow=True,
         place="St Petersburg", text="Sparta II towed in",
         source="Governor, Reuters", cert="CONFIRMED", pin=(30.3, 59.94)),
    dict(n=20, region="MIDDLE EAST", topic="Conflict", follow=False,
         place="Gaza", text="Israeli strike kills UNRWA worker",
         source="UNRWA, MEE", cert="CONFIRMED", pin=(34.45, 31.5)),
    dict(n=21, region="MIDDLE EAST", topic="Diplomacy", follow=False,
         place="Cairo", text="Sisi hosts Iraq\u2019s new PM",
         source="Egypt govt, Ahram", cert="CONFIRMED", pin=(31.24, 30.04)),
    dict(n=22, region="AFRICA", topic="Tech & AI", follow=False,
         place="Pretoria", text="Ramaphosa backs AI fund",
         source="iAfrica, AllAfrica", cert="CONFIRMED", pin=(28.19, -25.75)),
    dict(n=23, region="AFRICA", topic="Security", follow=False,
         place="Somalia", text="to fight al-Shabaab with Uganda",
         source="Garowe", cert="STATED", pin=(45.34, 2.04)),
    dict(n=24, region="EAST ASIA", topic="Justice", follow=False,
         place="Beijing", text="official sentenced to death as spy",
         source="AP, SCMP", cert="CONFIRMED", pin=(116.4, 39.9)),
    dict(n=25, region="EAST ASIA", topic="Politics", follow=True,
         place="Seoul", text="Lee replaces 5 top officials",
         source="MK, OkayNews", cert="CONFIRMED", pin=(126.98, 37.57)),
    dict(n=26, region="SOUTHEAST ASIA", topic="Labour", follow=False,
         place="Manila", text="jeepney strike begins",
         source="Manila Times, ABS-CBN", cert="CONFIRMED", pin=(120.98, 14.6)),
    dict(n=27, region="OCEANIA", topic="Politics", follow=True,
         place="Canberra", text="COP31 head told to go",
         source="Reuters, Guardian", cert="CONFIRMED", pin=(149.13, -35.28)),
    dict(n=28, region="OCEANIA", topic="Sport", follow=False,
         place="Wellington", text="NZ save first Test vs India",
         source="ESPN, Mint", cert="CONFIRMED", pin=(174.78, -41.29)),
    dict(n=29, region="AMERICAS", topic="Security", follow=True,
         place="Mexico", text="to try Isidro, not extradite",
         source="Mexican govt", cert="CONFIRMED", pin=(-99.13, 19.43)),
    dict(n=30, region="AMERICAS", topic="Economy", follow=False,
         place="Bras\u00edlia", text="Brazil targets 1.5\u20132% surplus",
         source="Govt, Reuters", cert="CONFIRMED", pin=(-47.9, -15.8)),
    dict(n=31, region="AMERICAS", topic="Science", follow=False,
         place="Kourou", text="Ariane 6 launch scrubbed",
         source="Arianespace", cert="CONFIRMED", pin=(-52.65, 5.16)),
    dict(n=32, region="AMERICAS", topic="Justice", follow=False,
         place="Dominica", text="2 US men jailed for murders",
         source="CityNews, CP", cert="CONFIRMED", pin=(-61.39, 15.3)),
    dict(n=33, region="AMERICAS", topic="Health", follow=False,
         place="New York", text="MMR vaccine access widened",
         source="NY Health", cert="CONFIRMED", pin=(-74.0, 40.7)),
    dict(n=34, region="AMERICAS", topic="Business", follow=False,
         place="Austin", text="CrowdStrike to buy Zscaler",
         source="TheStreet, Inv.", cert="CONFIRMED", pin=(-97.74, 30.27)),
    dict(n=35, region="AMERICAS", topic="Politics", follow=False,
         place="US", text="Trump attacks Newsom on death row",
         source="Reuters, UPI", cert="CONFIRMED", pin=(-77.04, 38.9)),
]

NUMBERS = [
    ("7", "EUROPE", "sea drones hit the Merkury", "Zelensky"),
    ("+31.5%", "AMERICAS", "Nvidia shares as Huang returns", "NBC"),
    ("24", "SOUTHEAST ASIA", "dead in Indonesia factory fire", "Basarnas"),
    ("17", "MIDDLE EAST", "killed in Hodeidah, Houthis say", "Houthi media"),
    ("8", "SOUTH ASIA", "pacts signed by India and Nepal", "The Hindu"),
    ("22nd", "EUROPE", "EU package on Russia, proposed", "EU"),
]

UNKNOWNS = [
    ("Hormuz:", "the mine blasts are the IRGC\u2019s account"),
    ("Niger State:", "the toll is from Fulani groups"),
    ("Belgium:", "no budget deal yet; deadline 31 Dec"),
]

FOLLOWUPS = [
    ("Merkury", "hit 22" + NBSP + "Nov"),
    ("Nvidia", "Huang quit 11 days earlier"),
    ("\u2018El Chapo" + NBSP + "Isidro\u2019", "caught 20" + NBSP + "Nov"),
    ("COP31", "ended 22" + NBSP + "Nov"),
    ("Indonesia fire", "weekend"),
    ("Sparta II", "hit 21" + NBSP + "Nov"),
    ("S. Korea", "minister quit 22" + NBSP + "Nov"),
]

ALL_STORIES = LEADS + CARDS + LIST

# ---------------------------------------------------------------- registry
# Every text draw registers (element, bbox) in final 1024-px units.
REGISTRY = []


def reg(element, box):
    REGISTRY.append((element, box))


def check_registry():
    """Return a list of problems: overlaps between different elements and
    boxes that leave the canvas. Empty means the page is clean."""
    problems = []
    for element, (x0, y0, x1, y1) in REGISTRY:
        if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
            problems.append(
                "out of bounds %s: (%.1f, %.1f)-(%.1f, %.1f)"
                % (element, x0, y0, x1, y1))
    n = len(REGISTRY)
    for i in range(n):
        ei, (ax0, ay0, ax1, ay1) = REGISTRY[i]
        for j in range(i + 1, n):
            ej, (bx0, by0, bx1, by1) = REGISTRY[j]
            if ei == ej:
                continue
            ox = min(ax1, bx1) - max(ax0, bx0)
            oy = min(ay1, by1) - max(ay0, by0)
            if ox > 0.6 and oy > 0.6:
                problems.append(
                    "overlap %s vs %s: %.1f x %.1f px"
                    % (ei, ej, ox, oy))
    return problems


# ---------------------------------------------------------------- canvas
class Canvas:
    """Draws in final 1024-px units on a 2048x2048 Pillow image."""

    def __init__(self, image):
        self.d = ImageDraw.Draw(image)

    def _p(self, v):
        return v * S

    def _w(self, w):
        return max(1, round(w * S))

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, width=1):
        self.d.rectangle([self._p(x0), self._p(y0), self._p(x1), self._p(y1)],
                         fill=fill, outline=outline,
                         width=self._w(width) if outline else 1)

    def rrect(self, x0, y0, x1, y1, radius, fill=None, outline=None,
              width=1):
        self.d.rounded_rectangle(
            [self._p(x0), self._p(y0), self._p(x1), self._p(y1)],
            radius=self._p(radius), fill=fill, outline=outline,
            width=self._w(width) if outline else 1)

    def ellipse(self, x0, y0, x1, y1, fill=None, outline=None, width=1):
        self.d.ellipse([self._p(x0), self._p(y0), self._p(x1), self._p(y1)],
                       fill=fill, outline=outline,
                       width=self._w(width) if outline else 1)

    def polygon(self, points, fill=None):
        pts = [(self._p(x), self._p(y)) for x, y in points]
        self.d.polygon(pts, fill=fill)

    def line(self, points, fill, width=1):
        pts = [(self._p(x), self._p(y)) for x, y in points]
        self.d.line(pts, fill=fill, width=self._w(width))

    def polyline(self, points, fill, width=1):
        pts = [(self._p(x), self._p(y)) for x, y in points]
        self.d.line(pts, fill=fill, width=self._w(width), joint="curve")

    def text(self, x, y, s, key, size, color, anchor="la", element=None):
        f = font(key, size)
        self.d.text((self._p(x), self._p(y)), s, font=f, fill=color,
                    anchor=anchor)
        if element is not None:
            box = self.d.textbbox((self._p(x), self._p(y)), s, font=f,
                                  anchor=anchor)
            reg(element, (box[0] / S, box[1] / S, box[2] / S, box[3] / S))

    def textw(self, s, key, size):
        return font(key, size).getlength(s) / S


# A translated canvas: all coordinates shift by (ox, oy).
class Shifted:
    def __init__(self, base, ox, oy):
        self.b = base
        self.ox = ox
        self.oy = oy

    def rect(self, x0, y0, x1, y1, **kw):
        self.b.rect(x0 + self.ox, y0 + self.oy, x1 + self.ox, y1 + self.oy,
                    **kw)

    def rrect(self, x0, y0, x1, y1, radius, **kw):
        self.b.rrect(x0 + self.ox, y0 + self.oy, x1 + self.ox, y1 + self.oy,
                     radius, **kw)

    def ellipse(self, x0, y0, x1, y1, **kw):
        self.b.ellipse(x0 + self.ox, y0 + self.oy, x1 + self.ox,
                       y1 + self.oy, **kw)

    def polygon(self, points, **kw):
        self.b.polygon([(x + self.ox, y + self.oy) for x, y in points], **kw)

    def line(self, points, fill, width=1):
        self.b.line([(x + self.ox, y + self.oy) for x, y in points], fill,
                    width)

    def polyline(self, points, fill, width=1):
        self.b.polyline([(x + self.ox, y + self.oy) for x, y in points],
                        fill, width)

    def text(self, x, y, s, key, size, color, anchor="la", element=None):
        # Picture text is decorative; register it under the picture element
        # only when an element is given (pictures pass None: their text is
        # inside the clipped panel and never overlaps page text).
        self.b.text(x + self.ox, y + self.oy, s, key, size, color, anchor,
                    element)

    def textw(self, s, key, size):
        return self.b.textw(s, key, size)


def sky(c, x0, y0, x1, y1, top, bottom):
    """24-band vertical gradient, bands overlapping by 0.6 to hide seams."""
    h = y1 - y0
    for i in range(24):
        col = tuple(int(top[k] + (bottom[k] - top[k]) * i / 23)
                     for k in range(3))
        c.rect(x0, y0 + h * i / 24, x1, y0 + h * (i + 1) / 24 + 0.6,
               fill=col)


def flame(c, x, y, s):
    """Flame with its base centre at (x, y), scale s."""
    c.polygon([(x - 9 * s, y), (x - 4 * s, y - 16 * s), (x, y - 8 * s),
               (x + 4 * s, y - 22 * s), (x + 9 * s, y)],
              fill=(232, 96, 28))
    c.polygon([(x - 5 * s, y), (x - s, y - 9 * s), (x + 3 * s, y - 13 * s),
               (x + 5 * s, y)], fill=(250, 196, 60))


def smoke(c, x, y, s, colour):
    """Four filled circles rising up and to the right from (x, y)."""
    for dx, dy, r in ((0, 0, 4.5), (2.5, -5, 5.5), (6, -10, 6.5),
                      (10, -15, 5)):
        c.ellipse(x + dx * s - r * s, y + dy * s - r * s,
                  x + dx * s + r * s, y + dy * s + r * s, fill=colour)


# ---------------------------------------------------------------- text wrap
def wrap_runs(runs, width):
    """Greedy-wrap runs [(text, key, size, colour)] to `width` (final px).

    Splits on ordinary spaces only, so U+00A0-joined words never split.
    Returns lines: each a list of (text, key, size, colour, seg_width)."""
    words = []  # (word, key, size, colour, word_width)
    for text, key, size, colour in runs:
        f = font(key, size)
        for w in text.split(" "):
            if w == "":
                continue
            words.append((w, key, size, colour, f.getlength(w) / S))
    lines = []
    cur = []
    cur_w = 0.0
    for w, key, size, colour, ww in words:
        space_w = font(key, size).getlength(" ") / S if cur else 0.0
        if cur and cur_w + space_w + ww > width:
            lines.append(cur)
            cur = []
            cur_w = 0.0
            space_w = 0.0
        if cur:
            cur.append((" ", key, size, colour, space_w))
            cur_w += space_w
        cur.append((w, key, size, colour, ww))
        cur_w += ww
    if cur:
        lines.append(cur)
    return lines


def draw_para(c, x, y, runs, width, lh, element):
    """Draw a wrapped multi-run paragraph; return its height."""
    lines = wrap_runs(runs, width)
    for k, line in enumerate(lines):
        cx = x
        for text, key, size, colour, w in line:
            c.text(cx, y + k * lh, text, key, size, colour, element=element)
            cx += w
    return len(lines) * lh


# ---------------------------------------------------------------- components
def card(c, x0, y0, x1, y1, radius, fill=WHITE, outline=CARDB):
    c.rrect(x0 + 1.2, y0 + 2.2, x1 + 1.2, y1 + 2.2, radius, fill=SHADOW)
    c.rrect(x0, y0, x1, y1, radius, fill=fill, outline=outline, width=0.8)


def round_badge(c, cx, cy, n, colour, r, size, element):
    c.ellipse(cx - r, cy - r, cx + r, cy + r, fill=colour, outline=WHITE,
              width=1.2)
    c.text(cx, cy + 0.4, str(n), "cond_b", size, WHITE, anchor="mm",
           element=element)


def square_badge(c, cx, cy, n, colour, element):
    c.rect(cx - 7.6, cy - 7.6, cx + 7.6, cy + 7.6, fill=colour,
           outline=WHITE, width=1.2)
    c.text(cx, cy + 0.4, str(n), "cond_b", 9.8, WHITE, anchor="mm",
           element=element)


def certainty_icon(c, kind, cx, cy, r, element=None):
    col = CERT[kind]
    c.ellipse(cx - r, cy - r, cx + r, cy + r, fill=col)
    if kind == "CONFIRMED":
        w = max(1, round(0.30 * r * S))
        c.polyline([(cx - 0.50 * r, cy + 0.02 * r),
                    (cx - 0.12 * r, cy + 0.42 * r),
                    (cx + 0.55 * r, cy - 0.40 * r)], WHITE, width=w / S)
    elif kind == "STATED":
        for d in (-0.30, 0.30):
            mx = cx + d * r
            c.ellipse(mx - 0.22 * r, cy - 0.38 * r, mx + 0.22 * r,
                      cy + 0.06 * r, fill=WHITE)
            c.polygon([(mx + 0.05 * r, cy - 0.05 * r),
                       (mx + 0.22 * r, cy - 0.10 * r),
                       (mx - 0.12 * r, cy + 0.42 * r)], fill=WHITE)
    else:  # UNVERIFIED
        c.text(cx, cy + 0.06 * r, "?", "sans_b", 1.45 * r, WHITE,
               anchor="mm", element=element)


def tag_chip(c, right, top, kind, size, element):
    """White pill with icon + word; right edge `right`, top `top`."""
    col = CERT[kind]
    h = size + 6
    w = c.textw(kind, "cond_b", size) + h + 8
    x0 = right - w
    c.rrect(x0, top, right, top + h, h / 2, fill=WHITE, outline=col,
            width=1.1)
    certainty_icon(c, kind, x0 + h / 2, top + h / 2, h / 2 - 1)
    c.text(x0 + h + 3, top + 2.6, kind, "cond_b", size, col, element=element)
    return w


def lighten(col):
    return tuple(int(v * 0.55 + 255 * 0.45) for v in col)

# ---------------------------------------------------------------- pictures
# Each takes a Shifted canvas whose origin is the drawing area top-left.
# Coordinates are final 1024-px units, relative to that origin.

def pic_merkury(c):
    sky(c, 0, 0, 248, 82.8, (236, 150, 92), (250, 214, 168))
    c.rect(0, 54.6, 248, 82.8, fill=(36, 82, 120))
    for x0, y in ((10, 60.6), (62, 65.6), (114, 60.6), (166, 65.6),
                  (218, 60.6), (270, 65.6)):
        c.line([(x0, y), (x0 + 24, y)], (90, 140, 176), 1.2)
    c.rect(138, 48.6, 248, 57.6, fill=(120, 106, 92))
    c.line([(152, 48.6), (152, 4)], (70, 62, 56), 2.4)
    c.line([(142, 5), (168, 5)], (70, 62, 56), 2.4)
    c.line([(188, 48.6), (188, 4)], (70, 62, 56), 2.4)
    c.line([(178, 5), (204, 5)], (70, 62, 56), 2.4)
    c.polygon([(19.2, 55.6), (133.2, 55.6), (149.2, 4), (139.2, 2),
               (79.2, 28.2)], fill=(98, 104, 112))
    c.polygon([(133.2, 55.6), (149.2, 4), (155.2, 7), (143.2, 55.6)],
              fill=(70, 76, 84))
    smoke(c, 43.2, 44.6, 0.75, (88, 84, 84))
    flame(c, 39.2, 55.6, 0.7)
    for x0 in (15.2, 39.2, 63.2, 87.2, 111.2):
        c.line([(x0, 57.6), (x0 + 14, 57.6)], (200, 220, 236), 1.2)
    for x0 in (3.9, -2.1, -8.1):
        c.line([(x0, 65.6), (x0 + 4, 65.6)], (220, 232, 242), 1.1)
    c.polygon([(9.9, 62.6), (22.9, 64.6), (9.9, 67.6)], fill=(28, 28, 34))
    for x0 in (21.3, 15.3, 9.3):
        c.line([(x0, 71.4), (x0 + 4, 71.4)], (220, 232, 242), 1.1)
    c.polygon([(27.3, 68.4), (40.3, 70.4), (27.3, 73.4)], fill=(28, 28, 34))
    for x0 in (38.6, 32.6, 26.6):
        c.line([(x0, 65.6), (x0 + 4, 65.6)], (220, 232, 242), 1.1)
    c.polygon([(44.6, 62.6), (57.6, 64.6), (44.6, 67.6)], fill=(28, 28, 34))


def pic_tankers3(c):
    sky(c, 0, 0, 248, 82.8, (120, 104, 110), (214, 180, 150))
    c.rect(0, 56.3, 248, 82.8, fill=(36, 80, 116))
    # tanker 1 (big)
    c.polygon([(7.4, 50), (54.6, 50), (48.6, 62.4), (12.4, 62.4)],
              fill=(140, 40, 34))
    c.rect(11.4, 46.7, 42.8, 50, fill=(84, 88, 96))
    c.rect(42.8, 35.1, 50.8, 50, fill=(236, 236, 236))
    smoke(c, 21.6, 28.5, 0.621, (70, 66, 68))
    flame(c, 23.9, 47.5, 1.035)
    # tanker 2
    c.polygon([(59.5, 51.3), (99.6, 51.3), (94.5, 62.4), (63.8, 62.4)],
              fill=(140, 40, 34))
    c.rect(62.9, 48.5, 89.6, 51.3, fill=(84, 88, 96))
    c.rect(89.6, 38.6, 96.4, 51.3, fill=(236, 236, 236))
    smoke(c, 71.5, 33, 0.528, (70, 66, 68))
    flame(c, 73.5, 49.2, 0.88)
    # tanker 3
    c.polygon([(104.2, 52.3), (138.1, 52.3), (133.8, 62.4), (107.8, 62.4)],
              fill=(140, 40, 34))
    c.rect(107, 50, 129.6, 52.3, fill=(84, 88, 96))
    c.rect(129.6, 41.6, 135.4, 52.3, fill=(236, 236, 236))
    smoke(c, 114.3, 36.8, 0.447, (70, 66, 68))
    flame(c, 116, 50.6, 0.745)
    # sea mine: 8 spikes + black disc
    cx, cy = 136.4, 70.4
    spikes = [((141.4, 70.4), (144.3, 70.4)), ((139.9, 73.9), (142, 76)),
              ((136.4, 75.3), (136.4, 78.3)), ((132.9, 73.9), (130.8, 76)),
              ((131.4, 70.4), (128.5, 70.4)), ((132.9, 66.9), (130.8, 64.8)),
              ((136.4, 65.4), (136.4, 62.4)), ((139.9, 66.9), (142, 64.8))]
    for p0, p1 in spikes:
        c.line([p0, p1], (20, 20, 24), 1.4)
    c.ellipse(131.4, 65.4, 141.4, 75.3, fill=(30, 30, 34))


def pic_chart(c):
    sky(c, 0, 0, 248, 82.8, (14, 24, 44), (30, 46, 78))
    for y in (20.7, 41.4, 62.1):
        c.line([(0, y), (248, y)], (46, 62, 96), 0.8)
    c.polygon([(7.4, 54.6), (24.8, 49.7), (42.2, 59.6), (59.5, 56.3),
               (76.9, 69.6), (91.8, 66.2), (104.2, 29.8), (116.6, 14.9),
               (116.6, 82.8), (7.4, 82.8)], fill=(26, 70, 64))
    c.polyline([(7.5, 54.5), (25, 49.5), (42, 59.5), (59.5, 56.5),
                (77, 69.5), (92, 66), (104, 30), (116.5, 15)],
               (70, 210, 120), 3)
    c.polygon([(119.6, 7.9), (110.6, 13.9), (118.6, 19.9)],
              fill=(70, 210, 120))
    # GPU chip
    c.rrect(149.6, 27.3, 177.8, 55.5, 3, fill=(60, 70, 92))
    for x in (153.1, 160.2, 167.2, 174.2):
        c.line([(x, 23.3), (x, 27.3)], (150, 160, 180), 1.4)
        c.line([(x, 55.5), (x, 59.5)], (150, 160, 180), 1.4)
    for y in (30.8, 37.9, 44.9, 52):
        c.line([(145.6, y), (149.6, y)], (150, 160, 180), 1.4)
        c.line([(177.8, y), (181.8, y)], (150, 160, 180), 1.4)
    c.text(163.5, 41.5, "GPU", "cond_b", 10.8, (120, 220, 160), anchor="mm")
    c.text(8, 5, "NVDA", "sans_b", 14.1, (70, 210, 120))


def pic_scroll(c):
    sky(c, 0, 0, 182, 42.6, (226, 232, 240), (244, 244, 240))
    c.rect(10, 5, 61.1, 41.6, fill=(196, 196, 196))
    c.rect(8, 3, 59.1, 40.6, fill=(250, 247, 236))
    c.text(12, 6, "DRAFT", "cond_b", 7.2, (16, 34, 64))
    for y in (20.9, 26, 31.1):
        c.line([(12, y), (51.1, y)], (190, 186, 176), 1.1)
    c.ellipse(45.5, 27.8, 56.6, 38.9, fill=(176, 22, 30))
    c.line([(63.1, 38.6), (71.1, 13.7)], (60, 60, 70), 2.4)
    c.line([(73.1, 23.6), (73.1, 42.6)], (90, 90, 96), 1.2)
    c.rect(74.1, 25.6, 95.4, 29.8, fill=(217, 0, 18))
    c.rect(74.1, 29.8, 95.4, 34.1, fill=(0, 51, 160))
    c.rect(74.1, 34.1, 95.4, 38.3, fill=(242, 168, 0))


def pic_tower(c):
    sky(c, 0, 0, 182, 42.6, (70, 58, 64), (170, 120, 92))
    for x0, y0 in ((81.9, 29.8), (97.9, 25.6), (113.9, 21.3), (129.9, 29.8),
                   (145.9, 25.6), (161.9, 21.3)):
        c.rect(x0, y0, x0 + 13, 42.6, fill=(150, 120, 96))
    c.line([(23.4, 42.6), (32.8, 3)], (36, 36, 42), 1.8)
    c.line([(42.1, 42.6), (32.8, 3)], (36, 36, 42), 1.8)
    for y0, y1, x0, x1 in ((10.9, 10.9, 30.9, 34.6), (18.8, 18.8, 29, 36.5),
                           (26.8, 26.8, 27.1, 38.4),
                           (34.7, 34.7, 25.3, 40.3)):
        c.line([(x0, y0), (x1, y1)], (36, 36, 42), 1)
    c.ellipse(33.8, 9.8, 40, 17.5, fill=(220, 220, 226))
    smoke(c, 42.1, 24.7, 0.453, (60, 56, 58))
    flame(c, 38.7, 41.6, 0.589)


def pic_fire2(c):
    sky(c, 0, 0, 182, 42.6, (80, 52, 48), (170, 104, 72))
    c.rect(6, 23.4, 100.1, 42.6, fill=(150, 140, 130))
    for i in range(4):
        x0 = 6 + i * 23.55
        c.polygon([(x0, 23.4), (x0 + 23.5, 23.4), (x0 + 23.5, 16.2)],
                  fill=(120, 112, 104))
    for x0 in (11, 27.8, 44.6, 61.5, 78.3):
        c.rect(x0, 29.8, x0 + 6, 34.9, fill=(60, 40, 36))
    smoke(c, 47.3, 10.6, 0.499, (66, 58, 58))
    for x in (23.7, 52.8, 81.9):
        flame(c, x, 23.4, 0.634)


def pic_noflight(c):
    sky(c, 0, 0, 182, 42.6, (200, 208, 220), (230, 234, 240))
    c.ellipse(17.2, 18.3, 55.6, 24.3, fill=(80, 90, 110))
    c.polygon([(34.3, 21.3), (40.7, 21.3), (31.3, 6.8), (27, 6.8)],
              fill=(80, 90, 110))
    c.polygon([(34.3, 21.3), (40.7, 21.3), (31.3, 35.8), (27, 35.8)],
              fill=(80, 90, 110))
    c.polygon([(19.2, 21.3), (21.5, 21.3), (16.2, 12.8)], fill=(80, 90, 110))
    c.ellipse(17.5, 2.5, 55, 40, outline=(176, 22, 30), width=2.4)
    c.line([(23.3, 34.4), (49.5, 8.2)], (176, 22, 30), 2.4)
    c.line([(89.1, 42.6), (89.1, 25.6)], (110, 90, 70), 1.4)
    c.rect(80.1, 18.7, 98.1, 25.6, fill=(255, 255, 255),
           outline=(176, 22, 30), width=0.8)
    c.line([(110.9, 42.6), (110.9, 25.6)], (110, 90, 70), 1.4)
    c.rect(101.9, 18.7, 119.9, 25.6, fill=(255, 255, 255),
           outline=(176, 22, 30), width=0.8)


def pic_village(c):
    sky(c, 0, 0, 182, 42.6, (60, 40, 50), (150, 96, 70))
    c.rect(0, 37.5, 182, 42.6, fill=(110, 80, 50))
    huts = [(7.3, 27.7, 29.4, 4.3, 18.4, 32.4, 17),
            (36.4, 29.9, 55.2, 33.4, 45.8, 58.2, 20.9),
            (61.9, 28.4, 82.9, 58.9, 72.4, 85.9, 18.3)]
    for x0, y0, x1, rx0, cx, rx1, top in huts:
        c.rect(x0, y0, x1, 42.6, fill=(180, 140, 96))
        c.polygon([(rx0, y0), (cx, top), (rx1, y0)], fill=(120, 90, 50))
    for x0 in (16.1, 43.9, 70.3):
        c.rect(x0, 35.8, x0 + 4.5, 42.6, fill=(70, 46, 30))
    smoke(c, 47.3, 12.8, 0.408, (64, 54, 58))
    flame(c, 45.8, 22.2, 0.544)


def pic_health(c):
    sky(c, 0, 0, 182, 42.6, (226, 242, 236), (246, 250, 248))
    c.ellipse(4.9, 3.4, 40.6, 39.2, fill=(255, 255, 255),
              outline=(40, 122, 72), width=1.6)
    c.rect(19.2, 11.5, 26.3, 31.1, fill=(40, 122, 72))
    c.rect(12.9, 17.7, 32.6, 24.9, fill=(40, 122, 72))
    c.rrect(48.6, 24.3, 59.3, 32, 4, fill=(200, 40, 50))
    c.rrect(58, 24.3, 68.7, 32, 4, fill=(255, 255, 255),
            outline=(170, 170, 170), width=0.6)


def pic_ai(c):
    sky(c, 0, 0, 182, 42.6, (70, 140, 220), (130, 186, 236))
    c.polygon([(7.7, 4), (38.4, 4), (38.4, 22.2), (23, 40.6), (7.7, 22.2)],
              fill=(255, 255, 255))
    c.rrect(14.9, 9.8, 31.1, 26, 3, fill=(16, 34, 64))
    for x in (17.6, 23, 28.4):
        c.line([(x, 6.8), (x, 9.8)], (16, 34, 64), 1.2)
        c.line([(x, 26), (x, 29)], (16, 34, 64), 1.2)
    c.text(23, 18, "AI", "sans_b", 9.4, (120, 200, 255), anchor="mm")
    for x, y0 in ((44.7, 32), (53.7, 26.8), (62.7, 21.7)):
        c.line([(x, 39.6), (x, y0)], (230, 240, 250), 2.2)


def pic_train(c):
    sky(c, 0, 0, 182, 42.6, (214, 228, 240), (240, 242, 238))
    c.line([(0, 40.1), (182, 40.1)], (90, 90, 96), 1.4)
    for x in range(4, 180, 8):
        c.line([(x, 38.6), (x, 41.6)], (140, 120, 100), 1)
    c.rrect(6, 17.9, 60.6, 36.6, 4, fill=(30, 90, 160))
    c.rect(6, 29.8, 60.6, 32.4, fill=(250, 200, 60))
    for x0 in (12, 25.5, 39.1):
        c.rect(x0, 21.9, x0 + 6, 26.4, fill=(220, 236, 250))
    c.rect(63.6, 19.9, 98.3, 36.6, fill=(30, 90, 160))
    c.rect(63.6, 29.8, 98.3, 32.4, fill=(250, 200, 60))
    for x0 in (67.6, 77.2, 86.7):
        c.rect(x0, 23.9, x0 + 5, 27.3, fill=(220, 236, 250))
    for x0, y0 in ((10.8, 33.6), (49.4, 33.6), (68.4, 33.6), (87.1, 33.6)):
        c.ellipse(x0, y0, x0 + 6.4, 40, fill=(40, 40, 44))


def pic_music(c):
    sky(c, 0, 0, 182, 42.6, (24, 20, 36), (56, 40, 70))
    c.polygon([(33.4, 0), (39.4, 0), (59.8, 42.6), (13, 42.6)],
              fill=(72, 62, 94))
    c.ellipse(22.6, 6, 32, 16.2, fill=(196, 196, 206))
    for y in (8.5, 11.1, 13.6):
        c.line([(23.5, y), (31.1, y)], (120, 120, 130), 0.8)
    c.rect(25.8, 16.2, 28.8, 37.5, fill=(150, 150, 160))
    c.ellipse(19.6, 35.8, 35, 40, fill=(120, 120, 130))
    c.rrect(60.2, 14.5, 78.1, 29, 4, fill=(196, 156, 104))
    c.rect(60.2, 24.7, 78.1, 27.7, fill=(70, 46, 30))
    c.ellipse(50.4, 26.4, 87.9, 33.2, fill=(196, 156, 104))
    c.ellipse(46.1, 12.8, 51.1, 17, fill=(255, 255, 255))
    c.line([(50.7, 14.9), (50.7, 3.4)], (255, 255, 255), 1.2)


def pic_oil(c):
    sky(c, 0, 0, 182, 42.6, (232, 228, 216), (248, 246, 240))
    c.rect(8, 6, 31.4, 39.6, fill=(30, 60, 110))
    c.ellipse(8, 3, 31.4, 8.9, fill=(50, 86, 140))
    c.line([(8, 18.7), (31.4, 18.7)], (70, 104, 160), 1.6)
    c.line([(8, 29.5), (31.4, 29.5)], (70, 104, 160), 1.6)
    c.polyline([(39.5, 13.5), (47, 19.5), (51.5, 18), (62, 34)],
               (176, 22, 30), 2.5)
    c.polygon([(65.8, 35.8), (54.8, 34.1), (62.8, 29.8)], fill=(176, 22, 30))


PICS = {
    "merkury": pic_merkury, "tankers3": pic_tankers3, "chart": pic_chart,
    "scroll": pic_scroll, "tower": pic_tower, "fire2": pic_fire2,
    "noflight": pic_noflight, "village": pic_village, "health": pic_health,
    "ai": pic_ai, "train": pic_train, "music": pic_music, "oil": pic_oil,
}

# ---------------------------------------------------------------- picture panel
def picture_panel(img, c, x0, y0, x1, y1, region, place, label, lsize,
                  psize, ssize, sources, pic_fn, el):
    """A picture with caption strip and red label pill (spec 3.3)."""
    ch = max(psize, ssize) + 7
    # Draw the picture on a layer, clipped to the panel rectangle.
    layer = Image.new("RGB", (W * S, H * S))
    lc = Canvas(layer)
    pic_fn(Shifted(lc, x0, y0))
    mask = Image.new("L", (W * S, H * S), 0)
    md = ImageDraw.Draw(mask)
    md.rectangle([round(x0 * S), round(y0 * S), round(x1 * S),
                  round(y1 * S)], fill=255)
    img.paste(layer, (0, 0), mask)
    # Caption strip.
    c.rect(x0, y1 - ch, x1, y1, fill=CAPSTRIP)
    c.line([(x0, y1 - ch), (x1, y1 - ch)], CARDB, 0.6)
    col = REGION[region][1]
    c.text(x0 + 6, y1 - ch + (ch - psize) / 2 - 1.2, place, "cond_b",
           psize, col, element=el + "-place")
    c.text(x1 - 6, y1 - ch + (ch - ssize) / 2 - 1.3, sources, "cond",
           ssize, GREY, anchor="ra", element=el + "-src")
    # Red label pill, top right.
    w = c.textw(label, "sans_b", lsize) + 14
    h = lsize + 8
    px1 = x1 - 6
    c.rrect(px1 - w, y0 + 6, px1, y0 + 6 + h, h / 2, fill=RED)
    c.text(px1 - w / 2, y0 + 6 + h / 2 + 0.4, label, "sans_b", lsize,
           WHITE, anchor="mm", element=el + "-label")


# ---------------------------------------------------------------- masthead
def draw_masthead(c):
    n_stories = len(ALL_STORIES)
    n_regions = len({s["region"] for s in ALL_STORIES})
    n_topics = len({s["topic"] for s in ALL_STORIES})
    # Top line, centred as one unit.
    run1 = "THE WORLD IN ONE DAY  \u00b7  "
    run2 = ("%d STORIES  \u00b7  %d REGIONS  \u00b7  %d TOPICS  \u00b7  "
            "EVERY ONE NEW ON MONDAY 23 NOVEMBER"
            % (n_stories, n_regions, n_topics))
    w1 = c.textw(run1, "cond_b", 12)
    w2 = c.textw(run2, "cond_b", 12)
    x = 512 - (w1 + w2) / 2
    c.text(x, 6, run1, "cond_b", 12, INK, element="topline")
    c.text(x + w1, 6, run2, "cond_b", 12, RED, element="topline")
    # Date.
    c.text(512, 19, "Monday 23 November 2026", "serif_b", 58, INK,
           anchor="ma", element="date")
    box = c.d.textbbox((512 * S, 19 * S), "Monday 23 November 2026",
                       font=font("serif_b", 58), anchor="ma")
    ry = box[3] / S + 4
    # Double rule.
    c.line([(12, ry), (1012, ry)], INK, 2.0)
    c.line([(12, ry + 3), (1012, ry + 3)], INK, 0.7)
    # Deck.
    c.text(512, ry + 6,
           "Kyiv says its drones sank a Russian warship  \u00b7  "
           "Iran vows to fight US blockade  \u00b7  "
           "Nvidia brings back Huang, shares +31.5%",
           "serif_i", 16, RED, anchor="ma", element="deck")
    # Background bar.
    bar_top = ry + 27
    bar_bot = ry + 44
    c.rrect(12, bar_top, 1012, bar_bot, 8.5, fill=BGBAR)
    bg_runs = [("BACKGROUND", "cond_b", 11, NAVY),
               ("  ", "cond", 11, INK),
               ("US\u2013Israel war with Iran since Feb 2026  \u00b7  "
                "US naval blockade of Iran\u2019s ports  \u00b7  "
                "Russia\u2019s war on Ukraine since 2022  \u00b7  "
                "COP31 ended 22 Nov with no deal", "cond", 11, INK)]
    # Centre the runs as one unit: measure, then draw.
    total = sum(c.textw(t, k, s) for t, k, s, _ in bg_runs) + 8
    bx = 512 - total / 2
    c.text(bx, bar_top + 2.3, "BACKGROUND", "cond_b", 11, NAVY,
           element="bgbar")
    bx += c.textw("BACKGROUND", "cond_b", 11) + 8
    c.text(bx, bar_top + 2.3,
           "US\u2013Israel war with Iran since Feb 2026  \u00b7  "
           "US naval blockade of Iran\u2019s ports  \u00b7  "
           "Russia\u2019s war on Ukraine since 2022  \u00b7  "
           "COP31 ended 22 Nov with no deal",
           "cond", 11, INK, element="bgbar")
    # Region pills, centred as a row.
    counts = {}
    for s in ALL_STORIES:
        counts[s["region"]] = counts.get(s["region"], 0) + 1
    pill_top = bar_top + 21
    labels = []
    for key, name, col in REGIONS:
        labels.append(("%s %d" % (name, counts[key]), col))
    widths = [c.textw(t, "cond_b", 11) + 14 for t, _ in labels]
    row_w = sum(widths) + 5 * (len(labels) - 1)
    px = 512 - row_w / 2
    for (label, col), w in zip(labels, widths):
        c.rrect(px, pill_top, px + w, pill_top + 17, 8.5, fill=col)
        c.text(px + w / 2, pill_top + 8.8, label, "cond_b", 11, WHITE,
               anchor="mm", element="pill-" + label)
        px += w + 5
    # Timeline.
    ty = pill_top + 21
    c.rrect(12, ty, 70, ty + 31, 6, fill=RED)
    c.text(41, ty + 3, "THE DAY", "cond_b", 10.6, WHITE, anchor="ma",
           element="timeline-label")
    c.text(41, ty + 16.5, "IN UTC", "cond_b", 10.6, WHITE, anchor="ma",
           element="timeline-label")
    tw = (1012 - 76 + 5) / 7
    for i, (t, ev) in enumerate(TIMELINE):
        cx0 = 76 + i * tw
        cx1 = cx0 + tw - 5
        c.rrect(cx0 + 0.8, ty + 1.6, cx1 + 0.8, ty + 31 + 1.6, 6,
                fill=SHADOW)
        c.rrect(cx0, ty, cx1, ty + 31, 6, fill=WHITE, outline=CARDB,
                width=0.8)
        c.text(cx0 + 7, ty + 1.2, t, "sans_b", 13.4, RED,
               element="tl-time-%d" % i)
        c.text(cx0 + 7, ty + 17, ev, "cond_b", 10.4, INK,
               element="tl-ev-%d" % i)
    return ty + 31 + 4


# ---------------------------------------------------------------- leads
def lead_height(lead):
    """Height of one lead card's content, from the row top (201)."""
    why_runs = [("Why it matters: ", "cond_b", 11.4,
                 REGION[lead["region"]][1]),
                (lead["why"], "cond_b", 11.4, INK)]
    why_lines = len(wrap_runs(why_runs, 240))
    # picture 207-307; kicker 314; headline 334 (+2 lines); body (+2 lines);
    # why at 410.2; 8 px bottom padding.
    return (410.2 + why_lines * 14 + 8) - 201


def draw_lead(c, img, lead, x0, top, bottom):
    el = "lead%d" % lead["n"]
    col = REGION[lead["region"]][1]
    card(c, x0, top, x0 + 260, bottom, 8)
    ix = x0 + 6
    iright = x0 + 260 - 6
    picture_panel(img, c, ix, 207, iright, 307, lead["region"],
                  lead["place"], lead["label"], 15, 10.2, 10.2,
                  lead["sources"], PICS[lead["pic"]], el)
    y = 314
    round_badge(c, ix + 9, y + 7, lead["n"], col, 9, 11, el + "-badge")
    kx = ix + 23
    if lead["follow"]:
        c.text(kx, y, "\u21bb", "cond_b", 12, UPD, element=el + "-kicker")
        kx += c.textw("\u21bb", "cond_b", 12) + 3
    kicker = "%s \u00b7 %s" % (lead["region"], lead["field"])
    c.text(kx, y + 1, kicker, "cond_b", 10.2, col, element=el + "-kicker")
    tag_chip(c, iright, y - 1, lead["cert"], 9.2, el + "-chip")
    y += 20
    y += draw_para(c, ix, y,
                   [(lead["headline"], "sans_b", 18, INK)], 248, 19.6,
                   el + "-headline")
    y += 3
    y += draw_para(c, ix, y, [(lead["body"], "cond", 12.4, LEADBODY)],
                   248, 15, el + "-body")
    y += 4
    why_runs = [("Why it matters: ", "cond_b", 11.4, col),
                (lead["why"], "cond_b", 11.4, INK)]
    h = draw_para(c, ix + 8, y, why_runs, 240, 14, el + "-why")
    c.rect(ix, y - 1, ix + 3, y + h - 2, fill=col)


def draw_numbers(c, top, bottom):
    card(c, 822, top, 1012, bottom, 8, fill=NAVY, outline=NAVY)
    c.text(832, 209, "THE DAY IN NUMBERS", "cond_b", 11.4, WHITE,
           element="numbers-title")
    c.line([(832, 225), (1002, 225)], NUMLINE, 1)
    rh = (bottom - 8 - 231) / 6
    for i, (num, region, label, src) in enumerate(NUMBERS):
        ry = 231 + i * rh
        col = lighten(REGION[region][1])
        c.text(832, ry, num, "sans_b", 22, col,
               element="numbers-num-%d" % i)
        c.text(1002, ry + 7, src, "cond", 9.6, NUMSRC, anchor="ra",
               element="numbers-src-%d" % i)
        c.text(832, ry + 24, label, "cond", 10.8, NUMLBL,
               element="numbers-lbl-%d" % i)


# ---------------------------------------------------------------- cards
def draw_card(c, img, st, x0, top):
    el = "card%d" % st["n"]
    col = REGION[st["region"]][1]
    card(c, x0, top, x0 + 192, top + 140.2, 7)
    ix = x0 + 5
    iright = x0 + 192 - 5
    picture_panel(img, c, ix, top + 5, iright, top + 65, st["region"],
                  st["place"], st["label"], 13, 9.8, 10.4, st["sources"],
                  PICS[st["pic"]], el)
    y = top + 71
    round_badge(c, ix + 8, y + 6, st["n"], col, 8, 10, el + "-badge")
    kx = ix + 19
    if st["follow"]:
        c.text(kx, y - 1, "\u21bb", "cond_b", 11.4, UPD,
               element=el + "-kicker")
        kx += c.textw("\u21bb", "cond_b", 11.4) + 2
    kicker = "%s \u00b7 %s" % (st["topic"].upper(), st["field"])
    c.text(kx, y, kicker, "cond_b", 10.2, col, element=el + "-kicker")
    certainty_icon(c, st["cert"], iright - 7, y + 6, 6.8)
    y += 16
    draw_para(c, ix + 1, y, [(st["headline"], "cond_b", 14.2, INK)],
              180, 15.4, el + "-headline")

# ---------------------------------------------------------------- list
def draw_list(c):
    card(c, 12, 750.6, 710, 931.6, 8)
    n_list = len(LIST)
    c.text(22, 757.6,
           "ALSO ON MONDAY 23 NOVEMBER \u2014 %d MORE STORIES" % n_list,
           "cond_b", 11.4, NAVY, element="list-title")
    c.text(700, 758.1, "place \u00b7 what happened \u00b7 source \u00b7 how sure",
           "cond", 10.4, GREY, anchor="ra", element="list-head")
    y0 = 774.6
    rh = (931.6 - 6 - y0) / 11
    for col_i, col_x in enumerate((22, 367)):
        for row in range(11):
            st = LIST[col_i * 11 + row]
            ry = y0 + row * rh
            el = "list%d" % st["n"]
            if row % 2 == 0:
                c.rrect(col_x - 3, ry - 1.5, col_x + 336, ry + rh - 1.5, 3,
                        fill=ZEBRA)
            square_badge(c, col_x + 9, ry + rh / 2 - 0.5, st["n"],
                         REGION[st["region"]][1], el + "-badge")
            ty = ry + rh / 2 - 12.2 * 0.62
            tx = col_x + 21
            if st["follow"]:
                c.text(tx, ty, "\u21bb", "cond_b", 12.2, UPD,
                       element=el)
                tx += c.textw("\u21bb", "cond_b", 12.2) + 3
            c.text(tx, ty, st["place"], "cond_b", 12.2,
                   REGION[st["region"]][1], element=el)
            tx += c.textw(st["place"], "cond_b", 12.2) + 5
            c.text(tx, ty, st["text"], "cond", 12.2, INK, element=el)
            text_end = tx + c.textw(st["text"], "cond", 12.2)
            src_x = col_x + 333 - 17
            src_w = c.textw(st["source"], "cond", 10.6)
            if text_end > src_x - src_w - 4:
                print("WARNING list %d text within 4px of source"
                      % st["n"])
            c.text(src_x, ty + 1.6, st["source"], "cond", 10.6, GREY,
                   anchor="ra", element=el + "-src")
            certainty_icon(c, st["cert"], col_x + 333 - 7,
                           ry + rh / 2 - 0.5, 6.4)
    c.line([(22 + 333 + 6, y0), (22 + 333 + 6, y0 + 11 * rh - 3)], RULE, 1)


# ---------------------------------------------------------------- map
def project(lon, lat):
    scale = 276 / 306
    return (728 + (lon + 126) * scale, 774.6 + (58 - lat) * scale)


def place_badges():
    """Place round badges for stories 1-12 (spec 8.6).

    Returns {n: (bx, by)} badge centres. The true point is tried first,
    then rings of radius 10, 14, 18, 22, 26 in the order up, right, down,
    left, up-right, down-right, down-left, up-left. A spot must sit more
    than 8 px inside the map box vertically, inside it horizontally, at
    least 15 px from every badge already placed, and at least 9 px from
    the true points of pins not yet placed."""
    pins = [s for s in LEADS + CARDS if s["pin"] is not None]
    true_pt = {s["n"]: project(*s["pin"]) for s in pins}

    def crowded(n):
        x, y = true_pt[n]
        cnt = 0
        for m, (mx, my) in true_pt.items():
            if m == n:
                continue
            if abs(mx - x) + abs(my - y) <= 25:
                cnt += 1
        return cnt

    order = sorted(true_pt, key=lambda n: (-crowded(n), n))
    placed = {}
    remaining = set(true_pt)
    offsets = [(0, 0)]
    for r in (10, 14, 18, 22, 26):
        d = 0.7 * r
        offsets += [(0, -r), (r, 0), (0, r), (-r, 0),
                    (d, -d), (d, d), (-d, d), (-d, -d)]
    for n in order:
        tx, ty = true_pt[n]
        remaining.discard(n)
        chosen = None
        for dx, dy in offsets:
            bx, by = tx + dx, ty + dy
            if not (728 + 8 < bx < 1004 - 8):
                continue
            if not (774.6 + 8 < by < 863.0 - 8):
                continue
            ok = True
            for (px, py) in placed.values():
                if math.hypot(bx - px, by - py) < 15:
                    ok = False
                    break
            if not ok:
                continue
            for m in remaining:
                mx, my = true_pt[m]
                if math.hypot(bx - mx, by - my) < 9:
                    ok = False
                    break
            if ok:
                chosen = (bx, by)
                break
        if chosen is None:
            chosen = (tx, ty - 10)
        placed[n] = chosen
    return placed, true_pt


def draw_map(c, img):
    card(c, 720, 750.6, 1012, 931.6, 8)
    pinned = sum(1 for s in LEADS + CARDS if s["pin"] is not None)
    pinned += sum(1 for s in LIST if s["pin"] is not None)
    total = len(ALL_STORIES)
    if pinned == total:
        title = "ALL %d STORIES ON THE MAP" % total
    else:
        title = "%d OF %d STORIES ON THE MAP" % (pinned, total)
    c.text(730, 757.6, title, "cond_b", 11, NAVY, element="map-title")
    # Key, laid out right to left.
    k = 1002 - c.textw("14\u201335", "cond", 10)
    c.text(k, 758.2, "14\u201335", "cond", 10, INK, element="map-key")
    c.rect(k - 9, 761, k - 4, 766, fill=GREY)
    k -= 14 + c.textw("1\u201313", "cond", 10)
    c.text(k, 758.2, "1\u201313", "cond", 10, INK, element="map-key")
    c.ellipse(k - 11, 759.2, k - 3, 767.2, fill=GREY)
    # Ocean.
    c.rrect(728, 774.6, 1004, 863.0, 4, fill=OCEAN)
    # Land, clipped to the ocean box: polygons where the box mask agrees.
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "world_land.json"), encoding="utf-8") as f:
        rings = json.load(f)
    mask = Image.new("L", (W * S, H * S), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([728 * S, round(774.6 * S), 1004 * S,
                          round(863.0 * S)], radius=4 * S, fill=255)
    land_tinted = Image.new("RGB", (W * S, H * S), LANDC)
    # Paste land only where both the polygon mask and the box mask agree.
    poly_mask = Image.new("L", (W * S, H * S), 0)
    pd = ImageDraw.Draw(poly_mask)
    for ring in rings:
        pts = [(project(lon, lat)[0] * S, project(lon, lat)[1] * S)
               for lon, lat in ring]
        pd.polygon(pts, fill=255)
    both = Image.composite(poly_mask, Image.new("L", (W * S, H * S), 0),
                           mask)
    img.paste(land_tinted, (0, 0), both)
    # List dots first.
    for s in LIST:
        if s["pin"] is None:
            continue
        x, y = project(*s["pin"])
        col = REGION[s["region"]][1]
        c.rect(x - 2.6, y - 2.6, x + 2.6, y + 2.6, fill=col, outline=WHITE,
               width=0.7)
    # Round badges 1-12 with leader lines.
    placed, true_pt = place_badges()
    for n, (bx, by) in placed.items():
        st = ALL_STORIES[n - 1]
        col = REGION[st["region"]][1]
        tx, ty = true_pt[n]
        if abs(bx - tx) > 0.01 or abs(by - ty) > 0.01:
            c.line([(tx, ty), (bx, by)], col, 0.9)
            c.ellipse(tx - 1.6, ty - 1.6, tx + 1.6, ty + 1.6, fill=col)
    for n, (bx, by) in placed.items():
        st = ALL_STORIES[n - 1]
        round_badge(c, bx, by, n, REGION[st["region"]][1], 7.2, 9.2,
                    "map-badge-%d" % n)
    # What we don't know yet.
    box_top, box_bot = 869.0, 924.6
    c.rrect(728, box_top, 1004, box_bot, 5, fill=UNK_FILL,
            outline=UNK_OUT, width=0.9)
    c.text(735, box_top + 3, "WHAT WE DON\u2019T KNOW YET", "cond_b", 11,
           UNK_TITLE, element="unknowns-title")
    first_y = box_top + 17
    rh = (box_bot - 3 - first_y) / 3
    for i, (label, text) in enumerate(UNKNOWNS):
        ry = first_y + i * rh
        c.text(735, ry, label, "cond_b", 10.8, INK,
               element="unknowns-%d" % i)
        tx = 735 + c.textw(label, "cond_b", 10.8) + 4
        c.text(tx, ry, text, "cond", 10.8, INK,
               element="unknowns-%d" % i)


# ---------------------------------------------------------------- date check + footer
def draw_datecheck(c):
    top, bot = 939.6, 1001.0
    card(c, 12, top, 1012, bot, 7)
    c.rect(12, top + 4, 16, bot - 4, fill=RED)
    pill_w = c.textw("DATE CHECK", "sans_b", 11.4) + 14
    cy = (top + bot) / 2
    c.rrect(24, cy - 9, 24 + pill_w, cy + 9, 9, fill=RED)
    c.text(24 + pill_w / 2, cy + 0.4, "DATE CHECK", "sans_b", 11.4, WHITE,
           anchor="mm", element="datecheck-pill")
    dx = 12 + 14 + c.textw("DATE CHECK", "sans_b", 11.4) + 24
    width = 1012 - 10 - dx
    follow = " \u00b7 ".join("%s (%s)" % (name, when)
                             for name, when in FOLLOWUPS) + ". "
    runs = [
        ("All %d happened or were first reported on Mon 23 Nov "
         "(local time). " % len(ALL_STORIES), "cond", 11.2, INK),
        ("\u21bb" + NBSP + "Follow-ups, ", "cond_b", 11.2, UPD),
        ("shown for their 23 Nov turn: ", "cond_b", 11.2, UPD),
        (follow, "cond", 11.2, INK),
        ("Figures that changed: ", "cond_b", 11.2, RED),
        ("Hodeidah toll 10 \u2192 17 (Houthi media) \u00b7 Indonesia fire "
         "3 \u2192 24 dead. ", "cond", 11.2, INK),
        ("Not yet (Tue" + NBSP + "24): ", "cond_b", 11.2, RED),
        ("Ariane 6 retry \u00b7 Ramaphosa in parliament. ", "cond", 11.2,
         INK),
        ("Left out: ", "cond_b", 11.2, RED),
        ("Hong Kong results (Sun" + NBSP + "22), BepiColombo at Mercury "
         "(Sat" + NBSP + "21), first Peru quake toll (Sat" + NBSP + "21).",
         "cond", 11.2, INK),
    ]
    draw_para(c, dx, top + 6, runs, width, 12.6, "datecheck")


def draw_footer(c):
    y = 1008.5
    x = 14
    c.text(x, y, "HOW SURE", "cond_b", 11.6, INK, element="footer")
    x += c.textw("HOW SURE", "cond_b", 11.6) + 7
    for kind, text in (
            ("CONFIRMED", "CONFIRMED: official source or 2+ outlets named"),
            ("STATED", "STATED: one party\u2019s claim, not checked"),
            ("UNVERIFIED", "UNVERIFIED: unconfirmed, or attacker unknown")):
        certainty_icon(c, kind, x + 7.5, 1016, 7.3,
                       element="footer-" + kind)
        x += 18
        c.text(x, y, text, "cond", 11.6, INK, element="footer")
        x += c.textw(text, "cond", 11.6) + 8
    c.text(1010, y, "Drawings, not photos", "cond", 11.6, GREY,
           anchor="ra", element="footer-right")


# ---------------------------------------------------------------- render
def main():
    img = Image.new("RGB", (W * S, H * S), PAPER)
    c = Canvas(img)
    masthead_bottom = draw_masthead(c)
    print("masthead bottom: %.1f (spec ~193)" % masthead_bottom)

    # Leads: measure first, all cards take the tallest height.
    heights = [lead_height(lead) for lead in LEADS]
    lead_h = max(heights)
    lead_top = 201
    lead_bot = lead_top + lead_h
    print("lead heights: %s -> %.1f, bottom %.1f"
          % (["%.1f" % h for h in heights], lead_h, lead_bot))
    for i, lead in enumerate(LEADS):
        draw_lead(c, img, lead, 12 + i * 270, lead_top, lead_bot)
    draw_numbers(c, lead_top, lead_bot)

    # Picture cards, 2 rows x 5.
    row1 = lead_bot + 8
    for r in range(2):
        for col_i in range(5):
            st = CARDS[r * 5 + col_i]
            draw_card(c, img, st, 12 + 202 * col_i, row1 + r * (140.2 + 8))
    print("cards bottom: %.1f (spec 742.6)" % (row1 + 140.2 + 8 + 140.2))

    draw_list(c)
    draw_map(c, img)
    draw_datecheck(c)
    draw_footer(c)

    problems = check_registry()
    print("text boxes registered:", len(REGISTRY))
    if problems:
        print("OVERLAP/BOUNDS PROBLEMS (%d):" % len(problems))
        for p in problems:
            print("  -", p)
    else:
        print("overlap check: EMPTY")

    # Badge placement audit vs the spec's expected offsets.
    placed, true_pt = place_badges()
    expected = {1: (-7, 7), 2: (0, 0), 3: (10, 0), 4: (0, 0), 5: (7, 7),
                6: (0, 0), 7: (0, 10), 8: (0, 0), 9: (0, -10),
                10: (0, 0), 11: (0, 0), 12: (0, -10)}
    bad = []
    for n, (ex, ey) in expected.items():
        bx, by = placed[n]
        tx, ty = true_pt[n]
        if abs((bx - tx) - ex) > 0.6 or abs((by - ty) - ey) > 0.6:
            bad.append("badge %d: got (%.1f, %.1f), expected (%d, %d)"
                       % (n, bx - tx, by - ty, ex, ey))
    if bad:
        print("BADGE PLACEMENT MISMATCHES:")
        for b in bad:
            print("  -", b)
    else:
        print("badge placement: matches spec")

    # Headline line-count audit.
    for st in LEADS:
        n = len(wrap_runs([(st["headline"], "sans_b", 18, INK)], 248))
        if n != 2:
            print("WARNING lead %d headline: %d lines" % (st["n"], n))
    for st in CARDS:
        n = len(wrap_runs([(st["headline"], "cond_b", 14.2, INK)], 180))
        if n > 3:
            print("WARNING card %d headline: %d lines" % (st["n"], n))

    # Downscale once, quantize, save.
    small = img.resize((W, H), Image.LANCZOS)
    small = small.quantize(colors=256, method=Image.MEDIANCUT,
                           dither=Image.Dither.NONE)
    out = sys.argv[1] if len(sys.argv) > 1 else "entry.png"
    small.save(out, optimize=True)
    size = os.path.getsize(out)
    print("saved %s: %d bytes" % (out, size))
    if size >= 300 * 1024:
        print("WARNING: over the 300 KB target")
    return 0 if not problems and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
