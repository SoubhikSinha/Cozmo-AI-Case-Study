# Cozmo AI Case Study — Project Memory

## Goal
Build an end-to-end product: phone capture (photos/video/LiDAR) → AI pipeline → dimensioned floor plan + damage report, provably accurate vs. laser ground truth, scored on a live "walk-in test" against a never-seen room. Full assessment: `documents/Cozmo-AI-Case-Study.pdf`. 48-hour take-home for Cozmo AI.

## Capture route: Route 2 (stock protocol)
Chosen over building a custom iOS app — engineering time goes to the pipeline (65%+ of score: walk-in test, fix loop, benchmark) instead of capture UI/TestFlight plumbing.
- Photos/Video: native iPhone Camera app.
- LiDAR: **3D Scanner App** (App Store, free tier), export mode = **All Data** (never "Point Cloud" — that's pre-fused and drops per-frame poses).
- Full written protocol: `docs/capture_protocol.md`.
- Device: iPhone 16 Pro (Pro-class, LiDAR-capable) + MacBook Air M3.

## 3-tier architecture
All three tiers (Photos, Video, LiDAR) normalize into one shared `Capture` contract so downstream reconstruction/damage logic is tier-agnostic — accuracy differences come from data richness, not different code paths.
- `pipeline/core/types.py`: `Tier`, `Frame`, `Pose`, `Intrinsics`, `Capture` dataclasses. LiDAR-only fields (`pose`, `depth_path`, `confidence_path`, `intrinsics`) are `Optional`; Photo/Video leave them `None`.
- `pipeline/adapters/{photo,video,lidar}_adapter.py`: one adapter per tier, each takes one room's raw input → one `Capture`.
- `pipeline/core/confidence.py`: stub CI hook — every measurement must route through here (LiDAR tightest, Photos widest), real math deferred until reconstruction exists.
- `pipeline/cli.py`: `python -m pipeline.cli capture <tier> <path> --room-id <id>`.
- Stack: Python 3.11+, stdlib dataclasses, OpenCV for video frame extraction. No backend server at runtime — runs as local CLI.

## media/ folder conventions
```
media/
├── inbox/         # AirDrop lands here; emptied by the sorter
├── photos/<room>/
├── video/<room>/
├── lidar/<room>/  # full "All Data" export folder per room
└── ground_truth/<room>/
```
- Room folders are created dynamically — never pre-created (room count/names unknown ahead of time, esp. for the walk-in test).
- Repeatability takes are named `<room>_take2`.
- `scripts/sort_media.py --watch`: polls `media/inbox/`, debounces an AirDrop burst (3s quiet window), prompts once for room name, auto-classifies by extension/content, moves into place. One-shot `--room <name>` mode also available.
- Tier classification is automatic (extension + LiDAR content-sniffing via `frame_*.json`/`info.json`), never manual.

## Output schema (Part 2 contract)
`pipeline/schema.py`: `Measurement` (value + confidence_interval + unit), `Wall`, `Opening`, `DamageRegion`, `ConcealedFlag` (named auditable rule + evidence, no black-box guesses), `ScopeItem`, `Room`, `PropertyPlan` (the stitched whole-property output). Explicit `to_dict`/`from_dict` per class. Documented in `docs/schema.md` with a worked example. Note: `schema.Capture` (output-side tier/device metadata) is a different class from `pipeline.core.types.Capture` (raw input frames) — same name, different module, don't conflate.

## Room reconstruction
`pipeline/room_reconstruction.py`: `reconstruct_room(capture, room_id, name, device) -> Room`, dispatches on tier.
- **LiDAR**: back-projects each frame's depth+pose+intrinsics into a world point cloud, fits a percentile-based box-room bound (4 walls, ceiling height, floor area). Openings: per wall, picks the best-aligned frame and scans its eye-level depth row for an anomalously-far pixel run → converts to a wall-plane width. Verified on real capture: ~8.46m × 6.26m room, 282cm ceiling — runs but found no openings on that real scan (heuristic limitation, not a crash).
- **Photo/Video**: no depth/pose exists, so wall/ceiling values fall back to documented priors with deliberately wide confidence intervals (Photo widest; Video narrower via a frame-timestamp × assumed-walking-speed perimeter estimate). No opening detection yet for these tiers.
- All heuristic constants are `ponytail:`-tagged as calibration placeholders — real CI math is still deferred to `pipeline/core/confidence.py`.
- Tested with a synthetic 4m×4m×2.5m box room (real depth-PNG + pose fixtures, one wall with a synthetic doorway) in `tests/test_room_reconstruction.py`.
- **Fixed bug (real capture testing)**: the LiDAR bounding box originally used raw `min()`/`max()` on the point cloud, so a handful of noisy/reflected depth points (mirrors, glass, background through a window) blew up room size (one real room measured 12.3m × 9.4m instead of ~4.8m × 4.1m). Switched to a 5th/95th percentile trim on all three axes — verified fix on two real rooms, no regressions (15/15 → still passing).
- **Known open issue**: opening (door/window) detection finds nothing on every real room tested so far, despite working on synthetic fixtures — the eye-level-row gap heuristic likely doesn't hold up against real capture noise/alignment. Deliberately deferred (diagnosed as a real debugging task, not a quick fix) rather than patched blind — good candidate for the Part 4 fix-loop's "worst gate" target.

## Multi-room stitching
`pipeline/stitching.py`: `stitch_rooms(rooms, connectors, drift_correction=True) -> PropertyPlan`. Operates purely on already-reconstructed `Room` objects (never looks at `capture.tier`), so it's automatically tier-agnostic.
- `Connector(room_a, wall_a, room_b, wall_b)`: hand-supplied "this wall is that wall" declaration — adjacency isn't auto-detected from geometry (future work).
- BFS spanning tree from `rooms[0]` as anchor; each tree edge solved via closed-form 2-point rigid transform (rotation + translation, reversed winding since a shared wall is traversed oppositely by each room).
- Any connector not used by the tree is a loop-closure edge. `drift_correction=True` distributes the resulting positional mismatch linearly across the rooms on the BFS path (a simplified pose-graph relaxation, `ponytail:`-tagged — real bundle adjustment is the upgrade path); `False` leaves the gap, demonstrating the "poses used as-is" failure mode.
- `check_no_overlaps(plan)`: hand-rolled separating-axis test for convex room footprints (no new dependency).
- Demo/ablation: `scripts/stitch_ablation.py` — hardcoded 3-room hub-and-loop topology, prints room placements + residual loop-closure gap with correction on vs off. Verified: gap drops ~1697cm → ~849cm with correction on.
- Now wired into the real CLI via `pipeline/run.py --property-manifest` (see below) — connector manifests are hand-authored (adjacency isn't auto-detected from geometry), documented in `docs/multi_room_manifest.md`.
- Tested in `tests/test_stitching.py`: 3-room straight line lands at exact expected offsets with no overlaps; a hub-topology triangle confirms `drift_correction=True` strictly reduces the loop-closure residual vs `False`.

## One-command runner (Part 2 deliverable: "one command per capture")
`pipeline/run.py` has two modes:
- **Single room**: `python -m pipeline.run --tier {photo,video,lidar} --room-dir <path> [--room-id X] [--device X] [--out-dir output]`. adapter load → `reconstruct_room` → `detect_damage` (stub) → `stitch_rooms([room], connectors=[])` (trivial one-room `PropertyPlan` — same output contract the multi-room case uses).
- **Multi-room property**: `python -m pipeline.run --property-manifest <path.json> [--out-dir output]`. Reconstructs every room named in the manifest, then runs the real `stitch_rooms(rooms, connectors, drift_correction)` — genuinely wired now, not a stub. Manifest format + wall-ID-discovery workflow documented in `docs/multi_room_manifest.md`. Verified end-to-end: two synthetic photo rooms stitched via the CLI produce a correct two-room plan with a shared wall, no gap/overlap (visually confirmed).
- Both modes write `<property_id>.json` (schema-valid `PropertyPlan.to_dict()`) and `<property_id>.png` (rendered top-down floor plan, now correctly drawing multiple rooms) to `--out-dir`.
- `pipeline/damage_detection.py::detect_damage(room, capture) -> list[DamageRegion]`: real (simple) CV — HSV color thresholds for water/mold stains, edge+aspect-ratio detection for cracks. Real metric area for LiDAR (depth+intrinsics back-projection); rough fixed-scale estimate for Photo/Video. Works on synthetic staged-damage test images; found nothing on real bedroom_1 photos yet (thresholds not calibrated to real lighting — known gap).
- `pipeline/render.py::render_plan(plan, out_path)`: matplotlib, top-down view, room outline + name label + red square markers for openings. New dependency added to `pyproject.toml`.
- Adjacency is still hand-authored, never auto-detected from geometry (a separate, harder CV problem, explicitly out of scope) — see `docs/multi_room_manifest.md` for why and how to author connectors against real rooms.
- Tested end-to-end in `tests/test_run.py`: two real `subprocess` CLI invocations — single-room synthetic photo folder, and a 2-room manifest — asserting exit 0, JSON round-trips through `PropertyPlan.from_dict`, rendered PNG exists with nonzero size, and (multi-room case) `adjacency` is populated correctly.

## Damage detection, concealed-damage rules, scope (Part 2/3 pipeline)
- `pipeline/damage_taxonomy.py`: re-exports `DamageClass`/`Severity` from `schema.py`, adds descriptions + area-based severity thresholds.
- `pipeline/concealed_damage.py`: 3 named, auditable rules (`hidden_leak_below_bathroom`, `mold_indicates_hidden_moisture`, `structural_crack_load_bearing`). Building-topology facts a rule needs (e.g. "below a bathroom") are hand-supplied via a `context` dict — same "hand-supplied, not auto-inferred" pattern as stitching connectors. Wired into `run.py` via `--context '{"below_bathroom": true}'` (single-room) or a per-room `"context"` manifest field (multi-room).
- `pipeline/scope_generator.py`: one `ScopeItem` per damage region, keyed to `damage_region_id`.

## Confidence intervals (Part 2 requirement: computed, not hardcoded)
`pipeline/confidence.py::measurement_ci(tier, value, sample_count, unit)`: per-tier base error priors (LiDAR sensor noise, video SfM, photo sparse-view — `ponytail:`-tagged calibration placeholders) combined with real sqrt(N) averaging over the actual sample count backing the measurement (LiDAR: point-cloud size; Video/Photo: frame count), floored at a tier minimum. Wired into every `Measurement` in `room_reconstruction.py`. Verified: `LiDAR CI < Video CI < Photo CI` both synthetically and on real bedroom_1 data (relative widths ~0.5% / ~5% / ~20%). Superseded and removed the old `pipeline/core/confidence.py` stub.

## Benchmark gate scoring (Part 2 deliverable)
`pipeline/benchmark.py`: pure gate-math functions matching every Part 2 gate — `score_opening_widths` (+`match_openings_by_nearest_width`), `score_ceiling_height`, `score_ceiling_repeatability`, `score_repeatability_walls` (1cm OR 0.5%/wall), `score_footprint_tolerance` (photo ±8%), `score_video_tier_walls` (±3%). Each returns a `GateResult` with the actual numeric gap, not just pass/fail — the number is what Part 4's fix loop needs. `BenchmarkReport.to_markdown()` renders the table.

`scripts/run_benchmark.py` — **run against the real benchmark set**, results in `docs/benchmark_report.md`:

| Gate | Result | Actual vs threshold |
|---|---|---|
| ceiling_height (LiDAR) | **FAIL** | 69.0cm error vs 1.5cm threshold (predicted 203cm vs ground truth 272cm) |
| opening_widths (LiDAR) | **FAIL** | 0% detected (0/4) vs 85% threshold — confirms the known opening-detection gap |
| ceiling_repeatability (Photo) | PASS (vacuous) | photo tier's ceiling is a fixed default, not measured — flagged as not a real signal |
| repeatability_walls (Photo) | PASS (vacuous) | same caveat — photo tier's walls are a fixed default |
| photo_tier_footprint | PASS | 0.3% error, but a lucky coincidence of the fixed-default value vs bedroom_1's real size, not evidence the photo path works |
| video_tier_wall_lengths | **FAIL** | 43.8% error vs 3% threshold — the walking-speed-based estimate is far off for this room |

Only `bedroom_1` (rectangular ground truth) is auto-scored; the 3 irregular rooms (`common-space`, `kitchen-dining`, `hallway_washer_dryer`) aren't comparable against the box-room reconstruction model without real per-wall correspondence — documented as a known scope limit, not silently skipped.

Real, non-vacuous gates (ceiling height, openings, video walls) **all fail** — this is the honest Part 4 fix-loop input: three candidate "worst gates" now have real failing numbers to choose from (opening detection 0%, ceiling height 69cm off, video walls 43.8% off).

**Bug fix in passing**: `scripts/run_benchmark.py` had the wrong device string hardcoded (`iPhone16,2`); corrected to the real captured device (`iPhone17,1`, confirmed from the LiDAR export's own `info.json`).

## Device matrix (Part 1, the missed piece)
`scripts/generate_device_matrix.py` reads `docs/benchmark_results.json` (a structured export `run_benchmark.py` now also writes alongside its markdown report — tier + device tagged per `GateResult`) and generates `docs/device_matrix.md` — every number is a real measured result, never hand-typed. Run `run_benchmark.py` first to refresh the source data, then `generate_device_matrix.py`. Removed the old Phase-1 `pipeline/devicematrix.py` stub (dead code, fully superseded by this).

Real output: LiDAR and Video tiers both show real gate FAILs on their respective device-matrix rows; Photo's rows show PASS but every one is annotated inline with its vacuous-result caveat (fixed-default values, not measurements) — nothing is presented as working when it isn't.

## Current progress status
**Done & tested** (53/53 pytest passing, verified against real iPhone captures, full pipeline including benchmark gates and device matrix run against real bedroom_1 data):
- Input-layer scaffold: all 3 adapters + `Capture` contract (`pipeline/core`).
- Media intake: folder structure + `sort_media.py` with watch mode (`media/`, `scripts/`).
- Capture protocol doc (`docs/capture_protocol.md`).
- Output schema (`pipeline/schema.py`, `docs/schema.md`).
- Room reconstruction, all 3 tiers (`pipeline/room_reconstruction.py`), one real bug found+fixed via testing.
- Multi-room stitching + drift-correction ablation (`pipeline/stitching.py`), wired into the real CLI (`pipeline/run.py --property-manifest`, `docs/multi_room_manifest.md`).
- One-command runner + JSON/rendered output, single-room and multi-room (`pipeline/run.py`, `pipeline/render.py`).
- Damage detection + concealed-damage rules + scope generation (`pipeline/damage_detection.py`, `pipeline/damage_taxonomy.py`, `pipeline/concealed_damage.py`, `pipeline/scope_generator.py`).
- Real, computed confidence intervals, all tiers (`pipeline/confidence.py`).
- Benchmark gate scoring + real report against bedroom_1 (`pipeline/benchmark.py`, `scripts/run_benchmark.py`, `docs/benchmark_report.md`, `docs/benchmark_results.json`).
- Device matrix, generated from real results (`scripts/generate_device_matrix.py`, `docs/device_matrix.md`).
- Own benchmark set fully captured + ground truth recorded, all 4 rooms (`media/`, `media/ground_truth/`).
- `scripts/test_reconstruction.py`: CLI to run all 3 tiers against any real room in `media/` by name.

**Part 1: now fully complete** — capture route, all 3 tiers, and the device matrix (generated from real benchmark data) are all in place.

**Known real failing gates** (from `docs/benchmark_report.md`, real fix-loop candidates): opening detection (0% found on real LiDAR), ceiling height (69cm off on real LiDAR), video-tier wall lengths (43.8% off), damage detection (finds nothing on real staged photos).

**Not started**: picking + fixing the Part 4 "worst gate", automatic room-adjacency/connector detection, running the manifest CLI + full benchmark against the other 3 (irregular) real rooms, head-to-head vs. incumbent app (Part 3), reproduction bundle, technical report, device matrix write-up.

No git commits made yet in this repo (process evidence / Part 5 still pending — flag if/when to start committing incrementally).
