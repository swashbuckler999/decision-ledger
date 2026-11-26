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

## 2026-11-25 — an edge-case pass, after the simulation said everything worked

Immediately after pushing the nine commits the owner asked:

> Please check if we are missing any edge cases?

The three-situation simulation had just passed and 172 checks were green, so
this was a good test of whether green means anything. It did not: eight real
defects came out of one afternoon, and two of them lost data.

The question that found most of them was not "is this code correct" but **"what
environment has this never run in"**. Three answers, each with a bug behind it:

- **A linked git worktree.** `.git` is a file there, not a directory. Three
  components tested `.is_dir()`, so the scanner called a repository with full
  history unversioned, the miner found nothing in it, and the Stop hook's
  de-dup marker could not be written — measured as three identical warnings in
  three consecutive turns, which is precisely the behaviour REJ-0004 was
  written to avoid. Claude Code's own sessions run in worktrees. One corpus
  project is one too, and the survey had been quietly miscounting it: 39 git
  repositories under the old test, 40 under the new. ADR-0018.
- **A path with no git at all.** `mine_history --summary` crashed with
  `KeyError: 'first_commit'`, because the non-git early return built a dict
  with fewer keys than the normal one — on the exact command the
  `ledger-backfill` skill gives as step one.
- **A config pointing somewhere unusual.** `build_index.py` checked the
  overwrite guard on the configured index and then wrote to the hardcoded
  default. In a sandbox it exited 0, printed a path, created nothing where it
  said, and **destroyed a hand-written `INDEX.md`**. The ADR-0008 guard was
  present and did not fire, because it was inspecting a different file from the
  one being written. ADR-0019.

Then the config file itself, which is the one input edited by hand with no
schema in front of it. `"paths": "docs"` crashed; `"changelog_order": true`
crashed; `"adopted": "decisions"` did not crash and was worse, because `in` on
a string is a substring test and unrelated keys came back adopted. And `paths`
was unvalidated, so `C:/Windows/Temp/evil.md` resolved to exactly that — the
ledger appending to a file outside the repository it was installed in, against
the standing rule about blast radius. ADR-0020.

Three smaller ones, fixed in the same pass: the session briefing capped
rejections at 40 but injected every accepted decision, so a long-lived project
would crowd out the briefing with its own history; the hook messages named our
default filenames at projects that had adopted different ones, sending the
reader to a file that does not exist; and orphan detection resolved the
briefing against the process directory while resolving git against the hook's,
so a mismatch compared the wrong file against the right history.

### What this changed about how the work is checked

The simulation drives the scripts through the three *situations*. It had
nothing to say about the three *environments*, and that is where every one of
these lived. Both lists now get walked.

And the heredoc lesson landed for the fourth time: patching generated Python
through a shell heredoc failed again, mid-edit, with an unterminated quote.
The Write tool is not a preference in this project any more.

## 2026-11-25 — a privacy correction, mid-task

While a new README was being written the owner interrupted:

> None of the git files should have any reference of my local laptop.

The repository is public, so this is a requirement and not a preference. An
audit of all 64 tracked files found three things: the folder name holding the
82-project corpus, quoted verbatim in two records; a second authenticated
GitHub account named in CONSTRAINTS.md along with which one was usually active;
and the same account named in the briefing.

REJ-0007 had already refused to publish the corpus *project names*. The folder
containing them was missed — the rule had been written about names rather than
about paths, and a path is the same disclosure by another route.

Redacted in place and recorded in ADR-0021, which also says what was
deliberately kept: the publishing identity the owner supplied for exactly this
purpose, and the synthetic hostile paths in the ADR-0020 tests, which name no
real directory.

**History was not rewritten**, and that is the honest part of this entry. The
strings sit in six of nineteen commits, including the initial one, and all of
it is already pushed. A rewrite means every SHA changes and a force push over
a public branch, and it still would not guarantee removal — unreachable objects
stay fetchable by SHA until GitHub collects them, and forks and clones are
untouched. That trade-off is the owner's to make, so it was raised rather than
acted on.

## 2026-11-25 — a fourth corpus pass, and a third kind of edge case

The owner asked for three things at once: a landing page worth looking at,
another full pass over the 82 projects, and a deep hunt for edge cases still
missed.

### The pass

