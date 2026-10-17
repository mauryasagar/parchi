import json
import time
import urllib.request

PROMPT = """Read this WhatsApp order and return JSON only with these keys:
customer, items, delivery_day, notes.
items is a list of objects with: name, quantity, unit.
If something is not in the message, use null. Do not guess.

Message: {msg}"""

def parse(model, msg):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT.format(msg=msg)}],
        "format": "json",
        "stream": False,
        "think": False,
    }
    req = urllib.request.Request(
        "http://localhost:11434/api/chat",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["message"]["content"]

orders = [l.strip() for l in open("orders.txt", encoding="utf-8") if l.strip()]

for model in ["gemma4:e2b", "gemma4:e4b"]:
    results = []
    start = time.time()
    for i, msg in enumerate(orders, 1):
        print(model, i, "of", len(orders))
        try:
            results.append({"msg": msg, "parsed": json.loads(parse(model, msg))})
        except Exception as e:
            results.append({"msg": msg, "error": str(e)})
    secs = round(time.time() - start)
    name = model.replace(":", "_") + ".json"
    with open(name, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(model, "done in", secs, "seconds")