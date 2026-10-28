import json, re, sys, os, glob
import xml.etree.ElementTree as ET

MEASUREMENT_VERSION = "2026-10-08"
MAINTAINABILITY = "lakoća održavanja"

HUNK = re.compile(r"^@@\s*-\d+(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s*@@")
CODE_RE = re.compile(r"```|`[^`\n]+`")
URL_RE = re.compile(r"https?://[^\s)>\]]+")

def load(path, default):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default

def is_bot(user):
    return (user or {}).get("type") == "Bot"

CONST_DECLARATION = re.compile(r"^\s*(?:(?:public|private|protected|internal|new)\s+)*const\s")

def added_or_changed_lines(patch, skip_constants=False):
    res = set()
    if not patch:
        return res
    newline = 0
    for raw in patch.split("\n"):
        line = raw.rstrip("\r")
        m = HUNK.match(line)
        if m:
            newline = int(m.group(1)); continue
        if line.startswith("\\"):
            continue
        if line.startswith("+") and not line.startswith("+++"):
            if not (skip_constants and CONST_DECLARATION.match(line[1:])):
                res.add(newline)
            newline += 1
        elif line.startswith("-") and not line.startswith("---"):
            pass
        else:
            newline += 1
    return res

def range_touched(start, end, touched):
    return any(l in touched for l in range(start, end + 1))

def class_name(raw):
    name = re.split(r"[/+<]", raw or "", maxsplit=1)[0]
    return re.sub(r"`\d+$", "", name.split(".")[-1])

def parse_cobertura_classes(path):
    out = {}
    root = ET.parse(path).getroot()
    for cls in root.iter("class"):
        fn = (cls.get("filename") or "").replace("\\", "/")
        name = class_name(cls.get("name"))
        if not fn or not name:
            continue
        lines = out.setdefault(fn, {}).setdefault(name, {})
        for line in cls.iter("line"):
            try:
                num = int(line.get("number")); hits = int(line.get("hits"))
            except (TypeError, ValueError):
                continue
            lines[num] = max(lines.get(num, 0), hits)
    return out

def match_coverage(cov, diff_path):
    dp = diff_path.replace("\\", "/")
    if dp in cov:
        return cov[dp]
    for k, v in cov.items():
        if k.endswith(dp) or dp.endswith(k):
            return v
    return None

METRIC_LABELS = [("MELOC", "meloc", "predugačka metoda"),
                 ("CYCLO", "cyclo", "previše grananja"),
                 ("NOP", "nop", "previše parametara"),
                 ("CLOC", "cloc", "velika klasa"),
                 ("WMC", "wmc", "velika ukupna složenost"),
                 ("NAD", "nad", "previše polja"),
                 ("NMD", "nmd", "previše metoda"),
                 ("CBO", "cbo", "previše zavisnosti"),
                 ("DIT", "dit", "duboko nasleđivanje")]

def maint_detail(it):
    rules = it.get("rules", "")
    parts = [f"{name}={it.get(key, 0)} ({why})"
             for name, key, why in METRIC_LABELS if name in rules]
    return ", ".join(parts) if parts else rules

BODY_ASPECTS = [("Funkcionalna pogodnost", "funkcionalna pogodnost"),
                ("Besprekornost", "besprekornost"),
                ("Lakoća održavanja", "lakoća održavanja"),
                ("Frontend", "frontend"),
                ("Zaključak", "zaključak")]

IGNORED_SECTIONS = {"frontend"}
FRONTEND_DIR = (os.environ.get("FRONTEND_DIR", "") or "").strip().strip("/")

def is_frontend_path(path):
    return bool(FRONTEND_DIR and path and path.replace("\\", "/").startswith(FRONTEND_DIR + "/"))

CHECKBOX_RE = re.compile(r"^\s*[-*]\s*\[( |x|X)\]")

def normalize(text):
    text = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)
    return text.replace("\r\n", "\n").replace("\r", "\n")

TEMPLATE_LINES = {l.strip() for l in normalize(open("template.md", encoding="utf-8").read()).split("\n")
                  if l.strip() and l.strip().upper() != "TODO"} if os.path.exists("template.md") else set()

def clean_body_section(text):
    kept = []
    for ln in text.split("\n"):
        s = ln.strip()
        if not s or s.startswith("#") or CHECKBOX_RE.match(ln):
            continue
        if re.fullmatch(r"<hr\s*/?>", s, re.I) or s == "---":
            continue
        if re.fullmatch(r"\*\*.*\*\*:?", s):
            continue
        if s in TEMPLATE_LINES or (not TEMPLATE_LINES and s.endswith("?")):
            continue
        s = re.sub(r"(?i)\bTODO\b", "", s).strip()
        if s:
            kept.append(s)
    return "\n".join(kept).strip()

