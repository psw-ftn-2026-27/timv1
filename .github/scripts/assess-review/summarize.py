import json, os, sys, time, urllib.request

SYSTEM = (
  "Pišeš sažetak procene revizije koda za nastavnika. Dobijaš KONAČNU listu izmerenih problema na jednom PRu "
  "za jednog recenzenta. Za svaki problem je već utvrđeno da li ga je recenzent uočio ili promašio i da li je "
  "posle revizije rešen ili je i dalje otvoren, uz napomenu kako je presuda doneta. "
  "Ispričaj šta se desilo kroz ceo PR: šta je recenzent uočio i da li je to posle ispravljeno, šta je uočio a "
  "ostalo je neispravljeno, šta je promašio a ipak je ispravljeno i šta je promašio i ostalo je otvoreno. "
  "Grupiši po ishodu i preskoči ishode kojih nema. Za svaki problem navedi metodu ili klasu i šta je mereno "
  "(npr. broj parametara, dužina metode, nepokrivene linije). Kada je problem uočen, ukratko reci čime "
  "(komentar na liniji ili sekcija šablona), ako to piše u napomeni. "
  "Najviše četiri rečenice. Ne dodaji probleme, ne menjaj presude i stanja i ne ocenjuj kod. "
  "Ne pominji indekse ni id brojeve. Piši na srpskom ekavskom izgovoru, latinicom, gramatički ispravno. "
  "Ne koristi crtu ni srednju crtu kao znak interpunkcije, umesto toga koristi zarez ili tačku. "
  "Odgovori samo tekstom sažetka, bez naslova i bez navodnika."
)

KIND = {"coverage": "pokrivenost", "maintainability": "lakoća održavanja"}


def outcome(p):
    seen = "recenzent uočio" if p.get("addressed") else "recenzent promašio"
    state = "rešeno posle revizije" if p.get("status") == "resolved" else "i dalje otvoreno"
    return f"{seen}; {state}"


def build_prompt(reviewer):
    lines = [f"Recenzent: @{reviewer.get('login', '')}", "Izmereni problemi:"]
    for p in reviewer.get("problems") or []:
        where = p.get("method") or ""
        lines.append(f"- {KIND.get(p.get('kind'), p.get('kind'))}, {p.get('file', '')} · {where}: "
                     f"{p.get('detail', '')} | {outcome(p)} | napomena: {p.get('note') or ''}")
    return "\n".join(lines)


def ask(prompt):
    body = json.dumps({"model": os.environ["LLM_MODEL"], "max_tokens": 8000,
                       "output_config": {"effort": "low"}, "system": SYSTEM,
                       "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
                "content-type": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=120))
            if d.get("stop_reason") == "max_tokens":
                raise ValueError("odgovor je odsečen (max_tokens)")
            text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text").strip()
            if not text:
                raise ValueError("prazan odgovor")
            return text
        except Exception as e:
            detail = e.read().decode("utf-8", "replace")[:300] if hasattr(e, "read") else ""
            print(f"  sažetak, pokušaj {attempt} nije uspeo: {e} {detail}")
            if attempt < 3:
                time.sleep(10 * attempt)
    return None


def main():
    path = "review-assessment.json"
    assessment = json.load(open(path, encoding="utf-8"))
    dry_run = os.environ.get("SUMMARY_DRY_RUN") == "1"
    reviewers = assessment.get("reviewers") or []
    for idx, r in enumerate(reviewers):
        if not r.get("problems"):
            continue
        prompt = build_prompt(r)
        if dry_run:
            open(f"summary_prompt_{idx}.txt", "w", encoding="utf-8").write(prompt)
            continue
        text = ask(prompt)
        if text:
            r["summary"] = text
            print(f"sažetak za @{r.get('login')}: napisan")
        else:
            print(f"sažetak za @{r.get('login')}: ostaje sažetak iz procene")
    if len(reviewers) == 1:
        assessment["summary"] = reviewers[0].get("summary")
    json.dump(assessment, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    sys.exit(main())
