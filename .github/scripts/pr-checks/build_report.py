import json, os, re

build_rc = int(os.environ["BUILD_RC"])
test_rc = int(os.environ["TEST_RC"])

def read(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""

solution_error = os.environ.get("SOLUTION_ERROR", "")

if build_rc != 0:
    status = "build"
    lines = [l.strip() for l in read("build.log").split("\n")
             if re.search(r"\berror\s+[A-Z]{2,}\d+", l)]
    seen, errors = set(), []
    for l in lines:
        if l not in seen:
            seen.add(l); errors.append(l)
    if solution_error:
        errors = [solution_error]
    elif not errors:
        errors = ["Build nije uspeo, a greška nije prepoznata — ceo ispis je u Actions, u job-u build."]
elif test_rc != 0:
    status = "tests"
    seen, errors = set(), []
    for raw in read("test.log").split("\n"):
        s = re.sub(r"^\[xUnit\.net[^\]]*\]\s*", "", raw.strip()).strip()
        m = re.match(r"^Failed\s+(.+?)(?:\s+\[[^\]]*\])?$", s)
        if m:
            name = m.group(1).strip()
        elif "[FAIL]" in s:
            name = s.split("[FAIL]")[0].strip()
        else:
            continue
        if name and name not in seen:
            seen.add(name); errors.append(name)
    if not errors:
        log_text = read("test.log")
        if "inactivity" in log_text or "hang" in log_text.lower():
            errors = ["Testovi su prekinuti jer se neki test zaglavio duže od 5 minuta — ceo ispis je u Actions."]
        else:
            errors = ["Testovi nisu prošli, a pali test nije prepoznat — ceo ispis je u Actions, u job-u build."]
else:
    status = "ok"
    errors = []

def plural(n, one, few, many):
    last, last2 = n % 10, n % 100
    if last == 1 and last2 != 11:
        return f"{n} {one}"
    if last in (2, 3, 4) and last2 not in (12, 13, 14):
        return f"{n} {few}"
    return f"{n} {many}"


def first(items, limit=8):
    shown = items[:limit]
    if len(items) > limit:
        shown.append(f"… i još {len(items) - limit} — ceo spisak je u Actions")
    return shown


summary = ""
log = read("test.log")
runs = re.findall(r"(?:Failed|Passed)!\s+-\s+Failed:\s*(\d+),\s*Passed:\s*(\d+),\s*Skipped:\s*(\d+)", log)
if not runs:
    runs = re.findall(r"Test summary:[^\n]*?failed:\s*(\d+),\s*succeeded:\s*(\d+),\s*skipped:\s*(\d+)", log)
skipped = sum(int(s) for _, _, s in runs)
if runs:
    failed = sum(int(f) for f, _, _ in runs)
    passed = sum(int(p) for _, p, _ in runs)
    summary = f"neuspelih {failed}, uspelih {passed}"
    if len(runs) > 1:
        summary += ", " + plural(len(runs), "test projekat", "test projekta", "test projekata")

skipped_names = []
for raw in log.split("\n"):
    m = re.match(r"^Skipped\s+(.+?)(?:\s+\[[^\]]*\])?$", raw.strip())
    if m and m.group(1) not in skipped_names:
        skipped_names.append(m.group(1))

json.dump({"status": status, "summary": summary, "errors": first(errors),
           "skipped": skipped, "skippedTests": first(skipped_names)},
          open("build.json", "w", encoding="utf-8"), ensure_ascii=False)
print(f"build: {status} {summary} preskočenih={skipped}")
