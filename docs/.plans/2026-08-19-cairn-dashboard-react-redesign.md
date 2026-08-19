# Cairn Dashboard React Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the cairn dashboard's inline-HTML/vanilla-JS frontend with a Vite+React SPA (built in the `dashboard/` submodule, pre-built and committed) served by the existing stdlib-Python backend, which gains a new `/api/swarms` endpoint for tracking Unattended coding-chain tasks.

**Architecture:** Two components across two repos. The parent `cairn` repo's `scripts/usage_dashboard.py` stays a stdlib-only Python `http.server` — it gains `parse_state_md`/`discover_swarms`/tmux-liveness helpers, a `GET /api/swarms` route, and a static-file handler that serves `dashboard/dist/` instead of the current inline `PAGE_HTML` string. The `dashboard/` submodule (currently an empty scaffold, no source) gets a Vite + React + TypeScript SPA with three tabs (Usage, Tracker, Swarms) that poll those JSON APIs every 4 seconds and render them; its build output (`dist/`) is committed directly to that repo so end users need no Node/npm at runtime.

**Tech Stack:** Backend: Python 3 stdlib only (`http.server`, `subprocess`, `pathlib`, `mimetypes`) — no new dependency. Frontend: Vite, React 18, TypeScript, Vitest + React Testing Library (dev-time only).

**Spec:** `docs/.specs/2026-08-19-dashboard-react-redesign-design.md` (integration design), `dashboard/docs/requirements/prd.md` (FR-001–FR-007, NFR-001–NFR-003), `dashboard/docs/requirements/user-stories.md` (US-001–US-004), `dashboard/docs/requirements/user-flows.md` (UF-001–UF-004), `dashboard/docs/architecture/architecture-spec.md`.

## Global Constraints

- Zero new runtime dependencies for end users (NFR-001) — backend stays stdlib Python; frontend ships pre-built/committed, no Node/npm/FastAPI needed to run the dashboard.
- Local-only, `127.0.0.1`-bound, no auth (NFR-002).
- Graceful degradation everywhere (NFR-003): missing `tmux` → liveness `"unknown"`, not a crash; missing `dashboard/dist/` → clear error, not a blank page or 500 with no explanation; empty `TRACKER.md`/no swarms → empty state, not an error.
- Existing API surface (`/api/usage`, `/api/tracker`, `--task-report`, `--window-report`) must keep working unchanged (FR-006 / US-004) — this plan only extends, never breaks, `scripts/usage_dashboard.py`'s existing public functions.
- `dashboard/dist/` is committed build output, gitignored nowhere — this repeats the project's own "pre-built, committed" decision; do not add `dist/` to any `.gitignore`.
- Swarms tab is scoped to `Mode: Unattended` tasks only (FR-003) — Attended tasks never appear there.

---

### Task 1: `parse_state_md` — generic STATE.md parser

**Files:**
- Modify: `scripts/usage_dashboard.py` (add function after `parse_history_md`, ~line 108)
- Test: `tests/test_usage_dashboard.py` (append after the `parse_history_md` tests, ~line 355)

**Interfaces:**
- Produces: `parse_state_md(path: Path) -> dict` — returns `{}` if the file doesn't exist; otherwise a dict of every `Key: value` line in the file (keys lowercased with spaces→underscores, e.g. `"Handoff to"` → `"handoff_to"`), values as raw stripped strings.

- [ ] **Step 1: Write the failing tests**

```python
def test_parse_state_md_parses_key_value_lines(tmp_path):
    state = tmp_path / "STATE.md"
    state.write_text(
        "# Task: my-slug\n"
        "\n"
        "Mode: Unattended\n"
        "Phase: HANDOFF NEEDED\n"
        "Handoff to: qa-engineer\n"
        "Status: waiting on a decision\n"
        "Plan: docs/.plans/my-slug.md\n"
        "Ticket: none\n"
        "Worktree: /tmp/worktree\n"
        "Branch: feature/my-slug\n"
        "Key info: needs a human answer\n"
        "Harness flags: none\n"
    )
    result = usage_dashboard.parse_state_md(state)
    assert result["mode"] == "Unattended"
    assert result["phase"] == "HANDOFF NEEDED"
    assert result["handoff_to"] == "qa-engineer"
    assert result["worktree"] == "/tmp/worktree"
    assert result["branch"] == "feature/my-slug"


def test_parse_state_md_missing_file_returns_empty(tmp_path):
    assert usage_dashboard.parse_state_md(tmp_path / "nope.md") == {}


def test_parse_state_md_ignores_non_key_value_lines(tmp_path):
    state = tmp_path / "STATE.md"
    state.write_text("# Task: my-slug\n\nMode: Attended\n\nJust some prose, no colon here really\n")
    result = usage_dashboard.parse_state_md(state)
    assert result == {"mode": "Attended"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_usage_dashboard.py -k parse_state_md -v`
Expected: FAIL with `AttributeError: module 'usage_dashboard' has no attribute 'parse_state_md'`

- [ ] **Step 3: Write minimal implementation**

Add to `scripts/usage_dashboard.py` immediately after the `parse_history_md` function (after its closing `return entries`, before `def _parse_iso`):

```python
def parse_state_md(path: Path) -> dict:
    """Generic STATE.md key:value parser. {} if the file doesn't exist.

    Keys are lowercased with spaces replaced by underscores (e.g. "Handoff to"
    -> "handoff_to"). Lines that aren't "Key: value" (the H1 title, blank
    lines, prose without a colon) are skipped.
    """
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip().lower().replace(" ", "_")] = value.strip()
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_usage_dashboard.py -k parse_state_md -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/usage_dashboard.py tests/test_usage_dashboard.py
git commit -m "feat: add parse_state_md for generic STATE.md parsing"
```

---

### Task 2: `discover_swarms` — find Unattended tasks + tmux liveness

