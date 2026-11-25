---
id: ADR-0037
type: decision
title: Validate skill frontmatter as strict YAML
date: 2026-11-25
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0030, ADR-0034, REJ-0009]
tags: [skills, yaml, silent-failure, external-validator]
---

# ADR-0037: Validate skill frontmatter as strict YAML

## Discussion
Submitting to Anthropic's plugin directory ran the repository through an
external validator, and it found a defect every check in this project had
missed.

`wrap-session`'s frontmatter contained an unquoted colon:

```
when_to_use: ... is not a session ending: if it changes the plan use ...
```

A strict YAML parser rejects that outright — `mapping values are not allowed
here` — because `: ` inside a plain scalar reads as a nested mapping.
Verified directly: the shipped line raises `ScannerError`, the corrected line
parses.

It shipped because every parser in reach was lenient. `claude plugin validate
--strict` passed it. A live session read the skill and invoked it normally.
The frontmatter was broken and nothing in the pipeline said so.

The consequence of a stricter reader is not a warning: it is the whole
frontmatter block failing, taking `when_to_use` with it — the one field that
decides whether the skill is ever chosen. ADR-0030 spent three rounds getting
those trigger phrases right; a parser change would have discarded them
silently.

The line was introduced in the ADR-0034 edits a few hours earlier, by me,
while fixing a different ambiguity in the same field.

## Decision
A check over every `SKILL.md`: frontmatter must exist, carry `name`,
`description` and `when_to_use`, and contain no unquoted `: ` or `#` in any
plain scalar.

Implemented as a text check rather than with a YAML library, because this
project ships no dependencies and will not acquire one for a lint. The check
includes a self-test asserting it catches the exact line that shipped, so it
cannot rot into something that passes everything.

## Reasoning
The interesting part is why 270 checks did not catch it. Everything here
tests **behaviour through the harness we run on**, which parses leniently.
Nothing tested the files as *data* against a stricter reader, and a format is
exactly the kind of thing where your own tooling's tolerance is not the
contract.

This is the fifth distinct instrument to find a defect no earlier one could:
82 real projects, a worktree, four live sessions, a fresh-context reading of
the skill descriptions, and now an external validator. Each found a class the
others were structurally blind to.

## Cost
A hand-written approximation of YAML rules, which will diverge from real YAML
at the edges. It catches the two constructs that actually bite in a one-line
scalar and will miss more exotic ones.

## Re-evaluation trigger
If a frontmatter defect is found that this check passes, replace the text
check with a real parser and accept the dependency in the test suite only.

## Conclusion & consequences
All five skills now parse under a strict reader, and two checks pin it.

The wider lesson is about validators rather than YAML. An external checker
disagreeing with your own is information, not an obstacle — the directory's
validator was stricter than `claude plugin validate` on the same file, and
the stricter one was right.

## Diversions & Pivots

## User's own words
> Also trying to publish in Claude ai. Got this message