def section_start(body, name):
    pat = re.escape(name).replace("č", "[čc]")
    m = re.search(r"^\s*#{1,6}[^\n]*" + pat, body, re.I | re.M)
    if not m:
        m = re.search(r"^\s*\*\*[^*\n]*" + pat + r"[^*\n]*\*\*", body, re.I | re.M)
    return m.start() if m else None

def split_review_body(body):
    body = normalize(body)
    marks = sorted((p, name, aspect) for name, aspect in BODY_ASPECTS
                   for p in [section_start(body, name)] if p is not None)
    if not marks:
        cleaned = clean_body_section(body)
        return [("", "telo revizije", cleaned)] if cleaned else []

    out = []
    intro = clean_body_section(body[:marks[0][0]])
    if intro:
        out.append(("", "telo revizije — uvod", intro))
    for i, (pos, name, aspect) in enumerate(marks):
        if aspect in IGNORED_SECTIONS:
            continue
        end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
        text = clean_body_section(body[pos:end])
        if text:
            out.append((aspect, f"telo revizije — {aspect}", text))
    return out

def collect_review_bodies(author):
    seen, out = set(), []
    for r in load("reviews.json", []):
        user = r.get("user") or {}
        login = user.get("login", "") or ""
        rbody = (r.get("body") or "").strip()
        if not rbody or rbody in seen or is_bot(user):
            continue
        if login.lower() == author.lower():
            continue
        seen.add(rbody)
        out.append((r.get("id"), login, rbody))

    rb = (os.environ.get("REVIEW_BODY", "") or "").strip()
    rb_author = os.environ.get("REVIEW_AUTHOR", "") or ""
    if rb and rb not in seen and rb_author.lower() != author.lower():
        try:
            rb_id = int(os.environ.get("REVIEW_ID") or 0)
        except ValueError:
            rb_id = 0
        out.append((rb_id, rb_author, rb))
    return out

def plural(n, one, few, many):
    last, last2 = n % 10, n % 100
    if last == 1 and last2 != 11:
        return f"{n} {one}"
    if last in (2, 3, 4) and last2 not in (12, 13, 14):
        return f"{n} {few}"
    return f"{n} {many}"

def clip_hunk(h, keep=8, width=140):
    if not h:
        return []
    rows = [r.rstrip()[:width] for r in h.split("\n") if r.strip()]
    return rows[-keep:]

