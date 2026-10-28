import os, re, json, time, urllib.request

key = os.environ.get("ANTHROPIC_API_KEY", "") or ""
model = os.environ.get("ANTHROPIC_MODEL", "") or "claude-opus-5-5"

def write(status, suspects):
    json.dump({"status": status, "suspects": suspects},
              open("description.json", "w", encoding="utf-8"), ensure_ascii=False)

if not key:
    write("skip", []); raise SystemExit(0)

try:
    tpl = json.load(open("template.json", encoding="utf-8"))
except Exception:
    write("skip", []); raise SystemExit(0)

ptype = tpl.get("ptype") or "feature"
sections = {name: text for name, text in (tpl.get("sections") or {}).items() if text}

if not sections:
    write("empty", []); raise SystemExit(0)

system = (
    "Ti si asistent koji proverava opis Pull Request-a. Za svaku sekciju odluči da li sadrži "
    "STVARAN, smislen sadržaj ili je BESMISLICA/PLACEHOLDER (npr. 'asdf', 'test test', "
    "nasumični znakovi, nedovršen placeholder, jedna reč bez značenja). "
    "NE ocenjuješ kvalitet, stil ni potpunost, samo razlikuješ stvaran sadržaj od besmislice. "
    "Budi blag: ako deluje kao iskren pokušaj, označi ga kao smislen. "
    "JEZIK: 'note' piši na srpskom EKAVSKOM izgovoru i latinicom "
    "('izmeren' a ne 'izmjeren', 'gde' a ne 'gdje', 'pre' a ne 'prije'). "
    "U 'note' ne koristi crtu ni srednju crtu kao interpunkciju, umesto nje piši zarez ili dvotačku. "
    "Odgovori ISKLJUČIVO JSON-om: "
    '{"sections":[{"name":"...","ok":true,"note":"kratko"}]}'
)
user = "Tip PRa: %s\n\nSekcije:\n%s" % (
    ptype,
    "\n\n".join("### %s\n%s" % (n, t) for n, t in sections.items()),
)
body = json.dumps({"model": model, "max_tokens": 8000, "output_config": {"effort": "low"}, "system": system,
                   "messages": [{"role": "user", "content": user}]}).encode("utf-8")

verdict = None
for attempt in range(1, 4):
    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages", data=body, method="POST",
            headers={"content-type": "application/json", "x-api-key": key,
                     "anthropic-version": "2023-06-01"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            raise ValueError("u odgovoru nema JSON-a")
        verdict = json.loads(m.group(0))
        break
    except Exception as e:
        detail = e.read().decode("utf-8", "replace")[:500] if hasattr(e, "read") else ""
        print(f"LLM pokušaj {attempt} nije uspeo: {e} {detail}")
        if attempt < 3:
            time.sleep(10 * attempt)

if verdict is None:
    write("skip", []); raise SystemExit(0)

suspects = [{"name": s.get("name", "?"), "note": (s.get("note") or "").strip()}
            for s in verdict.get("sections", []) if not s.get("ok", True)]
write("suspect" if suspects else "ok", suspects)
print("Sumnjive sekcije:", [s["name"] for s in suspects])
