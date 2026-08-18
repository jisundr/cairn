# Design: `release-manager` agent (port from maestro)

## Summary

Ports maestro's `release-manager` agent to cairn, adapted to cairn's plugin-distribution model and its existing manual "Versioning" convention (`CLAUDE.md`). Automates the mechanical tail of cutting a release — changelog entry, commit, annotated tag, push — while keeping the semver judgment call itself an explicit, confirmed proposal rather than a silent auto-decision.

cairn currently has no `CHANGELOG.md` and no automation for the version-bump workflow described in `CLAUDE.md`'s "Versioning" section; every bump today is fully manual.

## Scope decision

| Decision | Chosen | Why |
|---|---|---|
| Bump ownership | Agent proposes the bump (version + reasoning), user confirms | User-selected. Diffing since the last tag is exactly the evidence needed to judge minor-vs-patch per `CLAUDE.md`'s existing rule ("minor for new features, patch for fixes... skip the bump only for changes with no user-visible effect") — automating the proposal removes rote work without removing human judgment from the final call. |
| Confirmation shape | Dry-run plan (proposed version + changelog draft + tag name) in one `AskUserQuestion`, then execute the full sequence on yes | Push + tag-push is a remote-visible, hard-to-reverse action — matches this session's own standing guidance to confirm before such actions. Mirrors maestro's own `maestro-upgrade` command pattern (dry-run diff summary first, single confirm, then apply) rather than inventing a new confirmation shape. A two-gate design (confirm bump, then separately confirm push) was considered and rejected as one gate too many for a single-maintainer repo. |
| Trigger | New `/cairn-release [rc]` command, plus `intent-analyzer` recognition | Matches cairn's existing command-driven pattern (`/cairn-dashboard`, `/cairn-doctor`, ...) for the explicit path, and the coding-chain precedent (Claude's own documented judgment call in `CLAUDE.md`, not a new `intent-analyzer.md` category) for the natural-language path — keeps `agents/intent-analyzer.md` unmodified, consistent with how the coding-chain port avoided touching it. |
| Changelog format | Keep a Changelog convention (`## [version] - date`, `### Added/Changed/Fixed` subsections) | User-selected. Recognized convention; subsection buckets double as a sanity check on the proposed bump (an entry with only `### Fixed` items proposing a minor bump is a mismatch worth catching before commit). |
| RC tags | Supported (`vX.Y.Z-rcN`) | User-selected, carried over from maestro unchanged. |
| Harness override | Loads `.harness/workflow.md` (and `.harness/standards.md` if release-relevant) when present; its convention wins over this spec's defaults | User-selected. Matches the existing "project convention overrides generic default" rule every other coding-chain agent already follows (`qa-engineer`, `software-engineer`, `qa-auditor`). No auto-suggestion to run `harness-engineer` if `.harness/` is absent — release-manager is invoked rarely enough that forcing harness setup first would be friction without proportional value, unlike `task-orchestrator`'s first-run suggestion (which precedes much more frequent Plan Mode invocations). |

## Flow

1. **Detect last release point.** `git describe --tags --abbrev=0`. If no tags exist yet, diff from the repo's first commit (bootstraps the first-ever release).
2. **Harness check.** If `.harness/workflow.md` exists, read it for release-process convention (changelog format, tag naming, commit-message format, branch/approval requirements) — overrides steps 3-5's defaults where it says something. If `.harness/standards.md` carries a commit-message convention, the release commit follows it.
3. **Gather evidence.** `git log`/`git diff` since the last tag (or first commit). Bucket changes by conventional-commit-style prefix where present (`feat`/`fix`/`chore`/...), falling back to reading diff content when commit messages don't carry one.
4. **Propose.** Draft: version number (minor/patch per `CLAUDE.md`'s existing rule, or `-rcN` suffix if requested), reasoning (which changes drove the bump level), full changelog entry in Keep a Changelog format, tag name. Present via one `AskUserQuestion` — accept, edit, or abort.
5. **Execute** (only on explicit accept):
   - Validate proposed version doesn't already exist as a tag (hard stop, never overwrite).
   - Write `version` in `.claude-plugin/plugin.json`.
   - Prepend the changelog entry to `CHANGELOG.md` (create the file with a standard Keep a Changelog header if it doesn't exist yet — this will be the first entry).
   - Validate `plugin.json`'s version matches the changelog entry's version and the tag about to be created (non-negotiable — carried over from maestro's own "committing the changelog before tagging is a hard requirement").
   - Commit (`chore: release vX.Y.Z`, or `.harness/standards.md`'s format if it overrides this).
   - Annotated tag (`git tag -a vX.Y.Z -m "..."`), summary drawn from the changelog entry.
   - Push commit and tag to `origin`.

## Scope guard

- Never modifies source code.
- Never merges branches.
- The changelog entry, `plugin.json` version bump, and the git tag are its sole write outputs — same boundary maestro's version already declared.
- `gh`/`glab` are not used — cairn's release is a plugin-marketplace version bump, not a PR/MR; no ticket/issue system involved.

## Trigger integration

- **New command**: `commands/cairn-release.md`, accepts an optional `rc` argument to request an RC tag instead of a final release.
- **`CLAUDE.md`**: add a short paragraph documenting `release-manager` in the agent roster (same style as the other ported agents), and a one-line note under a natural-language trigger mapping (e.g. "cut a release", "tag this", "release candidate") pointing to it — same pattern already used for the coding-chain's Direct/Chain flow judgment calls, not a change to `agents/intent-analyzer.md` itself.
- **`README.md`**: one bullet under Agents, one bullet under Commands, matching existing style.

## Out of scope

- No auto-invocation as the terminal step of any other agent/workflow (maestro's `meta-agent-sync` auto-trigger has no cairn counterpart — `meta-engineer`/`meta-auditor` were rejected as not applicable to cairn's architecture in the preceding assessment).
- No multi-remote push — `origin` only, matching every other push-capable cairn agent (`task-orchestrator`).