def do_build():
    author = os.environ.get("PR_AUTHOR", "") or ""
    maint = load("maintainability-report.json", None)
    files = load("files.json", None)
    if maint is None or files is None or not os.path.exists("Cobertura.xml"):
        print("ulazni podaci nedostaju", file=sys.stderr); sys.exit(3)
    raw_comments = load("comments.json", [])
    raw_issue = load("issue_comments.json", [])
    cov = parse_cobertura_classes("Cobertura.xml")

    touched = {}
    testable = {}
    for f in files:
        fn = f.get("filename")
        if fn:
            touched[fn] = added_or_changed_lines(f.get("patch"))
            testable[fn] = added_or_changed_lines(f.get("patch"), skip_constants=True)

    problems = []
    for it in maint.get("items", []):
        f = it.get("file")
        if f in touched and range_touched(it.get("startLine", 0), it.get("endLine", 0), touched[f]):
            problems.append({"kind": "maintainability", "file": f, "method": it.get("method", ""),
                             "rules": it.get("rules", ""), "detail": maint_detail(it),
                             "startLine": it.get("startLine"), "endLine": it.get("endLine"),
                             "meloc": it.get("meloc", 0), "nop": it.get("nop", 0)})

    for it in maint.get("classItems", []):
        f = it.get("file")
        if f in touched and range_touched(it.get("startLine", 0), it.get("endLine", 0), touched[f]):
            rules = "+".join(k.upper() for k, v in (it.get("levels") or {}).items() if v != "ok")
            if not rules:
                continue
            problems.append({"kind": "maintainability", "file": f,
                             "method": f"{it.get('name', '')} (klasa)",
                             "rules": rules, "detail": maint_detail({**it, "rules": rules}),
                             "startLine": it.get("startLine"), "endLine": it.get("endLine"),
                             "meloc": 0, "nop": 0})

    for f, lines in testable.items():
        classes = match_coverage(cov, f)
        if not classes:
            continue
        covered_anywhere = {l for hits in classes.values() for l, h in hits.items() if h > 0}
        for name, hits in sorted(classes.items()):
            missing = sorted(l for l in lines if l in hits and hits[l] == 0 and l not in covered_anywhere)
            if not missing:
                continue
            linije = plural(len(missing), "nova linija", "nove linije", "novih linija")
            problems.append({"kind": "coverage", "file": f, "method": name, "rules": "COVERAGE",
                             "detail": f"{linije} bez testa", "lines": missing[:10],
                             "meloc": 0, "nop": 0})

    comments = []

    for rid, login, rbody in collect_review_bodies(author):
        for aspect, label, text in split_review_body(rbody):
            comments.append({"id": rid, "login": login, "path": None,
                             "line": None, "hunk": [], "source": label,
                             "section": aspect, "body": text})

    for c in raw_comments:
        user = c.get("user") or {}
        login = user.get("login", "")
        if is_bot(user) or (login and login.lower() == author.lower()):
            continue
        if is_frontend_path(c.get("path")):
            continue
        comments.append({"id": c.get("id"), "login": login, "path": c.get("path"),
                         "line": c.get("line") or c.get("original_line"),
                         "hunk": clip_hunk(c.get("diff_hunk")),
                         "source": "inline",
                         "body": (c.get("body") or "").replace("\n", " ").strip()})

    for c in raw_issue:
        user = c.get("user") or {}
        login = user.get("login", "")
        if is_bot(user) or (login and login.lower() == author.lower()):
            continue
        body = (c.get("body") or "").strip()
        if not body or body.startswith("<!--"):
            continue
        comments.append({"id": c.get("id"), "login": login, "path": None,
                         "line": None, "hunk": [], "source": "opsti komentar",
                         "body": body.replace("\n", " ").strip()})

    for i, c in enumerate(comments):
        raw = str(c.get("body") or "")
        c["key"] = i
        c["hasCode"] = bool(CODE_RE.search(raw))
        c["links"] = len(URL_RE.findall(raw))

    order = []
    for login in [c["login"] for c in comments] + \
                 [(r.get("user") or {}).get("login", "") for r in load("reviews.json", [])
                  if not is_bot(r.get("user"))] + [os.environ.get("REVIEW_AUTHOR", "")]:
        if login and login.lower() != author.lower() and login.lower() not in [o.lower() for o in order]:
            order.append(login)

    reviewers = []
    for idx, login in enumerate(order):
        mine = [c for c in comments if (c["login"] or "").lower() == login.lower()]
        open(f"prompt_{idx}.txt", "w", encoding="utf-8").write(build_prompt(maint, problems, mine))
        reviewers.append({"login": login, "keys": [c["key"] for c in mine]})

    json.dump({"problems": problems, "comments": comments, "reviewers": reviewers},
              open("problems.json", "w", encoding="utf-8"), ensure_ascii=False)
    print(f"build: {len(problems)} problema, {len(comments)} komentara, recenzenti: "
          + ", ".join(f"{r['login']} ({len(r['keys'])})" for r in reviewers))

def build_prompt(maint, problems, comments):
    lines = []
    th = maint.get("thresholds") or {}
    if th:
        lines.append("PRAGOVI (sumnjivo / kritično — prekršaj je vrednost VEĆA od praga): " + ", ".join(
            f"{k.upper()}={v[0]}/{v[1]}" for k, v in th.items()
            if isinstance(v, list) and len(v) == 2))
        lines.append("")
    lines.append("IZMERENI PROBLEMI (zatvorena lista — drugih problema nema):")
    if problems:
        for i, p in enumerate(problems):
            loc = ""
            if p["kind"] == "coverage":
                loc = f" klasa={p['method']} nepokrivene linije: " + ", ".join(str(x) for x in p.get("lines") or [])
            elif p.get("method"):
                loc = f" metoda={p['method']} (linije {p.get('startLine')}-{p.get('endLine')})"
            lines.append(f"[{i}] tip={p['kind']} fajl={p['file']}{loc} — {p['detail']}")
    else:
        lines.append("(nema)")
    lines.append("")
    lines.append("KOMENTARI RECENZENTA (izvor: telo revizije / inline / opsti komentar):")
    if comments:
        for c in comments:
            ln = c.get("line")
            src = c.get("source", "inline")
            lines.append(f"{{id={c['key']}, izvor={src}, fajl={c.get('path') or '—'}, linija={ln if ln else '—'}}}")
            lines.append("  komentar:")
            for bl in str(c["body"]).split("\n"):
                if bl.strip():
                    lines.append("    " + bl.strip())
            if c.get("hunk"):
                lines.append("  kod:")
                for r in c["hunk"]:
                    lines.append("    " + r)
    else:
        lines.append("(nema)")
    lines.append("")
    lines.append("Vrati JSON: {\"problems\":[{\"index\":N,\"addressed\":true|false,\"note\":\"\"}],\"comments\":[{\"id\":N,\"onPoint\":true|false,\"kind\":\"\",\"aspect\":\"\",\"subaspect\":\"\",\"tone\":\"\",\"hasSuggestion\":true|false,\"hasRationale\":true|false,\"note\":\"\"}],\"summary\":\"...\"}")
    return "\n".join(lines)

