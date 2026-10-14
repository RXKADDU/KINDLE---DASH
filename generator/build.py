"""KD Kindle dashboard generator.

Runs on GitHub every hour: fetches gold and currency rates, then draws each
page as a 600 x 800 greyscale PNG for the Kindle 4.

Usage:
  python generator/build.py            fetch live data and render
  python generator/build.py --sample   render with sample data (no internet)
"""
import json, os, re, sys, html
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "generator", "fonts")
OUT = os.path.join(ROOT, "out")
LAST = os.path.join(ROOT, "data", "last.json")
CFG = json.load(open(os.path.join(ROOT, "config.json")))
TZ = ZoneInfo(CFG.get("timezone", "Asia/Dubai"))
GRAMS_PER_OZ = 31.1034768
AED_PEG = 3.6725
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

# ======================================================================
# Data
# ======================================================================

def log(*a): print(*a, flush=True)


def get_json(url):
    import requests
    r = requests.get(url, headers=UA, timeout=20); r.raise_for_status(); return r.json()


def get_text(url):
    import requests
    r = requests.get(url, headers=UA, timeout=20); r.raise_for_status(); return r.text


def fetch_fx():
    """Returns (usd_inr, usd_aed, source)."""
    try:
        j = get_json("https://open.er-api.com/v6/latest/USD")
        return float(j["rates"]["INR"]), float(j["rates"]["AED"]), "open.er-api.com"
    except Exception as e: log("fx open.er-api failed:", e)
    for u in ["https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
              "https://latest.currency-api.pages.dev/v1/currencies/usd.json"]:
        try:
            j = get_json(u)["usd"]
            return float(j["inr"]), float(j["aed"]), "currency-api"
        except Exception as e: log("fx fallback failed:", u, e)
    try:
        j = get_json("https://api.frankfurter.app/latest?from=USD&to=INR")
        return float(j["rates"]["INR"]), AED_PEG, "frankfurter"
    except Exception as e: log("fx frankfurter failed:", e)
    return None


def fetch_spot():
    """World spot gold, USD per troy ounce."""
    try:
        return float(get_json("https://api.gold-api.com/price/XAU")["price"]), "gold-api.com"
    except Exception as e: log("spot gold-api failed:", e)
    for u in ["https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/xau.json",
              "https://latest.currency-api.pages.dev/v1/currencies/xau.json"]:
        try:
            return float(get_json(u)["xau"]["usd"]), "currency-api"
        except Exception as e: log("spot fallback failed:", u, e)
    return None


DUBAI_SOURCES = [
    "https://www.khaleejtimes.com/gold-forex",
    "https://gulfnews.com/gold-forex",
    "https://igold.ae/gold-rate",
    "https://dubaicityofgold.com/",
]


def scrape_dubai(estimate24):
    """Try to read Dubai retail 24K/22K AED per gram from public pages.
    A value is only accepted if it is within 6% of the spot based estimate."""
    def find(text, k):
        pat = rf"\b{k}\s*(?:K|KT|Karat|Carat)\b[^0-9]{{0,60}}?([1-9]\d{{2}}(?:[.,]\d{{1,2}})?)"
        for m in re.finditer(pat, text, re.I):
            yield float(m.group(1).replace(",", "."))
    for url in DUBAI_SOURCES:
        try:
            raw = get_text(url)
            text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
            text = re.sub(r"\s+", " ", text)
            g24 = next((v for v in find(text, 24) if abs(v / estimate24 - 1) < 0.06), None)
            g22 = next((v for v in find(text, 22) if g24 and 0.88 < v / g24 < 0.95), None)
            if g24 and g22:
                return {"24K": g24, "22K": g22}, url
            log("dubai source had no usable rates:", url)
        except Exception as e:
            log("dubai source failed:", url, e)
    return None, None


def load_last():
    try: return json.load(open(LAST))
    except Exception: return {}


def fetch_all():
    now = datetime.now(TZ)
    last = load_last()
    data = dict(last)

    fx = fetch_fx()
    if fx:
        data["usd_inr"], data["usd_aed"], data["fx_source"] = fx
        data["fx_time"] = now.isoformat()

    spot = fetch_spot()
    if spot and data.get("usd_aed"):
        data["spot_usd_oz"], data["spot_source"] = spot
        est = CFG["gold_estimate"]
        e24 = spot[0] / GRAMS_PER_OZ * data["usd_aed"] * est["premium_24k"]
        rates, src = scrape_dubai(e24)
        if rates:
            data["gold_aed"], data["gold_source"], data["gold_estimated"] = rates, src, False
        else:
            data["gold_aed"] = {"24K": round(e24 * 4) / 4,
                                "22K": round(e24 * est["ratio_22k"] * 4) / 4}
            data["gold_source"], data["gold_estimated"] = "spot estimate", True
        data["gold_time"] = now.isoformat()

    if "usd_inr" not in data or "gold_aed" not in data:
        raise SystemExit("No data available and no cached data to fall back on")
    os.makedirs(os.path.dirname(LAST), exist_ok=True)
    json.dump(data, open(LAST, "w"), indent=2)
    return data


