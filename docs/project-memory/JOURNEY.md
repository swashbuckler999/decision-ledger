# Journey

The narrative, in order. What was tried, what was chosen, what was built and
thrown away, and why. Append-only.

## 2026-11-24 - Founding session

### How it started
The owner asked what kind of skill could track the full lifecycle of a project's
thinking - discussion, decision, reasoning, conclusion, and the rejection branch
alongside it - so that any person, or any Claude account with no memory of the
conversation, could cold-start and resume without losing anything.

The first answer given was that no existing skill does this, and that a skill
alone cannot, because skills load only when something triggers them. The shape
proposed was skill plus hooks plus an append-only record format.

### Three opinions, deliberately
The owner then brought two external opinions into the design: a DeepSeek
conversation and two Gemini answers. This turned out to matter. Each contributed
something the others missed, and each contained at least one error worth
recording so it is not re-introduced later.

**From DeepSeek:** plugin packaging as the distribution path, and the
`UserPromptSubmit` hook as an enforcement layer. Both adopted. Its
`settings.json` hook JSON was wrong - hook objects placed directly in the event
array instead of nested under a matcher group's `hooks` key - which would have
failed silently. Its `.project-memory/` layout was rejected (REJ-0001) and its
single-file `DECISIONS.md` was rejected (REJ-0003).

**From Gemini, first answer:** the three-namespace ADR / REJ / CR split, the
150-line cap on the state file, and bidirectional supersession links. All
adopted, and the namespace split (ADR-0004) materially improved the design: it
makes the "what must I not re-propose" scan cheap enough that it will actually
be done.

**From Gemini, second answer:** the single best contribution of the three - a
`Diversions & Pivots` section appended inside an existing record, so a mid-flight
change of plan preserves the original reasoning instead of overwriting it. Its
factual claims about Claude Code configuration were wrong: it named
`claude.json`, `.clauderc` and a root `prompt.md` as the places Claude Code takes
instruction from. None of those exist. It also proposed that the agent "must
debate" every proposal, which was dropped as a recipe for noise, and offered no
enforcement mechanism at all beyond a prompt (REJ-0002).

### What was verified rather than assumed
Before writing any code, the hook, plugin and skill contracts were checked
against the official documentation rather than taken from any of the three
opinions. Several assumptions did not survive. `when_to_use` is a real
frontmatter field - the initial scepticism about it was wrong and DeepSeek was
right. `additionalContext` must sit inside `hookSpecificOutput` or it is silently
ignored. `PreCompact` exists, takes `manual` and `auto` matchers, and its stdout
becomes the compaction instructions under a 10,000-character cap - better than
assumed, and missed entirely by both external opinions.

### What was built and what broke
Five hooks, three skills, two scripts, forty tests. One real bug shipped and was
caught by testing rather than reading: `git status --porcelain` collapses
untracked directories to `docs/`, so a brand-new ledger record never matched the
ledger path prefix and the Stop gate fired when it should have stayed silent.
Fixed with `--untracked-files=all` and pinned by a named regression test.

A second apparent failure during the same test run was a bad test, not a bug -
the fixture file had been written into a gitignored directory. Worth recording
because the two looked identical in the output.

### Still open
The Stop and UserPromptSubmit hooks are the ones most likely to be wrong. Both
are quiet by default and narrowly triggered, but whether they earn their place
can only be judged after a real session. The plan is to cut them rather than
endlessly tune them if they become wallpaper.

## 2026-11-24 - Asked whether it was ready to publish

The honest answer was no, and proving why took three failed attempts that
were all my own test harness rather than the plugin.

**Attempt 1: a real headless session.** `claude --plugin-dir ... -p "..."`
never started: the environment resolved an unrecognised model and an invalid
API key. Inconclusive, and not something to work around by touching the
owner's API configuration.

**Attempt 2: run the hook command strings through a shell.** All five
"failed" because Python's `subprocess(shell=True)` uses `cmd.exe` on Windows,
which does not expand `${VAR}`. Wrong shell, not a wrong plugin.

**Attempt 3: force bash.** All five failed with `python: command not found`,
which looked like a damning portability finding. It was not: bare `bash` on
Windows resolves to WSL's bash, a Linux environment with no access to the
Windows Python install.