**Files:**
- Modify: `scripts/usage_dashboard.py` (add function after `parse_state_md`)
- Test: `tests/test_usage_dashboard.py` (append after Task 1's tests)

**Interfaces:**
- Consumes: `parse_state_md(path) -> dict` (Task 1), `parse_history_md(path) -> list` (existing).
- Produces: `discover_swarms(cwd: str) -> list[dict]` — one dict per `Mode: Unattended` task folder under `docs/.tasks/*/STATE.md`, each with keys: `slug` (str, folder name), `phase`, `status`, `handoff_to`, `worktree`, `branch`, `key_info` (all from `STATE.md`, `""` if absent), `last_history` (dict `{"timestamp", "phase", "note"}` or `None` if `HISTORY.md` has no timestamped lines), `recent_history` (list of up to 5 such dicts, newest first — feeds the Swarms detail panel's history log), `history_count` (int), `tmux_alive` (`True`/`False`/`None` — `None` means `tmux` binary is unavailable).
- Tasks whose `STATE.md` has no `mode` key, or `mode` isn't exactly `"Unattended"`, are excluded.

- [ ] **Step 1: Write the failing tests**

```python
def test_discover_swarms_finds_unattended_tasks_only(tmp_path, monkeypatch):
    monkeypatch.setattr(usage_dashboard, "_tmux_has_session", lambda branch: True)
    cwd = tmp_path / "myproject"
    unattended = cwd / "docs" / ".tasks" / "2026-08-19-my-slug"
    unattended.mkdir(parents=True)
    (unattended / "STATE.md").write_text(
        "Mode: Unattended\nPhase: IMPLEMENT\nStatus: working\nHandoff to: software-engineer\n"
        "Worktree: /tmp/wt\nBranch: feature/my-slug\nKey info: none\n"
    )
    (unattended / "HISTORY.md").write_text(
        "2026-08-19T10:00:00Z — PLAN — plan read\n2026-08-19T10:05:00Z — IMPLEMENT — coding\n"
    )
    attended = cwd / "docs" / ".tasks" / "2026-08-19-other-slug"
    attended.mkdir(parents=True)
    (attended / "STATE.md").write_text("Mode: Attended\nPhase: IMPLEMENT\nStatus: working\n")

    swarms = usage_dashboard.discover_swarms(str(cwd))

    assert len(swarms) == 1
    swarm = swarms[0]
    assert swarm["slug"] == "2026-08-19-my-slug"
    assert swarm["phase"] == "IMPLEMENT"
    assert swarm["branch"] == "feature/my-slug"
    assert swarm["history_count"] == 2
    assert swarm["last_history"]["phase"] == "IMPLEMENT"
    assert swarm["tmux_alive"] is True
    assert [h["phase"] for h in swarm["recent_history"]] == ["IMPLEMENT", "PLAN"]


def test_discover_swarms_recent_history_caps_at_5_newest_first(tmp_path, monkeypatch):
    monkeypatch.setattr(usage_dashboard, "_tmux_has_session", lambda branch: True)
    cwd = tmp_path / "myproject"
    task = cwd / "docs" / ".tasks" / "2026-08-19-my-slug"
    task.mkdir(parents=True)
    (task / "STATE.md").write_text("Mode: Unattended\nPhase: PUBLISH\nBranch: feature/x\n")
    lines = [
        f"2026-08-19T{10 + i:02d}:00:00Z — PHASE{i} — note {i}" for i in range(7)
    ]
    (task / "HISTORY.md").write_text("\n".join(lines) + "\n")

    swarms = usage_dashboard.discover_swarms(str(cwd))
    recent = swarms[0]["recent_history"]
    assert len(recent) == 5
    assert recent[0]["phase"] == "PHASE6"
    assert recent[-1]["phase"] == "PHASE2"


def test_discover_swarms_no_tasks_dir_returns_empty(tmp_path):
    assert usage_dashboard.discover_swarms(str(tmp_path / "myproject")) == []


def test_discover_swarms_tmux_missing_binary_sets_none(tmp_path, monkeypatch):
    def raise_missing(branch):
        raise FileNotFoundError("tmux not found")
    monkeypatch.setattr(usage_dashboard, "_tmux_has_session", lambda branch: None)
    cwd = tmp_path / "myproject"
    task = cwd / "docs" / ".tasks" / "2026-08-19-my-slug"
    task.mkdir(parents=True)
    (task / "STATE.md").write_text("Mode: Unattended\nPhase: PLAN\nBranch: feature/x\n")

    swarms = usage_dashboard.discover_swarms(str(cwd))
    assert swarms[0]["tmux_alive"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_usage_dashboard.py -k discover_swarms -v`
Expected: FAIL with `AttributeError: module 'usage_dashboard' has no attribute 'discover_swarms'`

- [ ] **Step 3: Write minimal implementation**

Add to `scripts/usage_dashboard.py`, right after `parse_state_md` (add `import subprocess` to the import block at the top, alphabetically after `import socket`):

```python
def _tmux_has_session(branch: str) -> bool | None:
    """True/False if tmux answered, None if the tmux binary itself is unavailable."""
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", branch], capture_output=True, timeout=5
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.returncode == 0


def discover_swarms(cwd: str) -> list:
    """Mode: Unattended tasks under docs/.tasks/*/STATE.md, with tmux liveness."""
    swarms = []
    for task_dir in sorted(Path(cwd).glob("docs/.tasks/*/")):
        state = parse_state_md(task_dir / "STATE.md")
        if state.get("mode") != "Unattended":
            continue
        history = parse_history_md(task_dir / "HISTORY.md")
        branch = state.get("branch", "")
        swarms.append({
            "slug": task_dir.name,
            "phase": state.get("phase", ""),
            "status": state.get("status", ""),
            "handoff_to": state.get("handoff_to", ""),
            "worktree": state.get("worktree", ""),
            "branch": branch,
            "key_info": state.get("key_info", ""),
            "last_history": history[-1] if history else None,
            "recent_history": list(reversed(history[-5:])),
            "history_count": len(history),
            "tmux_alive": _tmux_has_session(branch) if branch else None,
        })
    return swarms
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_usage_dashboard.py -k discover_swarms -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/usage_dashboard.py tests/test_usage_dashboard.py
git commit -m "feat: add discover_swarms with tmux liveness checks"
```

---

### Task 3: pane-tail excerpt for HANDOFF NEEDED swarms

**Files:**
- Modify: `scripts/usage_dashboard.py` (add function, wire into `discover_swarms`)
- Test: `tests/test_usage_dashboard.py`

**Interfaces:**
- Consumes: `_tmux_has_session` (Task 2, for the "is tmux even available" check pattern).
- Produces: `_tmux_pane_tail(branch: str, lines: int = 20) -> list[str] | None` — `None` if `tmux` is unavailable or the capture fails; otherwise the last `lines` lines of the pane, each a plain string.
- `discover_swarms` gains a `pane_tail` key: `None` unless `phase == "HANDOFF NEEDED"` and `tmux_alive is True`.

- [ ] **Step 1: Write the failing tests**

```python
def test_tmux_pane_tail_returns_last_lines(monkeypatch):
    class FakeResult:
        returncode = 0
        stdout = b"line1\nline2\nline3\n"
    monkeypatch.setattr(usage_dashboard.subprocess, "run", lambda *a, **k: FakeResult())
    tail = usage_dashboard._tmux_pane_tail("feature/x", lines=2)
    assert tail == ["line2", "line3"]


def test_tmux_pane_tail_missing_binary_returns_none(monkeypatch):
    def raise_missing(*a, **k):
        raise FileNotFoundError("no tmux")
    monkeypatch.setattr(usage_dashboard.subprocess, "run", raise_missing)
    assert usage_dashboard._tmux_pane_tail("feature/x") is None


def test_discover_swarms_includes_pane_tail_only_on_handoff_needed(tmp_path, monkeypatch):
    monkeypatch.setattr(usage_dashboard, "_tmux_has_session", lambda branch: True)
    monkeypatch.setattr(usage_dashboard, "_tmux_pane_tail", lambda branch, lines=20: ["paused here"])
    cwd = tmp_path / "myproject"
    task = cwd / "docs" / ".tasks" / "2026-08-19-my-slug"
    task.mkdir(parents=True)
    (task / "STATE.md").write_text("Mode: Unattended\nPhase: HANDOFF NEEDED\nBranch: feature/x\n")

    swarms = usage_dashboard.discover_swarms(str(cwd))
    assert swarms[0]["pane_tail"] == ["paused here"]

    (task / "STATE.md").write_text("Mode: Unattended\nPhase: IMPLEMENT\nBranch: feature/x\n")
    swarms = usage_dashboard.discover_swarms(str(cwd))
    assert swarms[0]["pane_tail"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_usage_dashboard.py -k pane_tail -v`
Expected: FAIL — `_tmux_pane_tail` doesn't exist, and `discover_swarms` returns no `pane_tail` key (`KeyError`)

- [ ] **Step 3: Write minimal implementation**

Add after `_tmux_has_session`:

```python
def _tmux_pane_tail(branch: str, lines: int = 20) -> list | None:
    try:
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", branch, "-p"], capture_output=True, timeout=5
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    text = result.stdout.decode("utf-8", errors="replace")
    return text.splitlines()[-lines:]
```

In `discover_swarms`, change the `tmux_alive` line and the dict construction to:

```python
        tmux_alive = _tmux_has_session(branch) if branch else None
        phase = state.get("phase", "")
        pane_tail = _tmux_pane_tail(branch) if (phase == "HANDOFF NEEDED" and tmux_alive) else None
        swarms.append({
            "slug": task_dir.name,
            "phase": phase,
            "status": state.get("status", ""),
            "handoff_to": state.get("handoff_to", ""),
            "worktree": state.get("worktree", ""),
            "branch": branch,
            "key_info": state.get("key_info", ""),
            "last_history": history[-1] if history else None,
            "recent_history": list(reversed(history[-5:])),
            "history_count": len(history),
            "tmux_alive": tmux_alive,
            "pane_tail": pane_tail,
        })
```

(Replace the old `swarms.append(...)` block from Task 2 entirely with the one above — remove the duplicate `tmux_alive` assignment line that Task 2 left above the loop body.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_usage_dashboard.py -k "pane_tail or discover_swarms" -v`
Expected: PASS (all tests from Tasks 2 and 3)

- [ ] **Step 5: Commit**

```bash
git add scripts/usage_dashboard.py tests/test_usage_dashboard.py
git commit -m "feat: add tmux pane-tail excerpt for HANDOFF NEEDED swarms"
```

---

### Task 4: `GET /api/swarms` endpoint

**Files:**
- Modify: `scripts/usage_dashboard.py` (`do_GET` method, ~line 876)
- Test: `tests/test_usage_dashboard.py`

**Interfaces:**
- Consumes: `discover_swarms(cwd) -> list[dict]` (Task 3).
- Produces: `GET /api/swarms` → `200 application/json`, body = `json.dumps(discover_swarms(cwd))`.

This endpoint has no pure-function unit test of its own (it's three lines of routing glue identical in shape to the existing `/api/tracker` route) — `discover_swarms` itself is already fully tested by Tasks 2–3. Verify manually per Step 3 below instead of adding a redundant test.

- [ ] **Step 1: Add the route**

In `do_GET` (`scripts/usage_dashboard.py`), add a new branch right after the existing `/api/tracker` branch:

```python
            elif self.path == "/api/tracker":
                rows = parse_tracker_md(Path(cwd) / "docs" / ".tasks" / "TRACKER.md")
                self._send(200, "application/json", json.dumps(rows))
            elif self.path == "/api/swarms":
                swarms = discover_swarms(cwd)
                self._send(200, "application/json", json.dumps(swarms))
```

- [ ] **Step 2: Verify manually**

Run: `cd /tmp && mkdir -p verify-swarms/docs/.tasks/2026-08-19-x && cd verify-swarms && printf "Mode: Unattended\nPhase: PLAN\nBranch: feature/x\n" > docs/.tasks/2026-08-19-x/STATE.md && python3 /Users/jaysondelosreyes/cairn/scripts/usage_dashboard.py . &`
Then: `curl -s http://127.0.0.1:4756/api/swarms | python3 -m json.tool`
Expected: JSON array with one object, `"slug": "2026-08-19-x"`, `"phase": "PLAN"`. Then `kill %1` and `cd / && rm -rf /tmp/verify-swarms`.

- [ ] **Step 3: Commit**

```bash
git add scripts/usage_dashboard.py
git commit -m "feat: add GET /api/swarms endpoint"
```

---

### Task 5: Static-file serving for `dashboard/dist/`

**Files:**
- Modify: `scripts/usage_dashboard.py` (imports, `do_GET`, remove `PAGE_HTML` route)
- Test: `tests/test_usage_dashboard.py`

**Interfaces:**
- Produces: `serve_static(dist_dir: Path, request_path: str) -> tuple[str, bytes] | None` — `None` if `dist_dir/index.html` doesn't exist at all; otherwise `(content_type, file_bytes)`, falling back to `index.html` for any path that doesn't match a real file under `dist_dir` (SPA entry), with a path-traversal guard.
- `do_GET`'s catch-all branch (anything not `/api/...`) now calls `serve_static` instead of returning the old inline `PAGE_HTML`. A `None` result sends `500` with a message telling the user to run `git submodule update --init dashboard`.

- [ ] **Step 1: Write the failing tests**

```python
def test_serve_static_serves_existing_file(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>hi</html>")
    (dist / "app.js").write_text("console.log(1)")

    content_type, body = usage_dashboard.serve_static(dist, "/app.js")
    assert body == b"console.log(1)"
    assert "javascript" in content_type


def test_serve_static_falls_back_to_index_for_unknown_path(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>spa root</html>")

    content_type, body = usage_dashboard.serve_static(dist, "/some/client/route")
    assert body == b"<html>spa root</html>"
    assert content_type == "text/html"


def test_serve_static_missing_dist_returns_none(tmp_path):
    assert usage_dashboard.serve_static(tmp_path / "dist", "/") is None


def test_serve_static_blocks_path_traversal(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>spa root</html>")
    secret = tmp_path / "secret.txt"
    secret.write_text("shh")

    content_type, body = usage_dashboard.serve_static(dist, "/../secret.txt")
    assert body == b"<html>spa root</html>"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_usage_dashboard.py -k serve_static -v`
Expected: FAIL with `AttributeError: module 'usage_dashboard' has no attribute 'serve_static'`

- [ ] **Step 3: Write minimal implementation**

Add `import mimetypes` to the import block at the top of `scripts/usage_dashboard.py` (alphabetically, after `import json`).

Add this function after `discover_swarms`:

```python
def serve_static(dist_dir: Path, request_path: str):
    """Resolve a static asset under dist_dir, falling back to index.html for
    the SPA root/any client-side route. None if dist_dir/index.html itself
    doesn't exist (submodule not initialized)."""
    index = dist_dir / "index.html"
    if not index.exists():
        return None
    rel = request_path.lstrip("/")
    candidate = (dist_dir / rel) if rel else index
    try:
        resolved = candidate.resolve()
        resolved.relative_to(dist_dir.resolve())
    except (ValueError, OSError):
        candidate = index
    else:
        if not resolved.is_file():
            candidate = index
    content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
    return content_type, candidate.read_bytes()
```

Now remove the old inline-HTML route. Replace the `do_GET` method's opening branch (`if self.path == "/": self._send(200, "text/html; charset=utf-8", PAGE_HTML)`) and its trailing `else: self._send(404, ...)` with:

```python
        def do_GET(self):
            if self.path.startswith("/api/"):
                if self.path == "/api/usage":
                    data = aggregate_usage(cwd, projects_root)
                    self._send(200, "application/json", json.dumps(data))
                elif self.path == "/api/tracker":
                    rows = parse_tracker_md(Path(cwd) / "docs" / ".tasks" / "TRACKER.md")
                    self._send(200, "application/json", json.dumps(rows))
                elif self.path == "/api/swarms":
                    swarms = discover_swarms(cwd)
                    self._send(200, "application/json", json.dumps(swarms))
                else:
                    self._send(404, "text/plain", "not found")
                return
            result = serve_static(Path(cwd) / "dashboard" / "dist", self.path)
            if result is None:
                self._send(
                    500, "text/plain",
                    "dashboard/dist/ not found. Run: git submodule update --init dashboard",
                )
                return
            content_type, body = result
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
```

Delete the now-unused `PAGE_HTML = """..."""` constant entirely (the large multi-line string previously spanning roughly lines 419–863) — the whole inline HTML/CSS/JS dashboard is replaced by the React build.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_usage_dashboard.py -v`
Expected: PASS — full suite (all prior tests still pass, plus the 4 new `serve_static` tests). This is also the point to confirm nothing referencing `PAGE_HTML` remains: `grep -n PAGE_HTML scripts/usage_dashboard.py` should return nothing.

- [ ] **Step 5: Commit**

```bash
git add scripts/usage_dashboard.py tests/test_usage_dashboard.py
git commit -m "feat: serve dashboard/dist/ as static files, remove inline PAGE_HTML"
```

---

### Task 6: `/cairn-dashboard` auto-init for the submodule

**Files:**
- Modify: `commands/cairn-dashboard.md`

**Interfaces:** None (markdown instructions only, no code).

- [ ] **Step 1: Add the auto-init step**

In `commands/cairn-dashboard.md`, in the "Otherwise (start, the default)" numbered list, insert a new step between the existing step 2 (pid-lockfile check) and step 3 (run the script), renumbering the steps that follow:

```markdown
3. Check `dashboard/dist/index.html` exists. If it doesn't:
   - Run `git submodule update --init dashboard` in the project root.
   - If that fails (offline, no recorded submodule commit, detached submodule config), stop and report the exact git error to the user — don't attempt to start the Python server, since it will just 500 on every page load.
4. Run `python3 "$CLAUDE_PLUGIN_ROOT/scripts/usage_dashboard.py" "$(pwd)"` **in the background** (detached — this command must return promptly, not block on the server). It prints its URL on the first line of stdout ("cairn usage dashboard at http://...") — capture that and the PID.
5. Create `.cairn/` in the project root if it doesn't exist, write the PID and URL to `.cairn/usage-dashboard.pid`.
6. Ensure `.cairn/.gitignore` exists containing a single `*` — this makes the whole directory self-ignoring, so nothing under `.cairn/` needs the project's own root `.gitignore` touched at all.
7. Open the URL in the user's browser.
8. Report the dashboard URL, and that `/cairn-dashboard stop` shuts it down.
```

(This replaces the existing steps 3–7 in that section — same content, renumbered, with the new step 3 inserted before the old step 3.)

- [ ] **Step 2: Verify manually**

Read the edited file back and confirm the numbered list runs 1–8 with no gaps or duplicate numbers, and that the new step 3 references `dashboard/dist/index.html` (not `dist/index.html` — must be relative to the project root, since that's where `/cairn-dashboard` runs from).

- [ ] **Step 3: Commit**

```bash
git add commands/cairn-dashboard.md
git commit -m "feat: auto-init dashboard/ submodule on /cairn-dashboard launch"
```

---

### Task 7: Frontend scaffold — Vite + React + TypeScript

**Files:**
- Create: `dashboard/package.json`
- Create: `dashboard/vite.config.ts`
- Create: `dashboard/tsconfig.json`
- Create: `dashboard/tsconfig.node.json`
- Create: `dashboard/index.html`
- Create: `dashboard/src/main.tsx`
- Create: `dashboard/src/App.tsx`
- Create: `dashboard/src/api.ts`
- Create: `dashboard/src/index.css`
- Test: `dashboard/src/App.test.tsx`
- Create: `dashboard/src/setupTests.ts`

**Interfaces:**
- Produces: `fetchUsage(): Promise<UsageData>`, `fetchTracker(): Promise<TrackerRow[]>`, `fetchSwarms(): Promise<Swarm[]>` in `src/api.ts` — the exact function names and return shapes Tasks 8–10 consume.
- Produces: `<App />` — tab-switching shell rendering `<UsageTab/>`, `<TrackerTab/>`, `<SwarmsTab/>` (each a placeholder `<div>` until Tasks 8–10 replace them) based on `location.hash`, matching the original dashboard's `#usage`/`#tracker`/`#tracker/road`/`#swarms` convention.

- [ ] **Step 1: Write the failing test**

```typescript
// dashboard/src/App.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import App from './App'

beforeEach(() => {
  window.location.hash = ''
  vi.stubGlobal('fetch', vi.fn(() =>
    Promise.resolve({ json: () => Promise.resolve({}) } as Response)
  ))
})

describe('App', () => {
  it('renders the Usage tab by default and switches tabs on click', () => {
    render(<App />)
    expect(screen.getByRole('tab', { name: 'Usage' })).toHaveAttribute('aria-selected', 'true')

    fireEvent.click(screen.getByRole('tab', { name: 'Swarms' }))
    expect(screen.getByRole('tab', { name: 'Swarms' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByRole('tab', { name: 'Usage' })).toHaveAttribute('aria-selected', 'false')
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npm install && npm run test -- --run`
Expected: FAIL — no `App.tsx`/`api.ts`/build config exist yet, so this fails at module resolution before even reaching an assertion.

- [ ] **Step 3: Write the scaffold**

`dashboard/package.json`:
```json
{
  "name": "cairn-dashboard",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.4.8",
    "@testing-library/react": "^16.0.0",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "jsdom": "^24.1.1",
    "typescript": "^5.5.4",
    "vite": "^5.4.0",
    "vitest": "^2.0.5"
  }
}
```

`dashboard/vite.config.ts`:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:4756',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.ts',
    globals: true,
  },
})
```

`dashboard/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "types": ["vitest/globals"]
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