def sample_data():
    t = datetime.now(TZ).isoformat()
    return {"usd_inr": 95.90693, "usd_aed": 3.6725, "fx_time": t, "fx_source": "sample",
            "gold_aed": {"24K": 497.75, "22K": 460.75}, "gold_time": t,
            "gold_source": "sample", "gold_estimated": False}


# ======================================================================
# Drawing (e-ink rules: text >= 20 px, black + 2 greys, lines >= 2 px)
# ======================================================================
W, H, M = 600, 800, 34
INK, SOFT, RULE = 0, 80, 160
_fc = {}
def font(name, size):
    k = (name, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(os.path.join(FONTS, name), size)
    return _fc[k]


def inr(x, dp=0):
    s = f"{x:.{dp}f}"; whole, _, frac = s.partition(".")
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]; parts = []
        while len(head) > 2: parts.insert(0, head[-2:]); head = head[:-2]
        if head: parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return whole + ("." + frac if frac else "")


def T(d, xy, s, f, fill=INK, anchor="la"): d.text(xy, s, font=f, fill=fill, anchor=anchor)


def tracked(d, x, y, s, f, fill=INK, track=2.5, right=False):
    ws = [d.textlength(c, font=f) for c in s]
    tot = sum(ws) + track * (len(s) - 1)
    if right: x -= tot
    for c, w in zip(s, ws): d.text((x, y), c, font=f, fill=fill); x += w + track


def pill(d, x, y, label, size=26, h=42):
    f = font("Inter-Bold.otf", size); w = d.textlength(label, font=f)
    d.rounded_rectangle([x, y, x + w + 26, y + h], radius=8, fill=INK)
    T(d, (x + 13 + w / 2, y + h / 2), label, f, 255, anchor="mm")


class Page:
    def __init__(self, ctx, title, subtitle):
        self.img = Image.new("L", (W, H), 255); self.d = d = ImageDraw.Draw(self.img)
        # top bar (identical on every page)
        f = font("Inter-Bold.otf", 21)
        tracked(d, M, 30, title, f)
        tracked(d, W - M, 30, ctx["date"], f, right=True)
        r = font("Inter-Medium.otf", 22)
        T(d, (M, 62), subtitle, r, SOFT)
        T(d, (W - M, 62), "Updated " + ctx["updated"], r, SOFT, anchor="ra")
        d.line([(M, 102), (W - M, 102)], fill=INK, width=3)
        # bottom bar (identical on every page)
        y = H - 44
        d.line([(M, y - 26), (W - M, y - 26)], fill=RULE, width=2)
        for i in range(ctx["total"]):
            cx = M + 9 + i * 26; box = [cx - 8, y - 8, cx + 8, y + 8]
            if i == ctx["index"]: d.ellipse(box, fill=INK)
            else: d.ellipse(box, outline=INK, width=3)
        T(d, (W - M, y), f"◀  {ctx['name']}  ▶", font("Inter-SemiBold.otf", 22), INK, anchor="rm")


def page_home(ctx, data):
    p = Page(ctx, "MARKETS", "Gold and exchange"); d = p.d
    usd_inr, usd_aed = data["usd_inr"], data["usd_aed"]; aed_inr = usd_inr / usd_aed
    lab = font("Inter-Bold.otf", 21)
    big = font("InterDisplay-Bold.otf", 54)
    cur = font("InterDisplay-SemiBold.otf", 26)
    sub = font("InterDisplay-SemiBold.otf", 28)
    y = 122
    tracked(d, M, y, "GOLD  ·  PER GRAM" + ("  ·  EST." if data.get("gold_estimated") else ""), lab)
    y += 40
    karats = [k for k in CFG["gold_karats"] if k in data["gold_aed"]]
    for i, k in enumerate(karats):
        aed = data["gold_aed"][k]
        pill(d, M, y + 8, k)
        v = f"{aed:,.2f}"
        T(d, (W - M, y + 52), v, big, INK, anchor="rs")
        T(d, (W - M - d.textlength(v, font=big) - 10, y + 50), "AED", cur, SOFT, anchor="rs")
        T(d, (W - M, y + 92), f"₹ {inr(aed * aed_inr)}    $ {aed / usd_aed:,.2f}", sub, SOFT, anchor="rs")
        y += 116
        if i < len(karats) - 1: d.line([(M, y - 10), (W - M, y - 10)], fill=RULE, width=2)
    d.line([(M, y + 2), (W - M, y + 2)], fill=INK, width=3)
    y += 24
    tracked(d, M, y, "EXCHANGE", lab)
    y += 40
    lf = font("InterDisplay-SemiBold.otf", 32); vf = font("InterDisplay-Bold.otf", 46)
    rows = [("1 AED", f"₹ {aed_inr:.2f}"), ("1 USD", f"₹ {usd_inr:.2f}"),
            ("100 INR", f"AED {100 / aed_inr:.2f}")]
    for i, (l, v) in enumerate(rows):
        T(d, (M, y + 48), l, lf, SOFT, anchor="ls"); T(d, (W - M, y + 50), v, vf, INK, anchor="rs")
        y += 72
        if i < len(rows) - 1: d.line([(M, y - 8), (W - M, y - 8)], fill=RULE, width=2)
    return p.img