PROBLEM_KEYS = ("kind", "file", "method", "rules", "detail", "meloc", "nop")

def tally(items, key, only=None):
    acc = {}
    for c in items:
        if only is not None and not only(c):
            continue
        v = c.get(key) or "nepoznato"
        acc[v] = acc.get(v, 0) + 1
    return acc

def comment_stats(out_comments):
    defects = [c for c in out_comments if c.get("kind") == "nedostatak" and c["onPoint"]]
    return {"total": len(out_comments),
            "onPoint": sum(1 for c in out_comments if c["onPoint"]),
            "withCodeSnippet": sum(1 for c in out_comments if c["hasCodeSnippet"]),
            "withLinks": sum(1 for c in out_comments if c["linkCount"] > 0),
            "bySource": tally(out_comments, "source"),
            "byKind": tally(out_comments, "kind"),
            "byAspect": tally(out_comments, "aspect"),
            "bySubaspect": tally(out_comments, "subaspect", lambda c: c.get("aspect") == MAINTAINABILITY),
            "byTone": tally(out_comments, "tone"),
            "defects": len(defects),
            "defectsWithSuggestion": sum(1 for c in defects if c["hasSuggestion"]),
            "defectsWithRationale": sum(1 for c in defects if c["hasRationale"])}

def problem_key(p):
    return (p.get("kind"), p.get("file"), p.get("method") or "")

def load_history():
    history, order = {}, []
    paths = glob.glob("prev/*/review-assessment.json")
    for path in sorted(paths, key=lambda x: int(x.split("/")[1])):
        try:
            previous = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (previous.get("measurement") or {}).get("version") != MEASUREMENT_VERSION:
            continue
        for r in previous.get("reviewers") or []:
            login = (r.get("login") or "").lower()
            for p in r.get("problems") or []:
                if p.get("status") == "resolved":
                    continue
                k = problem_key(p)
                if k not in history:
                    history[k] = {"problem": None, "last": {}}
                    order.append(k)
                history[k]["problem"] = {kk: p.get(kk) for kk in PROBLEM_KEYS}
                history[k]["last"][login] = (bool(p.get("addressed")), p.get("note"))
    return history, order

def with_history(login, current, history, order):
    login = login.lower()
    current_keys = {problem_key(p) for p in current}
    merged = [{**p, "status": "open"} for p in current]
    for k in order:
        h = history[k]
        if k in current_keys or login not in h["last"]:
            continue
        addressed, note = h["last"][login]
        merged.append({**h["problem"], "addressed": addressed, "note": note, "status": "resolved"})
    return merged

def counts(merged):
    caught = sum(1 for p in merged if p["addressed"])
    resolved = sum(1 for p in merged if p["status"] == "resolved")
    return {"problemsTotal": len(merged), "addressed": caught, "missed": len(merged) - caught,
            "resolved": resolved,
            "resolvedAddressed": sum(1 for p in merged if p["status"] == "resolved" and p["addressed"])}

def problem_lines(out_problems):
    md = []
    for p in out_problems:
        mark = "✅ uočeno" if p["addressed"] else "❌ promašeno"
        if p.get("status") == "resolved":
            mark += " · ✔ rešeno"
        kind = "pokrivenost" if p["kind"] == "coverage" else "lakoća održavanja"
        loc = p["file"] if not p["method"] else f"{p['file']} · {p['method']}"
        md.append(f"- {mark}, {kind}: `{loc}`: {p['detail']}")
    return md

SUB = ('<sub>Alati automatski mere dve stvari na kodu koji PR menja: nove linije koje nisu pokrivene testovima i metode ili klase koje prelaze pragove lakoće održavanja (🟡 i 🔴 iz komentara „Stanje PRa”). Ova procena proverava da li je recenzent te probleme pomenuo u svojim komentarima. Ne blokira spajanje i ne ocenjuje reviziju u celini, već recenzentu pokazuje šta je eventualno propustio.</sub>')