**Attempt 4, with Git Bash explicitly:** all five hooks exit 0, under both
expansion models - harness-substituted and shell-expanded - with a plugin root
containing a space, and the PostToolUse side effect written to disk.

Worth keeping because the near-miss was instructive: three consecutive
"failures" would each have justified a code change, and every one would have
been a fix to a bug that did not exist. The discipline that saved it was
asking why the test failed before editing anything.

What is still not proven is the registration path itself. The command strings
work; whether Claude Code loads `hooks/hooks.json` from an installed plugin
and invokes them can only be observed from inside a live session. Until then
the plugin is well-tested machinery that has never done its actual job.

## 2026-11-24 — simulating the three situations the owner actually named

The owner stopped the publish-and-push track and named the three cases the
skill has to survive:

> 1. Completely Fresh Project
> 2. Working Project with no such maintenance: Properly extract whatever
>    happened till then, properly document them arrange them, and then
>    structure it properly, and then keep on maintaining. Remember it should be
>    always cold-start-ready for any other account to pick it up any point of
>    time.
> 3. Working Project with already maintained documents almost related to the
>    Skill: Properly structure and segregate and maintain, and keep on
>    maintaining.

Three sandbox projects were built with real git history and the actual scripts
run against them. Nothing real was touched.

**Case 2 had no implementation at all.** The scanner classified an eight-month
project with nine reasoning-bearing commits as `readme-only`, the ledger opened
at ADR-0001, and the `ledger-adopt` skill's own closing step admitted it:
nothing is read into records, and backfilling is left to the user. The
capability was documented as a gap rather than built. That became
`ledger-backfill` and `mine_history.py` (ADR-0015).

**Case 3 was silently broken.** The fixture's `docs/adr/0001-….md`,
`0002-….md` — the `adr-tools` convention, the most widespread one there is —
failed a regex that required a letter prefix, and because the review note sat
inside the `if numbered` branch, *nothing was printed*. One real project,
Trading Tool V2, has exactly that layout. Installing the ledger there would
have created a second decisions folder beside the first and said nothing
(ADR-0014). The regex was the visible half; the silence was the defect.

**Case 1 exposed the cheapest gap.** Two records written into a fresh project,
Stop gate run, silence — and no briefing file anywhere. Correct by the gate's
logic and a direct failure of the cold-start promise, since writing records
*is* touching the ledger and so satisfies the only check that might have
noticed (ADR-0017).

### The route taken and abandoned: loose mining

The first history miner matched loosely, and the argument for it was drawn from
a decision already accepted here — ADR-0013 sets match strictness by
consequence, and mining writes nothing, so a false positive costs one line in a
list. On the fixture it flagged 7 of 10 commits and skipped exactly the
mechanical three.

Against the corpus it flagged **4,273 of 4,380 commits, 98%**, with a 100%
match rate in twenty-seven of thirty-eight repositories. The first diagnosis
was wrong too: the 97% body rate looked like `Co-Authored-By` trailers being
counted as reasoning, and it is not — those bodies are genuine, because these
repositories were written under guidelines that demand it. In this corpus a
message body separates nothing; in a typical project it is the best signal
there is.

Rejected in REJ-0008 and replaced by scoring with a per-repository body weight
(ADR-0016). The rule from ADR-0013 was applied correctly and still gave the
wrong answer, because volume is itself a consequence and the loose tier never
counted it. 98% → 30%.

This is the second time in this project that a filter validated against
fixtures written by its own author has been wrong in a way only the corpus
showed. It is no longer a lesson, it is the procedure.

### A bug hiding behind an empty result

`deleted_paths()` returned `[]` on all 38 git repositories. That looked like
"no project ever deleted a file", which is in fact true of this corpus, and is
indistinguishable from broken. A sandbox repository with one deletion showed it
was broken: `str.splitlines()` treats `\x1e` as a line break, so the sentinel
in the format string was destroyed by the call parsing it. Recorded in
CONSTRAINTS.md.

The CRLF bug taught that git normalisation can hide a defect. This one taught
the quieter version: a code path that returns nothing on all real data is
untested, not working.