82 projects, 0 errors, 65 seconds, and **nothing written** — proved rather than
asserted, by capturing every project's dirty count, HEAD, file count and newest
mtime before and after. Two projects showed movement and both were explained:
this repository, which was being committed to during the run, and one project
whose tunnel log is appended by a process of the owner's that is still running.

Results: 40 git repositories (one of them a linked worktree, visible only since
ADR-0018), 37 projects that would be adopted, 26 changelogs, 6 journeys, 1
decisions directory with `adr-tools` naming, 5 changelogs where the order could
not be determined and the scanner correctly refused to guess.

And four projects flagged for backfill, **two of them wrongly**.

### The third question

The first round of edge cases asked *what situation is the project in*. The
second asked *what environment is it running in*. This one asked **what state
could the files be in** — and found four more defects, none of which the first
two questions could have reached.

The worst finding came from the pass itself: the plugin's own repository, with
21 decisions and a full ledger, was told it was not greenfield and should run
the backfill. ADR-0014 had excluded the ledger's own directory from role
detection so that an installed project stops being warned about its own files;
that left the "no memory files" field empty, which is exactly what the backfill
check reads. So the advice fired for **every real installation**, and following
it would duplicate everything already recorded.

Then concurrency, which had never been tried. Four sessions recording at once
produced duplicate ids, a failed write, and — the serious one — a lost changelog
entry: both processes read the file, both spliced their own entry into what they
read, both wrote, and each write was complete, correct and missing the other's
line. Five records, three entries, no error. Fixed with an exclusive-create id
claim, pid-stamped temp files, and a lock around the whole read-modify-write
(ADR-0023).

And four smaller ones in the same family: a UTF-8 BOM silently erased a
record's frontmatter, a `|` in a title corrupted the index table, a record
directory that is really a file crashed with a traceback, and a failed write
left its temp file behind forever (ADR-0024).

Nine probes passed unchanged, and they are in the suite now too — non-ASCII
paths, unborn and detached HEAD, five shapes of malformed hook payload, empty
and non-JSON stdin, a 500 KB payload, two roles pointed at one file.

### The landing page

The first rewrite was structurally better and the owner's verdict was blunt:

> The landing page is too much dull. No design, no beauty at all.

Fair. It was a restructured wall of text. Replaced with a hand-built SVG banner
in light and dark variants, served through `<picture>` so it follows the
reader's theme, a Mermaid lifecycle diagram that GitHub renders natively in
colour, and GitHub's own alert callouts.

The step-by-step install was first written as an HTML table with code fences
inside `<td>`, then changed to a plain numbered list — GitHub does not render
fenced code inside table cells reliably, and a broken install block on the
landing page is worse than a plainer one.

Then two more requirements arrived: a proper introduction explaining what the
thing is *for*, and install steps an AI agent can follow from a pasted link
without guessing. The second became `docs/AGENT-INSTALL.md`, keyed on the
scanner's literal output strings rather than on descriptions of the project,
with explicit prohibitions where a plausible choice is wrong (ADR-0025).

### What is now a rule

Three rounds, three questions, and every round found defects the previous ones
could not: *what situation*, *what environment*, *what state*. The probe script
is the method, not a one-off.

And one unbroken pattern worth naming: **every data-loss bug this project has
had was silent.** The CRLF rewrite, the index overwriting a hand-written file,
the changelog dropping an entry while reporting success. Noisy failures get
fixed by whoever hits them. These would not have been.

## 2026-11-25 — the install trial, and what it could and could not prove

The oldest open question in this project was whether Claude Code actually
registers what the plugin declares. Everything up to now had run scripts out of
the working tree, which cannot answer that.

A throwaway project was built outside any real repository, the local repo added
as a marketplace, the plugin installed at project scope, and the project opted
in exactly as the install guide says. `claude plugin details` then answered the
question directly, in the harness's own words: five skills discovered, five
hooks registered, **658 tokens always-on in every session**. That last number
had never been measured.

Driving every hook from the *installed* copy, with `${CLAUDE_PLUGIN_ROOT}`
expanded the way the harness expands it, all five behaved: the briefing came
back carrying its unique string and the rejection's title, PreCompact emitted
its preservation instruction, PostToolUse wrote a correctly-relative path into
the activity trail, UserPromptSubmit caught diversion-shaped phrasing, and Stop
stayed silent — which was the right answer, since a briefing existed and
nothing outside the ledger had changed.

