"""Mockup v2 for KD's Kindle 4 dashboard (600 x 800 greyscale, 167 ppi).

E-ink rules used:
  * smallest text is 20 px (about 3 mm tall on the Kindle 4 screen)
  * only black, one dark grey and one mid grey (the panel has 16 grey levels)
  * lines at least 2 px so they do not break up on refresh
"""
from PIL import Image, ImageDraw, ImageFont
import sys, os

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
F = "/usr/share/fonts/opentype/inter/"
def font(name, size): return ImageFont.truetype(F + name, size)

W, H = 600, 800
M = 34
INK, SOFT, RULE = 0, 80, 160
MIN = 20  # smallest text size

# ---- sample data (live version will fetch these every hour) ----
USD_AED = 3.6725
USD_INR = 95.90693
AED_INR = USD_INR / USD_AED
GOLD_AED = {"24K": 497.75, "22K": 460.75}
DAY, DATE_LONG, DATE_SHORT = "WEDNESDAY", "14 October 2026", "WED 14 OCT"
UPDATED = "Updated 16:00"
PAGES = 3


def inr(x, dp=0):
    s = f"{x:.{dp}f}"; whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]; parts = []
        while len(head) > 2: parts.insert(0, head[-2:]); head = head[:-2]
        if head: parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return whole + ("." + frac if frac else "")


def T(d, xy, s, f, fill=INK, anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)


def tracked(d, x, y, s, f, fill=INK, track=2.5, right=False):
    ws = [d.textlength(c, font=f) for c in s]
    tot = sum(ws) + track * (len(s) - 1)
    if right: x -= tot
    for c, w in zip(s, ws):
        d.text((x, y), c, font=f, fill=fill); x += w + track


def pill(d, x, y, label, size=26, h=42):
    f = font("Inter-Bold.otf", size); w = d.textlength(label, font=f)
    d.rounded_rectangle([x, y, x + w + 26, y + h], radius=8, fill=INK)
    T(d, (x + 13 + w / 2, y + h / 2), label, f, 255, anchor="mm")
    return w + 26


def footer(d, page):
    y = H - 44
    d.line([(M, y - 26), (W - M, y - 26)], fill=RULE, width=2)
    for i in range(PAGES):
        cx, cy = M + 9 + i * 26, y
        box = [cx - 8, cy - 8, cx + 8, cy + 8]
        if i == page: d.ellipse(box, fill=INK)
        else: d.ellipse(box, outline=INK, width=3)
    names = ["Home", "Gold", "Exchange"]
    f = font("Inter-SemiBold.otf", 22)
    T(d, (W - M, y), f"◀  {names[page]}  ▶", f, INK, anchor="rm")


def small_header(d, kicker, sub):
    f = font("Inter-Bold.otf", MIN + 1)
    tracked(d, M, 30, kicker, f)
    tracked(d, W - M, 30, DATE_SHORT, f, right=True)
    r = font("Inter-Medium.otf", 22)
    T(d, (M, 62), sub, r, SOFT)
    T(d, (W - M, 62), UPDATED, r, SOFT, anchor="ra")
    d.line([(M, 102), (W - M, 102)], fill=INK, width=3)


# ---------------- page 1: home ----------------
def home():
    img = Image.new("L", (W, H), 255); d = ImageDraw.Draw(img)
    # big day + date
    T(d, (M, 24), DAY, font("InterDisplay-Bold.otf", 50), INK)
    T(d, (M, 86), DATE_LONG, font("InterDisplay-Medium.otf", 30), SOFT)
    T(d, (W - M, 96), UPDATED, font("Inter-Medium.otf", 22), SOFT, anchor="ra")
    d.line([(M, 140), (W - M, 140)], fill=INK, width=4)

    lab = font("Inter-Bold.otf", MIN + 1)
    big = font("InterDisplay-Bold.otf", 52)
    cur = font("InterDisplay-SemiBold.otf", 26)
    sub = font("InterDisplay-SemiBold.otf", 27)

    # gold block
    y = 160
    tracked(d, M, y, "GOLD  ·  PER GRAM", lab)
    y += 42
    for i, (k, aed) in enumerate(GOLD_AED.items()):
        pill(d, M, y + 6, k)
        T(d, (W - M, y + 50), f"{aed:,.2f}", big, INK, anchor="rs")
        aw = d.textlength(f"{aed:,.2f}", font=big)
        T(d, (W - M - aw - 10, y + 48), "AED", cur, SOFT, anchor="rs")
        T(d, (W - M, y + 88), f"₹ {inr(aed * AED_INR)}    $ {aed / USD_AED:,.2f}", sub, SOFT, anchor="rs")
        y += 112
        if i == 0: d.line([(M, y - 10), (W - M, y - 10)], fill=RULE, width=2)

    d.line([(M, y + 4), (W - M, y + 4)], fill=INK, width=3)

    # exchange block
    y += 22
    tracked(d, M, y, "EXCHANGE", lab)
    y += 42
    lf = font("InterDisplay-SemiBold.otf", 32)
    vf = font("InterDisplay-Bold.otf", 44)
    for i, (l, v) in enumerate([("1 AED", f"₹ {AED_INR:.2f}"),
                                ("1 USD", f"₹ {USD_INR:.2f}"),
                                ("100 INR", f"AED {100 / AED_INR:.2f}")]):
        T(d, (M, y + 44), l, lf, SOFT, anchor="ls")
        T(d, (W - M, y + 46), v, vf, INK, anchor="rs")
        y += 66
        if i < 2: d.line([(M, y - 6), (W - M, y - 6)], fill=RULE, width=2)

    footer(d, 0)
    return img


