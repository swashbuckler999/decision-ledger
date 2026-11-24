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
