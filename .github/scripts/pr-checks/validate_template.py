import json
import os
import re

body = os.environ.get("PR_BODY", "") or ""
frontend_dir = (os.environ.get("FRONTEND_DIR", "") or "").strip().strip("/")
backend_dir = (os.environ.get("BACKEND_DIR", "") or "").strip().strip("/")

TEMPLATE_LINES = set()
if os.path.exists("pr_template.md"):
    TEMPLATE_LINES = {ln.strip() for ln in open("pr_template.md", encoding="utf-8") if ln.strip()}

TYPES = ["feature", "bugfix", "refactor", "test", "chore", "docs"]
BACKEND_BY_TYPE = {
    "feature":  ["Izmene nad bazom", "Testiranje funkcionalnosti"],
    "bugfix":   ["Testiranje funkcionalnosti"],
    "refactor": ["Testiranje funkcionalnosti"],
    "test":     [],
    "chore":    [],
    "docs":     [],
}
SECTIONS = ["Obim PRa", "Tip PRa", "Change goal", "Izmene nad bazom",
            "Testiranje funkcionalnosti", "Frontend izmene"]
BOUNDARIES = SECTIONS + ["Backend"]
CHECKBOX = re.compile(r"^[-*]\s*\[( |x|X)\]")


def split_sections(text):
    marks = []
    for name in BOUNDARIES:
        pattern = re.escape(name).replace("PRa", "PR-?a")
        m = re.search(r"\*\*\s*" + pattern + r"\s*\*\*", text, re.I)
        if m:
            marks.append((text.rfind("\n", 0, m.start()) + 1, name))
    marks.sort()
    out = {}
    for i, (pos, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        out[name] = text[pos:end]
    return out


def own_lines(name, chunk):
    own, leftover = [], []
    for ln in chunk.splitlines():
        s = ln.strip()
        if not s:
            continue
        if re.fullmatch(r"<hr\s*/?>|-{3,}", s, re.I):
            continue
        if name.lower() in s.lower() and "**" in s:
            continue
        if re.fullmatch(r"\*\*.*\*\*:?", s):
            continue
        (leftover if s in TEMPLATE_LINES else own).append(s)
    return own, leftover


def marked(chunk, options):
    return [o for o in options if re.search(r"[-*]\s*\[[xX]\]\s*" + re.escape(o) + r"\b", chunk or "", re.I)]


def is_todo(line):
    return line.upper().startswith("TODO")


def check_filled(name, chunk, errors):
    if chunk is None:
        errors.append(f"Sekcija „{name}” ne postoji u opisu.")
        return ""
    own, leftover = own_lines(name, chunk)
    text = [s for s in own if not is_todo(s)]
    todo = any(is_todo(s) for s in own + leftover)
    if not text and todo:
        errors.append(f"Sekcija „{name}” nije popunjena, ostao je TODO.")
    elif not text and leftover:
        errors.append(f"Sekcija „{name}” sadrži samo primer iz šablona, upiši svoj sadržaj.")
    elif not text:
        errors.append(f"Sekcija „{name}” je prazna.")
    elif todo:
        errors.append(f"Sekcija „{name}”: obriši red koji počinje sa TODO.")
    return "\n".join(text)


def answer(lines):
    picked = [o for o in ("Da", "Ne")
              if any(re.match(r"^[-*]\s*\[[xX]\]\s*" + o + r"\b", s, re.I) for s in lines)]
    return picked[0] if len(picked) == 1 else None


def database_parts(chunk):
    parts = {"changes": [], "description": [], "migrations": []}
    part = None
    for ln in chunk.splitlines():
        s = ln.strip()
        low = s.lower()
        if not s or re.fullmatch(r"<hr\s*/?>|-{3,}", s, re.I):
            continue
        if "pokrenuti migracije" in low:
            part = "migrations"
        elif re.search(r"uklju[čc]uje izmene nad bazom", low):
            part = "changes"
        elif low.startswith("**seed"):
            part = None
        elif part == "changes" and not CHECKBOX.match(s):
            part = "description"
            parts[part].append(s)
        elif part:
            parts[part].append(s)
    return parts


def check_database(chunk, errors):
    name = "Izmene nad bazom"
    if chunk is None:
        errors.append(f"Sekcija „{name}” ne postoji u opisu.")
        return ""
    parts = database_parts(chunk)
    changes = answer(parts["changes"])
    if changes is None:
        errors.append(f"Sekcija „{name}”: obeleži da li PR uključuje izmene nad bazom (Da ili Ne).")
        return ""
    if changes == "Ne":
        return ""

    description = [s for s in parts["description"] if s not in TEMPLATE_LINES and not is_todo(s)]
    if not description:
        errors.append(f"Sekcija „{name}”: opiši kako PR menja bazu umesto TODO.")
    elif any(is_todo(s) for s in parts["description"]):
        errors.append(f"Sekcija „{name}”: obriši red koji počinje sa TODO.")
    if answer(parts["migrations"]) is None:
        errors.append(f"Sekcija „{name}”: obeleži da li je potrebno pokrenuti migracije (Da ili Ne).")
    return "\n".join(description)


def check_frontend(chunk, errors):
    name = "Frontend izmene"
    if chunk is None:
        errors.append(f"Sekcija „{name}” ne postoji u opisu.")
        return ""
    own, leftover = own_lines(name, chunk)
    kinds = [s for s in own if CHECKBOX.match(s) and re.match(r"^[-*]\s*\[[xX]\]", s)]
    text = [s for s in own if not CHECKBOX.match(s) and not is_todo(s)]
    if not kinds:
        errors.append(f"Sekcija „{name}”: obeleži bar jednu vrstu izmene na frontu.")
    if not text:
        errors.append(f"Sekcija „{name}”: u 1–2 rečenice opiši izmenu na frontu umesto TODO.")
    elif any(is_todo(s) for s in own + leftover):
        errors.append(f"Sekcija „{name}”: obriši red koji počinje sa TODO.")
    return "\n".join(kinds + text)


def touched_parts():
    if not frontend_dir or not os.path.exists("files.json"):
        return None
    names = [f.get("filename", "") for f in json.load(open("files.json", encoding="utf-8"))]
    frontend = any(n.startswith(frontend_dir + "/") for n in names)
    if backend_dir:
        backend = any(n.startswith(backend_dir + "/") for n in names)
    else:
        backend = any(not n.startswith(frontend_dir + "/") and not n.startswith(".github/") for n in names)
    return {"backend": backend, "frontend": frontend}


sections = split_sections(body)
errors = []

if not sections:
    errors.append("Opis PRa ne prati šablon, nijedna sekcija nije pronađena. "
                  "Nalepi sadržaj .github/pull_request_template.md u opis i popuni ga.")
    json.dump({"status": "fail", "ptype": None, "scope": [], "touched": None, "errors": errors, "sections": {}},
              open("template.json", "w", encoding="utf-8"), ensure_ascii=False)
    print("FAIL: " + errors[0])
    raise SystemExit(0)

selected = marked(sections.get("Tip PRa", body), TYPES)
if not selected:
    errors.append("Tip PRa nije obeležen, obeleži tačno jedan (feature/bugfix/refactor/test/chore/docs).")
elif len(selected) > 1:
    errors.append("Obeleženo je više tipova (" + ", ".join(selected) + "), obeleži tačno jedan.")
ptype = selected[0] if len(selected) == 1 else None

scope = marked(sections["Obim PRa"], ["backend", "frontend"]) if "Obim PRa" in sections else ["backend"]
touched = touched_parts()
suggested = [part for part in ("backend", "frontend") if touched and touched[part]]

if "Obim PRa" not in sections and frontend_dir:
    errors.append("Sekcija „Obim PRa” ne postoji u opisu.")
    scope = suggested or ["backend"]
elif not scope:
    if suggested:
        errors.append("Obim PRa nije obeležen, prema izmenjenim fajlovima obeleži: " + " i ".join(suggested) + ".")
    else:
        errors.append("Obim PRa nije obeležen, obeleži backend, frontend ili oba.")
elif suggested:
    for part, folder in (("frontend", frontend_dir), ("backend", backend_dir or "van " + frontend_dir)):
        if touched[part] and part not in scope:
            errors.append(f"PR menja {part} ({folder}/), a u obimu PRa {part} nije obeležen.")
        if not touched[part] and part in scope:
            errors.append(f"U obimu PRa obeležen je {part}, a PR ne menja {part} ({folder}/).")

content = {"Change goal": check_filled("Change goal", sections.get("Change goal"), errors)}
if "backend" in scope and ptype is not None:
    for name in BACKEND_BY_TYPE[ptype]:
        if name == "Izmene nad bazom":
            content[name] = check_database(sections.get(name), errors)
        else:
            content[name] = check_filled(name, sections.get(name), errors)
if "frontend" in scope:
    content["Frontend izmene"] = check_frontend(sections.get("Frontend izmene"), errors)

json.dump({"status": "fail" if errors else "ok", "ptype": ptype, "scope": scope,
           "touched": touched, "errors": errors, "sections": content},
          open("template.json", "w", encoding="utf-8"), ensure_ascii=False)
print(("FAIL: " + "; ".join(errors)) if errors else f"OK ({ptype}, {'+'.join(scope)})")
