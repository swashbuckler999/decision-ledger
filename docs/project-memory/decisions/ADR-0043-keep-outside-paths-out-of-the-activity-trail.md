---
id: ADR-0043
type: decision
title: Keep outside paths out of the activity trail
date: 2026-11-26
status: accepted
supersedes: []
superseded_by: null
related: [ADR-0021, ADR-0024, ADR-0041, ADR-0042]
tags: [privacy, activity-trail, real-install]
---

# ADR-0043: Keep outside paths out of the activity trail

## Discussion
A second real installation, in a different project, checked something nobody
here had: what the activity trail writes when the edited file is **outside**
the project.

`post_tool_use.py` makes the path relative to the project and, when that
fails, kept the original — which for an outside file is the full absolute
path. That session saw its own edit to a file under `~/.ssh` written out in
full, and said so.

Reproduced directly: an in-project edit logs `` `inside.py` ``; an outside one
logged the complete path including the home directory and the username.

The trail is gitignored, so none of it reaches a remote — that part of the
design held, and the same session verified it independently by checking what
had actually been pushed. But the file still sits inside the repository
folder, carrying a username and a home directory, and it is written
automatically on every edit with nobody looking.

## Decision
An edit outside the project is recorded as `(a file outside the project)`.
The event is kept; the path is not.

## Reasoning
The trail exists to let `wrap-session` reconstruct work on **this** project
when the conversation is gone. An absolute path to somewhere else does not
serve that. It is cost with no corresponding benefit, which makes it an easy
call once it is visible.

Keeping the event rather than dropping it matters: "something outside the
project was edited" is real signal for a session summary, and silently
discarding it would hide a thing worth knowing. Only the location is dropped.

This is the same judgement as ADR-0021, one layer down. That one took machine
references out of files a human writes; this one takes them out of a file a
hook writes automatically, which is the more dangerous of the two precisely
because nobody reviews it.

## Cost
A wrap-up can no longer say *which* outside file was touched, only that one
was. If that turns out to matter, the answer is to ask the user, not to log
the path.

## Re-evaluation trigger
If a session reconstruction is ever wrong because the trail hid an outside
path, record the containing directory's basename rather than the full path —
never the home directory.

## Conclusion & consequences
Four checks pin it, including that no drive letter, `/home/` or `/Users/`
appears anywhere in the trail.

Both findings in this round came from installing into a real project and
watching what the plugin actually wrote. Neither was reachable from inside
this repository: one needed a plugin that was installed but disabled, the
other needed an edit outside the project. The pattern is now unmistakable —
every environment this plugin has not been run in has had something to say.

## Diversions & Pivots

## User's own words
> Got few findings from another project I am installing the Skill and later
> tried to upgrade it.
