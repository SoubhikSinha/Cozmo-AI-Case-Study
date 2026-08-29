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

## Current progress status
**Done & tested** (10/10 pytest passing, verified against real iPhone captures — 3 real rooms sorted and adapter-loaded):
- Input-layer scaffold: all 3 adapters + `Capture` contract (`pipeline/`).
- Media intake: folder structure + `sort_media.py` with watch mode (`media/`, `scripts/`).
- Capture protocol doc (`docs/capture_protocol.md`).

**Open — Part 1**: device matrix (tier × device × measured accuracy). Blocked on real benchmark numbers — deferred to after Part 2 (gates/benchmark) work produces real data to populate it.

**Not started**: room reconstruction, wall/opening extraction, multi-room stitching, damage detection + concealed-damage rules, real confidence-interval math, drift correction, benchmark suite (Part 2), head-to-head vs. incumbent app (Part 3), fix loop (Part 4), reproduction bundle, technical report.

No git commits made yet in this repo (process evidence / Part 5 still pending — flag if/when to start committing incrementally).
