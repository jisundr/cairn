---
description: "File sanitized feedback about a cairn bug to jisundr/cairn's issue board. Drafts a local file first — always reviewed by you before anything is pushed, never automatic."
---

## Your task

1. Invoke `Skill(skill: "feedback-context")` — it documents the gate check, the gather/draft/review/push flow, and the fixed draft field list. Follow it exactly; this command does not have its own separate drafting rules.
2. If the user's invocation already described the issue (e.g. `/cairn:cairn-feedback the dashboard crashed on start`), treat that as the "what happened" input for the skill's Gather step. Otherwise ask what happened first.
3. Follow the skill's Draft/Review/Push flow (Gate → Gather → Draft → Stop → Offer push) exactly as documented. Do not skip the Stop step under any circumstance, even if the user seems eager to push immediately — the review gate is not optional.
