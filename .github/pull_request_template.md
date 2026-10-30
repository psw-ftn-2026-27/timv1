📄 **Pull Request Template**

Polja se obeležavaju upisivanjem x u zagrade: `- [ ]` postaje `- [x]`.

**Važno:** u svakoj sekciji koju popunjavaš red koji počinje sa `TODO` zameni svojim tekstom, a sam TODO red obriši. Sekcija koju popunjavaš, a u kojoj je ostao TODO, ne prolazi proveru šablona. Sekcije koje za tvoj PR nisu obavezne ne diraj, TODO u njima može da ostane.

<hr>

📋 **Obim PRa**

Obeleži šta PR menja (možeš obeležiti oba). U zavisnosti od odgovora popunjavaš sekcije za backend, frontend ili oba.

- [ ] backend
- [ ] frontend

<hr>

🏷️ **Tip PRa**

Obeleži tačno jedan tip. Tip opisuje svrhu celog PRa, i za backend i za frontend.

- [ ] feature
- [ ] bugfix
- [ ] refactor
- [ ] test
- [ ] chore
- [ ] docs

<hr>

🎯 **Change goal** (obavezno uvek, i za backend i za frontend)

TODO: Nalepi tekst korisničke priče koji uključuje acceptance criteria. Ako korisnička priča ne postoji (npr. bugfix, refactor, chore), opiši cilj izmene i po čemu se vidi da je postignut.

<hr>

⚙️ **Backend** (popunjavaš ako PR menja backend)

Koje backend sekcije je obavezno popuniti u zavisnosti od tipa PRa:

| Tip | Izmene nad bazom | Testiranje funkcionalnosti |
|---|---|---|
| feature | ✅ | ✅ |
| bugfix | — | ✅ |
| refactor | — | ✅ |
| test | — | — |
| chore | — | — |
| docs | — | — |

🗄️ **Izmene nad bazom**

Da li PR uključuje izmene nad bazom?

- [ ] Da
- [ ] Ne

TODO: Ako je odgovor Da, istakni kako tvoj PR menja bazu podataka (npr. nova tabela, nove ili uklonjene kolone).

Da li je potrebno pokrenuti migracije nakon preuzimanja tvog PRa? (odgovaraš ako PR uključuje izmene nad bazom)

- [ ] Da
- [ ] Ne

**Seed skripta** (putanja do skripte koju kolega pokreće nakon migracija, ako postoji):

TODO: path/to/seed_script.sql

✅ **Testiranje funkcionalnosti**

TODO: Koraci koje kolega prati da proveri da li funkcionalnost radi, po uzoru na primer:

1. Prijaviti se kao admin (Username: username, Password: password)
2. Otići na tab za pregled svih korisnika
3. Proveriti prikaz korisnika u tabeli
4. Kliknuti na dugme Block
5. Proveriti da li se korisnik pojavio u tabeli blokiranih korisnika

<hr>

💻 **Frontend izmene** (popunjavaš ako PR menja frontend)

Šta je u suštini rađeno na frontu (obeleži sve što važi):

- [ ] samo stilovi / izgled
- [ ] jedna komponenta
- [ ] ceo ekran (stranica)
- [ ] ceo feature (više ekrana ili komponenti)
- [ ] samo poziv novog API-ja / servis, bez vidljivih izmena
- [ ] ostalo

TODO: U 1–2 rečenice opiši izmenu i gde se vidi (po želji dodaj slike ekrana).
