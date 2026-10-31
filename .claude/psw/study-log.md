# Study log

Shared format of the files in `.workspace/study/`. `/psw-pitaj`, `/psw-ucenje` and
`/psw-implementacija` write them; `/psw-ucenje` reads the `ask` and `study` entries to
decide what to ask next. Create the folder and a file when it is missing.

A **node** is one lesson file of the knowledge base, named by its path relative to
`docs/knowledge-base/`, for example
`server/2-arhitektura-modula/1-domenski-sloj/4-agregat.md`. The `README.md` files of the
segments are introductions and are never nodes.

## `profile.json`

The git identities whose commits count as the student's own work.

```json
{ "identities": [{ "name": "Ana Anić", "email": "ana@uns.ac.rs" }] }
```

## `log.jsonl`

One JSON object per line, appended and never rewritten. Dates are `YYYY-MM-DD`; paths
are relative to the repository root.

A question the student asked through `/psw-pitaj`:

```json
{"kind":"ask","date":"2026-10-20","nodes":["klijent/1-angular/4-signali.md"],"file":"frontend/src/app/modules/social/blog-reading/blog-list/blog-list.ts","topic":"zašto je filter signal"}
```

A question `/psw-ucenje` put to the student:

```json
{"kind":"study","date":"2026-10-27","node":"server/2-arhitektura-modula/1-domenski-sloj/4-agregat.md","file":"backend/Modules/Exploration/Exploration.Domain/Tours/Tour.cs","lines":"41-63","type":"objasni","outcome":"after_push"}
```

A prediction the student made in `/psw-implementacija`, written after its reveal:

```json
{"kind":"predict","date":"2026-10-22","spec":"exploration-ocena-ture","stage":"server","prediction":1,"nodes":["server/2-arhitektura-modula/5-čista-arhitektura.md"],"outcome":"partial"}
```

A decision `/psw-implementacija` made without the student:

```json
{"kind":"decision","date":"2026-10-22","spec":"exploration-ocena-ture","stage":"server","origin":"stage","text":"ocena se čuva kao vrednosni objekat"}
```

- `type` is `objasni` or `izmeni`.
- `outcome` in a `study` entry is `correct` (right at once), `after_push` (right after
  the one push), or `revealed` (the answer had to be given).
- `outcome` in a `predict` entry is `match` (the prediction holds in substance),
  `partial` (part of it holds), or `differ` (its main point does not hold).
- `nodes` in an `ask` entry may be empty when no lesson covers the question.
- `spec` is the spec's file name without `.md`; `stage` is `server` or `klijent`;
  `prediction` is `1` or `2` within the stage.
- `origin` is `stage` (the background agent reports deciding it) or `review` (a
  departure from the design fixed before the reveal).

## `plan-<YYYY-MM-DD-HHmm>.md`

The `Plan učenja` block that closes a round of `/psw-ucenje`, saved exactly as printed.
