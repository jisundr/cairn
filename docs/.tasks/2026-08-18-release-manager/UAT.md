# UAT Checklist: release-manager

Manual verification checklist for the `release-manager` agent and `/cairn-release` command (see `docs/.plans/2026-08-18-release-manager.md` and `docs/.specs/2026-08-18-release-manager-design.md`).

- [ ] `claude plugin validate . --strict` passes on the merged branch.
- [ ] In a real (non-scratch) checkout with `claude` on `PATH`, run `/cairn-release` and confirm the agent:
  - [ ] Detects the correct last tag (or falls back to the first commit if no tags exist).
  - [ ] Reads `.harness/workflow.md`/`standards.md` when present in the target repo (N/A in cairn itself — `.harness/` doesn't exist here yet).
  - [ ] Proposes a semver bump matching the actual git history since the last tag (minor for `feat:`, patch for `fix:`-only).
  - [ ] Drafts a well-formed Keep a Changelog entry (only populated subsections).
  - [ ] Shows version + reasoning + changelog draft + tag name together in a single `AskUserQuestion` confirmation before writing anything.
- [ ] Confirm the plan, and verify on accept:
  - [ ] `.claude-plugin/plugin.json`'s `version` is bumped to the confirmed value.
  - [ ] `CHANGELOG.md` is created (if missing) or prepended with the new entry, matching Keep a Changelog format.
  - [ ] A single commit is created containing both changes.
  - [ ] An annotated tag `vX.Y.Z` (or `vX.Y.Z-rcN` if `rc` was passed) is created, pointing at that commit.
  - [ ] Both the commit and the tag are pushed to `origin` — verify no other remote received a push.
- [ ] Decline the proposed plan on a separate dry run and confirm nothing is written (no commit, no tag, no push) and the agent reports "No release cut. Nothing was written."
- [ ] Attempt `/cairn-release` a second time immediately after a real release and confirm the tag-collision hard stop fires before anything is written (no duplicate tag, no accidental push).
- [ ] Run `/cairn-release rc` and confirm the tag carries the `-rcN` suffix instead of a final version.
- [ ] Spot-check `bash tests/smoke/run_all.sh` locally — all 5 scenarios (baseline, rc-argument, tag-collision, existing-tags Detect, `.harness/workflow.md` override) still pass.
- [ ] Confirm `CLAUDE.md` and `README.md` bullets for `release-manager`/`/cairn-release` still read accurately against the final merged behavior.
