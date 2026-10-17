import json
import urllib.request

MODEL = "gemma4:e2b"

PROMPT = """Read this WhatsApp order and return JSON only with these keys:
customer, items, delivery_day, notes.
items is a list of objects with: name, quantity, unit.
If something is not in the message, use null. Do not guess.

Message: {msg}"""

def parse(msg):
    body = {
        "model": MODEL,
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

msg = "bhaiya kal subah 5 kg laddoo chahiye, Sharma ji ke ghar, 10 baje tak"
print(parse(msg))