# ---------------- page 2: gold detail ----------------
def gold():
    img = Image.new("L", (W, H), 255); d = ImageDraw.Draw(img)
    small_header(d, "GOLD  ·  DUBAI", "Retail rate, per gram")
    big = font("InterDisplay-Bold.otf", 84)
    cur = font("InterDisplay-SemiBold.otf", 30)
    mid = font("InterDisplay-SemiBold.otf", 38)
    lab = font("Inter-SemiBold.otf", MIN)
    y = 128
    for i, (k, aed) in enumerate(GOLD_AED.items()):
        pill(d, M, y, k)
        T(d, (M, y + 66), "AED", cur, SOFT)
        T(d, (M + 72, y + 52), f"{aed:,.2f}", big, INK)
        ry = y + 166
        T(d, (M, ry), "INDIAN RUPEE", lab, SOFT)
        T(d, (M, ry + 24), f"₹ {inr(aed * AED_INR)}", mid, INK)
        cx = W // 2 + 20
        T(d, (cx, ry), "US DOLLAR", lab, SOFT)
        T(d, (cx, ry + 24), f"$ {aed / USD_AED:,.2f}", mid, INK)
        y += 300
        if i == 0: d.line([(M, y - 40), (W - M, y - 40)], fill=RULE, width=2)
    footer(d, 1)
    return img


# ---------------- page 3: exchange detail ----------------
def fx():
    img = Image.new("L", (W, H), 255); d = ImageDraw.Draw(img)
    small_header(d, "EXCHANGE", "Mid-market rates")
    lf = font("InterDisplay-SemiBold.otf", 34)
    vf = font("InterDisplay-Bold.otf", 56)
    y = 124
    rows = [("1 AED", f"₹ {AED_INR:.2f}"), ("1 USD", f"₹ {USD_INR:.2f}"),
            ("1 USD", f"AED {USD_AED:.4f}"), ("100 INR", f"AED {100 / AED_INR:.2f}")]
    for i, (l, v) in enumerate(rows):
        T(d, (M, y + 58), l, lf, SOFT, anchor="ls")
        T(d, (W - M, y + 62), v, vf, INK, anchor="rs")
        y += 88
        d.line([(M, y - 8), (W - M, y - 8)], fill=INK if i == 3 else RULE, width=3 if i == 3 else 2)
    tracked(d, M, y + 16, "QUICK CONVERT", font("Inter-Bold.otf", MIN + 1))
    q = font("InterDisplay-SemiBold.otf", 32)
    qy = y + 58
    for l, v in [("AED 1,000", f"₹ {inr(1000 * AED_INR)}"),
                 (f"₹ {inr(100000)}", f"AED {100000 / AED_INR:,.0f}"),
                 ("$ 1,000", f"₹ {inr(1000 * USD_INR)}")]:
        T(d, (M, qy), l, q, SOFT); T(d, (W - M, qy), v, q, INK, anchor="ra"); qy += 52
    footer(d, 2)
    return img


def framed(screen):
    bw, top, bot = 46, 70, 150
    fr = Image.new("L", (W + 2 * bw, H + top + bot), 0); d = ImageDraw.Draw(fr)
    d.rounded_rectangle([0, 0, fr.width - 1, fr.height - 1], radius=36, fill=70)
    d.rectangle([bw - 4, top - 4, bw + W + 3, top + H + 3], fill=40)
    fr.paste(screen, (bw, top))
    cx, cy = fr.width // 2, top + H + bot // 2
    d.rounded_rectangle([cx - 34, cy - 34, cx + 34, cy + 34], radius=10, outline=150, width=3)
    for x0 in (8, fr.width - 18):
        d.rounded_rectangle([x0, top + 260, x0 + 10, top + 520], radius=4, fill=120)
    return fr


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    pages = [home(), gold(), fx()]
    for n, p in zip(["page1_home", "page2_gold", "page3_exchange"], pages):
        p.save(os.path.join(OUT, n + ".png"))
    fr = [framed(p) for p in pages]
    gap, pad = 50, 36
    prev = Image.new("L", (fr[0].width * 3 + gap * 2 + pad * 2, fr[0].height + pad * 2), 236)
    for i, f in enumerate(fr): prev.paste(f, (pad + i * (f.width + gap), pad))
    prev.save(os.path.join(OUT, "preview_v2.png"))
    print("ok")
