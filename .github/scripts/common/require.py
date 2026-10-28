import json
import sys


def read_status(path):
    if path.endswith(".json"):
        return json.load(open(path, encoding="utf-8"))["status"]
    return open(path, encoding="utf-8").read().strip()


def main():
    if len(sys.argv) < 4 or sys.argv[2] not in ("--ok", "--not"):
        print("upotreba: require.py FAJL --ok|--not VREDNOST...", file=sys.stderr)
        sys.exit(2)
    status = read_status(sys.argv[1])
    values = sys.argv[3:]
    passed = status in values if sys.argv[2] == "--ok" else status not in values
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
