#!/usr/bin/env python3
"""4-stage flow diagram for LinkedIn 'Projects' media — 2x retina, all-Helvetica."""

from PIL import Image, ImageDraw, ImageFont

# Render at 2x for retina sharpness — final output is 3200x1800 px
SCALE = 2
W, H = 1600 * SCALE, 900 * SCALE
PAD = 70 * SCALE

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

HELVETICA      = "/System/Library/Fonts/Helvetica.ttc"
HELVETICA_REG  = 0
HELVETICA_BOLD = 1

def f(size, bold=False):
    return ImageFont.truetype(
        HELVETICA, size * SCALE,
        index=HELVETICA_BOLD if bold else HELVETICA_REG,
    )

img = Image.new("RGB", (W, H), P50)
d = ImageDraw.Draw(img)

def draw_arrow(draw, x, y, length, color, stroke):
    """Right-pointing arrow centred vertically on y. x is left edge of shaft."""
    head = stroke * 4
    draw.line([(x, y), (x + length - head, y)], fill=color, width=stroke)
    draw.polygon(
        [(x + length, y),
         (x + length - head, y - head * 0.7),
         (x + length - head, y + head * 0.7)],
        fill=color,
    )

# ── Title block ─────────────────────────────────────────────────────────
d.text((PAD, 56 * SCALE), "End-to-End VDI Onboarding Pipeline",
       fill=P800, font=f(46, bold=True))

# Subtitle with manually-drawn arrow
subtitle_font = f(22)
part1 = "From ITSM ticket"
part2 = "Active Directory security group, in one reproducible run"
subtitle_y = 116 * SCALE
arrow_y = subtitle_y + 12 * SCALE
d.text((PAD, subtitle_y), part1, fill=Z500, font=subtitle_font)
w1 = d.textbbox((0, 0), part1, font=subtitle_font)[2]
arrow_x = PAD + w1 + 16 * SCALE
draw_arrow(d, arrow_x, arrow_y, length=32 * SCALE, color=Z500, stroke=2 * SCALE)
d.text((arrow_x + 48 * SCALE, subtitle_y), part2, fill=Z500, font=subtitle_font)

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

TOP = 210 * SCALE
CARD_H = 430 * SCALE
ARROW_W = 56 * SCALE
N = len(stages)
CARD_W = (W - PAD * 2 - ARROW_W * (N - 1)) / N
RADIUS = 20 * SCALE
STRIPE_H = 12 * SCALE
BORDER = 2 * SCALE

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

    cw, ch = int(CARD_W), int(CARD_H)

    # Build the card as a flat image: white body + purple top stripe.
    # Then composite it onto the canvas through a rounded-rectangle mask
    # so the stripe is automatically clipped to the rounded card shape.
    card = Image.new("RGB", (cw, ch), WHITE)
    ImageDraw.Draw(card).rectangle([(0, 0), (cw, STRIPE_H)], fill=P700)

    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [(0, 0), (cw, ch)], radius=RADIUS, fill=255,
    )

    img.paste(card, (int(x), int(y)), mask)

    # Draw the P200 outline on top, matching the card shape
    d.rounded_rectangle(
        [(x, y), (x + CARD_W, y + CARD_H)],
        radius=RADIUS, outline=P200, width=BORDER,
    )

    # Number badge
    bsize = 56 * SCALE
    bx, by = x + 28 * SCALE, y + 36 * SCALE
    d.ellipse([(bx, by), (bx + bsize, by + bsize)], fill=P100)
    d.text((bx + bsize / 2, by + bsize / 2), num,
           fill=P700, font=f(22, bold=True), anchor="mm")

    # Title
    d.text((x + 28 * SCALE, y + 130 * SCALE), title,
           fill=Z900, font=f(30, bold=True))

    # Body (wrapped)
    wrap(d, body,
         (x + 28 * SCALE, y + 195 * SCALE),
         max_w=CARD_W - 56 * SCALE,
         font=f(18),
         fill=Z700, line_h=28 * SCALE)

    # Tag chip
    chip_y = y + CARD_H - 64 * SCALE
    tag_font = f(14, bold=True)
    tw = d.textbbox((0, 0), tag, font=tag_font)
    chip_w = (tw[2] - tw[0]) + 28 * SCALE
    chip_h = 32 * SCALE
    d.rounded_rectangle(
        [(x + 28 * SCALE, chip_y), (x + 28 * SCALE + chip_w, chip_y + chip_h)],
        radius=16 * SCALE, fill=P100,
    )
    d.text((x + 28 * SCALE + chip_w / 2, chip_y + chip_h / 2),
           tag, fill=P800, font=tag_font, anchor="mm")

    # Arrow between cards
    if i < N - 1:
        ax = x + CARD_W + 8 * SCALE
        ay = y + CARD_H / 2
        draw_arrow(d, ax, ay, length=ARROW_W - 16 * SCALE,
                   color=P400, stroke=4 * SCALE)

# ── Stats strip ─────────────────────────────────────────────────────────
STATS_TOP = TOP + CARD_H + 50 * SCALE
stats = [
    ("~250",          "workers onboarded / month"),
    ("__ARROW__",     "daily processing time"),
    ("1 year",        "history in one tracker"),
    ("SOP-driven",    "operated by a teammate"),
]
col_w = (W - PAD * 2) / 4
stat_font = f(30, bold=True)
label_font = f(15)
for i, (num, label) in enumerate(stats):
    cx = PAD + i * col_w + col_w / 2
    if num == "__ARROW__":
        left, right = "2h", "<10 min"
        lw = d.textbbox((0, 0), left,  font=stat_font)[2]
        rw = d.textbbox((0, 0), right, font=stat_font)[2]
        gap, arrow_len = 14 * SCALE, 40 * SCALE
        total = lw + gap + arrow_len + gap + rw
        sx = cx - total / 2
        d.text((sx, STATS_TOP - 18 * SCALE), left,
               fill=P800, font=stat_font)
        draw_arrow(d, sx + lw + gap, STATS_TOP,
                   length=arrow_len, color=P800, stroke=3 * SCALE)
        d.text((sx + lw + gap + arrow_len + gap, STATS_TOP - 18 * SCALE),
               right, fill=P800, font=stat_font)
    else:
        d.text((cx, STATS_TOP), num,
               fill=P800, font=stat_font, anchor="mm")
    d.text((cx, STATS_TOP + 42 * SCALE), label,
           fill=Z500, font=label_font, anchor="mm")

# ── Footer ──────────────────────────────────────────────────────────────
d.text((PAD, H - 48 * SCALE), "Olena Karpenko · lenkarpen.github.io",
       fill=Z500, font=f(16))

OUT = "/Users/okarpenk/Library/CloudStorage/OneDrive-Microsoft/Documents/Portfolio/pipeline-diagram.png"
img.save(OUT, "PNG", optimize=True)
print(f"Saved: {OUT}")
print(f"Size:  {W}x{H} px  ({SCALE}x resolution)")
