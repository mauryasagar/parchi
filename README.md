# Parchi

Parchi turns messy WhatsApp order messages (often Hinglish) into a clean order sheet for small food sellers: home bakers, sweet shops, tiffin services. A "parchi" is the slip of paper an order gets written on.

Built for the DEV Hacktoberfest Week 2 "Side Hustle" challenge.

## What it does

1. Reads orders saved in `orders.txt`, one message per line.
2. A local Gemma model pulls out customer, items, quantity and delivery day.
3. Plain Python adds up the total from `prices.csv`. The AI never does the math.
4. Unclear orders get a `check` note so the seller can look at them.
5. A prep list adds up what to make for each day.

Everything runs on your own laptop through Ollama. No customer names or numbers leave the machine.

## Run it

You need Python, Ollama, and the model:

```
ollama pull gemma4:e4b
```

Then, in this folder:

```
python parse_all.py
python parchi.py
python prep.py
```

`parse_all.py` reads `orders.txt` with both gemma4:e2b and gemma4:e4b and writes the results to JSON files. Those files are not in the repo, so run this first. `parchi.py` and `prep.py` read the E4B results. To compare the two models, run `python compare.py`.

Pull gemma4:e2b too if you want the comparison: `ollama pull gemma4:e2b`

## Files

- `orders.txt`: 15 made-up test orders (not real customers)
- `prices.csv`: made-up price list, edit it for your own items
- `parse_all.py`: sends each order to the model
- `parchi.py`: totals and check notes, writes `orders.csv`
- `prep.py`: prep list by delivery day
- `compare.py`: E2B vs E4B side by side

## Known limits

- Tested on 15 made-up messages, not real ones yet.
- "Monday se friday" is treated as one group, not five days.
- Sometimes the model puts the delivery time in notes instead of the delivery day.
- Orders with no customer name get flagged, even though a real WhatsApp chat would show the contact.
- Orders like "mithai ka dabba" with no weight or price can't be totalled.

## License

MIT