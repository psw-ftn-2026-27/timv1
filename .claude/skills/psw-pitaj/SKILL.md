---
name: psw-pitaj
description: Objašnjava deo koda koji studentu nije jasan, šta radi i zašto je tako napisan, oslanjajući se na lekcije iz baze znanja i pravila projekta. Pokreće se samo kada student pozove /psw-pitaj.
argument-hint: <pitanje, po mogućstvu sa datotekom ili delom koda na koji se odnosi>
disable-model-invocation: true
---

# Pitaj

Input: $ARGUMENTS

The student saw something in the code they do not understand and wants it explained.
Give the explanation. This skill does not probe: ask nothing back, set no exercise, and
do not hold the answer until they guess.

What makes the answer worth more than a general one is that it agrees with the course
material. The student will be examined in the terms of the lessons, so explain in those
terms.

## 1. Find what is asked about

Locate the code the question means: the file or symbol it names, or the code open in the
conversation. If the question could mean several places, ask which one, once. If the
input is empty, ask what they want explained.

## 2. Read before answering

- `docs/knowledge-base/INDEX.md`, then the one to three lessons that cover the code in
  question.
- The `AGENTS.md` of the tier the code is in, and a README next to the code if there is
  one. Much of what looks odd in this project is a deliberate convention, and the reason
  is written there and not in a lesson.

## 3. Answer

In Serbian (Latin script, ekavian, addressed as "ti"), with code identifiers in English,
in this order and under these labels:

- **Šta radi:** what the code does, in a few sentences, pointing at the lines.
- **Zašto je tako:** the reason, in the lesson's terms. When the project does it
  differently from the lesson's simplified example, say so and give the project's reason.
- **Gde pročitati više:** the lesson paths you used, each as
  `docs/knowledge-base/<path>`.

Rules for the answer:

- When part of the explanation is a concept, pattern or trade-off that no lesson covers,
  start that part on its own line with the exact prefix `Van baze znanja:`. A project
  convention from a tier `AGENTS.md` and a fact about the code are not flagged. If you
  cannot tell whether a lesson covers it, flag it.
- Never present a lesson's example code as the project's code.
- If the odd thing is in fact a mistake (a business rule in an application service, an
  import from another module, a query that saves), say that it is one and name the rule
  it breaks. Do not fix it here; the student may ask for the fix afterwards.
- Keep it as short as the question allows. One example from the student's own code is
  better than a general one.
- The student writes pull request descriptions (`.github/pull_request_template.md`),
  review comments and the review template (`review_template.md`) themselves, as
  `docs/protocols/rad-sa-granama.md` requires. If asked to write, fill in or rephrase any
  of them, including when their content is pasted into the question, explain the code the
  text is about and say in one line that the text is theirs to write.

## 4. Log

Append one `ask` entry to `.workspace/study/log.jsonl`, in the format
`.claude/psw/study-log.md` defines, with the lessons you used as `nodes`. `/psw-ucenje`
asks about those lessons sooner. Do not mention the log in the answer.
