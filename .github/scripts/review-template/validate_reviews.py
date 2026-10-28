import os, re, json

ASPECTS = ["Funkcionalna pogodnost", "Besprekornost", "Lakoća održavanja"]
FRONTEND = "Frontend"
CLOSING = "Zaključak"
DEFAULT_QUESTIONS = {"Besprekornost": 2, "Lakoća održavanja": 3, "Funkcionalna pogodnost": 1}

CHK = re.compile(r"^\s*[-*]\s*\[( |x|X)\]")
LABEL_WORDS = r"(obrazlo[žz]enje|napomena|zaklju[čc]ak)"
STOP = re.compile(r"^\s*(#{1,6}\s|<hr|-{3,}\s*$|\*\*[^*\n]*" + LABEL_WORDS + r"[^*\n]*\*\*)",
                  re.I | re.M)

def clean(text):
    text = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)
    return text.replace("\r\n", "\n").replace("\r", "\n")

def start_of(body, name):
    pattern = re.escape(name).replace("č", "[čc]")
    m = re.search(r"^\s*#{1,6}[^\n]*" + pattern, body, re.I | re.M)
    if m:
        return m.start()
    m = re.search(r"^\s*\*\*[^*\n]*" + pattern + r"[^*\n]*\*\*", body, re.I | re.M)
    return m.start() if m else None

def sections(body):
    starts = {n: start_of(body, n) for n in ASPECTS + [FRONTEND, CLOSING]}
    found = sorted(p for p in starts.values() if p is not None)
    out = {}
    for n, p in starts.items():
        if p is None:
            continue
        end = min([q for q in found if q > p] or [len(body)])
        out[n] = body[p:end]
    return out

def groups(sec):
    result, cur = [], []
    for ln in sec.splitlines():
        m = CHK.match(ln)
        if m:
            cur.append(m.group(1).lower() == "x")
        elif ln.strip() and cur:
            result.append(cur); cur = []
    if cur:
        result.append(cur)
    return result

def explanation(sec, word):
    m = re.search(r"\*\*[^*\n]*" + word + r"[^*\n]*\*\*", sec, re.I)
    if not m:
        return None
    rest = re.sub(r"^[ \t]*\([^)\n]*\)", "", sec[m.end():])
    stop = STOP.search(rest)
    txt = rest[:stop.start()] if stop else rest
    txt = re.sub(r"(?im)^\s*[-*]\s*\[( |x|X)\].*$", "", txt)
    txt = re.sub(r"(?i)\bTODO\b", "", txt)
    return re.sub(r"[\s:.\-–—]+", " ", txt).strip()

template = clean(open("template.md", encoding="utf-8").read())
tsec = sections(template)
questions = {a: (len(groups(tsec[a])) if a in tsec and groups(tsec[a]) else DEFAULT_QUESTIONS[a])
             for a in ASPECTS}
frontend_questions = len(groups(tsec[FRONTEND])) if FRONTEND in tsec else 0
REQUIRED = ASPECTS + ([FRONTEND] if frontend_questions else []) + [CLOSING]

def answered(g):
    return all(sum(g_) == 1 for g_ in g)

def picked_no(sec):
    return re.search(r"(?im)^\s*[-*]\s*\[[xX]\]\s*NE\s*$", sec) is not None

def evaluate(raw):
    body = clean(raw)
    secs = sections(body)
    res = {}
    for a in ASPECTS:
        if a not in secs:
            res[a] = f"Aspekt „{a}” nije obrađen."
            continue
        g = groups(secs[a])
        exp = explanation(secs[a], r"obrazlo[žz]enje")
        errs = []
        if len(g) < questions[a]:
            errs.append(f"odgovori na sva pitanja iz šablona (pitanja: {questions[a]}, odgovoreno: {len(g)})")
        elif not answered(g):
            errs.append("na svako pitanje obeleži tačno jedan odgovor")
        if exp is None:
            errs.append("nedostaje polje „obrazloženje” iz šablona")
        elif not exp:
            errs.append("obrazloženje je prazno (ostao TODO)")
        res[a] = f"Aspekt „{a}”: " + ", ".join(errs) + "." if errs else None
    if frontend_questions:
        sec = secs.get(FRONTEND)
        if sec is None:
            res[FRONTEND] = ("Sekcija „Frontend” nije obrađena. Ako PR ne menja frontend, "
                             "na svako pitanje obeleži „NIJE RELEVANTNO ZA OVAJ PR”.")
        else:
            g = groups(sec)
            errs = []
            if len(g) < frontend_questions:
                errs.append(f"odgovori na sva pitanja iz šablona (pitanja: {frontend_questions}, odgovoreno: {len(g)})")
            elif not answered(g):
                errs.append("na svako pitanje obeleži tačno jedan odgovor")
            if picked_no(sec) and not explanation(sec, r"napomena"):
                errs.append("odgovorio si NE, pa popuni napomenu")
            res[FRONTEND] = "Sekcija „Frontend”: " + ", ".join(errs) + "." if errs else None
    exp = explanation(secs.get(CLOSING, ""), r"zaklju[čc]ak")
    if exp is None:
        res[CLOSING] = "Nedostaje „Zaključak, sumarni komentar” iz šablona."
    elif not exp:
        res[CLOSING] = "Zaključak je prazan (ostao TODO)."
    else:
        res[CLOSING] = None
    return res

author = (os.environ.get("PR_AUTHOR") or "").lower()
reviews = json.load(open("reviews.json", encoding="utf-8"))
try:
    current = json.loads(os.environ.get("EVENT_REVIEW") or "null")
except ValueError:
    current = None
if current and current.get("id") not in {r.get("id") for r in reviews}:
    reviews.append(current)

by_reviewer = {}
for r in sorted(reviews, key=lambda r: r.get("submitted_at") or ""):
    user = r.get("user") or {}
    login = user.get("login") or ""
    if not login or login.lower() == author or user.get("type") == "Bot":
        continue
    if (r.get("state") or "").upper() == "PENDING":
        continue
    by_reviewer.setdefault(login, []).append(r.get("body") or "")

if not by_reviewer:
    print("WAIT")
    print("Još nema revizije od recenzenta.")
    raise SystemExit(0)

failures = []
for login, bodies in by_reviewer.items():
    results = [evaluate(b) for b in bodies]
    missing = [k for k in REQUIRED if all(r[k] for r in results)]
    if not missing:
        print("OK")
        print(f"Revizija recenzenta @{login} prati šablon.")
        raise SystemExit(0)
    failures.append((login, [results[-1][k] for k in missing]))

print("FAIL")
for login, errs in failures:
    for e in errs:
        print(f"@{login}: {e}")
