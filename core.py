"""Parchi core.

The local model only READS a messy order message and returns JSON.
Everything else (prices, totals, checks, the prep list) is plain Python,
so the numbers can never be made up by the model.
"""
import csv
import json
import math
import os
import re
import urllib.request

OLLAMA = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:e4b"
CACHE_FILE = "cache.json"
PRICES_FILE = "prices.csv"
ORDERS_FILE = "orders.txt"

PROMPT = """Read this WhatsApp order and return JSON only with these keys:
customer, items, delivery_day, notes.
items is a list of objects with: name, quantity, unit.
If something is not in the message, use null. Do not guess.

Message: {msg}"""

UNITS = {
    "kilo": "kg", "kg": "kg", "kgs": "kg", "kilogram": "kg",
    "gm": "g", "gms": "g", "gram": "g", "grams": "g", "g": "g",
    "dozen": "dozen", "dz": "dozen",
    "piece": "piece", "pieces": "piece", "pcs": "piece", "pc": "piece",
}

HINDI_DAYS = [
    ("somwar", "monday"), ("somvar", "monday"),
    ("mangalwar", "tuesday"), ("mangalvar", "tuesday"),
    ("budhwar", "wednesday"), ("budhvar", "wednesday"),
    ("guruwar", "thursday"), ("guruvar", "thursday"),
    ("shukrawar", "friday"), ("shukravar", "friday"),
    ("shanivar", "saturday"), ("shaniwar", "saturday"),
    ("ravivar", "sunday"), ("raviwar", "sunday"),
]
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
RANK = {"aaj": 0, "kal": 1, "parso": 2, "unknown": 10}
for _i, _d in enumerate(WEEKDAYS):
    RANK[_d] = 3 + _i

_WD = "|".join(WEEKDAYS)
RANGE_FROM = re.compile(r"\b(?:kal|aaj|parso|today|tomorrow|" + _WD + r")\s+se\b")
RANGE_TO = re.compile(r"\b(?:" + _WD + r")\s*(?:to|-|till|until|se)\s*(?:" + _WD + r")\b")


# ---------------------------------------------------------------- model ----

def ask_model(model, msg):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT.format(msg=msg)}],
        "format": "json",
        "stream": False,
        "think": False,
    }
    req = urllib.request.Request(
        OLLAMA + "/api/chat",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        content = json.loads(r.read())["message"]["content"]
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("the model did not return an object")
    return data


def _load_cache():
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def parse_cached(model, msg):
    """Return (parsed, was_cached). Same message + model is never read twice."""
    cache = _load_cache()
    key = model + "||" + msg
    if key in cache:
        return cache[key], True
    data = ask_model(model, msg)
    cache[key] = data
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    return data, False


def list_models():
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=3) as r:
            names = [m["name"] for m in json.loads(r.read()).get("models", [])]
        return sorted(names) or [DEFAULT_MODEL]
    except Exception:
        return [DEFAULT_MODEL]


# --------------------------------------------------------------- prices ----

def load_prices(path=PRICES_FILE):
    prices = {}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            prices[r["item"].strip().lower()] = (r["unit"].strip().lower(), float(r["price"]))
    return prices


def price_rows(prices):
    return [{"item": k, "unit": u, "price": p} for k, (u, p) in prices.items()]


PRICE_UNITS = ("kg", "dozen", "piece", "day")


def save_prices(rows, path=PRICES_FILE):
    """Check an edited price list and write it to prices.csv.

    Returns (clean_rows, None) on success or (None, message) if something is wrong.
    Raises OSError if the file cannot be written (for example, it is open in Excel).
    """
    if not isinstance(rows, list) or not rows:
        return None, "The price list is empty. Add at least one item."
    clean_rows, seen = [], set()
    for n, r in enumerate(rows, 1):
        if not isinstance(r, dict):
            return None, f"Row {n} is not valid."
        item = " ".join(str(r.get("item") or "").split()).lower()
        unit = str(r.get("unit") or "").strip().lower()
        price = to_float(r.get("price"))
        if not item:
            return None, f"Row {n}: the item name is empty."
        if len(item) > 60:
            return None, f"Row {n}: the item name is too long."
        if unit not in PRICE_UNITS:
            return None, f"{item}: choose a unit (kg, dozen, piece or day)."
        if price is None or not math.isfinite(price) or price <= 0 or price > 1_000_000:
            return None, f"{item}: the price must be a number above 0."
        if item in seen:
            return None, f"{item} is in the list twice. Keep one."
        seen.add(item)
        clean_rows.append({"item": item, "unit": unit, "price": price})

    tmp = path + ".tmp"
    try:
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["item", "unit", "price"])
            for r in clean_rows:
                p = r["price"]
                w.writerow([r["item"], r["unit"], int(p) if p.is_integer() else p])
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return clean_rows, None


def find_price(name, prices):
    name = name.strip().lower()
    for candidate in (name, name[:-1] if name.endswith("s") else name):
        if candidate in prices:
            return candidate
    hits = [k for k in prices if k in name]
    return max(hits, key=len) if hits else None