def page_gold(ctx, data):
    sub = "Estimate from world price" if data.get("gold_estimated") else "Dubai retail, per gram"
    p = Page(ctx, "GOLD", sub); d = p.d
    usd_inr, usd_aed = data["usd_inr"], data["usd_aed"]; aed_inr = usd_inr / usd_aed
    big = font("InterDisplay-Bold.otf", 84); cur = font("InterDisplay-SemiBold.otf", 30)
    mid = font("InterDisplay-SemiBold.otf", 38); lab = font("Inter-SemiBold.otf", 20)
    y = 128
    karats = [k for k in CFG["gold_karats"] if k in data["gold_aed"]]
    for i, k in enumerate(karats):
        aed = data["gold_aed"][k]
        pill(d, M, y, k)
        T(d, (M, y + 66), "AED", cur, SOFT); T(d, (M + 72, y + 52), f"{aed:,.2f}", big, INK)
        ry = y + 166
        T(d, (M, ry), "INDIAN RUPEE", lab, SOFT); T(d, (M, ry + 24), f"₹ {inr(aed * aed_inr)}", mid, INK)
        cx = W // 2 + 20
        T(d, (cx, ry), "US DOLLAR", lab, SOFT); T(d, (cx, ry + 24), f"$ {aed / usd_aed:,.2f}", mid, INK)
        y += 300
        if i < len(karats) - 1: d.line([(M, y - 40), (W - M, y - 40)], fill=RULE, width=2)
    return p.img


def page_exchange(ctx, data):
    p = Page(ctx, "EXCHANGE", "Mid-market rates"); d = p.d
    usd_inr, usd_aed = data["usd_inr"], data["usd_aed"]; aed_inr = usd_inr / usd_aed
    lf = font("InterDisplay-SemiBold.otf", 34); vf = font("InterDisplay-Bold.otf", 56)
    y = 124
    rows = [("1 AED", f"₹ {aed_inr:.2f}"), ("1 USD", f"₹ {usd_inr:.2f}"),
            ("1 USD", f"AED {usd_aed:.4f}"), ("100 INR", f"AED {100 / aed_inr:.2f}")]
    for i, (l, v) in enumerate(rows):
        T(d, (M, y + 58), l, lf, SOFT, anchor="ls"); T(d, (W - M, y + 62), v, vf, INK, anchor="rs")
        y += 88
        last = i == len(rows) - 1
        d.line([(M, y - 8), (W - M, y - 8)], fill=INK if last else RULE, width=3 if last else 2)
    tracked(d, M, y + 16, "QUICK CONVERT", font("Inter-Bold.otf", 21))
    q = font("InterDisplay-SemiBold.otf", 32); qy = y + 58
    for l, v in [("AED 1,000", f"₹ {inr(1000 * aed_inr)}"),
                 (f"₹ {inr(100000)}", f"AED {100000 / aed_inr:,.0f}"),
                 ("$ 1,000", f"₹ {inr(1000 * usd_inr)}")]:
        T(d, (M, qy), l, q, SOFT); T(d, (W - M, qy), v, q, INK, anchor="ra"); qy += 52
    return p.img


PAGES = {"home": ("Home", page_home), "gold": ("Gold", page_gold), "exchange": ("Exchange", page_exchange)}


def render(data):
    now = datetime.now(TZ)
    stamp = datetime.fromisoformat(min(data["fx_time"], data["gold_time"])).astimezone(TZ)
    names = [p for p in CFG["pages"] if p in PAGES]
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith(".png") or f == "pages.txt": os.remove(os.path.join(OUT, f))
    files = []
    for i, key in enumerate(names):
        label, fn = PAGES[key]
        ctx = {"date": now.strftime("%a %d %b").upper(), "updated": stamp.strftime("%H:%M"),
               "index": i, "total": len(names), "name": label}
        fname = f"{i + 1}_{key}.png"
        fn(ctx, data).save(os.path.join(OUT, fname), optimize=True)
        files.append(fname)
    open(os.path.join(OUT, "pages.txt"), "w").write("\n".join(files) + "\n")
    status = {k: v for k, v in data.items()}
    status["built"] = now.isoformat()
    json.dump(status, open(os.path.join(OUT, "status.json"), "w"), indent=2)
    log("rendered:", ", ".join(files))
    log("sources: fx =", data.get("fx_source"), "| gold =", data.get("gold_source"))


if __name__ == "__main__":
    render(sample_data() if "--sample" in sys.argv else fetch_all())
