import json, math, os

def load(name, default):
    p = os.path.join("parts", name)
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default

bld = load("build.json", {"status": "error", "summary": "", "errors": []})
tpl = load("template.json", {"status": "error", "errors": [], "ptype": None})
dsc = load("description.json", {"status": "skip", "suspects": []})
cov = load("coverage.json", {"status": "error", "threshold": 0.8})
mnt = load("maintainability.json", {"status": "error", "methods": [], "classes": [], "thresholds": {}})

MARK = {"ok": "✅", "suspect": "🟡", "critical": "🔴"}

out = ["<!-- teamtracker-pr-checks -->", "## Stanje PRa", ""]

def pct(x):
    if x is None:
        return "?"
    tenths = math.floor(x * 1000 + 1e-9) / 10
    return f"{tenths:.0f}%" if tenths == int(tenths) else f"{tenths:.1f}%"

if tpl["status"] == "ok":
    tpl_txt = f"✅ ispravan (`{tpl.get('ptype') or '?'}` · {' + '.join(tpl.get('scope') or ['backend'])})"
elif tpl["status"] == "fail":
    tpl_txt = "❌ **nije ispravan**"
else:
    tpl_txt = "❌ **provera nije izvršena** (greška u alatu), pokreni ponovo (Actions → **Re-run failed jobs**)"

already = " ".join(tpl.get("errors", []))
suspects = [s for s in dsc.get("suspects", []) if (s.get("name") or "") not in already]

if dsc["status"] == "suspect" and not suspects:
    dsc_txt = "⏸️ pokriveno proverom šablona"
else:
    dsc_txt = {"ok": "✅ smislen", "suspect": "⚠️ sumnjive sekcije",
               "skip": "⏸️ preskočeno",
               "empty": "⏸️ pokriveno proverom šablona"}.get(dsc["status"], "⏸️ preskočeno")

if cov["status"] == "ok" and cov.get("ratio") is None:
    cov_txt = "✅ nema novih testabilnih linija"
elif cov["status"] == "ok":
    cov_txt = (f"✅ {pct(cov.get('ratio'))}, {cov.get('coveredNew')} od "
               f"{cov.get('addedExec')} novih linija (prag {pct(cov.get('threshold'))})")
elif cov["status"] == "fail":
    cov_txt = f"❌ **{pct(cov.get('ratio'))}** (prag {pct(cov.get('threshold'))})"
elif bld["status"] == "ok":
    cov_txt = "❌ **nije izmereno**"
else:
    cov_txt = "⚠️ nije izmereno (build ili testovi nisu prošli)"

def plural(n, one, few, many):
    last, last2 = n % 10, n % 100
    if last == 1 and last2 != 11:
        return f"{n} {one}"
    if last in (2, 3, 4) and last2 not in (12, 13, 14):
        return f"{n} {few}"
    return f"{n} {many}"

if cov.get("skippedFiles") and cov["status"] in ("ok", "fail"):
    cov_txt += " · ⚠️ " + plural(len(cov["skippedFiles"]), "fajl nije uračunat",
                                  "fajla nisu uračunata", "fajlova nije uračunato")

nm, nc = len(mnt.get("methods", [])), len(mnt.get("classes", []))
if mnt.get("status") == "error":
    mnt_txt = "⚠️ nije izmereno (greška u alatu), ne blokira (Actions → **Re-run failed jobs**)"
elif nm or nc:
    parts = ([plural(nm, "metoda", "metode", "metoda")] if nm else []) + \
            ([plural(nc, "klasa", "klase", "klasa")] if nc else [])
    mnt_txt = "⚠️ " + ", ".join(parts)
else:
    mnt_txt = "✅ nema prekršaja"

sonar_key = os.environ.get("SONAR_PROJECT_KEY", "").strip()
sonar_txt = ""
if sonar_key:
    pr_link = f"https://sonarcloud.io/dashboard?id={sonar_key}&pullRequest={os.environ.get('PR_NUMBER', '')}"
    sonar_txt = f" · 🔗 [detalji u SonarQube Cloud]({pr_link})"

skipped = bld.get("skipped") or 0
if bld["status"] == "ok":
    bld_txt = "✅ prolaze" + (f" ({bld['summary']})" if bld.get("summary") else "")
    if skipped:
        bld_txt += f" · ⚠️ preskočenih {skipped}"
elif bld["status"] == "build":
    bld_txt = "❌ **projekat se ne prevodi**"
