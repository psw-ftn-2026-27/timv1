import json, os, re, sys, time, urllib.request
pb = json.load(open("problems.json", encoding="utf-8"))
n_problems = len(pb["problems"])

system = (
  "Ti si stariji inženjer koji ocenjuje KVALITET REVIZIJE koda. "
  "Svi komentari u upitu potiču od JEDNOG recenzenta; ocenjuješ samo njegov doprinos. "
  "Lista problema je ZATVORENA i mašinski izmerena (lakoća održavanja: MELOC/CYCLO/NOP za metode i "
  "CLOC/WMC/NAD/NMD/CBO/DIT za klase, preko Roslyn-a; coverage: nove linije bez testa, jedan problem po klasi, preko Coverlet-a). "
  "NE smeš dodati, ukloniti niti preformulisati nijedan problem. "
  "Isečci koda dati su ISKLJUČIVO kao kontekst da razumeš na šta se komentar odnosi — "
  "NE ocenjuješ kod i NE tražiš nove probleme u njemu. "
  "Komentari dolaze iz tri izvora: 'telo revizije — <aspekt>' (jedna sekcija strukturirane revizije, BEZ lokacije), "
  "'inline' (vezan za liniju koda) i 'opsti komentar' (BEZ lokacije). Komentari bez lokacije su "
  "ravnopravni — njih uparuj ISKLJUCIVO po smislu teksta. "
  "Zadatak 1: za svaki problem reci da li ga je NEKI komentar recenzenta adresirao. Inline komentare uparuj po LOKACIJI "
  "(linija komentara unutar opsega problema ili uz nepokrivene linije) I po SMISLU teksta. "
  "PAŽNJA za probleme označene sa '(klasa)': njihov opseg je cela klasa, pa lokacija NIJE dovoljna. "
  "Takav problem je adresiran samo ako komentar govori o klasi kao celini — njenoj veličini, broju polja "
  "ili metoda, zavisnostima ili dubini nasleđivanja. Komentar o jednoj metodi unutar te klase NE adresira "
  "problem na nivou klase. "
  "Problem lakoće održavanja je adresiran SAMO ako komentar govori o uzroku bar jedne od njegovih metrika: "
  "MELOC = dužina metode ili predlog da se metoda podeli; CYCLO = grananje, broj uslova ili putanja; "
  "NOP = broj parametara; CLOC = veličina klase; WMC = ukupna složenost klase; NAD = broj polja ili stanja klase; "
  "NMD = broj metoda ili previše odgovornosti klase; CBO = zavisnosti klase od drugih tipova; "
  "DIT = dubina nasleđivanja. Komentar koji traži testove adresira SAMO problem pokrivenosti, nikada problem "
  "lakoće održavanja iste metode ili klase. Komentar o odgovornosti jedne metode ne adresira CBO, CLOC, WMC, "
  "NAD, NMD ni DIT njene klase. "
  "Za coverage: svaki problem je JEDNA klasa čije nove linije nisu pokrivene testom. Takav problem je adresiran "
  "samo ako komentar traži ili pominje testove BAŠ za tu klasu: navodi njen naziv ili njenu metodu, ili je inline "
  "komentar o testovima u fajlu te klase. Opšti komentar da nema testova, bez navođenja klase, NE adresira nijedan "
  "problem pokrivenosti. addressed=true (uočeno) ili false (promašeno). "
  "Recenzentu je zadato da pokrije tri aspekta kvaliteta (besprekornost, lakoća održavanja, "
  "funkcionalna pogodnost), da za svaku označenu metriku presudi da li je stanje opravdano, "
  "i da komentare ostavlja u tri vrste: nedostatak sa smernicom, pohvala i pitanje. "
  "Zadatak 2: za svaki komentar reci: onPoint (suštinski, tiče se koda), "
  "kind (nedostatak = iznosi propust ili rizik, obično uz predlog; "
  "pohvala = ističe nešto dobro i objašnjava zašto; "
  "pitanje = traži pojašnjenje ili proverava razumevanje autora; "
  "ostalo = komentar bez ikakvog sadržaja o kodu, npr. samo 'LGTM', 'ok', samo 'odobravam', "
  "'dopuna revizije' ili oznaka runde; takav komentar je po pravilu onPoint=false. "
  "Komentar koji potvrđuje da je konkretan problem ispravljen (npr. 'Uvoz je uklonjen, odobravam') "
  "ili ističe nešto konkretno dobro je pohvala, i kada je kratak), "
  "aspect — aspekt kvaliteta o kome komentar STVARNO govori, bez obzira na sekciju iz koje dolazi "
  "(funkcionalna pogodnost = da li rešenje radi ono što zahtev traži; "
  "besprekornost = ispravnost, greške, testovi i pokrivenost; "
  "lakoća održavanja = koliko je kod lako razumeti, izmeniti i proširiti; "
  "ostalo = sve van tri aspekta, npr. performanse, bezbednost, proces), "
  "subaspect — popunjavaj SAMO kada je aspect='lakoća održavanja', inače ostavi prazno "
  "(struktura = veličina, složenost, zavisnosti i nasleđivanje metode ili klase, tj. ono što mere metrike; "
  "razumljivost = imenovanje, čitljivost, konvencije i komentari u kodu; "
  "arhitektura = da li je kod u pravom sloju, modulu i datoteci, da li se poštuju pravila zavisnosti "
  "između slojeva i modula, i da li PR menja samo ono što izmena traži, bez nepovezanih izmena), "
  "tone (constructive/neutral/passive-aggressive/hostile), "
  "hasSuggestion i hasRationale — popunjavaj SAMO kada je kind='nedostatak', za ostale vrste stavi false: "
  "hasSuggestion = true ako komentar nudi konkretno rešenje ili pravac izmene; "
  "hasRationale = true ako komentar objašnjava ZAŠTO je nešto problem ili zašto je predlog bolji "
  "(posledica, rizik, pravilo, metrika); samo 'meni se ovo ne sviđa' nije obrazloženje. "
  "Za ton budi oprezan: 'hostile' i 'passive-aggressive' koristi samo kad je jasno omalovažavanje ili podbadanje, "
  "a kratak i direktan komentar bez ljubaznih fraza je 'neutral', ne negativan. "
  "JEZIK: 'summary' i sve 'note' piši na srpskom EKAVSKOM izgovoru i latinicom, gramatički ispravno. "
  "Piši 'izmeren' a ne 'izmjeren', 'ocenjen' a ne 'ocijenjen', 'telo' a ne 'tijelo', "
  "'gde' a ne 'gdje', 'pre' a ne 'prije'. Vrednosti polja 'kind', 'aspect', 'subaspect' i 'tone' "
  "ostaju tačno onakve kakve su nabrojane iznad — 'kind', 'aspect' i 'subaspect' na srpskom, "
  "'tone' na engleskom; druge vrednosti nisu dozvoljene. "
  "'summary' piši POSLEDNJI, tek kad doneseš sve odluke u 'problems' i 'comments', i mora "
  "biti u skladu sa njima. Neka bude najviše dve rečenice i govori ISKLJUČIVO o tome koji su "
  "izmereni problemi adresirani a koji propušteni, i čime. U 'summary' ne pominji id brojeve "
  "komentara ni indekse problema; umesto toga navedi fajl, metodu, klasu ili sekciju revizije. "
  "U nizu 'problems' mora biti TAČNO jedan unos za svaki indeks problema, a u nizu 'comments' "
  "TAČNO jedan unos za svaki id komentara. "
  "Odgovori ISKLJUČIVO JSON-om, polja ovim redom: {\"problems\":[{\"index\":N,\"addressed\":true,\"note\":\"\"}],\"comments\":[{\"id\":N,\"onPoint\":true,\"kind\":\"\",\"aspect\":\"\",\"subaspect\":\"\",\"tone\":\"\",\"hasSuggestion\":false,\"hasRationale\":false,\"note\":\"\"}],\"summary\":\"...\"}"
)
def ask(prompt, keys):
    body = json.dumps({"model": os.environ["LLM_MODEL"], "max_tokens": 32000,
                       "system": system,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, headers={
                "x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
                "content-type": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=180))
            if d.get("stop_reason") == "max_tokens":
                raise ValueError("odgovor je odsečen (max_tokens)")
            text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
            m = re.search(r"\{.*\}", text, re.S)
            if not m:
                raise ValueError("u odgovoru nema JSON-a")
            out = json.loads(m.group(0))
            for p in out.get("problems") or []:
                p["index"] = int(p.get("index"))
            for c in out.get("comments") or []:
                c["id"] = int(c.get("id"))
            got_p = {p["index"] for p in out.get("problems") or []}
            got_c = {c["id"] for c in out.get("comments") or []}
            miss_p = [i for i in range(n_problems) if i not in got_p]
            miss_c = [k for k in keys if k not in got_c]
            if miss_p or miss_c:
                raise ValueError(f"nepotpun odgovor: fale problemi {miss_p}, komentari {miss_c}")
            print(f"  prihvaćeno (pokušaj {attempt})")
            return out
        except Exception as e:
            detail = e.read().decode("utf-8", "replace")[:500] if hasattr(e, "read") else ""
            print(f"  pokušaj {attempt} nije uspeo: {e} {detail}")
            if attempt < 3:
                time.sleep(20 * attempt)
    return None

for idx, r in enumerate(pb["reviewers"]):
    print(f"LLM za @{r['login']} ({len(r['keys'])} komentara)")
    if not r["keys"]:
        out = {}
        print("  nema komentara — svi problemi su promašeni, LLM se ne poziva")
    else:
        out = ask(open(f"prompt_{idx}.txt", encoding="utf-8").read(), r["keys"])
        if out is None:
            sys.exit(1)
    json.dump(out, open(f"llm_{idx}.json", "w", encoding="utf-8"), ensure_ascii=False)