The ADR-0024 activity fix was confirmed in a real install rather than a
fixture: `git check-ignore` shows the trail ignored.

**The model turn did not happen.** The CLI in this environment is routed to a
third-party model gateway whose key is rejected, so the session died at
authentication before any hook ran. That is the environment's configuration and
not the plugin's, and working around it would have meant touching someone
else's credentials, which is not a thing to do for a convenience.

So the first next step in the briefing — "run it inside one live session" — is
now two, and the first is done. The claim that remains open is narrow and worth
stating precisely: whether the harness *calls* these hooks during a real
session, and whether a skill is ever *chosen* on its own from its
`when_to_use`. A skill nobody invokes is invisible, and no test in this
repository can detect that.

### A gap the owner found while this was running

> "Install it — this project only" — There is no instruction for installing the
> skills for all projects in the AI????

Correct, and it mattered. Account-wide install existed and was documented, but
in the *agent* path it was a footnote reading "only if the user explicitly
asked", and in the human path it was a tip below step 4. Someone pasting the
link and saying "install this for all my projects" would get project scope.

Both paths now present the two scopes side by side at the point of decision,
the README carries a second ready-to-paste prompt for account-wide, and the
agent page gained the thing that actually surprises people: installing at user
scope makes the plugin *available* everywhere and switches it on nowhere, and
the agent must opt in only the current project and leave the others alone.

## 2026-11-25 — a simulated session, and the hole it found immediately

With a live model turn unavailable, the owner asked whether a simulated CLI
test was possible. It was, and it mattered more than expected.

Every test until now drove **one hook, once, against a state the test itself
built**. A session is a state machine: what the Stop gate says depends on what
PostToolUse did three turns earlier and on whether anything has been recorded
since. Those transitions are unreachable one hook at a time, because the
condition is created by an earlier turn.

`tests/simulate_session.py` replays twelve turns of a plausible session. On
its **first run** it found the Stop gate silent at the turn it exists for:
code changed, nothing recorded, no warning — where 231 unit checks all said it
fires.

The cause was created by the turn before. The PostToolUse hook writes the
activity trail on every edit, the trail is a ledger path, and the gate treated
any dirty ledger path as "something was recorded". On the first edit in a fresh
install the hook creates `activity/.gitignore`, git reports it untracked, and
the gate goes quiet. So the reminder was suppressed in **the first session of
every new project** — the session where the habit is being set — and recovered
afterwards, which is exactly why nothing caught it.

Underneath it was a conceptual conflation: `is_ledger_path` answers *does this
belong to the ledger*, the gate needed *did a human record reasoning*, and one
function was answering both. Split in ADR-0028; the trail is now ignored by the
gate entirely, being neither code nor a recording.

Confirmed the way these things should be: the same replay fails on the pre-fix
build and passes on the fixed one, from an install-shaped copy as well as the
source tree.

### Four questions, four sets of defects

The pattern is now explicit enough to state as method. Each question found
things the others could not:

1. **What situation is the project in?** — fresh, undocumented, documented
2. **What environment is it running in?** — worktree, no git, odd config
3. **What state are the files in?** — BOM, pipes, concurrency, unwritable
4. **What happened earlier in this session?** — the one above

And the unbroken pattern underneath all four: **every failure was silent.** The
CRLF rewrite, the index overwriting a hand-written file, the changelog dropping
an entry, and now a reminder that simply never arrives. All four reported
success.

## 2026-11-25 — simulating the two things that looked unsimulable

The owner pushed back on the claim that the last gap needed a live session:

> Can't it be simulate?
> If require pull/copy a project from those 82 in a sandbox and do the trial
> run there.

Both halves were right, and both found defects.

### Real projects, real copies

Four corpus passes had been read-only, so the scanner was well tested against
real material and **every write path was not** — adoption, record creation,
index generation and changelog insertion had only ever run against fixtures
this project wrote for itself.

Three projects were copied into a sandbox, one per situation, and the whole
flow run on the copies. Each original was fingerprinted before and after: every
file's size and mtime, content hashes of anything the ledger might touch, git
HEAD, dirty count. All three originals came back identical.

The result worth keeping is the mature project's changelog: **369,195 bytes of
someone's real writing, +138 bytes, inserted at the top in the file's own
`## date - title` style, with every original byte after the heading surviving
verbatim** and the line endings unchanged. The adoption promise is no longer a
claim about fixtures.