def do_assemble():
    sha = os.environ.get("HEAD_SHA", "")
    model = os.environ.get("LLM_MODEL", "")
    pb = json.load(open("problems.json", encoding="utf-8"))
    problems, comments = pb["problems"], pb["comments"]
    by_key = {c["key"]: c for c in comments}
    history, order = load_history()

    per_reviewer = []
    for idx, r in enumerate(pb["reviewers"]):
        llm = json.load(open(f"llm_{idx}.json", encoding="utf-8"))
        pv = {p.get("index"): p for p in (llm.get("problems") or [])}
        cv = {c.get("id"): c for c in (llm.get("comments") or [])}
        out_problems = [{**{k: p[k] for k in PROBLEM_KEYS},
                         "addressed": bool((pv.get(i) or {}).get("addressed")),
                         "note": (pv.get(i) or {}).get("note")}
                        for i, p in enumerate(problems)]
        out_comments = [assemble_comment(by_key[k], cv[k]) for k in r["keys"]]
        merged = with_history(r["login"], out_problems, history, order)
        per_reviewer.append({"login": r["login"],
                             "summary": llm.get("summary") if out_problems and r["keys"] else None,
                             **counts(merged),
                             "problems": merged, "comments": out_comments,
                             "commentStats": comment_stats(out_comments)})

    union_by_key = {}
    for r in per_reviewer:
        for p in r["problems"]:
            k = problem_key(p)
            if k not in union_by_key:
                union_by_key[k] = dict(p)
            elif p["addressed"] and not union_by_key[k]["addressed"]:
                union_by_key[k].update(addressed=True, note=p["note"])
    union_problems = list(union_by_key.values())
    union_comments = [c for r in per_reviewer for c in r["comments"]]

    measurement = {"version": MEASUREMENT_VERSION,
                   "workflowSha": os.environ.get("WORKFLOW_SHA", "")}
    assessment = {"sha": sha, "model": model, "measurement": measurement,
                  "summary": per_reviewer[0]["summary"] if len(per_reviewer) == 1 else None,
                  **counts(union_problems),
                  "problems": union_problems, "comments": union_comments,
                  "commentStats": comment_stats(union_comments),
                  "reviewers": per_reviewer}
    json.dump(assessment, open("review-assessment.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    md = ["<!-- teamtracker-review-assessment -->", "## Automatska procena revizije", "", SUB, ""]
    if not union_problems:
        md.append("_Alati nisu izmerili nijedan problem na kodu koji ovaj PR menja, pa nema šta da se uporedi sa komentarima recenzenta._")
    for r in per_reviewer:
        if not r["problems"]:
            continue
        head = f"#### @{r['login']}: uočeno {r['addressed']} · promašeno {r['missed']}"
        if r["resolved"]:
            head += f" · rešeno posle revizije: {r['resolvedAddressed']} od {r['addressed']} uočenih"
        md.append(head)
        md.append("")
        md += problem_lines(r["problems"]) + [""]
    open("comment.md", "w", encoding="utf-8").write("\n".join(md))
    print("assemble: " + ", ".join(f"{r['login']} {r['addressed']}/{r['problemsTotal']}" for r in per_reviewer))

def assemble_comment(c, v):
    ex = c["body"]
    section = c.get("section") or ""
    kind = "zaključak" if section == "zaključak" else v.get("kind")
    aspect = v.get("aspect")
    defect = kind == "nedostatak"
    return {"commentGitHubId": c["id"], "authorLogin": c["login"],
            "source": c.get("source", "inline"),
            "excerpt": ex[:160] + ("…" if len(ex) > 160 else ""),
            "onPoint": bool(v.get("onPoint", False)),
            "section": section,
            "aspect": aspect, "kind": kind,
            "subaspect": (v.get("subaspect") or None) if aspect == MAINTAINABILITY else None,
            "tone": v.get("tone"),
            "hasSuggestion": defect and bool(v.get("hasSuggestion")),
            "hasRationale": defect and bool(v.get("hasRationale")),
            "hasCodeSnippet": bool(c.get("hasCode")), "linkCount": int(c.get("links") or 0),
            "note": v.get("note")}

mode = sys.argv[1] if len(sys.argv) > 1 else ""
if mode == "build":
    do_build()
elif mode == "assemble":
    do_assemble()
else:
    print("upotreba: build|assemble", file=sys.stderr); sys.exit(2)
