# Lightweight Worktree+PR/MR Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend "create a worktree, open a PR/MR" beyond `task-orchestrator`'s Chain-flow Plan/Publish mechanism to Direct flow, `superpowers:brainstorming`'s bounded path, and `documentation-engineer` doc-sync work, so their usage can also land in a PR/MR body via the existing usage-report machinery.

**Architecture:** A new `task-orchestrator` **Lightweight mode** (two thin entry points, Start and Finish) reuses Plan Mode's worktree-creation step and Publish Mode's commit/PR-creation steps without the task-folder/plan-file/feasibility/doc-gate/ticket-sync machinery those require. `software-engineer` Direct Mode, `qa-engineer` Direct Mode, and `documentation-engineer` gain an optional `Worktree:` context field to `cd` into and a conditional trigger to call Lightweight Finish when one is present. `usage_dashboard.py` gains a `--window-report` CLI mode (a single-window variant of the phase-table report shipped for Chain flow) for Lightweight Finish to call.

**Tech Stack:** Markdown agent-definition files (no code execution), Python 3 stdlib (`scripts/usage_dashboard.py`), pytest.

**Spec:** `docs/.specs/2026-08-17-worktree-pr-lightweight-mode-design.md`

## Global Constraints

- Spike path (`superpowers:brainstorming`) is explicitly out of scope — never gets a worktree/PR.
- The ask is always suggested via `AskUserQuestion`, never forced/default-on.
- Lightweight mode reuses Chain flow's existing worktree-creation (`Skill(skill: "superpowers:using-git-worktrees")`) and PR-creation (`gh`/`glab` remote detection, consolidated commit) mechanics exactly — never reimplemented.
- Lightweight mode writes no `STATE.md`/`HISTORY.md`/task folder — there is none in this mode.
- Never `--no-verify` on a commit hook failure in Lightweight Finish — same rule as Publish Mode.
- `usage_dashboard.py --window-report`'s output is best-effort: an `unavailable` result never blocks Lightweight Finish, it just means no usage section in the PR/MR body.

---

## Task 1: `usage_dashboard.py --window-report` CLI mode

**Files:**
- Modify: `scripts/usage_dashboard.py`
- Test: `tests/test_usage_dashboard.py`

**Interfaces:**
- Consumes: `usage_by_windows(cwd, projects_root, windows)` (already shipped — takes `windows: list[(label, start_iso, end_iso)]`, returns `{label: {*USAGE_FIELDS, "calls", "cost", "unpriced_calls"}}`).
- Produces: `build_window_report(cwd: str, projects_root: Path, start_iso: str, end_iso: str) -> str` — markdown table, single `Work` row + `Total`, same shape as `build_task_report`'s output minus the phase breakdown. CLI: `python3 usage_dashboard.py --window-report <start-iso> <end-iso> [cwd]`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_usage_dashboard.py`:

```python
def test_build_window_report_renders_single_row(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"
    transcripts_dir = projects_root / usage_dashboard.encode_project_dir(str(cwd))
    _write_session(transcripts_dir, "session-a", [
        _assistant_line("2026-08-17T14:10:00Z", "claude-sonnet-5", input_tokens=1_000_000, output_tokens=0,
                         cache_creation_input_tokens=0, cache_read_input_tokens=0),
        _assistant_line("2026-08-17T15:30:00Z", "claude-sonnet-5", input_tokens=0, output_tokens=0,
                         cache_creation_input_tokens=0, cache_read_input_tokens=0),  # outside window
    ])

    report = usage_dashboard.build_window_report(str(cwd), projects_root, "2026-08-17T14:00:00Z", "2026-08-17T15:00:00Z")

    assert "Work" in report
    assert "Total" in report
    assert "approximate" not in report.lower()  # single explicit window, not the phase-table's backdated-PLAN caveat


def test_build_window_report_no_transcripts_reports_zero(tmp_path):
    cwd = tmp_path / "myproject"
    cwd.mkdir()
    projects_root = tmp_path / "claude_projects"

    report = usage_dashboard.build_window_report(str(cwd), projects_root, "2026-08-17T14:00:00Z", "2026-08-17T15:00:00Z")

    assert "0" in report
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_usage_dashboard.py -k window_report -v`
Expected: FAIL with `AttributeError: module 'usage_dashboard' has no attribute 'build_window_report'`