The adr-tools project adopted cleanly too — new record filed `0005-` after
their `0001`–`0004`, bare naming matched, `id: ADR-0005` kept inside, their
four records byte-identical.

### Simulating whether a skill gets chosen

This looked impossible and was not. Selection is a model judgement made from
exactly one input: the `name`, `description` and `when_to_use` the harness
advertises. Give a model only that text and a user message, with no other
context, and the real decision is reproduced.

The part that mattered: **the author cannot run this test.** The question is
whether the text works for a reader who did not write it, and this session
wrote it.

Three rounds, twenty-two scenarios. The first found all ten right and three
real overlaps invisible from the inside — "hand off" claimed by three skills at
once, adopt and backfill both claiming "installing the ledger" with the
tie-break citing a tool output the model never sees, and "when the user pushes
back on something" firing on *"use single quotes"*.

Then the lesson of the day. **The rewrite that fixed those overlaps introduced
a worse bug.** Adding "if the project has no ledger yet, use ledger-adopt or
ledger-backfill first" was right for a project with history and wrong for a new
one: adopt needs existing notes, backfill needs existing commits, and a
brand-new repository has neither. A decision in a fresh project — the simplest
case this plugin has — now selected nothing. Round two caught it at once;
round three, with all four traps together, came back clean.

What generalises: a description written by the person who built the thing
cannot be reviewed by them. The overlaps were glaring in the report and
invisible in the writing, and the only reason they surfaced is that something
with no memory of writing them was asked to use them.

## 2026-11-25 — the live session, and the bug no amount of testing here could find

The trial finally ran: a real Claude Code session, in a throwaway project, with
the plugin installed.

Both unknowns closed. **SessionStart context reaches the model** — it answered
the endpoint and the rejection cold, before touching a tool, and could quote
the injected block. **All five skills were visible and invokable**, and
`decision-ledger` ran end to end: it read its own SKILL.md and templates,
followed them, quoted the user verbatim, and produced ADR-0001 plus the
master-file updates.

Then it reported four defects, and the first one is the most serious thing
found in this project.

### Every script path in every instruction was wrong

`python scripts/new_record.py` — a bare relative path, in all nine skill call
sites and twelve more across the README and install guides. The scripts live
in the **plugin**; the agent's working directory is the **user's project**. It
resolves to nothing.

It had never appeared because every test, simulation and corpus pass ran from
the development checkout, where `scripts/` happens to resolve. **The checkout
is a privileged environment, and testing in it is testing the one place the
bug cannot occur.**

The consequence was worse than a missing file, because the skill says what to
do without the script: the session allocated the id by hand and wrote the
changelog directly. So the atomic id allocation (ADR-0023), the CRLF-preserving
insert (ADR-0010) and the adoption-aware ordering were **all bypassed, and it
reported success.** Months of work on the deterministic layer, unreachable in
production, with nothing anywhere saying so.

Asked to establish the fix empirically rather than have me guess it, the
session came back with three facts. `CLAUDE_PLUGIN_ROOT` is **empty** in a tool
shell — the harness substitutes it for hook commands, which is exactly why the
hooks were never affected — and in Git Bash the empty expansion silently
becomes a path inside the Git installation. `scripts/` and `skills/` are
siblings, and a skill is handed its own absolute base directory. And a
**second, independent bug**: `project_dir()` falls back to `os.getcwd()`, and
the harness had reset that session's working directory mid-session, so fixing
only the path would have scaffolded records into an unrelated folder.

Fixed three ways, because one was not enough: the SessionStart hook now hands
over both absolute paths (it runs where the variable works and can locate
itself), a `--project` flag pins the target so no script infers it from
ambient state, and all 21 call sites are anchored with a fallback for the
projects where the briefing is silent — which is precisely the projects the
adoption skills exist for.

### The other three

The rejection list in the briefing ships titles only, yet told the model to
cite a rejection "unless its re-evaluation trigger has actually fired" — which
cannot be judged from a title. It now says to open the record first.

"Append, never rewrite" never said what to do when the file does not exist. A
literal reader skips the entry entirely. It now says that creating a missing
file is not a rewrite.

And the activity trail is systematically incomplete: it matches
`Edit|Write|NotebookEdit`, so anything written through the shell leaves no
entry — the normal case in permission modes that favour Bash. Matching `Bash`
too was considered and rejected; the trail is a hint, never evidence, and that
is now written where it will be read.

