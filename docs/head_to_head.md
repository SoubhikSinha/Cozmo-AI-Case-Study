# Part 3: Head-to-Head vs. Incumbent App

**Competitor app:** magicplan, version **2026.34.1** (free tier)

**Rooms compared:** `bedroom_1` and `common-space`, both LiDAR tier — the same 2 physical rooms captured for our own benchmark set (Phase 6), rescanned with magicplan on the same iPhone 16 Pro.

**Export:** `media/competitor_benchmark/magicplan/Bedroom + Drawing Space Report.pdf`

## Status: comparison run, result is a clear loss

`scripts/run_head_to_head.py` builds the table from real data: our LiDAR reconstruction, magicplan's parsed export (`pipeline/competitor_parser.py`), and ground truth. Full table + CSV: `docs/head_to_head_table.md` / `.csv`.

**Result: 0% beat-or-tie rate (0 of 3 shared dimensions)**, far short of the assessment's ≥70% bar:

| Dimension | Ground Truth | Us | Our Error | magicplan | Their Error | Winner |
|---|---|---|---|---|---|---|
| bedroom_1 length | 351cm | 447.5cm | 96.5cm | 353.1cm | 2.1cm | magicplan |
| bedroom_1 breadth | 348cm | 311.7cm | 36.3cm | 359.4cm | 11.4cm | magicplan |
| bedroom_1 ceiling height | 272cm | 203.0cm | 69.0cm | 277.5cm | 5.5cm | magicplan |

magicplan wins every dimension, by a wide margin each time — not a close call. This traces directly to the two known LiDAR-tier issues already on record (`docs/benchmark_report.md`): the box-room bounding-box fit doesn't match this room's true footprint, and the ceiling-height percentile trim clips too aggressively. Both are real Part 4 fix-loop candidates; this head-to-head result is additional, independent evidence for prioritizing them.

**`common-space` excluded** from this table, not silently dropped: its ground truth is an irregular room (see `media/ground_truth/common-space/ground_truth.json` — a per-wall perimeter, not a single L×B box), so there's no single "width"/"length" ground-truth value to compare magicplan's (also box-shaped) measurement against without inventing a mapping. Only `bedroom_1` has a ground-truth shape both our model and magicplan's export can be compared against on equal terms.

Openings were not compared — magicplan's export doesn't have per-opening data confidently extracted (see `media/competitor_benchmark/magicplan/measurements.json`'s note), and our own LiDAR output detected 0 openings on this room, so no dimension is "present in both outputs" for that category.
