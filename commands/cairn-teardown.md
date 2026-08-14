---
description: "Remove the cairn entrypoint section that /cairn-setup added to this project's root CLAUDE.md."
---

## Your task

Undo what `/cairn-setup` did to this project's root `CLAUDE.md`.

1. **Check for `CLAUDE.md` at the project root.**
   - If it does not exist: report there's nothing to remove and stop.

2. **Look for the `<!-- cairn:start -->` ... `<!-- cairn:end -->` block.**
   - If not found: report cairn isn't wired in this project and stop.

3. **Remove the block**, including the markers themselves, and collapse any blank-line artifact left behind (don't leave two consecutive blank lines where the block used to be).

4. **Report what changed** — confirm the section was removed. Note that this only removes the `CLAUDE.md` wiring; it does not uninstall the cairn plugin itself (use `/plugin uninstall cairn@cairn-plugins` for that, if wanted).
