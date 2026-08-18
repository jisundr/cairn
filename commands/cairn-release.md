---
description: "Cut a cairn release: propose a semver bump + changelog from git history since the last tag, confirm once, then commit, tag, and push. Pass 'rc' as an argument to cut a release candidate instead of a final release."
argument-hint: "[rc]"
---

## Your task

Dispatch the `release-manager` agent with the optional argument (`rc` if passed, otherwise none) as opening context. `release-manager` handles the full flow itself — detecting the last tag, reading `.harness/workflow.md` if present, proposing the bump and changelog, confirming, and executing the commit/tag/push. Report its completion summary back to the user — relay what it reported accurately: preserve its specific facts verbatim (version numbers, tag names, changelog entry text/bullets, and any collision or blocker it flagged) rather than condensing them into a generic paraphrase. A brief framing sentence is fine; the substantive content underneath it is not.
