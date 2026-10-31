---
name: psw-implementacija
description: Implementira jednu specifikaciju sa odobrenim dizajnom na novoj grani od development-a. Dok se kod piše, student predviđa kako će izgledati, pa predviđanje poredi sa stvarnim kodom. Završava lokalnim commit-om i kratkim pregledom za opis pull request-a. Pokreće se samo kada student pozove /psw-implementacija.
argument-hint: <datoteka specifikacije iz .workspace/specs/>
disable-model-invocation: true
---

# Implementacija

Input: $ARGUMENTS

You build one spec whose design is approved. The code is written by a background agent,
one stage at a time, so that you stay free to talk. While a stage is being written the
student predicts what it will contain; when it is done you put the real code next to the
prediction. What the student should take from this skill is how the design they approved
turns into classes, files and tests, and the prediction is where that happens. Finishing
the code quickly is worth nothing if the student only watched.

Read `.claude/psw/exchange.md` now. Its sections on not answering, grounding and
language apply here; the four-message exchange does not, because a prediction has its
own shape (section 3). Read `.claude/psw/study-log.md` too, for the `predict` and
`decision` entries this skill appends to `.workspace/study/log.jsonl`. Do not mention the
log to the student.

## 1. Preflight

1. Resolve the input to a file in `.workspace/specs/`. With no input, list the specs
   whose status is `Dizajn odobren` and ask which one. Any other status: stop and say
   which skill comes first.
2. Read the spec, the root `AGENTS.md`, `backend/AGENTS.md`, `frontend/AGENTS.md`, and
   the module's code that the design names.
3. If the spec has a `Zavisnost` line, check the other module's `Contracts` for the
   member it needs. If the member is missing, stop: the feature cannot be built until
   the other team adds it. Never add it yourself.
4. Require a clean working tree (`git status --porcelain` prints nothing). Otherwise
   stop and ask the student to commit or put aside their changes.
5. Run `git fetch origin`, then create the branch from the fresh `development`:
   `git switch -c <modul>/<kratak-opis> origin/development`, with the words of the spec's
   file name. If the branch exists, ask whether to continue on it.
6. Tell the student in two or three sentences what will happen: two stages, two
   predictions in each, then they try the feature and it is committed.

## 2. Stages

Two stages, in this order. Skip a stage the design gives no work to, and say so.

| Stage | Builds | Checks it runs |
|---|---|---|
| Server | domain model, operations, persistence and migration, controller, the tests the spec lists | `dotnet build` and `dotnet test` from `backend/`; after a model change, `dotnet ef migrations has-pending-model-changes` for the module's context |
| Klijent | mirrored types, pages and components, the group's service, routes | `npm run lint` and `npm run build` from `frontend/` |

Start each stage as a background agent with the Agent tool, so the conversation goes on
while it works. Give it this brief, filled in:

> Implement the <server | client> part of the feature specified in `<spec path>`. Before
> writing anything, read the spec, the root `AGENTS.md`, `<backend | frontend>/AGENTS.md`
> and the READMEs next to the code you touch. Build exactly what the spec's `Dizajn`
> section names and nothing more. <Server: write the tests the spec lists, plus the
> authentication and role rejections `backend/AGENTS.md` requires for each command; add
> the migration with `dotnet ef`, never by hand. Client: mirror the changed DTOs in the
> module's `api/` types; write no tests.> Stay inside <`backend/Modules/<Name>/` |
> `frontend/src/app/modules/<name>/`>. Do not touch a platform-owned file, another
> module, a `Contracts` project or a `.csproj`; if the work needs one, stop and report
> it. Do not read knowledge-base lessons and never copy code from them. If the spec
> leaves a decision open or cannot be built as written, stop and report the question
> instead of choosing. Run <the stage's checks> and fix what fails;
> if a check cannot run, for example because PostgreSQL is down, report it and do not
> work around it. Do not commit, switch branches or push. End with the files you created
> or changed, the result of each check, and anything you had to decide.

If agents cannot run in the background in this session, keep the same order with one
change: ask both predictions of a stage first, then build the stage yourself, then
reveal.

## 3. Predictions

Two per stage, asked while the stage is being written. A prediction is three messages.

1. **Frame** (you). Three to five sentences taken from the spec's design, then one
   question about something the stage will produce. Give nothing from the lesson and
   nothing about how the project usually does it.
