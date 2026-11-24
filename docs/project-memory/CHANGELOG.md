# Changelog

Dated, append-only. Newest entries at the bottom; each links the record that
carries the reasoning.

- 2026-11-24 **ADR-0001** Package as a plugin rather than a bare skill - `docs/project-memory/decisions/ADR-0001-package-as-a-plugin-rather-than-a-bare-skill.md`
- 2026-11-24 **ADR-0002** Visible docs/project-memory for the ledger - `docs/project-memory/decisions/ADR-0002-visible-docs-directory-for-the-ledger.md`
- 2026-11-24 **ADR-0003** Hooks carry enforcement, instructions carry the protocol - `docs/project-memory/decisions/ADR-0003-hooks-carry-enforcement-not-instructions.md`
- 2026-11-24 **ADR-0004** Separate namespaces for decisions, rejections and change requests - `docs/project-memory/decisions/ADR-0004-separate-namespaces-for-adr-rej-and-cr.md`
- 2026-11-24 **ADR-0005** State file is hand-maintained and capped at 150 lines - `docs/project-memory/decisions/ADR-0005-state-file-hand-maintained-and-capped.md`
- 2026-11-24 **REJ-0001** Hidden directory for project memory - `docs/project-memory/rejections/REJ-0001-hidden-directory-for-project-memory.md`
- 2026-11-24 **REJ-0002** Global CLAUDE.md mandate as the enforcement mechanism - `docs/project-memory/rejections/REJ-0002-global-claude-md-mandate-as-enforcement.md`
- 2026-11-24 **REJ-0003** Single append-only DECISIONS.md - `docs/project-memory/rejections/REJ-0003-single-append-only-decisions-file.md`
- 2026-11-24 **REJ-0004** Blocking Stop hook by default - `docs/project-memory/rejections/REJ-0004-blocking-stop-hook-by-default.md`
- 2026-11-24 **CR-0001** Build for the Forex ML project first, publish later - `docs/project-memory/change-requests/CR-0001-build-for-forex-ml-publish-later.md`
- 2026-11-24 Hook test suite added, 40 checks, all passing - `tests/test_hooks.py`
- 2026-11-24 Fixed: Stop gate fired wrongly because git collapses untracked directories
- 2026-11-24 SessionStart matcher narrowed to startup|clear|compact|fork, saving ~1,490 tokens per resume - see ADR-0003 Diversions
- 2026-11-24 **REJ-0005** Run the ledger on a cheaper model, in a subagent - `docs/project-memory/rejections/REJ-0005-run-the-ledger-on-a-cheaper-model.md`
- 2026-11-24 Published to https://github.com/swashbuckler999/decision-ledger (public)
- 2026-11-24 **ADR-0006** Constraints get their own append-only file - `docs/project-memory/decisions/ADR-0006-constraints-get-their-own-append-only-file.md`
- 2026-11-24 **ADR-0007** Mechanical check for state-file loss - `docs/project-memory/decisions/ADR-0007-mechanical-check-for-state-file-loss.md`
- 2026-11-24 **ADR-0008** Never overwrite a file we did not write - `docs/project-memory/decisions/ADR-0008-never-overwrite-a-file-we-did-not-write.md`
- 2026-11-24 **CR-0002** Adapt to projects that already keep notes - `docs/project-memory/change-requests/CR-0002-adapt-to-projects-that-already-keep-notes.md`
- 2026-11-24 **ADR-0009** Adopt what exists, own only the briefing - `docs/project-memory/decisions/ADR-0009-adopt-what-exists-own-only-the-briefing.md`
- 2026-11-24 **REJ-0006** Migrate existing documents into ledger records - `docs/project-memory/rejections/REJ-0006-migrate-existing-docs-into-records.md`
- 2026-11-24 **ADR-0010** Respect the changelog's own order and format - `docs/project-memory/decisions/ADR-0010-respect-the-changelogs-own-order-and-format.md`