# ---------------------------------------------------------------- helpers --

def to_float(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.strip().replace(",", ""))
        except ValueError:
            return None
    return None


def clean(v):
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def norm_unit(raw):
    u = (raw or "").strip().lower() if isinstance(raw, str) else ""
    return (UNITS.get(u, u)) or None


def normalize_day(text):
    d = (text or "").lower()
    for hi, en in HINDI_DAYS:
        d = d.replace(hi, en)
    return d.strip()


def day_bucket(text):
    d = normalize_day(text)
    if not d:
        return "unknown", "day unknown"
    if re.search(r"\b(aaj|today)\b", d):
        return "aaj", "aaj (today)"
    if re.search(r"\bparso\b", d):
        return "parso", "parso (day after tomorrow)"
    if re.search(r"\b(kal|tomorrow)\b", d):
        return "kal", "kal (tomorrow)"
    for w in WEEKDAYS:
        if w in d:
            return w, w.capitalize()
    return "unknown", "day unknown"


def is_range(text):
    d = normalize_day(text)
    return bool(RANGE_FROM.search(d) or RANGE_TO.search(d))


# ----------------------------------------------------------------- slips ----

def price_item(item, prices):
    name = clean(item.get("name")) or ""
    qty = to_float(item.get("quantity"))
    unit = norm_unit(item.get("unit"))
    out = {
        "name": name,
        "qty": qty,
        "unit": unit,
        "qty_text": "?" if qty is None else " ".join(x for x in [f"{qty:g}", unit or ""] if x),
        "line_total": None,
        "problem": None,
    }
    label = name or "an item"
    if not name:
        out["problem"] = "an item has no name"
        return out
    if qty is None:
        out["problem"] = f"{label}: quantity missing"
        return out
    key = find_price(name, prices)
    if not key:
        out["problem"] = f"{label}: not in the price list"
        return out
    price_unit, price = prices[key]
    q, u = qty, unit
    if u == "g":
        q, u = q / 1000, "kg"
    if u == "dozen" and price_unit == "piece":
        q, u = q * 12, "piece"
    elif u == "piece" and price_unit == "dozen":
        q, u = q / 12, "dozen"
    if u is None and price_unit in ("piece", "day"):
        u = price_unit
    if u != price_unit:
        out["problem"] = f"{label}: priced per {price_unit}, order says {unit or 'no unit'}"
        return out
    out["line_total"] = round(q * price, 2)
    return out


def build_slip(msg, parsed, prices, error=None):
    items = [price_item(i, prices) for i in (parsed.get("items") or []) if isinstance(i, dict)]
    customer = clean(parsed.get("customer"))
    day = clean(parsed.get("delivery_day"))
    notes = clean(parsed.get("notes"))

    # The model sometimes puts "aaj shaam 6 baje" in notes. Move it where it belongs.
    if day is None and notes and day_bucket(notes)[0] != "unknown":
        day, notes = notes, None

    day_key, day_label = day_bucket(day or "")
    ranged = is_range(day or "")

    problems = [i["problem"] for i in items if i["problem"]]
    if error:
        problems.append(error)
    elif not items:
        problems.append("no items found")
    if ranged:
        problems.append("date range: confirm how many days")
        for i in items:
            i["line_total"] = None
    elif day_key == "unknown" and not error:
        problems.append("delivery day unclear")

    total = round(sum(i["line_total"] for i in items if i["line_total"] is not None), 2)
    return {
        "msg": msg,
        "customer": customer,
        "items": items,
        "day": day,
        "day_key": day_key,
        "day_label": day_label,
        "is_range": ranged,
        "notes": notes,
        "total": total,
        "problems": problems,
    }


# ------------------------------------------------------------------ prep ----

def make_prep(slips):
    groups = {}
    left_out = []
    for s in slips:
        if s.get("is_range"):
            left_out.append({"msg": s.get("msg", ""), "why": "date range, confirm how many days"})
            continue
        key = s.get("day_key", "unknown")
        label = s.get("day_label", "day unknown")
        for it in s.get("items", []):
            name = (it.get("name") or "").strip().lower()
            qty = it.get("qty")
            if qty is None or not name:
                left_out.append({"msg": s.get("msg", ""), "why": f"{name or 'an item'}: no quantity"})
                continue
            unit = it.get("unit") or ""
            if unit == "g":
                qty, unit = qty / 1000, "kg"
            g = groups.setdefault(key, {"label": label, "items": {}})
            g["items"][(name, unit)] = g["items"].get((name, unit), 0) + qty
    days = []
    for key, g in sorted(groups.items(), key=lambda kv: RANK.get(kv[0], 10)):
        lines = [
            {"qty": " ".join(x for x in [f"{qty:g}", unit] if x), "name": name}
            for (name, unit), qty in g["items"].items()
        ]
        days.append({"day": g["label"], "items": lines})
    return {
        "days": days,
        "left_out": left_out,
        "orders": len(slips),
        "need_check": sum(1 for s in slips if s.get("problems")),
        "grand_total": round(sum(s.get("total") or 0 for s in slips), 2),
    }
