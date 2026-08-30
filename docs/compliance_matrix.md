# Compliance Matrix

Requirement → file path → artifact → status. Status is honest, not aspirational: DONE (built, tested, verified on real data), PARTIAL (built and tested but doesn't meet the literal bar on real data), OPEN (not done, with reason).

## Part 1 — Capture route, tiers, device matrix

| Requirement | File path | Artifact | Status |
|---|---|---|---|
| Choose capture route | `docs/capture_protocol.md` | Route 2: native Camera + 3D Scanner App | DONE |
| One-page stock-capture protocol | `docs/capture_protocol.md` | Install/walk/avoid/handoff instructions | DONE |
| Photo tier (2-8 stills, no depth/pose) | `pipeline/adapters/photo_adapter.py` | `PhotoAdapter` | DONE |
| Video tier (handheld walkthrough) | `pipeline/adapters/video_adapter.py` | `VideoAdapter` | DONE |
| LiDAR tier (depth+poses+intrinsics) | `pipeline/adapters/lidar_adapter.py` | `LidarAdapter` | DONE |
| Device matrix (tier x hardware x honest accuracy) | `docs/device_matrix.md`, `scripts/generate_device_matrix.py` | Generated from real `docs/benchmark_results.json`, not hand-typed | DONE |

## Part 2 — Output contract and gates

| Requirement | File path | Artifact | Status |
|---|---|---|---|
| Dimensioned per-room plan (walls, ceiling, area, openings) | `pipeline/room_reconstruction.py`, `pipeline/schema.py::Room` | `reconstruct_room()` | DONE (built+tested); ceiling/opening **accuracy** is PARTIAL, see gates below |
| Stitched multi-room plan, correct adjacency | `pipeline/stitching.py` | `stitch_rooms()` | DONE (tier-agnostic, tested on synthetic topologies); PARTIAL on real data — never run against the real 4-room capture (needs hand-verified real connectors, not yet authored) |
| Per-surface damage regions, class + metric extent | `pipeline/damage_detection.py`, `pipeline/damage_taxonomy.py` | `detect_damage()` | DONE (bounded, tested; explosion bug fixed); PARTIAL — finds false positives on real photos (color thresholds not calibrated to real lighting) |
| Concealed-damage flags with rule cited | `pipeline/concealed_damage.py` | 3 named rules, each `ConcealedFlag` records `rule_name`+evidence | DONE |
| Scope line items keyed to surfaces | `pipeline/scope_generator.py` | `generate_scope_items()` | DONE |
| Confidence interval on every measurement | `pipeline/confidence.py` | `measurement_ci()`, sample-count-based, not hardcoded | DONE — verified LiDAR CI < Video CI < Photo CI, both synthetically and on real data |
| One command per capture | `pipeline/run.py` | `python -m pipeline.run --tier <t> --room-dir <path>` | DONE |
| JSON to our own published schema | `pipeline/schema.py`, `docs/schema.md` | `PropertyPlan.to_dict()` | DONE |
| Rendered plan | `pipeline/render.py` | `render_plan()`, matplotlib PNG | DONE |
| Benchmark set: 3+ rooms + connector, all 3 tiers, staged 2-class damage, repeatability recapture, ground truth | `media/`, `media/ground_truth/` | 4 real rooms (`bedroom_1`, `common-space`, `kitchen-dining`, `hallway_washer_dryer`), all captured on iPhone 16 Pro | DONE |
| Gate: opening widths ≤2cm on ≥85% | `pipeline/benchmark.py::score_opening_widths` | Real result: **0% (0/4 detected)** | OPEN — real gate FAIL, disclosed, Part 4 fix-loop candidate not yet taken |
| Gate: ceiling height ≤1.5cm + repeatability ≤1cm | `pipeline/benchmark.py::score_ceiling_height` | Real result: **5.81cm error** (post-Part-4-fix; was 69.01cm) | PARTIAL — Part 4 fix shipped, 91.6% error reduction, gate still fails (3.9x over) |
| Gate: repeatability, same room/tier within 1cm or 0.5%/wall | `pipeline/benchmark.py::score_repeatability_walls` | Real result: PASS, but on Photo tier's fixed-default values | PARTIAL — vacuous pass, not a real measurement (disclosed) |
| Drift accountability: method stated + on/off ablation | `pipeline/stitching.py`, `scripts/stitch_ablation.py`, `docs/fix_loop_diagnosis.md` (drift-adjacent context) | Loop-closure-error distribution + `--ablation`-style before/after (1697cm -> 849cm gap) | PARTIAL — demonstrated only on synthetic room topologies, never run against the real multi-room capture (same connector-authoring blocker as stitching above) |
| Gate: photo-tier whole-property stitch, ±8%, no overlaps | `pipeline/stitching.py`, `pipeline/run.py --property-manifest` | Tested on synthetic 2-room manifest via real CLI | PARTIAL — never run on the real 4-room set for the same reason |
| Gate: video-tier wall lengths ±3% | `pipeline/benchmark.py::score_video_tier_walls` | Real result: **43.8% error** | OPEN — real gate FAIL, disclosed |

## Part 3 — Head-to-head vs. incumbent

| Requirement | File path | Artifact | Status |
|---|---|---|---|
| Name competitor app + version, submit export | `docs/head_to_head.md`, `media/competitor_benchmark/magicplan/` | magicplan 2026.34.1, PDF export | DONE |
| One table, our error vs. theirs, dimension by dimension | `pipeline/head_to_head.py`, `docs/head_to_head_table.md`/`.csv`, `docs/head_to_head_report.md` | Generated from real data via `scripts/run_head_to_head.py` | DONE (mechanically) |
| Beat/tie on ≥70% of shared dimensions, on 2 rooms | same as above | Real result: **0% (0/3), only 1 room scored** | OPEN — real result is a clear miss on both the room count and the percentage; `common-space` excluded because its ground truth is an irregular room with no comparable box value |

## Part 4 — Fix loop

| Requirement | File path | Artifact | Status |
|---|---|---|---|
| Worst gate + failing number | `docs/fix_loop_report.md`, `scripts/rank_gates.py` | `ceiling_height`, 69.01cm error, 46.0x over threshold | DONE |
| Root-cause hypothesis + evidence | `docs/fix_loop_diagnosis.md` | Point-cloud density/coverage inspection with real numbers | DONE |
| Fix + predicted number, written before implementation | `docs/fix_loop_diagnosis.md` | p90-of-band fix, predicted 5.81cm | DONE |
| Fix shipped | `pipeline/room_reconstruction.py` | `_estimate_ceiling_height_cm()`, isolated diff | DONE |
| Before/after runs, regenerable, readable diff | `results/fix_loop/{before,after}/`, `results/fix_loop/diff.md`, `code_diff.patch` | Verified byte-identical from a clean git clone | DONE |
| Honest post-mortem if short of gate | `docs/fix_loop_report.md` | States gate still fails (3.9x over) and why, plus two further rejected attempts | DONE |

## Part 5 — Process evidence

| Requirement | File path | Artifact | Status |
|---|---|---|---|
| Commit as you work, not a 1-2 commit dump | git history | 8 commits over ~19 hours, real time gaps | DONE (clears the automatic-zero bar) — but 3 of 8 commits carry ~89% of changed lines each, bundling multiple concerns; not flawless, going-forward discipline adopted for remaining work |

## Deliverables (this document's own checklist)

| # | Deliverable | File path | Status |
|---|---|---|---|
| 1 | Compliance matrix | `docs/compliance_matrix.md` | DONE (this file) |
| 2 | Capture route + device matrix | `docs/capture_protocol.md`, `docs/device_matrix.md` | DONE |
| 3 | Repo + README, <15min fresh setup, one command per capture | `README.md` | DONE |
| 4 | Reproduction bundle | `docs/reproduction_bundle.md`, `scripts/reproduce_all.py` | DONE |
| 5 | Benchmark report: gates x3 tiers, repeatability, head-to-head, timing | `docs/benchmark_report.md`, `docs/head_to_head_table.md`, `docs/timing.md` | DONE |
| 6 | Fix loop bundle | `results/fix_loop/`, `docs/fix_loop_report.md` | DONE |
| 7 | Technical report, max 6 pages | `docs/technical_report.md` | DONE |
| 8 | Raw benchmark data | `docs/raw_data_manifest.md`, `media/` | DONE (manifest); raw binaries delivered alongside the repo, not inside git — see manifest |