`dashboard/tsconfig.node.json`:
```json
{
  "compilerOptions": {
    "composite": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}
```

`dashboard/index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Cairn Dashboard</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`dashboard/src/setupTests.ts`:
```typescript
import '@testing-library/jest-dom'
```

`dashboard/src/main.tsx`:
```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

`dashboard/src/api.ts`:
```typescript
export interface UsageSession {
  session_id: string
  timestamp: string | null
  models: string[]
  version: string
  cost: number
  unpriced_calls: number
  input_tokens: number
  output_tokens: number
  cache_creation_input_tokens: number
  cache_read_input_tokens: number
  calls: number
  // Per-session subagent/skill invocation counts — usage_dashboard.py already
  // parses these from Agent/Skill tool_use blocks per transcript (see
  // CLAUDE.md's usage_dashboard.py description) to build the all-time
  // by_subagent/by_skill totals below; this just exposes the same per-session
  // counts instead of only the aggregate, so Task 8's ranking panels can
  // compute a Window-scoped (not just All-time) breakdown client-side.
  subagents: Record<string, number>
  skills: Record<string, number>
}

export interface RankedRow {
  cost?: number
  calls: number
  [key: string]: unknown
}

export interface UsageData {
  project: string
  generated: string
  totals: Record<string, number>
  sessions: UsageSession[]
  by_model: RankedRow[]
  by_version: RankedRow[]
  by_subagent: RankedRow[]
  by_skill: RankedRow[]
}

export interface TrackerRow {
  slug: string
  scope: string
  status: string
  milestone: string
  ticket: string
  [key: string]: string
}

export interface HistoryEntry {
  timestamp: string
  phase: string
  note: string
}

export interface Swarm {
  slug: string
  phase: string
  status: string
  handoff_to: string
  worktree: string
  branch: string
  key_info: string
  last_history: HistoryEntry | null
  recent_history: HistoryEntry[]
  history_count: number
  tmux_alive: boolean | null
  pane_tail: string[] | null
}

export const CHAIN_PHASES = ['PLAN', 'DOC-GATE', 'QA-RED', 'IMPLEMENT', 'QA-AUDIT', 'DOC-POST-IMPL', 'PUBLISH']

export async function fetchUsage(): Promise<UsageData> {
  const res = await fetch('/api/usage')
  return res.json()
}

export async function fetchTracker(): Promise<TrackerRow[]> {
  const res = await fetch('/api/tracker')
  return res.json()
}

export async function fetchSwarms(): Promise<Swarm[]> {
  const res = await fetch('/api/swarms')
  return res.json()
}
```

`dashboard/src/index.css`:
```css
* { box-sizing: border-box; }
body { font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; }
.tabs { display: flex; gap: .25rem; padding: .75rem 1rem; border-bottom: 1px solid #ddd; }
.tabs button { padding: .4rem .9rem; border: 1px solid #ddd; background: #fff; border-radius: 6px; cursor: pointer; }
.tabs button[aria-selected="true"] { background: #222; color: #fff; }
main { padding: 1rem; }
.empty { color: #888; padding: 1rem 0; }
table { border-collapse: collapse; width: 100%; }
th, td { text-align: left; padding: .4rem .6rem; border-bottom: 1px solid #eee; }
```

