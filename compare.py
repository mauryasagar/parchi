import json

a = json.load(open("gemma4_e2b.json", encoding="utf-8"))
b = json.load(open("gemma4_e4b.json", encoding="utf-8"))

def short(r):
    if "error" in r:
        return "ERROR " + r["error"][:40]
    p = r["parsed"]
    items = "; ".join(
        f'{i.get("name")} {i.get("quantity")} {i.get("unit")}'
        for i in (p.get("items") or [])
        if isinstance(i, dict)
    )
    return f'{p.get("customer")} | {items} | {p.get("delivery_day")} | {p.get("notes")}'

for n, (x, y) in enumerate(zip(a, b), 1):
    print(n, x["msg"])
    print("  E2B:", short(x))
    print("  E4B:", short(y))