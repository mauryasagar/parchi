import csv
import json

UNITS = {"kilo": "kg", "kg": "kg", "kgs": "kg",
         "gm": "g", "gram": "g", "g": "g", "grams": "g",
         "dozen": "dozen", "piece": "piece", "pieces": "piece", "pcs": "piece"}

prices = {}
for r in csv.DictReader(open("prices.csv", encoding="utf-8")):
    prices[r["item"].strip().lower()] = (r["unit"].strip(), float(r["price"]))

def find_price(name):
    name = name.strip().lower()
    if name in prices:
        return name
    hits = [k for k in prices if k in name]
    return max(hits, key=len) if hits else None

def price_line(item):
    name = item.get("name")
    if not name:
        return None, "item name missing"
    key = find_price(name)
    if not key:
        return None, f"{name} not in price list"
    try:
        qty = float(item.get("quantity"))
    except (TypeError, ValueError):
        return None, f"{name} quantity missing"
    raw = item.get("unit")
    unit = UNITS.get((raw or "").strip().lower(), raw)
    if unit == "g":
        qty, unit = qty / 1000, "kg"
    pu, price = prices[key]
    if unit is None and pu == "piece":
        unit = "piece"
    if unit != pu:
        return None, f"{name} unit unclear (got {raw}, price is per {pu})"
    return qty * price, None

data = json.load(open("gemma4_e4b.json", encoding="utf-8"))
rows = []
for d in data:
    if "error" in d:
        rows.append(["", "", "", "", 0, "parse error: " + d["msg"][:30]])
        continue
    p = d["parsed"]
    total, problems, shown = 0, [], []
    for it in (p.get("items") or []):
        if not isinstance(it, dict):
            continue
        shown.append(f'{it.get("name")} {it.get("quantity")} {it.get("unit") or ""}'.strip())
        amount, problem = price_line(it)
        if problem:
            problems.append(problem)
        else:
            total += amount
    if not shown:
        problems.append("no items found")
    if not p.get("customer"):
        problems.append("customer missing")
    if not p.get("delivery_day"):
        problems.append("delivery day missing")
    rows.append([p.get("customer") or "", "; ".join(shown), p.get("delivery_day") or "",
                 p.get("notes") or "", round(total, 2), " | ".join(problems)])

with open("orders.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["customer", "items", "delivery_day", "notes", "total_rs", "check"])
    w.writerows(rows)

for r in rows:
    print(r[0] or "?", "|", r[1], "|", r[4], "|", "CHECK: " + r[5] if r[5] else "ok")