# Fix Loop: Before vs. After Diff

Gate under fix: `ceiling_height` (LiDAR tier, room `bedroom_1`). Prediction was written down in `docs/fix_loop_diagnosis.md` *before* this fix was implemented — see that file for the reasoning; this file only reports what actually happened.

## Code change

Full patch: `results/fix_loop/code_diff.patch` (also reviewable via `git diff pipeline/room_reconstruction.py`). One file touched, isolated to the ceiling-height computation inside `_reconstruct_lidar` plus one new helper function, `_estimate_ceiling_height_cm`. Wall-length, floor-area, and opening-detection code paths are untouched (confirmed below — wall values are bit-for-bit identical before/after).

## Gate result

| | Before | After | Predicted (written before the fix) |
|---|---|---|---|
| Predicted ceiling height | 202.99cm | **266.19cm** | 266.19cm |
| Ground truth | 272.00cm | 272.00cm | 272.00cm |
| Absolute error | 69.01cm | **5.81cm** | 5.81cm |
| Gate threshold | ≤1.5cm | ≤1.5cm | ≤1.5cm |
| Gate result | FAIL (46.0x over) | **FAIL (3.9x over)** | FAIL (predicted) |

**The prediction matched the actual result exactly** (266.19cm / 5.81cm both times) — expected, since the prediction in `docs/fix_loop_diagnosis.md` was computed by directly running the proposed formula against this room's real point cloud data before writing any pipeline code, not estimated by intuition.

## Plain-English summary of what changed

- **Ceiling height error dropped from 69.01cm to 5.81cm — a 91.6% reduction.**
- **The gate still does not pass** (threshold ≤1.5cm; result is 5.81cm, 3.9x over). This was predicted in advance, not discovered after the fact: the diagnosis document explicitly stated this fix would produce "meaningful movement short of the gate," not a full pass, because the underlying data (a walkthrough capture that rarely tilts up enough to see the ceiling) genuinely lacks dense ceiling coverage — no percentile-based heuristic on this data can fully close that gap.
- **Confidence interval widened appropriately**: before, the CI was ±0.5cm (based on the full ~1.19M-point cloud, i.e. confidently wrong); after, the CI is ±0.67cm based on the much smaller filtered band (~108K points) that actually informed the ceiling estimate specifically. This is a secondary, correct side effect of the fix: the CI now reflects the real sample size behind *this specific measurement*, not the whole point cloud's size.
- **Nothing else changed**: wall lengths (447.52cm / 311.67cm / 447.52cm / 311.67cm) are bit-for-bit identical before and after, confirming the fix is isolated to ceiling height only, as intended. Floor area and openings (0 detected, unchanged known limitation) are also untouched.

## Regeneration

Both directories are regenerable via the exact commands in `results/fix_loop/before/command.txt` and `results/fix_loop/after/command.txt` — the only difference between the two runs is the code state (before/after the commit containing this fix), not the command or the input data.