elif bld["status"] == "tests":
    bld_txt = "❌ **testovi ne prolaze**" + (f" ({bld['summary']})" if bld.get("summary") else "")
else:
    bld_txt = "⚠️ provera nije izvršena"

out += ["| Provera | Status |", "|---|---|",
        f"| Build i testovi | {bld_txt} |",
        f"| Šablon PRa | {tpl_txt} |",
        f"| Sadržaj opisa | {dsc_txt} |",
        f"| Pokrivenost novog koda | {cov_txt} |",
        f"| Lakoća održavanja | {mnt_txt}{sonar_txt} |", ""]

if bld["status"] in ("build", "tests"):
    naslov = ("### ❌ Projekat se ne prevodi, spajanje je blokirano"
              if bld["status"] == "build"
              else "### ❌ Testovi ne prolaze, spajanje je blokirano")
    out += [naslov, ""]
    if bld.get("errors"):
        out += ["```"] + bld["errors"] + ["```", ""]
    out += ["> Dok se projekat ne prevede i dok svi testovi ne prođu, pokrivenost novog koda "
            "se ne meri. Ceo ispis je u Actions, u job-u `build`.", ""]

if bld["status"] == "ok" and skipped:
    out += ["### ⚠️ Preskočeni testovi (savetodavno, ne blokira)", "",
            f"Ovi testovi su označeni da se ne pokreću (`Skip`), pa ne proveravaju ništa "
            f"({skipped} ukupno):", ""]
    out += [f"- `{name}`" for name in bld.get("skippedTests") or []] or \
           ["- imena preskočenih testova su u Actions, u job-u `build`"]
    out += ["", "> Recenzent: proveri razlog u `Skip = \"...\"` i da li preskočeni test skriva grešku.", ""]

if tpl["status"] == "fail":
    out += ["### ❌ Šablon PRa, spajanje je blokirano", ""]
    out += [f"- {e}" for e in tpl.get("errors", [])]
    out += ["", "> Obeleži obim (backend, frontend ili oba) i **tačno jedan** tip PRa. Change goal je uvek obavezan. "
            "Za backend: `feature` traži izmene nad bazom i testiranje, `bugfix`/`refactor` testiranje, "
            "dok za `test`/`chore`/`docs` nijedna sekcija nije obavezna. Kod izmena nad bazom obeleži da li PR "
            "menja bazu, ako menja, opiši izmenu i odgovori na pitanje o migracijama. Za frontend obeleži bar "
            "jednu vrstu izmene i dodaj 1–2 rečenice opisa. Svaku sekciju koju popunjavaš a koja počinje sa TODO "
            "zameni svojim tekstom, a TODO red obriši.", ""]

if dsc["status"] == "suspect" and suspects:
    out += ["### ⚠️ Sadržaj opisa (savetodavno, ne blokira)", "",
            "Ove sekcije deluju kao nedovršen placeholder:", ""]
    for s in suspects:
        note = f": {s['note']}" if s.get("note") else ""
        out.append(f"- **{s['name']}**{note}")
    out.append("")

if cov["status"] == "fail":
    out += ["### ❌ Pokrivenost, spajanje je blokirano", "",
            f"Od **{cov.get('addedExec')}** novih izvršivih linija, testom je pokriveno "
            f"**{cov.get('coveredNew')}**.", ""]
    if cov.get("files"):
        out.append("Najviše nepokrivenog:")
        out += [f"- `{f['file']}`: {plural(f['uncovered'], 'linija', 'linije', 'linija')}" for f in cov["files"]]
        out.append("")
    out += ["> Dodaj testove za novi kod pa će kapija proći. Kod koji se ne testira "
            "(DTO, migracije, neizvršive linije) ne ulazi u račun.", ""]

skipped_files = cov.get("skippedFiles") or []
if skipped_files:
    out += ["### ⚠️ Pokrivenost: fajlovi koji nisu uračunati", "",
            "GitHub ne prikazuje izmene ovih fajlova jer su prevelike, pa se ne zna koje su linije nove "
            "i pokrivenost za njih nije izmerena:", ""]
    out += [f"- `{name}`" for name in skipped_files]
    out += ["", "> Recenzent: za ove fajlove sam proveri da li su izmene pokrivene testovima.", ""]