2. **Prediction** (the student).
3. **Reveal** (you), only after the stage has finished and you have reviewed it
   (section 4). Show the real code as a short snippet with its path and lines, then say
   what the student predicted correctly, and what differs and why, in the lesson's terms.
   Add at most one `Pogledaj:` line, and only when something differed. There is no
   alternative to negotiate; the code is written. Then append the prediction's
   `predict` entry.

Read the lessons of a prediction before framing it, from `docs/knowledge-base/`.

| Stage | Prediction | Lessons |
|---|---|---|
| Server | The path of the feature's main operation: which class in which layer does what, in order, from the HTTP request to the database and back. | `server/2-arhitektura-modula/5-čista-arhitektura.md`, `server/2-arhitektura-modula/2-aplikacioni-sloj/2-aplikacioni-servis.md` |
| Server | When the domain model changes: what changes in the database, and whether a migration is needed and what it holds. Otherwise: the shape of the DTO the main query returns and how it gets filled. | `server/2-arhitektura-modula/3-infrastrukturni-sloj/2-efc-kontekst-i-model.md`, `3-migracije.md`; or `server/2-arhitektura-modula/2-aplikacioni-sloj/3-dto-i-mapiranje.md`, `server/2-arhitektura-modula/3-infrastrukturni-sloj/4-repozitorijumi.md` |
| Klijent | Which parts of the flow become a page and which a presentational component, and in which group they live. | `klijent/2-modularni-monolit/1-stranice-i-prikazne-komponente.md` |
| Klijent | When the flow has a command: where the command lives and what the page does once it succeeds or fails. Otherwise: what the mirrored type of the main DTO looks like. | `klijent/1-angular/11-komande.md`; or `klijent/2-modularni-monolit/2-preslikani-tipovi.md` |

Pacing:

- Ask the first prediction as soon as the stage has started, and the second after the
  student answers the first.
- When both are answered and the stage is still running, say in one line that the code
  is being written, and wait. Do not fill the wait with more questions.
- When the stage finishes before both are answered, say in one line that it is done, and
  reveal nothing until the student has answered.
- Reveal both predictions of a stage together, then start the next stage.
- A non-answer follows `exchange.md`: ask once for a rough guess, then offer two
  options. A prediction is never skipped.

## 4. Review before the reveal

The background agent can be wrong, and whatever you show becomes the correct answer in
the student's eyes. When a stage reports back:

1. Read its report, then the changes themselves (`git status --porcelain`, `git diff`,
   and the new files).
2. Hold them against the spec's `Dizajn` and the tier `AGENTS.md`. Fix what departs:
   something the spec does not name, a rule placed in a service, a file outside the
   module, a missing test from the spec's list. Append a `decision` entry for each
   departure you fixed and for each decision the stage reports making on its own.
3. If the stage stopped on an open decision, or the design cannot be built as written,
   put it to the student as one exchange in the form `exchange.md` describes, record the
   outcome under `Odluke` in the spec, and finish the stage.
4. If a check could not run, tell the student what is missing and stop until it runs.

Only then reveal.

## 5. Check, try, commit

1. Run all checks of both tiers once more on the finished work. Fix failures.
2. Ask the student to try the feature. Print the steps of the spec's `Ponašanje`, how to
   start the two applications (`dotnet run --project Host.Api` from `backend/`,
   `npm start` from `frontend/`), and the role to sign in with. Wait for them to confirm
   that the flow works as they designed it. If it does not, fix it and ask again.
3. Stage the feature's files by path and make one commit under the student's git
   identity. Match the subjects in `git log`: `feat: <one English sentence>`. End the
   message with one trailer block: the line `Spec: <spec file name without .md>`, then
   the attribution lines the session requires.
4. Set `**Status:** Implementirano` in the spec and add the line `**Grana:** <branch>`
   under it.

Invoking this skill authorises that one commit. It never authorises a push, a pull
request, a merge of `development` into the branch, or an edit outside the module.

## 6. Overview

Print this block in Serbian, short enough to paste into a pull request description:

```
## <Naziv>

**Namera:** <jedna ili dve rečenice: ko ima korist i koju>

**Dizajn:**
- Tok korišćenja: <jedna rečenica>
- Domenski model: <jedna rečenica>
- Operacije: <jedna rečenica>
- Testovi: <jedna rečenica>

**Provera:** <šta pokrivaju testovi; tok je isproban ručno>
```

Take the sentences from the spec, including a `Kompromis` when the design has one. Close
with one line saying that merging `development`, pushing and opening the pull request
follow `docs/protocols/rad-sa-granama.md` and are the student's to do.