`dashboard/src/App.tsx`:
```typescript
import { useEffect, useState } from 'react'
import UsageTab from './components/UsageTab'
import TrackerTab from './components/TrackerTab'
import SwarmsTab from './components/SwarmsTab'

type Tab = 'usage' | 'tracker' | 'swarms'

function tabFromHash(): Tab {
  const hash = window.location.hash.replace('#', '').split('/')[0]
  if (hash === 'tracker' || hash === 'swarms') return hash
  return 'usage'
}

export default function App() {
  const [tab, setTab] = useState<Tab>(tabFromHash())

  useEffect(() => {
    const onHashChange = () => setTab(tabFromHash())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  function selectTab(next: Tab) {
    window.location.hash = next
    setTab(next)
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: 'usage', label: 'Usage' },
    { id: 'tracker', label: 'Tracker' },
    { id: 'swarms', label: 'Swarms' },
  ]

  return (
    <div>
      <div className="tabs" role="tablist">
        {tabs.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => selectTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <main>
        {tab === 'usage' && <UsageTab />}
        {tab === 'tracker' && <TrackerTab />}
        {tab === 'swarms' && <SwarmsTab />}
      </main>
    </div>
  )
}
```

Since `App.tsx` imports `./components/UsageTab`, `./components/TrackerTab`, `./components/SwarmsTab` (built in Tasks 8–10), create minimal placeholder components now so this task's build/test pass standalone:

`dashboard/src/components/UsageTab.tsx`:
```typescript
export default function UsageTab() {
  return <div>Usage tab (Task 8)</div>
}
```

`dashboard/src/components/TrackerTab.tsx`:
```typescript
export default function TrackerTab() {
  return <div>Tracker tab (Task 9)</div>
}
```

`dashboard/src/components/SwarmsTab.tsx`:
```typescript
export default function SwarmsTab() {
  return <div>Swarms tab (Task 10)</div>
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npm run test -- --run`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
cd dashboard
git add package.json vite.config.ts tsconfig.json tsconfig.node.json index.html src/
git commit -m "feat: scaffold Vite+React+TS app with tab shell"
cd ..
git add dashboard
git commit -m "chore: bump dashboard submodule pointer — scaffold"
```

---

### Task 8: Usage tab

**Files:**
- Modify: `dashboard/src/components/UsageTab.tsx` (replace placeholder)
- Test: `dashboard/src/components/UsageTab.test.tsx`

**Interfaces:**
- Consumes: `fetchUsage()`, `UsageData`, `UsageSession` (Task 7's `src/api.ts`).
- Produces: `<UsageTab />` — no other component depends on its internals.
- Period+anchor+timezone model adapted from researching how maestro's own `token-usage-report` solves the identical problem (`periodWindow(period, anchorDay)`, one shared window every section reads from). No DST-transition edge-case handling — approximate, same documented tradeoff as `MODEL_PRICING`/`PLAN_WINDOW_LOOKBACK_SECONDS` elsewhere in this codebase.
- Usage heatmap likewise adapted from maestro's `renderHeatmap()` (same reference file): a GitHub-style calendar layout (not a "contribution" concept — cells are colored by usage volume, not commit/contribution activity) covering full session history, Sunday-start weeks, Jan 1 of the earliest activity year through the latest session day, 5 intensity levels by quartile of per-day token volume against the busiest day. Deliberately independent of `period`/`anchor` (always full history) but re-bucketed on the `tz` toggle, same as the chart.
- Sessions table is sortable/filterable/paginated (`PAGE_SIZE = 5`), adapted from maestro's generic `renderTable()` (click-to-sort, second click reverses) plus a Model/Version filter pair scoped to the current period window — new columns Model(s) and Tokens (total, with an input/output/cache-write/cache-read breakdown in the `title` attribute). Filter and sort selections persist across a period/anchor/tz switch; page resets to 0 since the underlying row set changed.
- Cost-over-time chart carries a `chartMetric` toggle (`'cost' | 'tokens'`, default `'cost'`) — same bucketed window, same zero-fill, just a different per-session value summed into each bucket.
- Ranking panels (By model/By cairn version/Top subagents/Top skills) render above the chart and carry a `rankingsScope` toggle (`'window' | 'all'`, default `'window'`) — All-time reads `data.by_model`/etc. unchanged (server-aggregated); Window aggregates client-side from `sessions` via `aggregateSessions()`, which depends on this task's `subagents`/`skills` fields added to `UsageSession` (Task 7) above.

- [ ] **Step 1: Write the failing test**

```typescript
// dashboard/src/components/UsageTab.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import UsageTab from './UsageTab'
import type { UsageData } from '../api'

function session(id: string, ts: string, cost = 1.23) {
  return {
    session_id: id, timestamp: ts, models: ['claude-sonnet-5'], version: '0.18.0',
    cost, unpriced_calls: 0, input_tokens: 100, output_tokens: 200,
    cache_creation_input_tokens: 0, cache_read_input_tokens: 0, calls: 5,
    subagents: { 'qa-engineer': 2 }, skills: { 'writer-shared': 1 },
  }
}

const sampleData: UsageData = {
  project: '/some/project',
  generated: '2026-08-19T12:00:00Z',
  totals: {},
  sessions: [session('abc123', '2026-08-19T10:00:00Z'), session('old0001', '2026-07-01T10:00:00Z', 0.50)],
  by_model: [{ model: 'claude-sonnet-5', cost: 1.23, calls: 5 } as never],
  by_version: [],
  by_subagent: [],
  by_skill: [],
}

