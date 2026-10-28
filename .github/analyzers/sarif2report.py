import glob
import json
import os
import re
import sys
from urllib.parse import unquote, urlparse

METHOD_METRICS = ("meloc", "cyclo", "nop")
CLASS_METRICS = ("cloc", "wmc", "nad", "nmd", "cbo", "dit")
MEASUREMENT_VERSION = "2026-10-08"


def read_thresholds(path):
    values = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            m = re.match(r"^\s*tt_(\w+)_(suspect|critical)\s*=\s*(-?\d+)\s*$", line)
            if m:
                values.setdefault(m.group(1), [0, 0])[0 if m.group(2) == "suspect" else 1] = int(m.group(3))
    return values


def relative(uri, root):
    parsed = urlparse(uri)
    path = unquote(parsed.path) if parsed.scheme == "file" else unquote(uri)
    path = path.replace("\\", "/")
    if re.match(r"^/[A-Za-z]:/", path):
        path = path[1:]
    root = root.replace("\\", "/").rstrip("/") + "/"
    return path[len(root):] if path.lower().startswith(root.lower()) else path


def level(value, pair):
    suspect, critical = pair
    return "critical" if value > critical else "suspect" if value > suspect else "ok"


def worst(levels):
    values = levels.values()
    return "critical" if "critical" in values else "suspect" if "suspect" in values else "ok"


def main():
    sarif_dir, root, out, config = sys.argv[1:5]
    thresholds = read_thresholds(config)

    methods, classes = {}, {}
    for path in sorted(glob.glob(os.path.join(sarif_dir, "*.sarif"))):
        log = json.load(open(path, encoding="utf-8-sig"))
        for run in log.get("runs", []):
            for result in run.get("results", []):
                if result.get("ruleId") != "TT000":
                    continue
                props = (result.get("properties") or {}).get("customProperties") or {}
                location = result["locations"][0]["physicalLocation"]
                file = relative(location["artifactLocation"]["uri"], root)
                key = (file, props["member"], int(props["startLine"]))
                base = {"file": file, "startLine": int(props["startLine"]), "endLine": int(props["endLine"])}
                if props["kind"] == "method":
                    item = methods.setdefault(key, dict(base, method=props["member"]))
                    item.update({m: int(props[m]) for m in METHOD_METRICS})
                else:
                    item = classes.setdefault(key, dict(base, name=props["member"], dit=0, hasSubclass=0))
                    item.update({m: int(v) for m, v in props.items() if m in CLASS_METRICS or m == "hasSubclass"})

    items, class_items = [], []
    for item in sorted(methods.values(), key=lambda i: (i["file"], i["startLine"])):
        levels = {m: level(item[m], thresholds[m]) for m in METHOD_METRICS}
        if worst(levels) == "ok":
            continue
        rules = "+".join(m.upper() for m in METHOD_METRICS if levels[m] != "ok")
        items.append(dict(item, levels=levels, worst=worst(levels), rules=rules))

    for item in sorted(classes.values(), key=lambda i: (i["file"], i["startLine"])):
        for m in CLASS_METRICS:
            item.setdefault(m, 0)
        levels = {m: level(item[m], thresholds[m]) for m in CLASS_METRICS}
        if item.pop("hasSubclass", 0):
            levels["dit"] = "ok"
        if worst(levels) == "ok":
            continue
        class_items.append(dict(item, levels=levels, worst=worst(levels)))

    def stat(metric, fn):
        values = [m[metric] for m in methods.values()]
        return fn(values) if values else 0

    report = {
        "version": MEASUREMENT_VERSION,
        "nop_max": stat("nop", max),
        "nop_avg": round(stat("nop", lambda v: sum(v) / len(v)), 2),
        "meloc_max": stat("meloc", max),
        "meloc_avg": round(stat("meloc", lambda v: sum(v) / len(v)), 2),
        "cyclo_max": stat("cyclo", max),
        "cyclo_avg": round(stat("cyclo", lambda v: sum(v) / len(v)), 2),
        "violations": len(items) + len(class_items),
        "thresholds": {m: thresholds[m] for m in METHOD_METRICS + CLASS_METRICS},
        "items": items,
        "classItems": class_items,
        "measured": {"methods": len(methods), "classes": len(classes)},
    }
    json.dump(report, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    if not methods and not classes:
        print("Analizator nije prijavio nijedno merenje (TT000).", file=sys.stderr)
        sys.exit(1)

    print(f"nop_max={report['nop_max']} nop_avg={report['nop_avg']:.2f} "
          f"meloc_max={report['meloc_max']} meloc_avg={report['meloc_avg']:.2f} "
          f"cyclo_max={report['cyclo_max']} violations={report['violations']}")


if __name__ == "__main__":
    main()