if bld["status"] == "ok" and cov["status"] == "error":
    out += ["### ❌ Pokrivenost nije izmerena, spajanje je blokirano", ""]
    if cov.get("reason") == "no-data":
        out += ["Testovi su prošli, ali nijedan test projekat nije proizveo podatke o pokrivenosti. "
                "Najčešći uzrok: iz `Directory.Build.props` ili `Directory.Packages.props` uklonjen je "
                "`coverlet.collector`, ili se novi test projekat ne završava na `.Tests`.", ""]
    else:
        out += ["Merenje nije uspelo zbog greške u alatu, ne zbog koda. "
                "Pokreni proveru ponovo: Actions → pokretanje → **Re-run failed jobs**.", ""]

if nm or nc:
    out += ["### ⚠️ Lakoća održavanja (savetodavno, ne blokira)", ""]
    if nm:
        out += ["**Metode koje ovaj PR dira**", "",
                "| Metoda | MELOC | CYCLO | NOP |", "|---|---|---|---|"]
        for m in mnt["methods"]:
            lv = m.get("levels", {})
            out.append(
                f"| `{m['file'].split('/')[-1]} · {m['method']}` "
                f"| {MARK.get(lv.get('meloc'),'✅')} {m.get('meloc')} "
                f"| {MARK.get(lv.get('cyclo'),'✅')} {m.get('cyclo')} "
                f"| {MARK.get(lv.get('nop'),'✅')} {m.get('nop')} |")
        out.append("")
    if nc:
        out += ["**Klase koje ovaj PR dira**", "",
                "| Klasa | CLOC | WMC | NAD | NMD | CBO | DIT |",
                "|---|---|---|---|---|---|---|"]
        for c in mnt["classes"]:
            lv = c.get("levels", {})
            cells = " ".join(
                f"| {MARK.get(lv.get(k),'✅')} {c.get(k)}" for k in
                ("cloc", "wmc", "nad", "nmd", "cbo", "dit"))
            out.append(f"| `{c['name']}` {cells} |")
        out.append("")
    out += ["🔴 **kritično**: verovatno traži refaktorisanje · "
            "🟡 **sumnjivo**: proveri da li je opravdano · ✅ u granicama", ""]

    th = mnt.get("thresholds", {})
    if th:
        names = {
            "meloc": "Broj linija koda u telu metode, bez vitičastih zagrada koje otvaraju i zatvaraju telo, "
                     "bez praznih linija i komentara (kod metode sa `=>` broje se linije izraza). "
                     "Duga metoda je teža za razumevanje, izmenu i testiranje.",
            "cyclo": "Broj tačaka odlučivanja u metodi: `if`, `while`, `for`, `foreach`, "
                     "`switch` (jednom, bez obzira na broj `case`-ova), `continue`, `goto`, "
                     "uslovni izraz `?:`, `catch`, logičko and/or (`&&`, `\\|\\|`, `and`, `or`) "
                     "i `??`, uvećan za 1. Metoda bez grananja ima 1. Svako grananje je još jedan put "
                     "izvršavanja koji treba pokriti testom.",
            "nop": "Broj parametara koje metoda prima. Mnogo parametara obično znači da "
                   "metoda radi previše ili da podatke treba grupisati u objekat.",
            "cloc": "Broj linija koda u klasi, bez komentara i praznih linija. "
                    "Velika klasa po pravilu nosi više odgovornosti.",
            "wmc": "Zbir ciklomatske složenosti svih metoda u klasi. Pokazuje koliko "
                   "ukupne složenosti klasa drži u sebi.",
            "nad": "Broj atributa u klasi ili record-u: deklarisana polja, auto-property-ji (`{ get; set; }`) i parametri record-a, "
                   "jer i oni čuvaju stanje objekta. Mnogo atributa znači da klasa čuva previše "
                   "stanja i teže se testira.",
            "nmd": "Broj deklarisanih metoda u klasi. Mnogo metoda ukazuje na više "
                   "odgovornosti spojenih na jednom mestu.",
            "cbo": "Broj različitih klasa iz ovog projekta od kojih klasa zavisi, bilo da su navedene u kodu "
                   "ili se koriste kroz rezultat poziva (interfejsi, enum-i i tipovi iz .NET biblioteka se ne broje). Visoka vrednost znači "
                   "da izmena na drugom mestu lako lomi ovu klasu.",
            "dit": "Broj predaka klase iz ovog projekta (bazne klase iz .NET biblioteka se ne broje). Prijavljuje se samo na "
                  "najdubljoj klasi u lancu, jer je cela hijerarhija jedan problem. Duboka "
                  "hijerarhija otežava praćenje odakle ponašanje zapravo dolazi.",
        }
        out += ["**Značenje metrika i pragovi**", "",
                "| Metrika | Sumnjivo kad je više od | Kritično kad je više od | Značenje |",
                "|---|---|---|---|"]
        for k, v in th.items():
            if isinstance(v, list) and len(v) == 2:
                out.append(f"| {k.upper()} | {v[0]} | {v[1]} | {names.get(k,'')} |")
        out.append("")

