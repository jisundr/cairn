# Design: `pr-reviewer` agent (generalized port of maestro's `gitlab-mr-reviewer`)

## Summary

Ports the full feature set of maestro's `gitlab-mr-reviewer` to cairn, generalized to both GitHub PRs and GitLab MRs instead of GitLab-only. Full scope by explicit choice — Initial Review, Fix-Verification Round, Thread Watch, Approval-to-Merge Gate, Pushback Triage all carry over — with Thread Watch (and its Approval-to-Merge Gate) staying an explicit opt-in mode, never auto-started, same as maestro's own design.

Two environment differences from maestro change the shape of the port:
1. cairn agents can hold the `Skill` tool directly (maestro's subagents never could) — the entire "Mid-Run Skill Handoff" relay mechanic (`SKILL INVOCATION REQUIRED` marker, pause, resume-with-raw-output) drops out. A cairn agent just calls `Skill(skill: "code-review", ...)` directly.
2. This session's `code-review` skill already does full GitHub PR review + inline comment posting end to end (`--comment`, effort levels low through ultra, correctness + reuse/simplification/efficiency categories). No GitLab-equivalent skill exists — that half has to be built from `glab` API mechanics, much like maestro's original.

## Scope decision

| Decision | Chosen | Why |
|---|---|---|
| Feature scope | Full port: Initial Review, Fix-Verification Round, Thread Watch, Approval-to-Merge Gate, Pushback Triage | User-selected ("full port but keep the watch part optional like MR watch") — over the narrower Initial-Review-only / no-merge-capability tiers initially proposed. |
| Thread Watch / merge automation | Opt-in only, never auto-started | Matches maestro's own design already (post-completion offer, explicit `/watch-mr`-equivalent) and the user's explicit "keep it optional" instruction. The Approval-to-Merge Gate inside it never auto-merges regardless — always a fresh `AskUserQuestion` per approval-state change. |
| Name | `pr-reviewer`, not `gitlab-mr-reviewer` | "PR" as the generic dev-workflow term; the agent documents itself as covering both GitHub PRs and GitLab MRs. |
| GitHub finding-generation | Delegate directly to `Skill(skill: "code-review", ...)` | That skill already resolves a GitHub PR target, reviews it, and posts comments end to end — reimplementing it would duplicate what the environment already has, same reasoning maestro itself used for its own built-in `review` Skill. |
| GitLab finding-generation | Self-implemented (fetch diff via `git fetch`, never checkout; review directly) | No GitLab-aware skill exists to delegate to. |
| GitLab review shape | Mirrors `code-review`'s categories (correctness + reuse/simplification/efficiency) and effort levels (low/medium/high/xhigh/max/ultra) | User-selected, over keeping maestro's original bug+CLAUDE.md-compliance-only shape with no effort levels — keeps behavior consistent regardless of which host a given PR/MR happens to live on. |
| Review-scope tiering | Initial Review = full diff. Intermediate Fix-Verification rounds (manual re-invoke or a Thread Watch tick) = delta-only since the last reviewed SHA. The pass immediately before the Approval-to-Merge Gate actually merges = one more full-diff pass. | User-selected. Delta-only rounds keep the recurring-check cost low (mirrors `qa-auditor`'s existing task-scoped-diff convention elsewhere in cairn); the pre-merge full pass exists because delta-only rounds could each individually look clean while something cumulative across rounds was missed — worth one full pass right before an irreversible action. |
| Storage | `docs/.reviews/<host>-<owner-repo>-<number>.md`, one file per PR/MR, appended across rounds | Matches cairn's dot-prefixed process-doc convention (`.plans/`, `.specs/`, `.tasks/`) rather than maestro's `.artifacts/`, which has no cairn counterpart. |
| Trigger | Manual dispatch, `intent-analyzer` `review` category + judgment-call mapping in `CLAUDE.md`, plus a `/cairn-watch-pr` command for the explicit Thread Watch entry point | Same pattern as `release-manager`'s trigger design — `agents/intent-analyzer.md` itself stays unmodified. |

## Flow

### Input Resolution (runs first, every mode)

1. Parse input: a GitHub PR URL, a GitLab MR URL, or a branch name (+ repo if not inferrable from local `origin`).
2. Host detection: explicit URL host wins if given; otherwise `git remote get-url origin` — `github.com` → `gh`, `gitlab.com`/custom GitLab host → `glab` (same convention `task-orchestrator` already uses).
3. Confirm the host CLI is authenticated (`gh auth status` / `glab auth status`); stop and report if not.
4. Mode detection: explicit Thread Watch trigger language / `/cairn-watch-pr` / resumed watch ledger → Thread Watch. Otherwise check the target's existing comments for this agent's own signature pattern (a `## Finding N —` heading, or a `**Update (<date>):**` line) → Fix-Verification Round if found, else Initial Review.
5. Fetch (never checkout) both branches fresh, every invocation — never reuse a prior run's cached SHA range, same as maestro (a rebase or retarget between rounds silently produces a wrong diff otherwise).

### Initial Review mode

1. Reference Style Lookup — sample existing comments/notes for a matching structure to draft in; fall back to a default format and say so if none found.
2. Get findings:
   - **GitHub** — `Skill(skill: "code-review", args: "<PR number or URL>")` (no `--comment`) at the effort level requested (default: whatever `/code-review`'s own default is). `--comment` is deliberately omitted: it makes `code-review` post inline immediately, which would bypass this agent's own draft/confirm/post separation (see Hard requirements) — findings come back to `pr-reviewer` to draft, save, and post itself, same as the GitLab path.
   - **GitLab** — run the review directly against the fetched diff, same categories + effort level as the GitHub path (see Scope decision above).
3. Draft Phase — format findings (same `## Finding N — <summary> _(<category>)_` / File / Line / snippet / suggested-fix shape maestro used), iterate freely with the user (cheap, local, no gate), then mandatory auto-save to `docs/.reviews/<host>-<owner-repo>-<number>.md` once the user confirms the draft is final — not itself a confirmation gate.
4. Confirmation & Posting Phase (see below).
5. Post-completion offer: "Watch this PR/MR for new threads until merged? (Y/N)" — declining is a clean no-op.

### Fix-Verification Round mode

1. Re-resolve the target fresh (never reuse cached state).
2. Fetch this PR/MR's comments/discussions (paginated where the host API requires it), identify this agent's own prior findings and any author replies, record each finding's thread/discussion identifier, original file/line, and summary.
3. Delta-diff since the last reviewed SHA (see Scope decision) against each open finding's file/line — classify `fixed` / `partially-fixed` / `still-open` / `disputed` (Pushback Triage resolves `disputed` further into `concession` / `reopened-with-spec` / `decline-acknowledged`).
4. Draft dated, self-contained round replies (`**Update (<date>):** <tag> — <1-3 sentences>`), same iterate-then-mandatory-save pattern as Initial Review, appended to the same per-PR/MR file (never a new file, never truncated).
5. Confirmation & Posting Phase.

### Thread Watch mode (opt-in only, runs via `/loop`)

Fix-Verification Round run repeatedly via the built-in `/loop` skill (not cairn-owned — a marketplace/core skill this environment already ships), one pass per tick, terminating on merge/close. `/loop` owns the timer; this agent never sleeps or polls on its own.

1. On first entry: record Watch Origin (`coding-chain` or `review`) and Sibling PR/MRs if any; initialize a Watch Ledger section in the same per-target file (Watch Origin, Sibling targets, Seen discussion/comment IDs, Approval State, Merge Prompt Shown For, Last Tick).
2. Per tick: refresh input resolution including current state (`open`/`merged`/`closed`) and approval status (GitHub: `gh pr view --json reviewDecision,mergeStateStatus`; GitLab: `glab api .../approvals`, unchanged from maestro). Terminate on `closed`/`merged` per Merge Termination rules below. Otherwise diff comments/discussions against the ledger for (a) new replies to this agent's own findings and (b) new threads opened by anyone else; detect approval-state changes.
3. Notify new threads (author, snippet, link); draft round replies for (a) and either a substantive response or a lightweight FYI/ack note for (b); append to the ledger file, bump Last Tick.
4. When approved and still open, and the merge gate hasn't already been shown for this exact approval state, surface the **Approval-to-Merge Gate** (below). A tick with nothing new skips straight to a "no new activity" report — no draft, no gate.
5. If anything was drafted this tick, run the Confirmation & Posting Phase inline before the tick ends.

### Approval-to-Merge Gate

Backend-neutral in intent (approval → confirm → merge → follow-through); mechanics differ by host:

- **GitHub** — read merge method from repo settings / `gh pr view --json mergeStateStatus,mergeable`; merge via `gh pr merge --merge|--squash|--rebase` matching the repo's configured method, honoring the project's own `CLAUDE.md` push-safety convention if documented.
- **GitLab** — unchanged from maestro (`glab api .../approvals`, `glab mr merge <iid> [--squash|--merge] [--remove-source-branch]`).

Never auto-merges. Presents the choice via `AskUserQuestion` every time the approval state changes; never re-prompts on an unchanged approved state. Before merging, runs the **full-diff pre-merge pass** (see Scope decision) — one more thorough review pass, not just the delta since the last round — and reports any new findings before proceeding with the merge confirmation. On merge success, flows directly into Merge Termination without waiting for the next tick. On merge failure, reports and keeps watching — never retries blindly.

### Merge Termination

- **Watch Origin: review** — report merged, stop. No further action.
- **Watch Origin: coding-chain** — check each declared Sibling PR/MR's state. All merged (or none declared) → emit a `THREAD WATCH: MERGE DETECTED — CODING CHAIN FOLLOW-THROUGH REQUIRED` marker for the main loop (post-merge submodule sync, if applicable — cairn's coding-chain equivalent of maestro's `coding-chain-guide` step). One or more siblings still open → report and stop watching this one; do not emit the marker. Never flips tracker Status here — that stays `task-orchestrator`/`project-manager`'s job (single-writer rule, unchanged from cairn's existing convention).

### Pushback Triage (guidance, not a hard checklist — host-neutral as-is)

1. A factual pushback ("that's already handled") — verify directly against the diff, not memory of the original finding. Concede plainly if correct, hold and explain if refuted.
2. A scope/judgment-call pushback — acknowledge and move on, don't relitigate on the first pass.
3. Reopening a declined finding needs a concrete, actionable spec from the user — plain disagreement should prompt a check-in first, not an automatic reopen.

### Confirmation & Posting Phase (shared across modes)

1. **Duplicate check** — fetch current comments/discussions (paginated where required), compare drafted content against what's already posted; exclude near-exact matches by default, mention exclusions before asking to post.
2. **Explicit posting confirmation** — `AskUserQuestion`, mode-aware copy (Initial Review / Fix-Verification Round / Thread Watch's combined round-reply-and-FYI-note copy). A prior "yes" to draft content never implies posting permission — always a separate ask.
3. **Post** — GitHub: `gh pr comment` for top-level, `gh api` for thread-level replies (`gh pr comment` alone doesn't thread); GitLab: `glab api .../discussions` (new) / `.../discussions/<id>/notes` (reply) / `.../notes` (plain FYI/ack), unchanged from maestro. Default to plain body-text comments (file/line in the body) — never diff-anchored/inline unless the user explicitly asks, and even then confirm the exact host-specific anchoring mechanism before attempting it. Capture returned IDs; on a post failure, stop posting further items and report which succeeded/failed without retrying with altered parameters silently.
4. **Un-resolve on reopen** — if a round reply reopens a previously-resolved finding, un-resolve that thread as part of the same posting step (never leave it for the user to ask separately).
5. **Summary** — how many posted, their IDs/URLs, anything skipped as duplicate or declined.

## Hard requirements (carried over, host-neutral)

- Draft-then-post are two separate, explicit gates — draft iteration is cheap/local, posting is visible to others and hard to reverse.
- Mandatory auto-save to the per-target `docs/.reviews/` file as soon as a draft is finalized, in every mode — not itself a confirmation gate.
- Always check for this agent's own prior comments before posting again, to avoid duplicates on re-run.
- Never check out the target's source branch in the user's working tree — fetch only.
- Every host-CLI command runs from inside a git repository (both `gh` and `glab` resolve target context from the local git remote).
- Findings are reported, never auto-fixed — a user request to fix code based on a finding redirects to `task-orchestrator`/`software-engineer` Direct Mode.

## Out of scope

- No new merge-safety mechanism beyond what each host CLI + the project's own `CLAUDE.md` convention already provides — this agent reads and honors, never invents its own merge policy.
- `LEARNINGS:` block emission (maestro's optional durable-learnings capture) — deferred; cairn has no `documentation-engineer` Learnings Capture mode counterpart yet to consume it. Revisit if that lands.
- No change to `agents/intent-analyzer.md` itself — the `review` category → `pr-reviewer` mapping lives in `CLAUDE.md` as a documented judgment call, same pattern as every other coding-chain routing decision.

## Implementation note

New files: `agents/pr-reviewer.md`, `commands/cairn-watch-pr.md`. Touches `CLAUDE.md` (agent roster entry + review-category judgment-call mapping) and `README.md` (Agents/Commands bullets).
