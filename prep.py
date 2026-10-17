import json
from collections import defaultdict

UNITS = {"kilo": "kg", "kg": "kg", "kgs": "kg",
         "gm": "g", "gram": "g", "g": "g", "grams": "g"}

HINDI_DAYS = [("somwar", "monday"), ("mangalwar", "tuesday"),
              ("budhwar", "wednesday"), ("guruwar", "thursday"),
              ("shukrawar", "friday"), ("shanivar", "saturday"),
              ("ravivar", "sunday")]
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday",
            "friday", "saturday", "sunday"]

def bucket(day):
    d = (day or "").lower()
    if not d:
        return "day unknown"
    if "aaj" in d or "today" in d:
        return "aaj (today)"
    if "parso" in d:
        return "parso (day after tomorrow)"
    if "kal" in d or "tomorrow" in d:
        return "kal (tomorrow)"
    for hi, en in HINDI_DAYS:
        d = d.replace(hi, en)
    if any(w in d for w in WEEKDAYS):
        return d
    return "day unknown"

data = json.load(open("gemma4_e4b.json", encoding="utf-8"))
plan = defaultdict(lambda: defaultdict(float))
skipped = []

for d in data:
    if "error" in d:
        continue
    p = d["parsed"]
    day = bucket(p.get("delivery_day") or p.get("notes"))
    for it in (p.get("items") or []):
        if not isinstance(it, dict):
            continue
        name = (it.get("name") or "").strip().lower()
        try:
            qty = float(it.get("quantity"))
        except (TypeError, ValueError):
            skipped.append(d["msg"])
            continue
        unit = UNITS.get((it.get("unit") or "").strip().lower(), it.get("unit") or "")
        if unit == "g":
            qty, unit = qty / 1000, "kg"
        plan[day][(name, unit)] += qty

for day, items in plan.items():
    print("\n" + day.upper())
    for (name, unit), qty in items.items():
        print(" ", " ".join(x for x in ["make", f"{qty:g}", unit, name] if x))

if skipped:
    print("\nCHECK (no quantity, not in prep list):")
    for m in skipped:
        print(" -", m)