---
name: psw-izvoz-razgovora
description: Pakuje sve razgovore sa agentom vođene u ovom repozitorijumu i njegovim direktorijumima u jednu zip arhivu u .workspace/export/, za studente koji učestvuju u istraživanju. Pokreće se samo kada student pozove /psw-izvoz-razgovora.
disable-model-invocation: true
---

# Izvoz razgovora

You run one script and report its result. Do not read the session files or the archive
yourself; their content does not belong in this conversation.

## 1. Run

From the repository root:

```
node .claude/skills/psw-izvoz-razgovora/export-conversations.mjs
```

The script finds every Claude Code session whose working directory is the repository or
a folder inside it, and writes `.workspace/export/<ime>-<datum>-<vreme>.zip` holding:

- `raw/`: the session files as stored, with the transcripts of background agents and the
  saved tool results;
- `readable/`: one text file per session and per background agent;
- `workspace/`: the student's `.workspace/specs/` and `.workspace/study/` as they are;
- `manifest.json`: for each session its identifier, time span, model, Claude Code
  version, working directory, size and message counts.

Every run packs everything again, so an earlier archive is never needed.

## 2. Report

Tell the student, in Serbian:

- how many sessions were packed, per folder, and how many files from `.workspace/specs/`
  and `.workspace/study/`, as the script printed them;
- the size and the full path of the archive;
- that the archive holds everything they typed or pasted into the agent in this
  repository, including code written by teammates, and that they should deliver it only
  in the way the research instructions say.

If the script fails, show its message unchanged. It reports a missing session folder and
a repository with no recorded sessions by itself.

## Limits to mention when they apply

- Sessions recorded before the repository folder was moved or renamed are stored under
  the old path and are not found.
- Sessions run inside WSL and sessions run on Windows are stored separately; each
  environment exports only its own.
- Sessions run in the web application are not on this computer.
