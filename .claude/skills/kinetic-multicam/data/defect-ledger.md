# Defect ledger

One row per defect seen in a real generation, newest last. Add a row when the user says something misbehaved: the date, the model it happened on, what was seen and the fix used. Never delete a row.

A row becomes a permanent rule (the Do NOT list in `SKILL.md`, the presets table, or a check in `scripts/verify_prompt.py` or `scripts/qa_result.py`) only when the user agrees at the review step (`SKILL.md`, Step 5). Fill the last column when it does, so each lesson lives in one place.

The first rows come from the notes this skill carried inside its Do NOT list before the ledger existed. Their day was not recorded: they happened while the template was built, before the first public version of 2026-07-29.

| Date | Model | Defect seen | Fix used | Promoted to |
|---|---|---|---|---|
| 2026-07 (day not recorded) | Seedance 2.0 Fast | The wording "Instantly snap" for a camera move was read by the generator as a hard cut, and the kinetic differential (a visible, motion-blurred travel) disappeared. | Every position line describes the visible travel (whip, sweep, rise, drop, punch-in, pull-out, roll) with motion blur, then the lock. The wording was retired in v3. | Do NOT list; presets table; `verify_prompt.py` accepts only position lines from the current menu. |
| 2026-07 (day not recorded) | Seedance 2.0 Fast | The default position "lower orbit ending in a centered composition" looks like the source framing (low plus centered), so the generation showed almost no visible change. | Retired as a default. Contrast rule: every position must differ from the source framing and from its two neighbors in axis or scale. Usable only between two extreme positions. | Do NOT list; presets table (marked RETIRED). |
| 2026-07 (day not recorded) | Seedance 2.0 Fast | A super on a filler phrase ("YOU CAN") was the observed failure of stamping every block with text. | Supers follow their own density rule (about one every 1.5 to 2 s) and only land on words that earn it; filler blocks stay camera-only. | Do NOT list; Step 2b. |
| 2026-07 (day not recorded) | Seedance 2.0 Fast | Baseline agents that had both /multicam and this skill on disk mixed the two templates ("Hard cut to...", "* At [Xs]:", "extreme high angle"). | Never mix: this template never says "hard cut" and uses `From [Xs] to [Xs]` ranges. | Do NOT list; the verifier byte-checks the template. |
| 2026-07 (day not recorded) | Seedance 2.0 Fast | An opening hold that drags past about 1.2 s kills the format. | Snap at a clean phrase boundary between 0.8 and 1.0 s when one exists. | Step 2; Do NOT list. |
| 2026-07 (day not recorded) | Google Omni | Runs the template but with clearly weaker results than Seedance 2.0 Fast. | Recommend Seedance 2.0 Fast only. | Overview; usage line in Step 4. |
| 2026-10-02 | Seedance 2.0 Fast | Not a defect seen in a generation: the template had no rule for where the supers sit, so the optional hook super on frame 1 and any super near an edge could fall under the app interface of an Instagram Reel. | One sentence added to the typography paragraph: keep all on-screen text inside the central band of the frame, clear of the top, bottom and right edges. Not yet re-validated on a generation. | Template; `verify_prompt.py` checks the sentence is present. |

## Validation log

Generations that confirmed or limited something, newest last. These are facts about the model, not defects.

| Date | Model | What was confirmed or limited | Recorded in |
|---|---|---|---|
| 2026-07 (day not recorded) | Seedance 2.0 Fast | The static-super block holds the camera while the super changes, confirmed on a real generation together with the face-protection and behind-the-body typography rules. The template is validated on this model. | `SKILL.md`, template section |
| 2026-10-02 | Seedance 2.5 | Not retested: no result is recorded for the whips or the supers on this model. | this ledger |
