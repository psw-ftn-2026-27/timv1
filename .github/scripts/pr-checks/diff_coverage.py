import json, re, os, glob
import xml.etree.ElementTree as ET

THRESHOLD = 0.80
HUNK = re.compile(r"^@@\s*-\d+(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s*@@")
CONST = re.compile(r"^\s*(?:(?:public|private|protected|internal|new)\s+)*const\s")

def added(patch):
    res = set()
    if not patch: return res
    n = 0
    for raw in patch.split("\n"):
        l = raw.rstrip("\r")
        m = HUNK.match(l)
        if m: n = int(m.group(1)); continue
        if l.startswith("\\"): continue
        if l.startswith("+") and not l.startswith("+++"):
            if not CONST.match(l[1:]): res.add(n)
            n += 1
        elif l.startswith("-") and not l.startswith("---"): pass
        else: n += 1
    return res

def cobertura(path):
    out = {}
    if not os.path.exists(path): return out
    root = ET.parse(path).getroot()
    for cls in root.iter("class"):
        fn = (cls.get("filename") or "").replace("\\", "/")
        if not fn: continue
        d = out.setdefault(fn, {})
        for ln in cls.iter("line"):
            try: num = int(ln.get("number")); hits = int(ln.get("hits"))
            except (TypeError, ValueError): continue
            d[num] = max(d.get(num, 0), hits)
    return out

def match(cov, dp):
    dp = dp.replace("\\", "/").lstrip("/")
    if dp in cov: return cov[dp]
    for k, v in cov.items():
        if k.endswith("/" + dp): return v
    shorter = [k for k in cov if dp.endswith("/" + k.lstrip("/"))]
    return cov[max(shorter, key=len)] if shorter else None

def write(status, **kw):
    kw["status"] = status
    kw["threshold"] = THRESHOLD
    json.dump(kw, open("coverage.json", "w", encoding="utf-8"), ensure_ascii=False)

raw = glob.glob("cov-raw/**/coverage.cobertura.xml", recursive=True)
if not raw:
    write("error", reason="no-data", addedExec=0, coveredNew=0, ratio=None)
    print("nema sirovih podataka o pokrivenosti"); raise SystemExit(0)
if not os.path.exists("cov-sum/Cobertura.xml"):
    write("error", reason="aggregate", addedExec=0, coveredNew=0, ratio=None)
    print("spajanje izveštaja nije uspelo"); raise SystemExit(0)

cov = cobertura("cov-sum/Cobertura.xml")
files = json.load(open("files.json", encoding="utf-8"))
addedExec = 0; coveredNew = 0; worst = []; skipped = []
for f in files:
    fn = f.get("filename")
    if not fn: continue
    cf = match(cov, fn)
    if not cf: continue
    t = added(f.get("patch"))
    if not t and not f.get("patch"):
        if f.get("status") == "added":
            t = set(cf.keys())
        elif f.get("status") != "removed" and f.get("changes", 1):
            skipped.append(fn)
    missing = 0
    for line in t:
        if line in cf:
            addedExec += 1
            if cf[line] > 0: coveredNew += 1
            else: missing += 1
    if missing:
        worst.append({"file": fn, "uncovered": missing})

if addedExec == 0:
    write("ok", addedExec=0, coveredNew=0, ratio=None, files=[], skippedFiles=skipped)
    print("nema novih testabilnih linija"); raise SystemExit(0)

ratio = coveredNew / addedExec
worst.sort(key=lambda x: -x["uncovered"])
write("ok" if ratio >= THRESHOLD else "fail",
      addedExec=addedExec, coveredNew=coveredNew, ratio=round(ratio, 4), files=worst[:5],
      skippedFiles=skipped)
print(f"{coveredNew}/{addedExec} = {ratio:.0%}")