out += ["### 👀 Za recenzenta", "",
        "Revizija pokriva tri aspekta kvaliteta softvera, ovim redom:", "",
        "1. **Funkcionalna pogodnost (ispunjenost zahteva):** da li se rešenje ponaša onako kako "
        "stakeholder zahteva, tj. kako je korisnička priča opisala. **Ovo se ne može izmeriti**, "
        "ovo procenjuje isključivo recenzent.",
        "2. **Besprekornost:** da li softver radi ispravno i da li je nov kod pokriven testovima.",
        f"   - **Pokrivenost novog koda** (meri analizator): ukoliko novododat kod nije dovoljno pokriven "
        f"testovima (prag je {pct(cov.get('threshold'))}), predloži koji slučajevi bi još trebalo da se pokriju.",
        "   - **Smislenost testova:** da li testovi pokrivaju sve kritične tačke izvršavanja softvera, "
        "a ne samo linije koda.",
        "     **PRIMER:** loš test pozove metodu i samo proveri da nije bacila izuzetak. Svakako ovakav "
        "test podiže pokrivenost, a ne tvrdi ništa. Dobar test za konkretan ulaz proverava očekivani "
        "izlaz, i pokriva granične slučajeve: npr. nulu, prazan skup, prekoračenje.",
        "3. **Lakoća održavanja:** koliko je kod lako razumeti, izmeniti i proširiti.",
        "   - **Menjane datoteke:** da li su menjane samo one datoteke koje ima smisla menjati "
        "za ovu izmenu, bez nepovezanih izmena.",
        "   - **Označene metrike (🟡 i 🔴)** (meri analizator): odluči da li je opravdano da ostanu takve "
        "ili nije, i daj predlog kako bi se kod mogao refaktorisati u cilju poboljšanja metrika.",
        "     **PRIMER:** metoda koja redom prepisuje dvadeset polja iz jednog objekta u drugi sme da "
        "bude duga. Takva metoda nema grananja, čita se odozgo nadole, a deljenje na manje metode je "
        "samo otežava. Metoda koja u sebi radi i proveru podataka i obračun i upis ima previše "
        "odgovornosti. Tu nam dužina signalizira tri odgovornosti spojene na jednom mestu.", "",
        "Ako PR menja frontend, u sekciji **Frontend** proveri menjane datoteke, timske konvencije, "
        "nazive identifikatora i veličinu i složenost klasa, komponenti i funkcija.", "",
        "Komentare ostavljaj tako da autoru bude jasno šta je dobro, a šta treba unaprediti. "
        "Dobra revizija obično sadrži tri vrste komentara:", "",
        "1. **Nedostatak sa smernicom:** šta nije u redu, predlog kako bi moglo bolje, "
        "i zašto smatraš da je bolje.",
        "2. **Pohvala:** kada uočiš pedantnost, pažljivost ili kreativno rešenje.",
        "3. **Pitanje:** kada kod nije jasan, da bi se popravila čitljivost ili proverilo "
        "razumevanje autora.", "",
        "Ako imaš jače predznanje, očekuje se da većina tvojih komentara bude iz prve kategorije. "
        "Ako ti je materija nova, prirodno je da preovlađuju druga i treća, i to je korisna revizija.", ""]

out.append("U nastavku iskoristi `review_template.md` kako bi kreirao reviziju koja pokriva sva tri "
           "aspekta: **funkcionalnu pogodnost**, **besprekornost** i **lakoću održavanja**.")

open("comment.md", "w", encoding="utf-8").write("\n".join(out))

hard_fail = (bld["status"] != "ok"
             or tpl["status"] != "ok"
             or cov["status"] in ("fail", "error"))
open("verdict.txt", "w").write("fail" if hard_fail else "ok")
print("hard_fail:", hard_fail)