### What this changes about how the work is checked

The four questions each found what the others could not: what situation, what
environment, what file state, what happened earlier in the session. This adds
a fifth, and it subsumes the rest: **what is true only here?** Every previous
round ran inside the one directory where the plugin's own layout is correct.

## 2026-11-25 — the verification run, which found three more

A second live session, started only to confirm the ADR-0031 path fix, verified
it on all four routes: the injected absolute paths were present and usable,
`new_record.py` ran first try and allocated `REJ-0002` correctly after the
existing `REJ-0001`, the record landed inside the project rather than wherever
the shell happened to be, and the base-directory fallback reached
`build_index.py` on its own. No guessing, no workarounds.

Then it found three more things, because a verification run is another sample
of the one environment that cannot be simulated here.

The changelog was being written **twice**: the script appends the entry as it
creates the record, and step 4 of the skill told the agent to append one "for
every record, without exception". The session avoided shipping the duplicate
only by reading the file first. Worse than the duplication, the hand-written
line used the file's own style while the script used its default, so two
formats ended up side by side — and the skill's own first rule is to match
what is already there.

The real cost is not tidiness. A model appending a line by hand **routes around
everything ADR-0010, ADR-0011 and ADR-0023 built**: the project's own entry
format, the newest-first insertion, the preserved line endings, the lock. One
writer per file, and the script is it.

Third, a literal reader was being sent to look for something that does not
exist: step 4 said to keep `00-PROJECT-STATE.md` describing reality, but that
file has no rejections or decisions section — the SessionStart hook composes
those lists from the record folders. Nothing to edit, and an instruction
implying otherwise invites someone to add the section to make it true.

None of these are testable. They are instructions, which is exactly why two
live sessions found them and 254 checks did not.

## 2026-11-25 — the third live session: both skills work, five more defects

`cold-start` and `wrap-session` had never been invoked by anything. Both did
what they claim. `cold-start` oriented a session that had never seen the
project, from the ledger rather than the code. `wrap-session` found the
unrecorded decision from earlier in the session **on its own** and wrote
ADR-0002 for it. That is the headline promise demonstrated end to end by an
agent with no memory of the work.

It also found five defects, and the shape of them is the interesting part.

**The Stop hook was crying wolf.** It flagged an editor settings file the
session had never written to — untracked before the session began, proved by
its own opening `git status`. The gate measures *what is not committed* and
reports it as *what you changed and did not record*. On a fixture those are
the same list. On a real working tree every untracked file appears at the end
of every session, forever, and the reminder that matters looks exactly like
the ones that do not. REJ-0004 rejected a blocking hook because a wall gets
the plugin uninstalled; this was the same failure arriving quietly. Fixed with
a session baseline (ADR-0033).

**Three instructions assumed every ledger file already exists.** The worst
inverted a skill's purpose: `wrap-session`'s table is headed "where it must
already exist", and the session was holding an endpoint pin that lived only in
the mutable state file with no `CONSTRAINTS.md` to move it to. Read literally,
the table forbids the move — so the one fact the table exists to rescue was
stranded in the one file that gets rewritten. The session refused to delete it
and reported the contradiction, which is exactly right.

`cold-start` had the same assumption about `CONSTRAINTS.md`, and a report
shape ending "nothing longer" that left no room for the honesty its own rules
demand — it found the state file promising a Parquet writer the code did not
have, and had nowhere to put that. And `wrap-session` never said whether to
commit, so the session fell back on a convention it found elsewhere.

This is the third appearance of "assumes the file exists" after ADR-0032. All
of it was written while looking at this repository, where every ledger file
has existed since the first week. **The author's own project is the worst
reference for instructions about a project that has nothing yet.**

### A sixth thing, found here rather than there

The concurrency test failed once in about seven full-suite runs and never in
six isolated trials — load-sensitive. Rather than guess at a fix with no
evidence, the test now reports the full stderr of a failing run instead of a
120-character tail, because the previous failure wasted the one chance to see
what happened.

### The pattern, stated plainly

Three live sessions, three sets of defects, no sign of the rate dropping. The
code is well covered — 263 checks and a session replay. The 660 lines of
instructions wrapped around it are still being read for the first time by
someone other than the person who wrote them, and every reading has found
something.

