# Cozmo AI Case Study

Phone capture (Photos / Video / LiDAR) -> dimensioned floor plan + damage
report. Runs entirely on-device/locally, no backend server at runtime.
Full context: `documents/Cozmo-AI-Case-Study.pdf`, `CLAUDE.md` (running
project log), `docs/compliance_matrix.md` (requirement-by-requirement status).

## Setup (fresh machine, <15 minutes)

```bash
git clone <this repo>
cd Cozmo-AI-Case-Study
python3 -m venv .venv
.venv/bin/python3 -m pip install -e .
```

That's it — no external services, no API keys, no model downloads. Verify:

```bash
.venv/bin/python3 -m pytest tests/ -q
# expect: 77 passed
```

## One command per capture

```bash
# Single room, any tier
.venv/bin/python3 -m pipeline.run --tier lidar  --room-dir media/lidar/bedroom_1/2026_08_29_09_16_57 --room-id bedroom_1
.venv/bin/python3 -m pipeline.run --tier photo  --room-dir media/photos/bedroom_1               --room-id bedroom_1
.venv/bin/python3 -m pipeline.run --tier video  --room-dir media/video/bedroom_1                --room-id bedroom_1

# Multi-room property (hand-authored connectors, see docs/multi_room_manifest.md)
.venv/bin/python3 -m pipeline.run --property-manifest path/to/property.json
```

Each writes `<room_id>.json` (schema-valid `PropertyPlan`, see `docs/schema.md`) and `<room_id>.png` (rendered top-down plan) to `--out-dir` (default `output/`).

## Getting your own capture in

1. Follow `docs/capture_protocol.md` (Route 2: native Camera + "3D Scanner App", exported as **All Data**).
2. AirDrop everything for one room (photos + video + LiDAR export folder) together into `media/inbox/`.
3. Run the sorter, which auto-classifies by file type and prompts once for a room name:
   ```bash
   .venv/bin/python3 scripts/sort_media.py --watch
   ```
4. Run `pipeline.run` against the sorted `media/<tier>/<room>/` folder as above.

## Reproducing every reported number

See `docs/reproduction_bundle.md` — one script, `scripts/reproduce_all.py`, regenerates every gate, timing, device-matrix, and head-to-head number in `docs/` from the raw captures in `media/`, live (no cached model outputs to go stale).

## Key documents

| Topic | File |
|---|---|
| Requirement compliance | `docs/compliance_matrix.md` |
| Capture protocol + device matrix | `docs/capture_protocol.md`, `docs/device_matrix.md` |
| Output JSON schema | `docs/schema.md` |
| Benchmark gates + timing | `docs/benchmark_report.md`, `docs/timing.md` |
| Head-to-head vs. magicplan | `docs/head_to_head_report.md` |
| Part 4 fix loop | `docs/fix_loop_report.md`, `results/fix_loop/` |
| Technical report (6 pages) | `docs/technical_report.md` |
| Raw benchmark data | `docs/raw_data_manifest.md` |
| Running project log | `CLAUDE.md` |

## Tests

```bash
.venv/bin/python3 -m pytest tests/ -q
```
