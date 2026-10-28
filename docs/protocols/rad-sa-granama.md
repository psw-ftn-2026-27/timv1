# Rad sa granama i pull request-ovima

## Kada se primenjuje

Svakodnevno. Svaka izmena ulazi u `development` isključivo kroz pull request; direktan push na `development` ili `main` nije dozvoljen.

Protokol ima dva procesa: [proces kreiranja pull request-a](#proces-kreiranja-pull-request-a), koji prati autor izmene, i [proces pregledanja pull request-a](#proces-pregledanja-pull-request-a), u kom učestvuju recenzent i autor.

## Grana po funkcionalnosti

Pre nego što se pristupi razvoju nove funkcionalnosti, pravi se nova grana od svežeg `development`-a. Veština za implementaciju (`psw-implementacija`) ovo radi automatski. Ime grane prati obrazac `<modul>/<kratak-opis>` (npr. `exploration/tour-review`). Jedna grana nosi jednu zaokruženu izmenu, a ne nedovršen ili parcijalan razvoj.

## Dnevna higijena

Preporuka je da na početku svake sesije razvoja povučete `development` u svoju granu kroz sledeće komande (sve se pokreću iz korena repozitorijuma):

```
git fetch origin
```

Ako vaša grana sadrži migraciju vašeg modula, pre spajanja proverite da li je u `development` u međuvremenu stigla migracija istog modula (primer je za modul `Exploration`):

```
git diff --name-only HEAD...origin/development -- backend/Modules/Exploration/Exploration.Infrastructure/Persistence/Migrations
```

Ako komanda ispiše ijednu datoteku, ne spajajte, već pratite protokol [Migracije: rešavanje konflikata](migracije-resavanje-konflikata.md). U suprotnom spojite `development`:

```
git merge origin/development
```

Time konflikte rešavate dok su mali i dok pamtite kontekst.

Ako spajanje ipak prijavi konflikt u datoteci `<Ime>DbContextModelSnapshot.cs` (folder `Migrations` vašeg modula), ne rešavajte ga ručno. Tu datoteku generiše EF Core i ona opisuje ceo model baze modula kao zbir svih migracija; ručno spojena, ona više ne odgovara migracijama i sledeća migracija ispada pogrešna. Prekinite spajanje komandom `git merge --abort`, pa pratite protokol [Migracije: rešavanje konflikata](migracije-resavanje-konflikata.md).

Posle spajanja pokrenite `dotnet tool restore` iz korena repozitorijuma i `npm install` iz direktorijuma `frontend`, jer je spajanje možda donelo nov alat ili novu biblioteku.

Ovaj proces je obavezno da ispratite pre formiranja pull request-a.

## Proces kreiranja pull request-a

### 1. Provera pre otvaranja

Prođite kroz sledeću listu:

1. `development` je povučen u granu i konflikti su rešeni (videti [Dnevna higijena](#dnevna-higijena)).
2. `dotnet build` prolazi iz direktorijuma `backend` (upozorenja su greške).
3. `dotnet test` prolazi za sve module, ne samo vaš. Arhitekturalni testovi u `Host.Tests` proveravaju pravila zavisnosti i ako oni padnu, ispravlja se kod, a ne test.
4. `npm run lint` i `npm run build` prolaze iz direktorijuma `frontend`. Linter čuva granicu modula na klijentu; ako prijavi uvoz iz drugog modula, ispravlja se kod, ne `eslint.config.js`.
5. `git status` ne prikazuje izmene izvan direktorijuma vašeg modula (`backend/Modules/<Ime>/` i `frontend/src/app/modules/<ime>/`). Izmena tuđeg ili platformskog koda u vašem PR-u je znak da nešto nije u redu. Vidite protokol [Zahtevi platformskom timu](zahtevi-platformskom-timu.md).

### 2. Opis pull request-a

Opis PR-a pišete sami, po šablonu koji se pojavi pri otvaranju PR-a, a koji se nalazi na putanji `.github/pull_request_template.md` u okviru vašeg repozitorijuma. Koje sekcije su obavezne zavisi od obima i tipa PR-a (tabela u šablonu). Opis je prvo što recenzent čita: iz njega mora da razume šta izmena treba da uradi i kako da je proveri. Veština `/psw-implementacija` na kraju rada ispisuje osnovne informacije o vašem PR-u, koje možete da iskoristite pri popunjavanju šablona.

### 3. Automatske provere

Pri otvaranju i svakoj izmeni PR-a pokreću se automatske provere, koje rezultat objavljuju kao komentar „Stanje PR-a”:

| Provera | Šta proverava |
|---|---|
| `Build i testovi` | Rešenje se prevodi i svi testovi prolaze |
| `Pokrivenost novog koda` | Koliki deo novih izvršivih linija je pokriven testovima (preporuka je bar 80%) |
| `Lakoća održavanja` | Metrike lakoće održavanja na izmenjenom kodu; 🟡 označava sumnjivu, a 🔴 kritičnu vrednost |

Ako `Build i testovi` ne prolaze, pratite odeljak [Kada CI padne](#kada-ci-padne).

### 4. Dodela recenzenta

PR pregleda bar jedan član vašeg tima koji nije pisao izmenu. Dodajte ga kao recenzenta (Reviewers) i javite mu. Ako PR dira `Contracts`, kao recenzenta dodajte i člana tima koji taj contract koristi. Dalje se nastavlja [proces pregledanja pull request-a](#proces-pregledanja-pull-request-a).

## Proces pregledanja pull request-a

Revizija ima dva cilja. Kratkoročno, da kod koji ulazi u `development` ispunjava zahteve, radi ispravno i lako se održava. Dugoročno, da članovi tima uče jedni od drugih.

### Recenzent

1. Pregledajte na vreme. Reviziju započnite u roku od 24 sata od kada ste dodati kao recenzent, jer se revizija u poslednjem trenutku svodi na odobravanje bez pregleda.
2. Prvo je bitno razumeti izmenu. Pročitajte opis PR-a i komentar „Stanje PR-a”, uključujući njegov odeljak „Za recenzenta”. Ako vam nije jasno šta izmena treba da uradi, pitajte autora pre nego što komentarišete.
3. Pregledajte izmenu po tri aspekta kvaliteta softvera, sledećim redom:

   - **Funkcionalna pogodnost (ispunjenost zahteva):** da li se rešenje ponaša onako kako je korisnička priča opisala. Ovo se ne može izmeriti i procenjujete isključivo vi, zato prođite korake iz sekcije Testiranje funkcionalnosti u opisu PR-a.
   
   - **Besprekornost:** da li softver radi ispravno i da li je nov kod pokriven testovima. Pokrivenost novog koda meri analizator; ako je ispod 80%, predložite koje slučajeve još treba pokriti. Smislenost testova procenjujete vi: dobar test za konkretan ulaz proverava očekivani izlaz i pokriva granične slučajeve (nula, prazan skup, prekoračenje), dok test koji samo pozove metodu i proveri da nije bacila izuzetak podiže pokrivenost, a ne tvrdi ništa.
   
   - **Lakoća održavanja:** koliko je kod lako razumeti, izmeniti i proširiti. Proverite da li su menjane samo datoteke koje ima smisla menjati, da li su poštovane timske konvencije i nazivi, i za svaku metriku označenu sa 🟡 ili 🔴 odlučite da li je vrednost opravdana. Značenje metrika i pragovi su u komentaru „Stanje PR-a”. Metoda koja redom prepisuje dvadeset polja sme da bude duga, jer nema grananja i čita se odozgo nadole; metoda koja u sebi radi i proveru podataka i obračun i upis ima previše odgovornosti, i tada predložite kako da se refaktoriše.

   Ako PR menja frontend, proverite i menjane datoteke, timske konvencije, nazive identifikatora i veličinu i složenost klasa, komponenti i funkcija.
   
4. Komentare ostavljajte na samim linijama koda, tako da autoru bude jasno šta je dobro, a šta treba unaprediti. Uvek gledajte da kritikujete sam kod tj. rešenje a ne konkretnu osobu. Komentari uglavnom pripadaju jednoj od tri vrste:

   - **nedostatak sa smernicom:** šta nije u redu, predlog kako bi moglo bolje i zašto smatrate da je bolje;
   - **pohvala:** kada uočite pedantnost, pažljivost ili kreativno rešenje;
   - **pitanje:** kada kod nije jasan, da bi se popravila čitljivost ili proverilo razumevanje autora.

   Ako imate jače predznanje, očekuje se da većina vaših komentara bude nedostatak sa smernicom. Ako vam je materija nova, prirodno je da preovlađuju pohvale i pitanja, i to je korisna revizija.
   
5. Popunite šablon revizije koji se nalazi u okviru vašeg repozitorijuma (`review_template.md`): Files changed → Review changes, nalepite šablon, popunite ga za sva tri aspekta i zaključak, i izaberite:
   - Request changes, ako postoji nedostatak koji mora da se ispravi pre spajanja;
   - Comment, ako imate samo pitanja ili sitne predloge;
   - Approve, tek kada ste pregledali ceo PR i kada su nedostaci ispravljeni.
   
6. Kada autor odgovori na komentar, proverite ispravku, pa tek onda razrešite komentar (Resolve conversation). Ne odobravajte PR koji niste pregledali.

### Autor

1. Odgovorite na svaki komentar: šta ste izmenili ili zašto se ne slažete. Komentar razrešava recenzent, a ne autor.
2. Ispravke šaljite kao nove commit-ove na istu granu, pa zatražite ponovni pregled (Re-request review).
3. Neslaganje oko koda je u redu. Ako se ne dogovorite u dva kruga komentara, razgovarajte uživo, a zaključak zapišite u komentar.
4. PR spaja autor, kada `Build i testovi` prolaze, postoji bar jedno odobrenje i nema nerazrešenih komentara.

## Alati veštačke inteligencije

Opis PR-a, tekst revizije i komentare pišete sami. Veštinu `/psw-pitaj` možete da koristite da biste razumeli kod koji pregledate, ali ne i da napiše opis, komentar ili popuni šablon revizije.

## Kada CI padne

CI izvršava isto što i vi lokalno, u tri odvojena posla. Posao `build-and-test` prevodi i testira serversku aplikaciju (restore, build, testovi sa PostgreSQL servisom), posao `frontend` izvršava `npm ci`, `npm run lint` i `npm run build`, a posao `migrations`, samo za pull request, ponavlja proveru migracija iz dnevne higijene. Sva tri moraju da prođu. Uz njih se na PR-u izvršavaju i [automatske provere](#3-automatske-provere); od njih spajanje blokira samo `Build i testovi`, dok `Pokrivenost novog koda` i `Lakoća održavanja` u komentaru „Stanje PR-a” upozoravaju na mesta koja treba pogledati pri reviziji. Zato je prvi korak kod pada uvek reprodukcija lokalno:

1. Otvorite u GitHub Actions posao koji je pao, pa log palog koraka, i pročitajte prvu grešku.
2. Pokrenite isti korak lokalno: iz `backend` (`dotnet build`, pa `dotnet test`) ili iz `frontend` (`npm run lint`, pa `npm run build`). Ako lokalno prolazi, a na CI pada, najčešći uzrok je datoteka koja nije commit-ovana ili push-ovana, što proveravate sa `git status`. Pad posla `migrations` se ne reprodukuje: poruka greške imenuje vašu migraciju i migraciju iz ciljne grane koja joj nedostaje, a ispravka je protokol [Migracije: rešavanje konflikata](migracije-resavanje-konflikata.md).
3. Popravka ide kao novi commit na istu granu; CI se pokreće ponovo sam.
4. PR kome ne prolaze build ili testovi se ne pregleda i ne spaja. Ako ne umete da protumačite pad, tražite pomoć odmah. Ne ostavljajte crven PR da čeka.