## 2026-11-25 — the fourth session: two correct fixes, one new bug

The fourth live run was meant to confirm the previous round. It confirmed it
and found a defect that round had created.

ADR-0034 gave `wrap-session` a commit step. ADR-0033 gave the Stop gate a
session baseline. Together: the session recorded a decision, committed the
ledger as instructed, and the gate announced **"nothing was written to the
decision ledger"** on the very turn a record had been written and committed —
listing the working tree's junk files as the unrecorded work.

Committing empties the dirty set, and the dirty set was the only place the
gate looked for proof anything had been recorded. It was reading the absence
of its own evidence as proof of the opposite, and the better the session
behaved the more confidently it was wrong.

Fixed by storing the session's starting HEAD in the baseline and counting
commits since it. With a mirror test, because committing must not become a
way to silence the gate.

### What the run says about the remaining risk

The three earlier sessions found defects in individual pieces. This one found
a defect produced by **two correct fixes meeting.** Neither change was wrong;
the join was. That failure mode does not shrink as the pieces improve, and no
test of either piece alone could have surfaced it.

So the live session is not a box to tick before publishing. It is the only
instrument that sees the plugin whole — and the one that keeps finding the
class of problem a 268-check suite is structurally unable to reach.

The good news from the same run: the ADR-0033 baseline worked. The junk files
created at the start of the session were correctly ignored as this session's
concern until the gate's other defect dragged them into the message.

## 2026-11-25 — "if you know, why not handle it?"

The macOS `python` vs `python3` failure had been documented in three places
and left as a manual step, on the grounds that detecting the interpreter
needed a cross-platform shell test nobody had verified. The owner rejected
that reasoning directly: if the problem is known, handle it.

Reading the documentation rather than guessing settled it. Hook commands run
under `sh -c` on macOS and Linux and Git Bash on Windows, so `||` is available
in the normal case everywhere. There is **no OS-conditional mechanism at all**
— no platform field, no per-OS entries, nothing that reveals the platform — so
the per-OS idea was never possible and that is now recorded so nobody hunts
for it again.

The fallback is safe only because every hook exits 0 via `guard()`, so a
non-zero status means the interpreter is missing and nothing else. Measured
both branches: one run when `python` works, correct output when it does not.

The order needed evidence. `python3` first looks right for POSIX and is wrong:
on this Windows machine `python3` resolves to a Microsoft Store stub that
produces nothing. `python` first means Windows never reaches it.

One risk accepted and written down rather than buried: on Windows without Git
Bash, hooks run under PowerShell, and PowerShell 5.1 cannot parse `||`. That
turns a working install into a broken one for those users. The trade is a
certain silent failure for most Mac and Linux users against a possible parse
error for a smaller group who have a one-line fix — and the README names all
three ways out.

The same reading confirmed ADR-0031 from the documentation side: these
variables "aren't present in the environment of commands Claude runs through
the Bash tool." The empty `CLAUDE_PLUGIN_ROOT` the first live session found
was specified behaviour, not a quirk.

## 2026-11-25 — the directory says no, and finds a bug on the way out

Submitting to Anthropic's plugin directory produced two results, and the
smaller one is the more useful.

### The validator found what 270 checks could not

`wrap-session`'s frontmatter held an unquoted colon — *"is not a session
ending: if it changes the plan"* — which a strict YAML parser rejects
outright with `mapping values are not allowed here`. Verified directly: the
shipped line raises, the corrected line parses.

It shipped because every parser in reach was lenient. `claude plugin validate
--strict` passed it. A live session read the skill and invoked it normally.
The frontmatter was broken and nothing said so.

The damage a stricter reader would do is not a warning — the whole block
fails, taking `when_to_use` with it, which is the single field deciding
whether the skill is ever chosen. Three rounds of ADR-0030 went into those
trigger phrases; a parser change would have discarded them in silence. And it
was introduced a few hours earlier, by this session, while fixing a different
ambiguity in the same field.

Everything here tests behaviour through the harness we run on, which parses
leniently. Nothing tested the files as *data* against a stricter reader.
That is now ADR-0037, with a self-testing guard.

### The directory itself is closed to us

Three blocking findings, all the same sentence: *only from Verified
organizations.* No command hooks. No `allowed-tools` beyond Read, Grep, Glob
and LS. No scripts or programs — nothing that is not Markdown, text, JSON,
YAML or a raster image.

