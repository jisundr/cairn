"""
Contract tests for intent-analyzer routing decisions.

This is an eval, not a unit test: every case is a real classification
decision from a live model call (`model: haiku`, matching the shipped
frontmatter) on a prompt chosen to sit near a category boundary — not a
mocked, deterministic function. A model can legitimately land on a
different (still defensible) call for the same borderline prompt on two
different runs. Gating on every single case passing every time produces
perpetual, meaningless red; instead this asserts an aggregate pass rate
across the whole case set, which is how eval suites for model-graded
tasks are normally run (see e.g. promptfoo/DeepEval/OpenAI Evals) — a
regression is the score dropping, not one case flipping.

Run:
    pytest tests/test_intent_routing.py -v -s

(-s shows the per-case PASS/FAIL summary and any failure detail even
when the overall assertion still passes.)
"""

import re
import subprocess
from concurrent.futures import ThreadPoolExecutor

# Tolerates markdown emphasis around the label (e.g. "**ROUTING DECISION:**
# review") — the model doesn't always match the template's plain-text form
# verbatim, and that styling variance isn't a classification error.
ROUTING_DECISION_RE = r"ROUTING DECISION:\**\s*{}\b"

# (prompt, expected_intent_type)
#
# Each prompt must be self-contained: cases run in an empty scratch
# directory with no repo/session context, so "this project" / "this PR" /
# "this function" style references read as genuinely ambiguous to the
# agent (it has nothing to resolve them against) and it correctly asks a
# clarifying question instead of classifying — that's the agent doing its
# job, not a bug. Keep every case concrete enough to classify standalone.
ROUTING_CASES = [
    # coding
    ("implement the leaderboard feature with a React frontend and FastAPI backend", "coding"),
    ("build a CSV export button for the reports dashboard that downloads the current filtered view", "coding"),
    ("add a loading spinner to the SubmitButton when the form is submitting", "coding"),
    ("fix the null check in userService.getById at src/services/userService.js", "coding"),
    # planning
    ("write a PRD for a global weekly leaderboard feature ranking users by points, for the mobile app", "planning"),
    ("create user stories for the checkout flow", "planning"),
    ("write the UX spec for the admin analytics dashboard showing daily active users and revenue", "planning"),
    ("write the architecture spec for a new notifications microservice", "planning"),
    ("create the database schema for a leaderboard feature: users, scores, and rankings tables", "planning"),
    ("log that we decided to use PostgreSQL over MongoDB for the primary database", "planning"),
    # review
    ("review the README and flag anywhere it's out of sync with the actual codebase", "review"),
    ("review the payments-service backend and list all tech debt and outstanding issues", "review"),
    ("review src/middleware/auth.js for security issues", "review"),
    # documentation
    ("write a README for the cairn Claude Code plugin, covering install and usage", "documentation"),
    ("write the setup and installation guide for the FastAPI backend service, covering environment variables and local dev setup", "documentation"),
    # query
    ("what's the difference between a git rebase and a git merge?", "query"),
    ("explain how JWT-based auth middleware works in Express", "query"),
]

# Observed baseline across repeated clean runs during development: 15-17/17
# pass, with 1-2 different borderline cases flipping each run (never the
# same case twice in a row). This leaves room for that variance while still
# catching a real regression (a bug that consistently breaks multiple cases,
# not just one draw of the dice).
MIN_PASS = len(ROUTING_CASES) - 2


def _run_case(claude_bin, agents_json, case_dir, prompt, expected):
    result = subprocess.run(
        [
            claude_bin,
            "-p", prompt,
            "--agents", agents_json,
            "--agent", "intent-analyzer",
            "--model", "haiku",
            "--output-format", "text",
        ],
        cwd=case_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    text = result.stdout
    pattern = ROUTING_DECISION_RE.format(re.escape(expected))
    return {
        "prompt": prompt,
        "expected": expected,
        "ok": bool(re.search(pattern, text)),
        "output": text,
        "stderr": result.stderr,
    }


def test_routing_accuracy(claude_bin, intent_analyzer_agents_json, tmp_path_factory):
    # Pre-create scratch dirs on the main thread — tmp_path_factory.mktemp
    # isn't safe to call concurrently from worker threads.
    case_dirs = [tmp_path_factory.mktemp(f"case{i}") for i in range(len(ROUTING_CASES))]

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(
            lambda args: _run_case(claude_bin, intent_analyzer_agents_json, *args),
            (
                (case_dirs[i], prompt, expected)
                for i, (prompt, expected) in enumerate(ROUTING_CASES)
            ),
        ))

    passed = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]

    summary = "\n".join(
        f"  [{'PASS' if r['ok'] else 'FAIL'}] {r['expected']:<14} {r['prompt']}"
        for r in results
    )
    print(f"\nRouting accuracy: {len(passed)}/{len(results)}\n{summary}")

    if failed:
        detail = "\n\n".join(
            f"--- {r['prompt']!r} (expected {r['expected']}) ---\n"
            f"{r['output']}\nstderr:\n{r['stderr']}"
            for r in failed
        )
        print(f"\nFailed case detail:\n{detail}")

    assert len(passed) >= MIN_PASS, (
        f"Only {len(passed)}/{len(results)} routing cases passed "
        f"(need >= {MIN_PASS}). Failed: {[r['prompt'] for r in failed]}"
    )
