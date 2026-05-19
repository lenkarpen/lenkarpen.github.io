#!/usr/bin/env python3
"""Build a clean 4-stage flow diagram for LinkedIn 'Projects' media.
Outputs a 1600x900 PNG matching the portfolio's purple palette."""

from PIL import Image, ImageDraw, ImageFont
import textwrap

W, H = 1600, 900
PAD = 70

# Palette (matches portfolio CSS variables)
WHITE = "#FFFFFF"
P50   = "#F4F4FB"
P100  = "#EBEBF8"
P200  = "#D2D2ED"
P400  = "#8B8EC8"
P600  = "#6264A7"
P700  = "#5254A3"
P800  = "#464775"
Z500  = "#71717A"
Z700  = "#3F3F46"
Z900  = "#18181B"

GEORGIA   = "/System/Library/Fonts/Supplemental/Georgia.ttf"
GEORGIA_B = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
HELVETICA = "/System/Library/Fonts/Helvetica.ttc"

def f(path, size):
    return ImageFont.truetype(path, size)

img = Image.new("RGB", (W, H), P50)
d = ImageDraw.Draw(img)

def draw_arrow(draw, x, y, length=40, color=P400, stroke=3):
    """Right-pointing arrow centred vertically on y. x is left edge of shaft."""
    head = 10
    draw.line([(x, y), (x + length - head, y)], fill=color, width=stroke)
    draw.polygon(
        [(x + length, y),
         (x + length - head, y - head * 0.7),
         (x + length - head, y + head * 0.7)],
        fill=color,
    )

# ── Title block ─────────────────────────────────────────────────────────
d.text((PAD, 56), "End-to-End VDI Onboarding Pipeline",
       fill=P800, font=f(GEORGIA_B, 46))

# Subtitle with manually-drawn arrow
subtitle_font = f(HELVETICA, 22)
part1 = "From ITSM ticket"
part2 = "Active Directory security group, in one reproducible run"
subtitle_y = 128
d.text((PAD, 116), part1, fill=Z500, font=subtitle_font)
w1 = d.textbbox((0, 0), part1, font=subtitle_font)[2]
arrow_x = PAD + w1 + 16
draw_arrow(d, arrow_x, subtitle_y, length=32, color=Z500, stroke=2)
d.text((arrow_x + 48, 116), part2, fill=Z500, font=subtitle_font)

# ── Stage cards ─────────────────────────────────────────────────────────
stages = [
    ("01", "Parse",
     "Extract ~10 structured fields from each ticket's HTML metadata cell.",
     "Python · BeautifulSoup"),
    ("02", "Reconcile",
     "Match parsed records to the identity warehouse with name normalisation.",
     "pandas"),
    ("03", "Detect",
     "Check (pool, region) against rolling 12-month history; flag anomalies.",
     "Python · history lookup"),
    ("04", "Provision",
     "Bulk-add users to AD groups, then re-read membership to verify.",
     "PowerShell · AD"),
]

TOP = 210
CARD_H = 430
ARROW_W = 56
N = len(stages)
CARD_W = (W - PAD * 2 - ARROW_W * (N - 1)) / N

def wrap(draw, text, xy, max_w, font, fill, line_h):
    x, y = xy
    words = text.split()
    line = ""
    for w in words:
        trial = (line + " " + w).strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] > max_w and line:
            draw.text((x, y), line, fill=fill, font=font)
            y += line_h
            line = w
        else:
            line = trial
    if line:
        draw.text((x, y), line, fill=fill, font=font)

for i, (num, title, body, tag) in enumerate(stages):
    x = PAD + i * (CARD_W + ARROW_W)
    y = TOP

    # Card
    d.rounded_rectangle([(x, y), (x + CARD_W, y + CARD_H)],
                        radius=20, fill=WHITE, outline=P200, width=2)

    # Top stripe
    d.rectangle([(x + 2, y + 2), (x + CARD_W - 2, y + 10)], fill=P700)

    # Number badge
    bx, by, bsize = x + 28, y + 36, 56
    d.ellipse([(bx, by), (bx + bsize, by + bsize)], fill=P100)
    d.text((bx + bsize / 2, by + bsize / 2), num,
           fill=P700, font=f(GEORGIA_B, 24), anchor="mm")

    # Title
    d.text((x + 28, y + 130), title, fill=Z900, font=f(GEORGIA_B, 32))

    # Body (wrapped)
    wrap(d, body, (x + 28, y + 195),
         max_w=CARD_W - 56, font=f(HELVETICA, 18),
         fill=Z700, line_h=28)

    # Tag chip
    chip_y = y + CARD_H - 64
    tag_font = f(HELVETICA, 14)
    tw = d.textbbox((0, 0), tag, font=tag_font)
    chip_w = (tw[2] - tw[0]) + 28
    d.rounded_rectangle([(x + 28, chip_y), (x + 28 + chip_w, chip_y + 32)],
                        radius=16, fill=P100)
    d.text((x + 28 + chip_w / 2, chip_y + 16), tag,
           fill=P800, font=tag_font, anchor="mm")

    # Arrow
    if i < N - 1:
        ax = x + CARD_W + 8
        ay = y + CARD_H / 2
        d.line([(ax, ay), (ax + ARROW_W - 24, ay)], fill=P400, width=4)
        d.polygon([(ax + ARROW_W - 8, ay),
                   (ax + ARROW_W - 24, ay - 10),
                   (ax + ARROW_W - 24, ay + 10)], fill=P400)

# ── Stats strip ─────────────────────────────────────────────────────────
STATS_TOP = TOP + CARD_H + 50
stats = [
    ("~250",          "workers onboarded / month"),
    ("__ARROW__",     "daily processing time"),     # 2h -> <10 min, drawn below
    ("1 year",        "history in one tracker"),
    ("SOP-driven",    "operated by a teammate"),
]
col_w = (W - PAD * 2) / 4
stat_font = f(GEORGIA_B, 30)
for i, (num, label) in enumerate(stats):
    cx = PAD + i * col_w + col_w / 2
    if num == "__ARROW__":
        left, right = "2h", "<10 min"
        lw = d.textbbox((0, 0), left,  font=stat_font)[2]
        rw = d.textbbox((0, 0), right, font=stat_font)[2]
        gap, arrow_len = 14, 40
        total = lw + gap + arrow_len + gap + rw
        sx = cx - total / 2
        d.text((sx, STATS_TOP - 18), left, fill=P800, font=stat_font)
        draw_arrow(d, sx + lw + gap, STATS_TOP, length=arrow_len, color=P800, stroke=3)
        d.text((sx + lw + gap + arrow_len + gap, STATS_TOP - 18),
               right, fill=P800, font=stat_font)
    else:
        d.text((cx, STATS_TOP), num,
               fill=P800, font=stat_font, anchor="mm")
    d.text((cx, STATS_TOP + 42), label,
           fill=Z500, font=f(HELVETICA, 15), anchor="mm")

# ── Footer ──────────────────────────────────────────────────────────────
d.text((PAD, H - 48), "Olena Karpenko · lenkarpen.github.io",
       fill=Z500, font=f(HELVETICA, 16))

OUT = "/Users/okarpenk/Library/CloudStorage/OneDrive-Microsoft/Documents/Portfolio/pipeline-diagram.png"
img.save(OUT, "PNG", optimize=True)
print(f"Saved: {OUT}")
print(f"Size: {W}×{H} px")
