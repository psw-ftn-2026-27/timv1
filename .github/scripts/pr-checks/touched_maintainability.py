import json, re, os

def write(status, methods, classes, thresholds, **kw):
    kw.update(status=status, methods=methods, classes=classes, thresholds=thresholds)
    json.dump(kw, open("maintainability.json", "w", encoding="utf-8"), ensure_ascii=False)

if not os.path.exists("maintainability-report.json"):
    write("error", [], [], {}, reason="tool")
    print("merenje metrika nije uspelo"); raise SystemExit(0)
if not os.path.exists("files.json"):
    write("error", [], [], {}, reason="files")
    print("spisak fajlova PRa nije preuzet"); raise SystemExit(0)

HUNK = re.compile(r"^@@\s*-\d+(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s*@@")

def added(patch):
    res = set()
    if not patch: return res
    n = 0
    for raw in patch.split("\n"):
        l = raw.rstrip("\r")
        m = HUNK.match(l)
        if m: n = int(m.group(1)); continue
        if l.startswith("\\"): continue
        if l.startswith("+") and not l.startswith("+++"): res.add(n); n += 1
        elif l.startswith("-") and not l.startswith("---"): pass
        else: n += 1
    return res

def touched(item, lines):
    s, e = item.get("startLine", 0), item.get("endLine", 0)
    return any(x in lines for x in range(s, e + 1))

report = json.load(open("maintainability-report.json", encoding="utf-8"))
files = json.load(open("files.json", encoding="utf-8"))
by_file = {f["filename"]: added(f.get("patch")) for f in files if f.get("filename")}

methods = [i for i in report.get("items", [])
           if i.get("file") in by_file and touched(i, by_file[i["file"]])]
classes = [i for i in report.get("classItems", [])
           if i.get("file") in by_file and touched(i, by_file[i["file"]])]

write("warn" if (methods or classes) else "ok", methods, classes, report.get("thresholds", {}))
print(f"dirnuto: {len(methods)} metoda, {len(classes)} klasa")

def esc(text):
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")

limits = report.get("thresholds", {})
for item, name in [(m, m.get("method", "")) for m in methods] + [(c, c.get("name", "")) for c in classes]:
    parts = []
    for metric, lvl in item.get("levels", {}).items():
        if lvl == "ok":
            continue
        pair = limits.get(metric, [0, 0])
        limit = pair[1] if lvl == "critical" else pair[0]
        word = "kritično" if lvl == "critical" else "sumnjivo"
        parts.append(f"{metric.upper()} = {item.get(metric)} ({word}, prag {limit})")
    if parts:
        print(f"::notice file={item['file']},line={item['startLine']},title=Lakoća održavanja::"
              + esc(f"{name}: " + ", ".join(parts)))