This plugin is five command hooks, eleven Python scripts, and skills that must
write files. Complying would leave five Markdown files with read-only tools
and no enforcement — not a smaller version of this, a different and useless
one. ADR-0003 chose hooks precisely because instructions alone degrade, and
REJ-0002 recorded why.

Two smaller refusals stand regardless of verification: the icon must be a
square PNG or JPEG of 512-2048 px, read **once** and never updated after; and
the name collides with `dupflo/decision-ledger`, which already holds the
display name "Decision Ledger".

### What this does not change

Distribution. The public marketplace route needs no submission, no review and
no Claude account, and was verified working today at both project and user
scope from the public repository. The directory is discovery; the repository
is distribution, and it has been live all along.

The validation report is worth keeping for one more reason: on the `||`
fallback from ADR-0036 it independently reached the same conclusion about the
Windows hazard, and recommended a Node shim as the way out. That is a real
option if this is ever revisited.

## 2026-11-26 — a rejection used the way rejections are supposed to be used

A real installation hit a project keeping every decision in one 800-line
`DECISIONS.md`. The installing agent read REJ-0003, recognised the shape, and
quoted the rejection back with the observation that the project had already
hit the failure it predicted. The plugin working exactly as designed.

Then the scanner was found silent about that file entirely (ADR-0038), and the
first fix — mention it, tell the user to link it from the briefing — was
rejected by the owner as a half-answer:

> It would be better to read them, structure them as per the skills mechanism,
> break into multiple files with reasoning as per the skills structure,
> understand it, and prepare it properly - INSTEAD OF THROWING IT AWAY!!!!

They were right, and two of this project's own records proved it faster than
argument could.

**REJ-0006 was being applied beyond its scope.** It refused to migrate a 369 KB
*changelog* — prose where the boundaries would have to be invented. A
decisions document is the opposite: the author drew the boundaries, wrote the
dates, wrote the reasoning, marked what was superseded. Every judgement the
rejection feared inventing had already been made.

**And the plugin contradicted itself.** `mine_history.py` reconstructs records
from commit messages — thinner, more incidental, less deliberate — and handles
the honesty problem with provenance markers. Refusing to read a file literally
named DECISIONS.md while mining one-line commits was an oversight wearing a
principle's clothes.

**The rejection's own trigger had already fired.** REJ-0006 said revisit "as
an explicitly invoked, one-document-at-a-time operation that backs up the
original outside the repository first, shows a diff, and requires
confirmation". It never said never. It said not silently, not during adoption,
not wholesale — which is precisely what was then built (ADR-0039).

That is the first time this project has used a re-evaluation trigger for its
intended purpose. A rejection with a real trigger is not a closed door; it is
a door with the key taped to it.

### Versioning, and a promise worth keeping

The owner also asked for an upgrade path, because a change like this is
worthless to anyone running an older copy who never learns it exists.

Claude Code already has `claude plugin update`. What was missing was
awareness. The design question was the weekly check: a version check normally
means asking a server, and the README promises nothing leaves the machine.

It reads the plugin cache instead — sibling version directories already on
disk, refreshed by the user's own `marketplace update`. No network call at
all, asserted by a test that greps the source for `urllib`, `requests`,
`socket` and `curl` (ADR-0040). A plugin whose first new feature quietly
starts contacting a server is one nobody should trust.

### And a bug that had shipped

Writing the parser surfaced that **every script mangled non-ASCII when it
printed**. `Café` reached the skill as `Caf?`, in the very worklist used to
quote an author's own words verbatim. The data was always read correctly; only
the printing was lossy, which is why it survived — the pipeline looked right
on both sides of the break.

## 2026-11-26 — a second real install, and two states this repo cannot produce

A different project installed the plugin and then tried to upgrade it. Two
findings came back, and neither was reachable from inside this repository.

**`enable` has its own `--scope`, and it does not inherit the install's.**
The plugin was installed at project scope but disabled — a state no fixture
here has ever had. The obvious next command, `claude plugin enable
<plugin>`, reported `(scope: user)` and wrote the enable into the user
settings file. So an agent following `AGENT-INSTALL.md` literally, never
typing `--scope user`, lands the hooks in every repository the user opens —
exactly what step 2 spends a bold paragraph forbidding.