- [ ] **Step 3: Implement `build_window_report` and the CLI branch**

In `scripts/usage_dashboard.py`, add directly after `build_task_report`:

```python
def build_window_report(cwd: str, projects_root: Path, start_iso: str, end_iso: str) -> str:
    """Markdown usage table for a single time window — Lightweight mode's variant of
    build_task_report, for paths with no HISTORY.md/task folder to read phases from."""
    windows = [("Work", start_iso, end_iso)]
    stats = usage_by_windows(cwd, projects_root, windows)
    row = stats["Work"]
    tokens = sum(row[f] for f in USAGE_FIELDS)

    lines = [
        "| Phase | Tokens | Cost |",
        "|---|---|---|",
        f"| Work | {tokens:,} | ${row['cost']:.2f} |",
        f"| **Total** | **{tokens:,}** | **${row['cost']:.2f}** |",
    ]
    if row["unpriced_calls"]:
        lines.append(f"_{row['unpriced_calls']} call(s) used a model with no pricing entry — excluded from cost._")
    return "\n".join(lines)
```

Then modify `main()`'s existing `--task-report` branch to also handle `--window-report`:

```python
def main():
    projects_root = Path.home() / ".claude" / "projects"

    if len(sys.argv) > 1 and sys.argv[1] == "--task-report":
        if len(sys.argv) < 3:
            print("usage: usage_dashboard.py --task-report <slug> [cwd]", file=sys.stderr)
            sys.exit(1)
        slug = sys.argv[2]
        cwd = sys.argv[3] if len(sys.argv) > 3 else str(Path.cwd())
        print(build_task_report(cwd, projects_root, slug))
        return

    if len(sys.argv) > 1 and sys.argv[1] == "--window-report":
        if len(sys.argv) < 4:
            print("usage: usage_dashboard.py --window-report <start-iso> <end-iso> [cwd]", file=sys.stderr)
            sys.exit(1)
        start_iso, end_iso = sys.argv[2], sys.argv[3]
        cwd = sys.argv[4] if len(sys.argv) > 4 else str(Path.cwd())
        print(build_window_report(cwd, projects_root, start_iso, end_iso))
        return

    cwd = sys.argv[1] if len(sys.argv) > 1 else str(Path.cwd())
    port = find_free_port(DEFAULT_PORT)
```