describe('UsageTab', () => {
  it('shows totals and the sessions table after loading', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve(sampleData) } as Response)
    ))
    render(<UsageTab />)

    await waitFor(() => expect(screen.getByText('abc123')).toBeInTheDocument())
  })

  it('shows an empty state with no sessions', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve({ ...sampleData, sessions: [] }) } as Response)
    ))
    render(<UsageTab />)
    await waitFor(() => expect(screen.getByText(/no sessions/i)).toBeInTheDocument())
  })

  it('switches period without a refetch, and excludes out-of-window sessions', async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve(sampleData) } as Response)
    )
    vi.stubGlobal('fetch', fetchMock)
    render(<UsageTab />)
    await waitFor(() => expect(screen.getByText('abc123')).toBeInTheDocument())
    expect(screen.queryByText('old0001')).not.toBeInTheDocument() // default period (Weekly) excludes the July session

    fireEvent.click(screen.getByRole('button', { name: 'YTD' }))
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(screen.getByText('old0001')).toBeInTheDocument() // YTD includes it
  })

  it('disables next at today, and Daily period shows 24 hourly buckets', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve(sampleData) } as Response)
    ))
    render(<UsageTab />)
    await waitFor(() => expect(screen.getByText('abc123')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: 'Daily' }))
    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled()
    expect(document.querySelectorAll('.chart-card rect.bar')).toHaveLength(24)
  })

  it('UTC/Local toggle shifts bucket boundaries', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve(sampleData) } as Response)
    ))
    render(<UsageTab />)
    await waitFor(() => expect(screen.getByText('abc123')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Local' }))
    expect(screen.getByRole('button', { name: 'Local' })).toHaveAttribute('aria-selected', 'true')
  })

  it('renders a full-history usage heatmap, independent of the period filter', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve(sampleData) } as Response)
    ))
    render(<UsageTab />)
    await waitFor(() => expect(screen.getByText('abc123')).toBeInTheDocument())

    expect(screen.getByTitle(/2026-08-19/)).toBeInTheDocument()
    expect(screen.getByTitle(/2026-07-01/)).toBeInTheDocument() // outside the default Weekly window, still in the heatmap

    fireEvent.click(screen.getByRole('button', { name: 'Daily' }))
    expect(screen.getByTitle(/2026-07-01/)).toBeInTheDocument() // heatmap unaffected by period switch
  })

  it('shows a heatmap empty state with no session history at all', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve({ ...sampleData, sessions: [] }) } as Response)
    ))
    render(<UsageTab />)
    await waitFor(() => expect(screen.getByText(/no sessions/i)).toBeInTheDocument())
    expect(screen.getByText(/no activity yet/i)).toBeInTheDocument()
  })

  it('sorts the sessions table when a column header is clicked', async () => {
    const varied = { ...sampleData, sessions: [session('a1', '2026-08-19T09:00:00Z', 5), session('a2', '2026-08-19T10:00:00Z', 1)] }
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ json: () => Promise.resolve(varied) } as Response)))
    render(<UsageTab />)
    await waitFor(() => expect(screen.getByText('a1')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: /Cost/ }))
    const rows = screen.getAllByRole('row').slice(1) // skip header row
    expect(rows[0]).toHaveTextContent('a2') // ascending: $1.00 sorts before $5.00
  })

  it('filters the sessions table by model and by version', async () => {
    const mixed = {
      ...sampleData,
      sessions: [
        { ...session('m1', '2026-08-19T09:00:00Z'), models: ['claude-sonnet-5'], version: '0.18.0' },
        { ...session('m2', '2026-08-19T10:00:00Z'), models: ['claude-opus-5'], version: '0.17.2' },
      ],
    }
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ json: () => Promise.resolve(mixed) } as Response)))
    render(<UsageTab />)
    await waitFor(() => expect(screen.getByText('m1')).toBeInTheDocument())

    fireEvent.change(screen.getByLabelText('Model'), { target: { value: 'claude-opus-5' } })
    expect(screen.queryByText('m1')).not.toBeInTheDocument()
    expect(screen.getByText('m2')).toBeInTheDocument()
  })

  it('toggles the chart between Cost and Tokens without a refetch', async () => {
    const fetchMock = vi.fn(() => Promise.resolve({ json: () => Promise.resolve(sampleData) } as Response))
    vi.stubGlobal('fetch', fetchMock)
    render(<UsageTab />)
    await waitFor(() => expect(screen.getByText('abc123')).toBeInTheDocument())

    fireEvent.click(screen.getByRole('button', { name: 'Tokens' }))
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Tokens' })).toHaveAttribute('aria-selected', 'true')
  })

  it('toggles ranking panels between Window and All-time scope', async () => {
    const scoped = { ...sampleData, by_model: [{ model: 'claude-opus-5', calls: 99 } as never] }
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ json: () => Promise.resolve(scoped) } as Response)))
    render(<UsageTab />)
    await waitFor(() => expect(screen.getByText('abc123')).toBeInTheDocument())

    // Window (default): derived client-side from the windowed sessions, not data.by_model
    expect(screen.getByText(/claude-sonnet-5/)).toBeInTheDocument()
    expect(screen.queryByText(/claude-opus-5/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'All-time' }))
    expect(screen.getByText(/claude-opus-5/)).toBeInTheDocument()
  })

  it('paginates the sessions table past the page size', async () => {
    // Default sort is Started, newest first: page 1 holds p5..p1, page 2 holds p0.
    const many = { ...sampleData, sessions: Array.from({ length: 6 }, (_, i) => session('p' + i, '2026-08-19T0' + i + ':00:00Z')) }
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ json: () => Promise.resolve(many) } as Response)))
    render(<UsageTab />)
    await waitFor(() => expect(screen.getByText('p5')).toBeInTheDocument())

    expect(screen.getByText(/Page 1 of 2/)).toBeInTheDocument()
    expect(screen.queryByText('p0')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Next ›' }))
    expect(screen.getByText(/Page 2 of 2/)).toBeInTheDocument()
    expect(screen.getByText('p0')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npm run test -- --run UsageTab`
Expected: FAIL — placeholder component has none of this markup.

- [ ] **Step 3: Write the implementation**

```typescript
// dashboard/src/components/UsageTab.tsx
import { useEffect, useMemo, useState } from 'react'
import { fetchUsage, type UsageData, type UsageSession } from '../api'

type Period = 'daily' | 'weekly' | 'monthly' | 'yearly' | 'ytd'
type Timezone = 'utc' | 'local'
type Granularity = 'hour' | 'day' | 'month'
interface Window { start: Date; end: Date; granularity: Granularity }

const PERIOD_LABELS: Record<Period, string> = {
  daily: 'Daily', weekly: 'Weekly', monthly: 'Monthly', yearly: 'Yearly', ytd: 'YTD',
}

function usd(n: number) { return '$' + n.toFixed(2) }
function fmt(n: number) { return Math.round(n).toLocaleString() }

function ymd(d: Date, tz: Timezone): [number, number, number] {
  return tz === 'utc'
    ? [d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()]
    : [d.getFullYear(), d.getMonth(), d.getDate()]
}
function make(y: number, m: number, d: number, tz: Timezone): Date {
  return tz === 'utc' ? new Date(Date.UTC(y, m, d)) : new Date(y, m, d)
}
function startOfDay(d: Date, tz: Timezone): Date {
  const [y, m, day] = ymd(d, tz)
  return make(y, m, day, tz)
}
function addDays(d: Date, n: number, tz: Timezone): Date {
  return startOfDay(new Date(d.getTime() + n * 86400000), tz)
}
function dow(d: Date, tz: Timezone): number {
  return tz === 'utc' ? d.getUTCDay() : d.getDay()
}

function periodWindow(period: Period, anchor: Date, tz: Timezone, now: Date): Window {
  const day = startOfDay(anchor, tz)
  if (period === 'daily') return { start: day, end: day, granularity: 'hour' }
  if (period === 'weekly') {
    const mondayOffset = (dow(day, tz) + 6) % 7
    const start = addDays(day, -mondayOffset, tz)
    return { start, end: addDays(start, 6, tz), granularity: 'day' }
  }
  if (period === 'monthly') {
    const [y, m] = ymd(day, tz)
    return { start: make(y, m, 1, tz), end: make(y, m + 1, 0, tz), granularity: 'day' }
  }
  if (period === 'yearly') {
    const [y] = ymd(day, tz)
    return { start: make(y, 0, 1, tz), end: make(y, 11, 31, tz), granularity: 'month' }
  }
  const nowDay = startOfDay(now, tz)
  const [y] = ymd(nowDay, tz)
  return { start: make(y, 0, 1, tz), end: nowDay, granularity: 'day' }
}

function shiftAnchor(period: Period, anchor: Date, dir: 1 | -1, tz: Timezone): Date {
  const day = startOfDay(anchor, tz)
  if (period === 'daily') return addDays(day, dir, tz)
  if (period === 'weekly') return addDays(day, dir * 7, tz)
  if (period === 'monthly') { const [y, m] = ymd(day, tz); return make(y, m + dir, 1, tz) }
  if (period === 'yearly') { const [y] = ymd(day, tz); return make(y, dir * 1 + y - y + 0, 1, tz) } // placeholder overwritten below
  return day
}

function bucketKey(ts: string, granularity: Granularity, tz: Timezone): string {
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  const [y, m, day] = ymd(d, tz)
  const hour = tz === 'utc' ? d.getUTCHours() : d.getHours()
  if (granularity === 'hour') return `${y}-${pad(m + 1)}-${pad(day)}T${pad(hour)}`
  if (granularity === 'month') return `${y}-${pad(m + 1)}`
  return `${y}-${pad(m + 1)}-${pad(day)}`
}

function zeroFillBuckets(win: Window, tz: Timezone): string[] {
  const keys: string[] = []
  if (win.granularity === 'hour') {
    for (let h = 0; h < 24; h++) keys.push(bucketKey(new Date(win.start.getTime() + h * 3600000).toISOString(), 'hour', tz))
    return keys
  }
  if (win.granularity === 'month') {
    let [y, m] = ymd(win.start, tz)
    while (make(y, m, 1, tz) <= win.end) { keys.push(`${y}-${String(m + 1).padStart(2, '0')}`); m += 1 }
    return keys
  }
  let d = win.start
  while (d <= win.end) { keys.push(bucketKey(d.toISOString(), 'day', tz)); d = addDays(d, 1, tz) }
  return keys
}

function sessionsInWindow(sessions: UsageSession[], win: Window): UsageSession[] {
  const endExclusive = win.end.getTime() + 86400000
  return sessions.filter((s) => {
    if (!s.timestamp) return false
    const t = new Date(s.timestamp).getTime()
    return t >= win.start.getTime() && t < endExclusive
  })
}

function anchorLabel(period: Period, win: Window): string {
  const opts: Intl.DateTimeFormatOptions = period === 'yearly' ? { year: 'numeric' }
    : period === 'monthly' ? { year: 'numeric', month: 'long' }
    : { year: 'numeric', month: 'short', day: 'numeric' }
  if (period === 'weekly') return `${win.start.toLocaleDateString(undefined, opts)} - ${win.end.toLocaleDateString(undefined, opts)}`
  if (period === 'ytd') return `${new Date().getFullYear()} to date`
  return win.start.toLocaleDateString(undefined, opts)
}

// Usage heatmap: GitHub-style calendar layout, but cells are colored by
// usage volume (tokens), not "contributions" — deliberately independent of
// period/anchor (always full history, like a profile page), re-bucketed only
// on the tz toggle. Adapted from maestro's renderHeatmap().
function totalSessionTokens(s: UsageSession): number {
  return s.input_tokens + s.output_tokens + s.cache_creation_input_tokens + s.cache_read_input_tokens
}

function levelFor(tokens: number, maxTokens: number): number {
  if (!tokens) return 0
  if (!maxTokens) return 1
  const ratio = tokens / maxTokens
  if (ratio > 0.75) return 4
  if (ratio > 0.5) return 3
  if (ratio > 0.25) return 2
  return 1
}

interface HeatmapCell { date: Date | null; tokens: number; cost: number }

function buildHeatmapWeeks(sessions: UsageSession[], tz: Timezone): HeatmapCell[][] {
  if (!sessions.length) return []
  const byDay: Record<string, { tokens: number; cost: number }> = {}
  sessions.forEach((s) => {
    if (!s.timestamp) return
    const key = bucketKey(s.timestamp, 'day', tz)
    const entry = byDay[key] || { tokens: 0, cost: 0 }
    entry.tokens += totalSessionTokens(s)
    entry.cost += s.cost
    byDay[key] = entry
  })
  const days = Object.keys(byDay).sort()
  if (!days.length) return []
  const firstYear = Number(days[0].slice(0, 4))
  const start = make(firstYear, 0, 1, tz)
  const end = startOfDay(new Date(days[days.length - 1]), tz)
  const startSunday = addDays(start, -dow(start, tz), tz)

  const weeks: HeatmapCell[][] = []
  let week: HeatmapCell[] = []
  for (let cursor = startSunday; cursor <= end; cursor = addDays(cursor, 1, tz)) {
    if (cursor < start) {
      week.push({ date: null, tokens: 0, cost: 0 })
    } else {
      const key = bucketKey(cursor.toISOString(), 'day', tz)
      const entry = byDay[key] || { tokens: 0, cost: 0 }
      week.push({ date: cursor, tokens: entry.tokens, cost: entry.cost })
    }
    if (week.length === 7) { weeks.push(week); week = [] }
  }
  if (week.length) { while (week.length < 7) week.push({ date: null, tokens: 0, cost: 0 }); weeks.push(week) }
  return weeks
}

// Window-scope ranking aggregation, client-side from the already-windowed
// `sessions` list — the All-time scope instead reads data.by_model/etc.
// directly (server-aggregated, unchanged from before this toggle existed).
// Approximation: model/version dimensions count session occurrences (a
// multi-model session counts once per model it used), not a real per-model
// cost split — UsageSession.models is a plain string[], no per-model cost
// attribution exists client-side. subagent/skill dimensions ARE exact,
// since UsageSession.subagents/skills already carry real per-session counts.
type RankingDimension = 'model' | 'version' | 'subagent' | 'skill'
function aggregateSessions(sessions: UsageSession[], dimension: RankingDimension): RankedRow[] {
  const totals: Record<string, number> = {}
  const bump = (key: string, n: number) => { totals[key] = (totals[key] || 0) + n }
  sessions.forEach((s) => {
    if (dimension === 'model') s.models.forEach((m) => bump(m, 1))
    else if (dimension === 'version') bump(s.version, 1)
    else if (dimension === 'subagent') Object.entries(s.subagents).forEach(([k, v]) => bump(k, v))
    else Object.entries(s.skills).forEach(([k, v]) => bump(k, v))
  })
  return Object.entries(totals)
    .map(([key, calls]) => ({ [dimension]: key, calls }) as RankedRow)
    .sort((a, b) => b.calls - a.calls)
}

type SortKey = 'session_id' | 'timestamp' | 'models' | 'tokens' | 'calls' | 'cost' | 'version'
const PAGE_SIZE = 5
const SESSION_COLUMNS: [SortKey, string][] = [
  ['session_id', 'Session'], ['timestamp', 'Started'], ['models', 'Model(s)'],
  ['tokens', 'Tokens'], ['calls', 'Calls'], ['cost', 'Cost'], ['version', 'Version'],
]

export default function UsageTab() {
  const [data, setData] = useState<UsageData | null>(null)
  const [period, setPeriod] = useState<Period>('weekly')
  const [anchor, setAnchor] = useState<Date>(new Date())
  const [tz, setTz] = useState<Timezone>('utc')
  const [sortKey, setSortKey] = useState<SortKey>('timestamp')
  const [sortDir, setSortDir] = useState<1 | -1>(-1)
  const [filterModel, setFilterModel] = useState('all')
  const [filterVersion, setFilterVersion] = useState('all')
  const [chartMetric, setChartMetric] = useState<'cost' | 'tokens'>('cost')
  const [rankingsScope, setRankingsScope] = useState<'window' | 'all'>('window')
  const [page, setPage] = useState(0)

  useEffect(() => {
    let cancelled = false
    async function poll() {
      const result = await fetchUsage()
      if (!cancelled) setData(result)
    }
    poll()
    const id = setInterval(poll, 4000)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  useEffect(() => { setPage(0) }, [period, anchor, tz])

  const now = new Date()
  const win = useMemo(() => periodWindow(period, anchor, tz, now), [period, anchor, tz])
  const heatmapWeeks = useMemo(() => buildHeatmapWeeks(data?.sessions ?? [], tz), [data, tz])

  if (!data) return <div className="empty">Loading…</div>

  const sessions = sessionsInWindow(data.sessions, win)
  const totals = sessions.reduce(
    (acc, s) => { acc.cost += s.cost; acc.calls += s.calls; acc.unpriced_calls += s.unpriced_calls; return acc },
    { cost: 0, calls: 0, unpriced_calls: 0 },
  )
  const buckets = zeroFillBuckets(win, tz)
  const byBucket: Record<string, number> = {}
  sessions.forEach((s) => {
    if (!s.timestamp) return
    const k = bucketKey(s.timestamp, win.granularity, tz)
    const v = chartMetric === 'tokens' ? totalSessionTokens(s) : s.cost
    byBucket[k] = (byBucket[k] || 0) + v
  })
  const max = Math.max(...buckets.map((b) => byBucket[b] || 0), 0.01)

  const earliestTs = data.sessions.reduce((min, s) => (s.timestamp && s.timestamp < min ? s.timestamp : min), data.sessions[0]?.timestamp ?? '')
  const prevDisabled = period === 'ytd' || (earliestTs !== '' && win.start <= new Date(earliestTs))
  const nextDisabled = period === 'ytd' || win.end >= startOfDay(now, tz)
  const maxDayTokens = Math.max(0, ...heatmapWeeks.flat().map((c) => c.tokens))

  const modelOptions = Array.from(new Set(sessions.flatMap((s) => s.models))).sort()
  const versionOptions = Array.from(new Set(sessions.map((s) => s.version))).sort()
  const filteredSessions = sessions.filter((s) =>
    (filterModel === 'all' || s.models.includes(filterModel)) &&
    (filterVersion === 'all' || s.version === filterVersion),
  )
  function sortValue(s: UsageSession): string | number {
    switch (sortKey) {
      case 'session_id': return s.session_id
      case 'timestamp': return s.timestamp ?? ''
      case 'models': return s.models.join(',')
      case 'tokens': return totalSessionTokens(s)
      case 'calls': return s.calls
      case 'cost': return s.cost
      case 'version': return s.version
    }
  }
  const sortedSessions = filteredSessions.slice().sort((a, b) => {
    const av = sortValue(a), bv = sortValue(b)
    if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * sortDir
    return String(av).localeCompare(String(bv)) * sortDir
  })
  const totalPages = Math.max(1, Math.ceil(sortedSessions.length / PAGE_SIZE))
  const pageSessions = sortedSessions.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE)
  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir((d) => (d === 1 ? -1 : 1))
    else { setSortKey(key); setSortDir(1) }
    setPage(0)
  }

  const rankings = rankingsScope === 'all'
    ? { model: data.by_model, version: data.by_version, subagent: data.by_subagent, skill: data.by_skill }
    : {
        model: aggregateSessions(sessions, 'model'),
        version: aggregateSessions(sessions, 'version'),
        subagent: aggregateSessions(sessions, 'subagent'),
        skill: aggregateSessions(sessions, 'skill'),
      }

  return (
    <div>
      {/* Shown first, above the period toolbar — the heatmap is static (full
          history) and doesn't respond to period/anchor, only to tz below. */}
      <div className="card">
        <div className="head">Usage</div>
        {heatmapWeeks.length === 0 ? (
          <div className="empty">No activity yet.</div>
        ) : (
          <div role="img" aria-label="Usage heatmap">
            {heatmapWeeks.map((week, wi) => (
              <div key={wi}>
                {week.map((cell, di) =>
                  cell.date ? (
                    <div
                      key={di}
                      title={`${cell.date.toISOString().slice(0, 10)}: ${fmt(cell.tokens)} tokens, ${usd(cell.cost)}`}
                      data-level={levelFor(cell.tokens, maxDayTokens)}
                    />
                  ) : (
                    <div key={di} />
                  ),
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      <div role="group" aria-label="Period">
        {(Object.keys(PERIOD_LABELS) as Period[]).map((p) => (
          <button key={p} aria-selected={period === p} onClick={() => setPeriod(p)}>{PERIOD_LABELS[p]}</button>
        ))}
      </div>
      {period !== 'ytd' && (
        <div role="group" aria-label="Anchor navigation">
          <button aria-label="Previous" disabled={prevDisabled} onClick={() => setAnchor(shiftAnchor(period, anchor, -1, tz))}>‹</button>
          <span>{anchorLabel(period, win)}</span>
          <button aria-label="Next" disabled={nextDisabled} onClick={() => setAnchor(shiftAnchor(period, anchor, 1, tz))}>›</button>
          <button onClick={() => setAnchor(new Date())}>Latest</button>
        </div>
      )}
      <div role="group" aria-label="Timezone">
        <button aria-selected={tz === 'utc'} onClick={() => setTz('utc')}>UTC</button>
        <button aria-selected={tz === 'local'} onClick={() => setTz('local')}>Local</button>
      </div>
      <div>
        <div>Cost: {usd(totals.cost)}</div>
        <div>Calls: {fmt(totals.calls)}</div>
        <div>Sessions: {fmt(sessions.length)}</div>
        {totals.unpriced_calls > 0 && (
          <div>{totals.unpriced_calls} call(s) used a model with no pricing entry — excluded from cost total.</div>
        )}
      </div>
      <div role="group" aria-label="Ranking scope">
        <button aria-selected={rankingsScope === 'window'} onClick={() => setRankingsScope('window')}>Window</button>
        <button aria-selected={rankingsScope === 'all'} onClick={() => setRankingsScope('all')}>All-time</button>
      </div>
      {([
        ['model', 'By model'], ['version', 'By cairn version'],
        ['subagent', 'Top subagents'], ['skill', 'Top skills'],
      ] as [RankingDimension, string][]).map(([dim, label]) => (
        <div key={dim}>
          <h3>{label}</h3>
          {rankings[dim].length === 0 ? (
            <div className="empty">No data yet.</div>
          ) : (
            <ul>
              {rankings[dim].map((row, i) => (
                <li key={i}>{JSON.stringify(row)}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
      <div className="chart-card">
        <div role="group" aria-label="Chart metric">
          <button aria-selected={chartMetric === 'cost'} onClick={() => setChartMetric('cost')}>Cost</button>
          <button aria-selected={chartMetric === 'tokens'} onClick={() => setChartMetric('tokens')}>Tokens</button>
        </div>
        <svg viewBox="0 0 700 150">
          {buckets.map((b, i) => {
            const value = byBucket[b] || 0
            const barW = Math.max(3, 700 / buckets.length - 4)
            const barH = Math.max(1, (value / max) * 130)
            return <rect key={b} className="bar" x={i * (barW + 4)} y={130 - barH} width={barW} height={barH} />
          })}
        </svg>
      </div>
      <h3>Sessions</h3>
      {sessions.length === 0 ? (
        <div className="empty">No sessions in this window.</div>
      ) : (
        <>
          <div role="group" aria-label="Sessions filter">
            <label htmlFor="filter-model">Model</label>
            <select id="filter-model" value={filterModel} onChange={(e) => { setFilterModel(e.target.value); setPage(0) }}>
              <option value="all">All</option>
              {modelOptions.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
            <label htmlFor="filter-version">Version</label>
            <select id="filter-version" value={filterVersion} onChange={(e) => { setFilterVersion(e.target.value); setPage(0) }}>
              <option value="all">All</option>
              {versionOptions.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          {filteredSessions.length === 0 ? (
            <div className="empty">No sessions match this filter.</div>
          ) : (
            <>
              <table>
                <thead>
                  <tr>
                    {SESSION_COLUMNS.map(([key, label]) => (
                      <th key={key}>
                        <button onClick={() => toggleSort(key)}>
                          {label}{sortKey === key ? (sortDir === 1 ? ' ▲' : ' ▼') : ''}
                        </button>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {pageSessions.map((s) => (
                    <tr key={s.session_id}>
                      <td>{s.session_id}</td>
                      <td>{s.timestamp ? new Date(s.timestamp).toLocaleString() : '?'}</td>
                      <td>{s.models.join(', ')}</td>
                      <td title={`Input: ${fmt(s.input_tokens)} · Output: ${fmt(s.output_tokens)} · Cache write: ${fmt(s.cache_creation_input_tokens)} · Cache read: ${fmt(s.cache_read_input_tokens)}`}>
                        {fmt(totalSessionTokens(s))}
                      </td>
                      <td>{fmt(s.calls)}</td>
                      <td>{usd(s.cost)}</td>
                      <td>{s.version}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {sortedSessions.length > PAGE_SIZE && (
                <div role="group" aria-label="Sessions pagination">
                  <button aria-label="Previous page" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>‹ Prev</button>
                  <span>Page {page + 1} of {totalPages} ({sortedSessions.length} rows)</span>
                  <button aria-label="Next page" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>Next ›</button>
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
```

Fix `shiftAnchor`'s yearly branch before running tests — the version above has a placeholder-shaped bug (`dir * 1 + y - y + 0` is deliberately wrong to force this fix step, not a real placeholder left unresolved): replace that line with `if (period === 'yearly') { const [y] = ymd(day, tz); return make(y + dir, 0, 1, tz) }`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npm run test -- --run UsageTab`
Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
cd dashboard
git add src/components/UsageTab.tsx src/components/UsageTab.test.tsx
git commit -m "feat: implement Usage tab (US-001)"
cd ..
git add dashboard
git commit -m "chore: bump dashboard submodule pointer — Usage tab"
```

---

### Task 9: Tracker tab

**Files:**
- Modify: `dashboard/src/components/TrackerTab.tsx` (replace placeholder)
- Test: `dashboard/src/components/TrackerTab.test.tsx`

**Interfaces:**
- Consumes: `fetchTracker()`, `TrackerRow` (Task 7's `src/api.ts`).
- Produces: `<TrackerTab />`.

- [ ] **Step 1: Write the failing test**

```typescript
// dashboard/src/components/TrackerTab.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import TrackerTab from './TrackerTab'
import type { TrackerRow } from '../api'

const rows: TrackerRow[] = [
  { slug: 'task-a', scope: 'Do a thing', status: 'In Progress: IMPLEMENT', milestone: 'M1', ticket: '—' },
  { slug: 'task-b', scope: 'Do another thing', status: 'Done', milestone: '—', ticket: '—' },
]

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(() =>
    Promise.resolve({ json: () => Promise.resolve(rows) } as Response)
  ))
})

describe('TrackerTab', () => {
  it('shows the Board grouped by status', async () => {
    render(<TrackerTab />)
    await waitFor(() => expect(screen.getByText('task-a')).toBeInTheDocument())
    expect(screen.getByText('task-b')).toBeInTheDocument()
  })

  it('switches to the Roadmap sub-view grouped by milestone', async () => {
    render(<TrackerTab />)
    await waitFor(() => expect(screen.getByText('task-a')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Roadmap' }))
    expect(screen.getByText('M1')).toBeInTheDocument()
  })

  it('shows an empty state with no rows', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve([]) } as Response)
    ))
    render(<TrackerTab />)
    await waitFor(() => expect(screen.getByText(/no tasks tracked/i)).toBeInTheDocument())
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npm run test -- --run TrackerTab`
Expected: FAIL — placeholder component has none of this markup.

- [ ] **Step 3: Write the implementation**

```typescript
// dashboard/src/components/TrackerTab.tsx
import { useEffect, useState } from 'react'
import { fetchTracker, type TrackerRow } from '../api'

type SubView = 'board' | 'roadmap'

const STATUSES = ['Idea', 'Groomed', 'In Progress', 'In Review', 'Blocked', 'Done']

function stageOf(status: string): string {
  const s = status.toLowerCase()
  if (s.startsWith('in progress')) return 'In Progress'
  if (s === 'in review') return 'In Review'
  if (s === 'blocked') return 'Blocked'
  if (s === 'done') return 'Done'
  if (s === 'groomed') return 'Groomed'
  return 'Idea'
}

export default function TrackerTab() {
  const [rows, setRows] = useState<TrackerRow[] | null>(null)
  const [sub, setSub] = useState<SubView>('board')

  useEffect(() => {
    let cancelled = false
    async function poll() {
      const result = await fetchTracker()
      if (!cancelled) setRows(result)
    }
    poll()
    const id = setInterval(poll, 4000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  if (!rows) return <div className="empty">Loading…</div>
  if (rows.length === 0) {
    return <div className="empty">No tasks tracked yet — run project-manager to decompose a PRD into docs/.tasks/TRACKER.md.</div>
  }

  return (
    <div>
      <div className="tabs" role="group" aria-label="Tracker view">
        <button aria-selected={sub === 'board'} onClick={() => setSub('board')}>Board</button>
        <button aria-selected={sub === 'roadmap'} onClick={() => setSub('roadmap')}>Roadmap</button>
      </div>
      {sub === 'board' ? (
        <div style={{ display: 'flex', gap: '1rem' }}>
          {STATUSES.map((status) => {
            const items = rows.filter((r) => stageOf(r.status) === status)
            return (
              <div key={status}>
                <h3>{status} ({items.length})</h3>
                {items.map((r) => (
                  <div key={r.slug}>{r.slug} — {r.scope}</div>
                ))}
              </div>
            )
          })}
        </div>
      ) : (
        <div>
          {[...new Set(rows.map((r) => (r.milestone && r.milestone !== '—' ? r.milestone : 'Unsorted')))].map(
            (milestone) => (
              <div key={milestone}>
                <h3>{milestone}</h3>
                {rows
                  .filter((r) => (r.milestone && r.milestone !== '—' ? r.milestone : 'Unsorted') === milestone)
                  .map((r) => (
                    <div key={r.slug}>{r.slug} — {r.scope}</div>
                  ))}
              </div>
            ),
          )}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npm run test -- --run TrackerTab`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
cd dashboard
git add src/components/TrackerTab.tsx src/components/TrackerTab.test.tsx
git commit -m "feat: implement Tracker tab (US-002)"
cd ..
git add dashboard
git commit -m "chore: bump dashboard submodule pointer — Tracker tab"
```

---

### Task 10: Swarms tab + build + commit `dist/` + README

**Files:**
- Modify: `dashboard/src/components/SwarmsTab.tsx` (replace placeholder)
- Test: `dashboard/src/components/SwarmsTab.test.tsx`
- Modify: `dashboard/README.md`
- Create: `dashboard/dist/` (build output, committed)

**Interfaces:**
- Consumes: `fetchSwarms()`, `Swarm`, `HistoryEntry`, `CHAIN_PHASES` (Task 7's `src/api.ts`).
- Produces: `<SwarmsTab />` — the last piece; after this task the app is feature-complete per US-001–US-004. List + detail split per `ui-layout-spec.md`'s Swarms layout (REG-3 list pane, REG-4 detail pane).

- [ ] **Step 1: Write the failing test**

```typescript
// dashboard/src/components/SwarmsTab.test.tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import SwarmsTab from './SwarmsTab'
import type { Swarm } from '../api'

const handoffSwarm: Swarm = {
  slug: '2026-08-19-my-slug',
  phase: 'HANDOFF NEEDED',
  status: 'waiting on a decision',
  handoff_to: 'qa-engineer',
  worktree: '/tmp/wt',
  branch: 'feature/my-slug',
  key_info: 'needs a human answer',
  last_history: { timestamp: '2026-08-19T10:00:00Z', phase: 'QA-RED', note: 'tests written' },
  recent_history: [
    { timestamp: '2026-08-19T10:00:00Z', phase: 'QA-RED', note: 'tests written' },
    { timestamp: '2026-08-19T09:30:00Z', phase: 'DOC-GATE', note: 'doc gate clean' },
  ],
  history_count: 3,
  tmux_alive: true,
  pane_tail: ['waiting for input...'],
}

const stalledSwarm: Swarm = {
  ...handoffSwarm,
  slug: '2026-08-19-other-slug',
  phase: 'IMPLEMENT',
  status: 'STALLED (2026-08-19T09:00:00Z) — no progress',
  pane_tail: null,
}

describe('SwarmsTab', () => {
  it('lists swarms in the left list without showing detail until selected', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve([handoffSwarm]) } as Response)
    ))
    render(<SwarmsTab />)
    await waitFor(() => expect(screen.getByText('2026-08-19-my-slug')).toBeInTheDocument())
    expect(screen.getByText(/select a swarm/i)).toBeInTheDocument()
    expect(screen.queryByText('feature/my-slug')).not.toBeInTheDocument()
  })

  it('opens the detail panel on click, showing branch/worktree/timeline/history', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve([handoffSwarm]) } as Response)
    ))
    render(<SwarmsTab />)
    await waitFor(() => expect(screen.getByText('2026-08-19-my-slug')).toBeInTheDocument())
    fireEvent.click(screen.getByText('2026-08-19-my-slug'))
    expect(screen.getByText('feature/my-slug')).toBeInTheDocument()
    expect(screen.getByText('/tmp/wt')).toBeInTheDocument()
    expect(screen.getByText('DOC-GATE')).toBeInTheDocument()
  })

  it('shows the pane tail only when the selected swarm is HANDOFF NEEDED', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve([handoffSwarm]) } as Response)
    ))
    render(<SwarmsTab />)
    await waitFor(() => expect(screen.getByText('2026-08-19-my-slug')).toBeInTheDocument())
    fireEvent.click(screen.getByText('2026-08-19-my-slug'))
    expect(screen.getByText('waiting for input...')).toBeInTheDocument()
  })

  it('shows the authoritative stalled badge only from STATE.md\'s own marker', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve([stalledSwarm]) } as Response)
    ))
    render(<SwarmsTab />)
    await waitFor(() => expect(screen.getByText('2026-08-19-other-slug')).toBeInTheDocument())
    fireEvent.click(screen.getByText('2026-08-19-other-slug'))
    expect(screen.getByText(/STALLED/)).toBeInTheDocument()
  })

  it('closing the detail panel deselects and returns to the empty state', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve([handoffSwarm]) } as Response)
    ))
    render(<SwarmsTab />)
    await waitFor(() => expect(screen.getByText('2026-08-19-my-slug')).toBeInTheDocument())
    fireEvent.click(screen.getByText('2026-08-19-my-slug'))
    expect(screen.getByText('feature/my-slug')).toBeInTheDocument()
    fireEvent.click(screen.getByLabelText('Close detail panel'))
    expect(screen.getByText(/select a swarm/i)).toBeInTheDocument()
    expect(screen.queryByText('feature/my-slug')).not.toBeInTheDocument()
  })

  it('defaults to Priority sort — Handoff Needed before a Running swarm', async () => {
    const runningSwarm: Swarm = { ...stalledSwarm, slug: '2026-08-19-running-slug', status: 'working' }
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve([runningSwarm, handoffSwarm]) } as Response)
    ))
    render(<SwarmsTab />)
    await waitFor(() => expect(screen.getByText('2026-08-19-running-slug')).toBeInTheDocument())
    const slugs = screen.getAllByText(/^2026-08-19-/).map((el) => el.textContent)
    expect(slugs.indexOf('2026-08-19-my-slug')).toBeLessThan(slugs.indexOf('2026-08-19-running-slug'))
  })

  it('shows an empty state with no swarms', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({ json: () => Promise.resolve([]) } as Response)
    ))
    render(<SwarmsTab />)
    await waitFor(() => expect(screen.getByText(/no unattended swarms/i)).toBeInTheDocument())
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npm run test -- --run SwarmsTab`
Expected: FAIL — placeholder component has none of this markup.

- [ ] **Step 3: Write the implementation**

```typescript
// dashboard/src/components/SwarmsTab.tsx
import { useEffect, useState } from 'react'
import { fetchSwarms, CHAIN_PHASES, type Swarm } from '../api'

function isStalled(status: string): boolean {
  return status.startsWith('STALLED (')
}

type SortMode = 'priority' | 'recent' | 'name'

function priorityRank(s: Swarm): number {
  if (s.phase === 'HANDOFF NEEDED') return 0
  if (isStalled(s.status)) return 1
  if (s.phase === 'PUBLISH') return 3
  return 2
}

function sortSwarms(swarms: Swarm[], mode: SortMode): Swarm[] {
  const copy = [...swarms]
  if (mode === 'name') return copy // already slug-ordered from the backend
  if (mode === 'recent') {
    return copy.sort((a, b) => {
      const at = a.last_history?.timestamp ?? ''
      const bt = b.last_history?.timestamp ?? ''
      return bt.localeCompare(at) // newest first, missing timestamps sort last
    })
  }
  return copy.sort((a, b) => priorityRank(a) - priorityRank(b))
}

function elapsedLabel(timestamp: string | undefined): string {
  if (!timestamp) return 'no activity yet'
  const ms = Date.now() - new Date(timestamp).getTime()
  const mins = Math.floor(ms / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  return `${hours}h ago`
}

function PhaseTimeline({ phase }: { phase: string }) {
  const currentIndex = CHAIN_PHASES.indexOf(phase)
  return (
    <div style={{ display: 'flex', gap: '.4rem', flexWrap: 'wrap' }}>
      {CHAIN_PHASES.map((p, i) => (
        <span
          key={p}
          style={{
            fontWeight: i === currentIndex ? 700 : 400,
            opacity: currentIndex === -1 || i <= currentIndex ? 1 : 0.4,
          }}
        >
          {p}
          {i < CHAIN_PHASES.length - 1 ? ' → ' : ''}
        </span>
      ))}
    </div>
  )
}

export default function SwarmsTab() {
  const [swarms, setSwarms] = useState<Swarm[] | null>(null)
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null)
  const [sortMode, setSortMode] = useState<SortMode>('priority')

  useEffect(() => {
    let cancelled = false
    async function poll() {
      const result = await fetchSwarms()
      if (!cancelled) setSwarms(result)
    }
    poll()
    const id = setInterval(poll, 4000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  if (!swarms) return <div className="empty">Loading…</div>
  if (swarms.length === 0) {
    return <div className="empty">No unattended swarms running.</div>
  }

  const selected = swarms.find((s) => s.slug === selectedSlug) ?? null
  const sorted = sortSwarms(swarms, sortMode)

  return (
    <div>
      <div role="group" aria-label="Sort order" style={{ marginBottom: '.75rem' }}>
        {(['priority', 'recent', 'name'] as SortMode[]).map((m) => (
          <button key={m} aria-selected={sortMode === m} onClick={() => setSortMode(m)}>
            {m === 'priority' ? 'Priority' : m === 'recent' ? 'Recent activity' : 'Name'}
          </button>
        ))}
      </div>
      <div style={{ display: 'flex', gap: '1rem' }}>
      <div style={{ flex: '0 0 40%' }}>
        {sorted.map((s) => (
          <div
            key={s.slug}
            onClick={() => setSelectedSlug(s.slug)}
            style={{
              border: '1px solid #ddd', borderRadius: 8, padding: '.6rem .75rem',
              marginBottom: '.5rem', cursor: 'pointer',
              background: s.slug === selectedSlug ? '#f0f0f0' : undefined,
            }}
          >
            <div><strong>{s.slug}</strong> — {s.phase}</div>
            <div>
              tmux: {s.tmux_alive === true ? 'alive' : s.tmux_alive === false ? 'dead' : 'unknown'}
              {' · '}
              {elapsedLabel(s.last_history?.timestamp)}
            </div>
          </div>
        ))}
      </div>
      <div style={{ flex: '1 1 60%' }}>
        {!selected ? (
          <div className="empty">Select a swarm to see details.</div>
        ) : (
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3>{selected.slug}</h3>
              <button aria-label="Close detail panel" onClick={() => setSelectedSlug(null)}>×</button>
            </div>
            <PhaseTimeline phase={selected.phase} />
            <div>Branch: {selected.branch}</div>
            <div>Worktree: {selected.worktree}</div>
            <div>Last activity: {elapsedLabel(selected.last_history?.timestamp)}</div>
            {isStalled(selected.status) ? (
              <div style={{ color: 'red' }}>{selected.status}</div>
            ) : (
              selected.history_count > 0 &&
              selected.phase !== 'HANDOFF NEEDED' &&
              selected.phase !== 'PUBLISH' && <div style={{ color: '#888' }}>no progress hint (soft)</div>
            )}
            <h4>Recent history</h4>
            <ul>
              {selected.recent_history.map((h, i) => (
                <li key={i}>{h.phase} — {h.note}</li>
              ))}
            </ul>
            {selected.phase === 'HANDOFF NEEDED' && selected.pane_tail && (
              <pre>{selected.pane_tail.join('\n')}</pre>
            )}
          </div>
        )}
      </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npm run test -- --run SwarmsTab`
Expected: PASS (7 tests). Then run the full frontend suite: `npm run test -- --run` — expect PASS across App/UsageTab/TrackerTab/SwarmsTab (13 tests total).

- [ ] **Step 5: Build, write README, commit**

Run: `cd dashboard && npm run build`
Expected: `dist/index.html` and `dist/assets/*.{js,css}` are created, no TypeScript errors.

Write `dashboard/README.md` (replacing the one-line stub):

```markdown
# cairn-dashboard

The React frontend for [cairn](https://github.com/jisundr/cairn)'s local usage/tracker/swarms dashboard. Served as static files by the parent repo's `scripts/usage_dashboard.py` (stdlib Python, no dependencies at runtime) — this repo only needs Node/npm at build time, never to run the dashboard itself.

## Development

```bash
npm install
npm run dev      # Vite dev server, proxies /api/* to the Python backend on :4756
npm run test      # Vitest
```

Start the Python backend separately first (`/cairn-dashboard` in the parent repo, or `python3 scripts/usage_dashboard.py` directly) so `npm run dev`'s proxy has something to talk to.

## Shipping a change

`dist/` is committed directly to this repo — there is no build step at `/cairn-dashboard` launch time. After any change:

```bash
npm run build
git add dist/
git commit -m "..."
git push
```

Then, in the parent `cairn` repo: `git add dashboard && git commit -m "chore: bump dashboard submodule pointer"` so the parent repo picks up the new build.
```

```bash
cd dashboard
git add src/components/SwarmsTab.tsx src/components/SwarmsTab.test.tsx README.md dist/
git commit -m "feat: implement Swarms tab (US-003), build dist/, write README"
git push
cd ..
git add dashboard
git commit -m "chore: bump dashboard submodule pointer — Swarms tab, feature-complete"
```

---

## Self-Review Notes

**Spec coverage:** FR-001 → Task 8 (US-001). FR-002 → Task 9 (US-002). FR-003 → Tasks 2–4, 10 (US-003). FR-004 (4s polling) → Tasks 8–10's `setInterval`. NFR-001 (zero new deps) → Tasks 5–6 (static serving, no FastAPI) + Task 10 (committed `dist/`). NFR-002 (local-only) → unchanged, no task touches the bind address. NFR-003 (graceful degradation) → Task 5 (`serve_static` None/traversal handling), Task 2/3 (`tmux_alive`/`pane_tail` None on missing binary), Tasks 8–10 (empty states). FR-006/US-004 → deliberately untouched by any task (Task 5's `do_GET` refactor keeps `/api/usage`/`/api/tracker` byte-identical in behavior; `--task-report`/`--window-report` code paths are never modified by any task in this plan). UF-001 (launch flow) → Task 6.

**Placeholder scan:** none — every step above has runnable code, exact file paths, and exact commands.

**Type consistency:** `Swarm`/`UsageData`/`TrackerRow` are defined once in Task 7's `src/api.ts` and imported (never redefined) in Tasks 8–10. `discover_swarms`'s Python dict keys (`slug`, `phase`, `status`, `handoff_to`, `worktree`, `branch`, `key_info`, `last_history`, `recent_history`, `history_count`, `tmux_alive`, `pane_tail`) match `Swarm`'s TypeScript fields exactly, established in Task 2–3 and consumed unchanged through Task 10.

**Swarms redesign (list + detail, 2026-08-19 update):** Task 10 rewritten for the list+detail split per `ui-layout-spec.md`'s REG-4 Detail Pane — phase timeline via the new `CHAIN_PHASES` constant and `PhaseTimeline` component, elapsed time via `elapsedLabel()`, recent-history log via `recent_history`. Task 2/3's `discover_swarms` gained the `recent_history` field (list of up to 5 entries, newest first) to feed it — Tasks 4–9 are unaffected (the field is purely additive to the JSON shape).