Worse, the page's own verification passes: `claude plugin list` still reports
`Scope: project`, because the listing reflects where the install is declared,
not where the enable went. Verified here: `enable --help` confirms
`-s, --scope <scope>` defaults to auto-detect. Recorded as ADR-0041.

**An installing session cannot verify its own install.** After a correct
install, invoking the skill the page tells you to use returns `Unknown skill`.
Nothing is wrong: hooks and skills enabled mid-session are not picked up by
the session that enabled them. The page said to start a new session for the
hook check but never said why, nor that the installing agent itself cannot
run it — leaving an agent with an install that looks broken by its own
documented next step, and every available wrong conclusion making it worse.
ADR-0042.

### And one they found by looking at what the plugin wrote

That session also checked what the activity trail records when the edited
file is **outside** the project, and found its own edit to a file under
`~/.ssh` written out as a full absolute path, home directory and username
included. The gitignore held — it never reached the remote, which they
verified independently against what had been pushed — but the file still sits
in the repository folder, written automatically on every edit, with nobody
reviewing it.

Fixed in ADR-0043: the event is kept, the path is not.

### What this round says about method

Both install findings needed states this repository cannot produce: a plugin
installed but disabled, and a skill invoked in the session that enabled it.
The trail finding needed somebody to edit a file outside the project and then
read the log.

That is now five distinct instruments — 82 real projects, a worktree, live
sessions, an external validator, and other people's installs — and the test
suite has still never been the one to find a defect of consequence. It
confirms; it does not discover.

## 2026-11-26 — read cold, and the trail turned out to be test output

A session opened the project with no prior context and read the docs. Two
things in the activity trail looked wrong: every line was a compaction
checkpoint, four at a time, one second apart, with `trigger: unknown` — and
there were no tool entries at all, in a repository that had been edited for
three days.

Only one of those was a defect.

**The missing tool entries are by design and already written down**, in
`post_tool_use.py`'s own docstring: the hook matches `Edit|Write|NotebookEdit`,
a file changed through the shell leaves no entry, a live session found that
directly, and in permission modes that encourage the shell the
under-recording is the normal case. Matching `Bash` too was considered and
rejected. ADR-0028 settles it: the trail is a hint, never evidence. The cold
reader's first instinct — "this is broken" — was answered by the docs in the
file it was reading, which is the thing the project is for.

**The duplicate checkpoints were real, and they came from the test suite.**
`test_hooks_survive_hostile_payloads` exists to feed the hooks garbage, and
four of its payloads carry no usable `cwd`. Alone in the file it set no
project override, so `project_dir()` fell back to `os.getcwd()`, found this
repository's ledger, and the hooks did their job on it: four compaction
checkpoints appended to the live trail per run, and `.git/ledger-baseline`
rewritten — the Stop gate's memory of what was already dirty when the session
started (ADR-0033). Run the tests mid-session and you quietly change what the
Stop hook reports for the rest of it.

270 of the trail's 271 lines were put there this way. Exactly one compaction
has ever been recorded here: `2026-11-24 16:56:31 (trigger: auto)`.

### Why 317 passing checks never noticed

Because nothing was failing. Every hook behaved exactly as specified; it was
pointed at the wrong project. The suite asserted on what the hooks returned
and on sandbox contents, and never once on whether running it had changed the
repository it ran in. A test aimed at the wrong target still passes.

So the fix is two lines of `cwd=` and the guard is the real work:
`test_the_suite_leaves_this_repository_alone` fingerprints the activity trail
and the `.git/ledger-*` markers before the first test and compares after the
last. It was verified by putting the leak back — it fails and names both
artefacts — then taking it out again. 318 checks, zero footprint.

### The pattern, for the sixth time

The route not taken: making the hooks refuse to write when the payload has no
`cwd`. That would have "fixed" the symptom and broken the plugin, because the
cwd fallback is the last resort that a live session already proved necessary
when every environment variable came back empty. Pinning the test with
`LEDGER_PROJECT_DIR` was also wrong — it outranks the payload, so it would
have neutralised the very `cwd` values the test exists to send. The fix had to
leave the subject of the test untouched.

And again the finding came from an instrument, not from reading code: this
time from somebody arriving with no memory of the project and asking why a
file looked odd. The test suite has still never found a defect of consequence
here. That is now six distinct instruments, and the newest one is the cheapest.