(This replaces the existing `--task-report`-only branch added for the PR/MR usage-token feature — the new `--window-report` block is inserted directly after it, before the fallthrough to server startup.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_usage_dashboard.py -v`
Expected: all PASS (27 existing + 2 new = 29)

- [ ] **Step 5: Commit**

```bash
git add scripts/usage_dashboard.py tests/test_usage_dashboard.py
git commit -m "feat: add usage_dashboard.py --window-report CLI mode for Lightweight mode"
```

---

## Task 2: `task-orchestrator` Lightweight mode

**Files:**
- Modify: `agents/task-orchestrator.md`

**Interfaces:**
- Consumes: `scripts/usage_dashboard.py --window-report` (Task 1).
- Produces: two request shapes callers use — `"task-orchestrator Lightweight Start"` (with `slug`, `task-type` in context) returning `Worktree:`/`Branch:`/`Start:` plain text; `"task-orchestrator Lightweight Finish"` (with `Worktree:`/`Branch:`/`Start:` in context) returning `PR/MR:` plain text. These exact field names (`Worktree:`, `Branch:`, `Start:`, `PR/MR:`) are what Tasks 3–5 read from/write to opening context.

- [ ] **Step 1: Add the Lightweight mode section**

In `agents/task-orchestrator.md`, insert a new top-level section directly after the `## PUBLISH MODE` section's last line (`Update STATE.md to Phase: PUBLISH, Handoff to: none (terminal), PR/MR URL in Key info. Append the final HISTORY.md line — same <ISO-8601 UTC> — PUBLISH — <note> format as every other phase line.`) and before `## UNATTENDED EXECUTION`:

```markdown
---

## LIGHTWEIGHT MODE

A third mode alongside Plan/Publish, for Direct flow, `superpowers:brainstorming`'s bounded path, and `documentation-engineer` doc-sync work — paths that never have a `docs/.plans/` file or a task folder, but still want a worktree and a PR/MR. Two thin entry points, invoked explicitly by name in the opening context; neither writes `STATE.md`/`HISTORY.md`/any task folder — there is none in this mode.

### Lightweight Start

Triggered by opening context naming `"task-orchestrator Lightweight Start"` plus `slug` and `task-type` (`direct` / `bounded` / `doc`).

1. Branch name: `<task-type>/<slug>` — caller-supplied slug, since no plan file exists to source one from.
2. Invoke `Skill(skill: "superpowers:using-git-worktrees")` — hard-required, exactly Plan Mode Step 5's mechanism, never reimplemented.
3. Record the current UTC time (`<ISO-8601 UTC>`) as the start timestamp.
4. Return plain text only — no `STATE.md` write:

```
LIGHTWEIGHT START COMPLETE
Worktree → <path>
Branch   → <branch-name>
Start    → <ISO-8601 UTC>
```

The caller holds all three fields and passes them back verbatim to Lightweight Finish.

### Lightweight Finish

Triggered by opening context naming `"task-orchestrator Lightweight Finish"` plus the `Worktree:`, `Branch:`, and `Start:` fields Lightweight Start returned.

1. `Bash git remote get-url origin` — same remote-host detection as Publish Mode Step 4 (`github.com` → `gh`, `gitlab.com`/custom GitLab host → `glab`; `origin` wins on multi-remote signals).
2. Stage and commit everything in the worktree — same consolidated-commit discipline as Publish Mode Step 5: plain conventional-commit message (no `.harness/workflow.md` to read conventions from in this mode), never `--no-verify` on a hook failure — stop and report instead (EXIT & DERAILMENT HANDLING).
3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/usage_dashboard.py --window-report <Start> <now, ISO-8601 UTC> <cwd>` via `Bash`. Best-effort: if it prints nothing usable (e.g. malformed timestamps), proceed without a usage section rather than blocking.
4. Create the PR/MR via the CLI detected in Step 1. Body includes the usage report from Step 3 when it produced a table (omit the section entirely if it didn't — same rule as Publish Mode Step 6). Record the resulting URL.
5. Return plain text only — no `STATE.md` to update, no ticket sync (none of Direct flow, bounded path, or doc-sync carry a ticket):

```
LIGHTWEIGHT FINISH COMPLETE
PR/MR → <url>
```

Terminal for this invocation.
```

- [ ] **Step 2: Update mode detection**

Find the `## START` section's opening paragraph (currently: `**Mode detection (runs first).** Read the opening context. If it explicitly requests Publish Mode (...) → **Publish Mode**. Otherwise → **Plan Mode**`). Replace it with:

```markdown
**Mode detection (runs first).** Read the opening context. If it explicitly names `"task-orchestrator Lightweight Start"` or `"task-orchestrator Lightweight Finish"` → **Lightweight mode** (see LIGHTWEIGHT MODE above) — check this first, since it's the only mode with no task folder involved at all. Otherwise, if it explicitly requests Publish Mode (e.g. "qa-auditor/documentation-auditor Doc Post-Impl just finished clean, invoke task-orchestrator Publish Mode"), or a `docs/.tasks/<slug>/STATE.md` exists with `Phase: DOC-POST-IMPL` (written by the main-thread session per PUBLISH MODE's opening note, not by `documentation-auditor` itself, once the Doc Post-Impl report has resolved clean) and no `PUBLISH` phase yet → **Publish Mode**. Otherwise → **Plan Mode** — this covers every fresh chain start, since Plan Mode is always the chain's entry point.
```

- [ ] **Step 3: Add an EXIT & DERAILMENT row**

In the `## EXIT & DERAILMENT HANDLING` table, add a row directly after the existing `Stale-detection fingerprint repeats...` row:

```markdown
| Lightweight Finish requested but no matching Lightweight Start context (missing `Worktree:`/`Branch:`/`Start:`) | Report it back rather than guessing — Lightweight Finish always needs those three fields passed in verbatim. |
```

- [ ] **Step 4: Validate**

Run: `claude plugin validate . --strict`
Expected: `✔ Validation passed`

- [ ] **Step 5: Commit**

```bash
git add agents/task-orchestrator.md
git commit -m "feat: add task-orchestrator Lightweight Start/Finish mode"
```

---

## Task 3: `software-engineer` Direct Mode worktree-awareness

**Files:**
- Modify: `agents/software-engineer.md`

**Interfaces:**
- Consumes: `Worktree:` field in opening context (from Task 2's Lightweight Start, relayed by the caller).

- [ ] **Step 1: Update Step 4 (Direct mode: load context)**

Replace the existing `### Step 4 — Direct mode: load context` body (`No STATE.md, no worktree. Read the opening context for the scoped bug-fix/decision request directly. Inspect the current branch/working tree state (git status, git diff if relevant) to understand what's already there before changing anything.`) with:

```markdown
No `STATE.md`. Read the opening context for the scoped bug-fix/decision request directly. If the opening context names a `Worktree:` path (the caller ran `task-orchestrator` Lightweight Start first), `cd` into it — same as Chain mode's Step 2. Otherwise, work directly against the current branch/working tree. Inspect branch/working-tree state (`git status`, `git diff` if relevant) to understand what's already there before changing anything.
```

- [ ] **Step 2: Update the Direct-mode hard requirement**

Replace `- Direct mode: NEVER create a branch, worktree, commit, or PR/MR — work stays on the current branch/working tree, uncommitted, for whoever's driving the session to handle next.` with:

```markdown
- Direct mode: NEVER create a branch, worktree, commit, or PR/MR itself — that's `task-orchestrator` Lightweight Start/Finish's job when one is in play (Step 4), never this agent's. Without a `Worktree:` field in context, work stays on the current branch/working tree, uncommitted, for whoever's driving the session to handle next — exactly as before this mode existed.
```

- [ ] **Step 3: Update the Direct-mode PHASE HANDOFF block**

Replace the existing Direct-mode `PHASE HANDOFF` block's context text (`Write tests against this fix (post-hoc, Direct mode) and confirm they pass. No commit or PR is created automatically — that's a separate decision for whoever's driving this session.`) with:

```markdown
Write tests against this fix (post-hoc, Direct mode) and confirm they
pass. [No worktree — no commit or PR is created automatically, that's a
separate decision for whoever's driving this session. | Working inside
<worktree> — once tests pass, invoke task-orchestrator Lightweight Finish
with Worktree: <path>, Branch: <branch>, Start: <timestamp> to commit and
open the PR/MR.]
```

(The bracketed line is the two alternative phrasings — pick whichever applies at handoff time, same convention the rest of this file already uses for conditional PHASE HANDOFF text, e.g. the `Flags` line's `[HARNESS FLAG: <note> | none]`.)

- [ ] **Step 4: Validate**

Run: `claude plugin validate . --strict`
Expected: `✔ Validation passed`

- [ ] **Step 5: Commit**

```bash
git add agents/software-engineer.md
git commit -m "feat: make software-engineer Direct Mode worktree-aware"
```

---

## Task 4: `qa-engineer` Direct Mode worktree-awareness + Lightweight Finish trigger

**Files:**
- Modify: `agents/qa-engineer.md`

**Interfaces:**
- Consumes: `Worktree:`/`Branch:`/`Start:` fields in opening context (relayed from `software-engineer`'s Direct-mode handoff, Task 3).
- Produces: invokes `task-orchestrator` Lightweight Finish (Task 2) when those fields are present.

- [ ] **Step 1: Read the current Direct-mode context-loading and terminal-handoff text**

`Read agents/qa-engineer.md` in full first — this task's exact anchor text depends on how Direct mode's context-loading step and its terminal PHASE HANDOFF are currently worded (both were touched by the earlier PR/MR usage-token feature's `HISTORY.md` timestamp edit, so re-read before assuming line numbers).

- [ ] **Step 2: Add worktree-awareness to Direct-mode context loading**

In whichever step Direct mode reads the opening request (the counterpart to `software-engineer`'s Step 4), add: if the opening context names a `Worktree:` path, `cd` into it before writing tests — same pattern as Task 3, Step 1.

- [ ] **Step 3: Make the terminal Direct-mode handoff conditional**

Where Direct mode's post-hoc-tests handoff currently ends the flow with no further step, add: if `Worktree:`/`Branch:`/`Start:` were present in context, once tests pass, its `PHASE HANDOFF` text names `task-orchestrator (Lightweight Finish)` next, carrying those three fields verbatim — pure instructional text for whoever's driving the session (same convention as every other chain handoff; `qa-engineer` never dispatches another agent itself). Without those fields, the handoff ends exactly as today.

- [ ] **Step 4: Validate**

Run: `claude plugin validate . --strict`
Expected: `✔ Validation passed`

- [ ] **Step 5: Commit**

```bash
git add agents/qa-engineer.md
git commit -m "feat: make qa-engineer Direct Mode worktree-aware, trigger Lightweight Finish"
```

---

## Task 5: `documentation-engineer` worktree-awareness + Lightweight Finish trigger

**Files:**
- Modify: `agents/documentation-engineer.md`

**Interfaces:**
- Consumes: `Worktree:`/`Branch:`/`Start:` fields in opening context.
- Produces: invokes `task-orchestrator` Lightweight Finish (Task 2) when those fields are present, from its own terminal `COMPLETION` (no `qa-engineer` step in doc-sync).

- [ ] **Step 1: Add worktree-awareness to Create/Update Step 1**

In `agents/documentation-engineer.md`, modify **Create Mode**'s `### Step 1 — Clarify scope (if needed)` and **Update Mode**'s `### Step 1 — Read the target file` to each open with: "If the opening context names a `Worktree:` path, `cd` into it before touching any file."

- [ ] **Step 2: Make `COMPLETION` conditionally trigger Lightweight Finish**

Replace the `## COMPLETION` block:

```markdown
## COMPLETION

```
Running → **🟢 documentation-engineer**

Result
  Status  → ✅ COMPLETE
  Mode    → Create | Update
  Created → [file path, or: none]
  Updated → [file path — section(s) changed, or: none]
```

Terminal — no PHASE HANDOFF.
```

with:

```markdown
## COMPLETION

```
Running → **🟢 documentation-engineer**

Result
  Status  → ✅ COMPLETE
  Mode    → Create | Update
  Created → [file path, or: none]
  Updated → [file path — section(s) changed, or: none]
  Worktree → [none | invoking task-orchestrator Lightweight Finish]
```

If `Worktree:`/`Branch:`/`Start:` were present in the opening context, add a `PHASE HANDOFF → task-orchestrator (Lightweight Finish)` block below the result, carrying those three fields verbatim — same "instructional text for whoever's driving the session" convention every other chain handoff already uses (`documentation-engineer` has no `Agent`/`Bash` in its `tools:` list, same as every other chain agent — it never dispatches another agent itself). Without those fields, terminal — no PHASE HANDOFF, exactly as before this mode existed.
```

- [ ] **Step 3: Validate**

Run: `claude plugin validate . --strict`
Expected: `✔ Validation passed`

- [ ] **Step 4: Commit**

```bash
git add agents/documentation-engineer.md
git commit -m "feat: make documentation-engineer worktree-aware, trigger Lightweight Finish"
```

---

## Task 6: Trigger-point documentation, `CLAUDE.md`, version bump

**Files:**
- Modify: `CLAUDE.md`
- Modify: `.claude-plugin/plugin.json`

**Interfaces:**
- None — documentation-only task, closes out the feature.

All three trigger points share one pattern, documented once and cross-referenced rather than repeated: **before any file is touched**, the invoking main-thread session asks via `AskUserQuestion` whether to run `task-orchestrator` Lightweight Start first (worktree + eventual PR/MR) or proceed exactly as today — suggested, never forced. If yes, Lightweight Start's `Worktree:`/`Branch:`/`Start:` fields are passed directly into the doing agent's opening context; if no, nothing about today's behavior changes.

- [ ] **Step 1: Document the shared pattern + Direct flow's trigger in `CLAUDE.md`**

In `CLAUDE.md`'s **Coding-chain sequence** section, in the **Direct flow** bullet (`- **Direct flow** (User Choice: proceed-directly, task type bug-fix/decision): software-engineer (Direct Mode...) → qa-engineer (Direct Mode...) → done. No task-orchestrator, no branch automation.`), append:

```markdown
Before dispatching `software-engineer`, the invoking main-thread session asks via `AskUserQuestion` whether to run `task-orchestrator` Lightweight Start first (worktree + eventual PR/MR, so this flow's usage lands somewhere) or work directly on the current branch as before — suggested, never forced, same pattern `task-orchestrator` (below) documents for its Lightweight mode. If yes, the `Worktree:`/`Branch:`/`Start:` fields Lightweight Start returns are relayed through `software-engineer` → `qa-engineer`; `qa-engineer`'s post-hoc-tests handoff then names `task-orchestrator` (Lightweight Finish) next once tests pass.
```

- [ ] **Step 2: Document the `task-orchestrator` entry in `CLAUDE.md`**

In the `task-orchestrator` (agents/) paragraph, append a sentence after the existing `Terminal (Publish).` note:

```markdown
Also runs a third, Chain-flow-independent **Lightweight mode** (Start/Finish) for Direct flow, `superpowers:brainstorming`'s bounded path, and `documentation-engineer` doc-sync work — same worktree-creation and PR-creation mechanics as Plan/Publish, without the task-folder/plan-file/feasibility/doc-gate/ticket-sync requirements those need. In every case, the ask (Lightweight Start or proceed as today) happens in the invoking main-thread session before the doing agent is dispatched at all — worktree isolation only works ahead of implementation, not retrofitted after. See `docs/.specs/2026-08-17-worktree-pr-lightweight-mode-design.md`.
```

- [ ] **Step 3: Document the `documentation-engineer` entry's new trigger**

In the `documentation-engineer` (agents/) paragraph, replace `Terminal, no skill loaded.` with:

```markdown
Terminal, no skill loaded. Before dispatching it, the invoking main-thread session may ask (same suggested-never-forced pattern as `task-orchestrator`'s Lightweight mode) whether to run Lightweight Start first; if so, the `Worktree:`/`Branch:`/`Start:` fields land directly in its opening context, and its own `COMPLETION` names `task-orchestrator` (Lightweight Finish) next as pure instructional text — this agent has no `Agent`/`Bash` tool to invoke anything itself.
```

- [ ] **Step 4: Document the bounded-path trigger**

In `CLAUDE.md`'s existing description of `spec-writing`/`plan-writing` (the paragraph beginning `**`spec-writing` and `plan-writing` (skills/)** — thin path-override wrappers...`), append one sentence:

```markdown
The same suggested-never-forced worktree+PR ask applies to `superpowers:brainstorming`'s bounded path (not a cairn file, so this is documented on the calling-session side only, the same way the `/cairn-setup` bypass-capture rule already governs a vendor skill's trigger without editing it): once the in-chat design is approved and before "Implement — proceed with the normal development workflow" begins, the invoking session asks whether to run `task-orchestrator` Lightweight Start first.
```

- [ ] **Step 5: Bump the plugin version**

In `.claude-plugin/plugin.json`, bump `"version"` from `"0.15.0"` to `"0.16.0"` (minor — new feature, per `CLAUDE.md`'s Versioning section).

- [ ] **Step 6: Validate**

Run: `claude plugin validate . --strict`
Expected: `✔ Validation passed`

Run: `pytest tests/test_usage_dashboard.py -v`
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md .claude-plugin/plugin.json
git commit -m "docs: document Lightweight worktree+PR/MR mode, bump to 0.16.0"
```

---

## Manual verification (not unit-testable — agent-definition files)

Per `CLAUDE.md`'s Testing section, run each affected path headless against a scratch directory:

```bash
cd /some/scratch/dir
git init   # if not already a repo
claude -p "Fix a small bug" --plugin-dir /path/to/cairn --permission-mode bypassPermissions --output-format text
```

Confirm: the worktree+PR ask fires before `software-engineer` Direct Mode starts; declining behaves exactly as today (no worktree, no PR); accepting produces a real worktree, a real branch named `direct/<slug>`, and — once `gh`/`glab` auth is available — a PR/MR whose body includes a usage table. Repeat for a bounded-path brainstorming request and a doc-sync request to `documentation-engineer`.
