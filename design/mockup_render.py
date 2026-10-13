"""Mockup renderer for KD's Kindle 4 dashboard (600 x 800, greyscale)."""
from PIL import Image, ImageDraw, ImageFont
import sys, os

OUT = sys.argv[1]
F = "/usr/share/fonts/opentype/inter/"
def font(name, size): return ImageFont.truetype(F + name, size)

W, H = 600, 800
M = 36  # side margin
INK, SOFT, RULE = 0, 85, 175

# ---- data (latest figures found while mocking up) ----
USD_AED = 3.6725
USD_INR = 96.964336
AED_INR = USD_INR / USD_AED
GOLD_AED = {"24K": 497.75, "22K": 460.75}
DATE_TXT = "TUE 13 OCT"
UPDATED = "Updated 18:00"


def inr(x, dp=0):
    """Indian digit grouping, e.g. 100000 -> 1,00,000"""
    s = f"{x:.{dp}f}"
    whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head: parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return whole + ("." + frac if frac else "")


def text(d, xy, s, f, fill=INK, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def tracked(d, x, y, s, f, fill=SOFT, track=2.5, anchor_right=False):
    widths = [d.textlength(ch, font=f) for ch in s]
    total = sum(widths) + track * (len(s) - 1)
    if anchor_right: x -= total
    for ch, w in zip(s, widths):
        d.text((x, y), ch, font=f, fill=fill); x += w + track


def header(d, kicker, sub):
    small = font("Inter-SemiBold.otf", 17)
    tracked(d, M, 34, kicker, small, fill=INK)
    tracked(d, W - M, 34, DATE_TXT, small, fill=INK, anchor_right=True)
    reg = font("Inter-Regular.otf", 19)
    text(d, (M, 62), sub, reg, SOFT)
    text(d, (W - M, 62), UPDATED, reg, SOFT, anchor="ra")
    d.line([(M, 100), (W - M, 100)], fill=INK, width=3)


def footer(d, page, total):
    y = H - 46
    d.line([(M, y - 22), (W - M, y - 22)], fill=RULE, width=1)
    for i in range(total):
        cx = M + 8 + i * 22
        if i == page:
            d.ellipse([cx - 6, y - 6 + 8, cx + 6, y + 6 + 8], fill=INK)
        else:
            d.ellipse([cx - 6, y - 6 + 8, cx + 6, y + 6 + 8], outline=INK, width=2)
    reg = font("Inter-Medium.otf", 17)
    text(d, (W - M, y + 8), f"{page + 1} / {total}   ◀ ▶ flip", reg, SOFT, anchor="rm")


def pill(d, x, y, label):
    f = font("Inter-Bold.otf", 24)
    w = d.textlength(label, font=f)
    d.rounded_rectangle([x, y, x + w + 28, y + 40], radius=8, fill=INK)
    text(d, (x + 14 + w / 2, y + 20), label, f, 255, anchor="mm")


def gold_page():
    img = Image.new("L", (W, H), 255); d = ImageDraw.Draw(img)
    header(d, "GOLD  ·  DUBAI", "Retail rate, per gram")
    big = font("InterDisplay-Bold.otf", 84)
    cur = font("InterDisplay-SemiBold.otf", 30)
    mid = font("InterDisplay-SemiBold.otf", 36)
    lab = font("Inter-Medium.otf", 16)
    y = 130
    for i, (k, aed) in enumerate(GOLD_AED.items()):
        pill(d, M, y, k)
        # AED headline
        text(d, (M, y + 66), "AED", cur, SOFT)
        text(d, (M + 72, y + 52), f"{aed:,.2f}", big, INK)
        # INR and USD row
        ry = y + 168
        text(d, (M, ry), "INDIA RUPEE", lab, SOFT)
        text(d, (M, ry + 22), f"₹ {inr(aed * AED_INR)}", mid, INK)
        cx = W // 2 + 20
        text(d, (cx, ry), "US DOLLAR", lab, SOFT)
        text(d, (cx, ry + 22), f"$ {aed / USD_AED:,.2f}", mid, INK)
        y += 300
        if i == 0:
            d.line([(M, y - 40), (W - M, y - 40)], fill=RULE, width=2)
    footer(d, 0, 2)
    return img


def fx_page():
    img = Image.new("L", (W, H), 255); d = ImageDraw.Draw(img)
    header(d, "EXCHANGE  ·  AED INR USD", "Mid-market rates")
    lbl = font("InterDisplay-SemiBold.otf", 34)
    val = font("InterDisplay-Bold.otf", 58)
    rows = [
        ("1 AED", f"₹ {AED_INR:.2f}"),
        ("1 USD", f"₹ {USD_INR:.2f}"),
        ("1 USD", f"AED {USD_AED:.4f}"),
        ("100 INR", f"AED {100 / AED_INR:.2f}"),
    ]
    y = 128
    for i, (l, v) in enumerate(rows):
        text(d, (M, y + 58), l, lbl, SOFT, anchor="ls")
        text(d, (W - M, y + 62), v, val, INK, anchor="rs")
        y += 92
        d.line([(M, y - 10), (W - M, y - 10)], fill=RULE, width=1 if i < 3 else 3)
        if i == 3:
            d.line([(M, y - 10), (W - M, y - 10)], fill=INK, width=3)
    # quick convert
    small = font("Inter-SemiBold.otf", 17)
    tracked(d, M, y + 18, "QUICK CONVERT", small, fill=INK)
    q = font("InterDisplay-SemiBold.otf", 32)
    qy = y + 58
    for l, v in [("AED 1,000", f"₹ {inr(1000 * AED_INR)}"),
                 (f"₹ {inr(100000)}", f"AED {100000 / AED_INR:,.0f}"),
                 ("$ 1,000", f"₹ {inr(1000 * USD_INR)}")]:
        text(d, (M, qy), l, q, SOFT)
        text(d, (W - M, qy), v, q, INK, anchor="ra")
        qy += 54
    footer(d, 1, 2)
    return img


os.makedirs(OUT, exist_ok=True)
g, x = gold_page(), fx_page()
g.save(os.path.join(OUT, "page1_gold.png"))
x.save(os.path.join(OUT, "page2_exchange.png"))

# side by side preview inside a simple Kindle-style frame
def framed(screen):
    bw, top, bot = 46, 70, 150
    fr = Image.new("L", (W + 2 * bw, H + top + bot), 0)
    d = ImageDraw.Draw(fr)
    d.rounded_rectangle([0, 0, fr.width - 1, fr.height - 1], radius=36, fill=70)
    d.rectangle([bw - 4, top - 4, bw + W + 3, top + H + 3], fill=40)
    fr.paste(screen, (bw, top))
    # 5-way pad hint
    cx, cy = fr.width // 2, top + H + bot // 2
    d.rounded_rectangle([cx - 34, cy - 34, cx + 34, cy + 34], radius=10, outline=150, width=3)
    # side page-turn buttons
    for x0 in (8, fr.width - 18):
        d.rounded_rectangle([x0, top + 260, x0 + 10, top + 520], radius=4, fill=120)
    return fr

a, b = framed(g), framed(x)
gap, pad = 60, 40
prev = Image.new("L", (a.width * 2 + gap + pad * 2, a.height + pad * 2), 236)
prev.paste(a, (pad, pad)); prev.paste(b, (pad + a.width + gap, pad))
prev.save(os.path.join(OUT, "preview.png"))
print("ok")
