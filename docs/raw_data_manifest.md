# Raw Benchmark Data Manifest

Sensor logs, ground truth, and app exports for all 4 real benchmark rooms, captured on an iPhone 16 Pro (`iPhone17,1`).

## Why this isn't all inside git

Raw LiDAR exports, photos, and video are large binary data (a single room's LiDAR export runs into hundreds of MB across thousands of per-frame images/depth maps). Committing that into git would bloat the repository for every future clone/CI run, which is why `.gitignore` excludes `media/{inbox,photos,video,lidar}/*` (folder structure and `.gitkeep` placeholders are tracked; contents are not). Ground truth JSON files *are* tracked (small, text, essential) — see the `!media/ground_truth/**/*.json` exception in `.gitignore`.

**For submission**: the raw `media/` tree (see below) is included as a separate data bundle alongside the git repository, not inside it. Anyone with the repo + this data bundle dropped into `media/` can run `scripts/reproduce_all.py` end to end.

## Inventory

| Room | LiDAR (raw frames) | Photos | Video | Ground truth | Notes |
|---|---|---|---|---|---|
| `bedroom_1` | `media/lidar/bedroom_1/2026_08_29_09_16_57/` | `media/photos/bedroom_1/` (8 stills) | `media/video/bedroom_1/*.MOV` | `media/ground_truth/bedroom_1/ground_truth.json` | Staged damage (water stain + structural crack, 2 classes); has a second photo-tier capture for repeatability |
| `bedroom_1_recapture` | — (photo tier only) | `media/photos/bedroom_1_recapture/` | — | uses `bedroom_1`'s ground truth (same physical room) | Repeatability gate capture |
| `common-space` | `media/lidar/common-space/2026_08_29_09_30_36/` | `media/photos/common-space/` | `media/video/common-space/*.MOV` | `media/ground_truth/common-space/ground_truth.json` | Irregular room, slanted ceiling — ground truth is a per-wall perimeter, not L x B |
| `kitchen-dining` | `media/lidar/kitchen-dining/2026_08_29_09_36_06/` | `media/photos/kitchen-dining/` | `media/video/kitchen-dining/*.MOV` | `media/ground_truth/kitchen-dining/ground_truth.json` | Combined kitchen (irregular) + dining (box) space |
| `hallway_washer_dryer` | `media/lidar/hallway_washer_dryer/2026_08_29_09_24_30/` | `media/photos/hallway_washer_dryer/` | `media/video/hallway_washer_dryer/*.MOV` | `media/ground_truth/hallway_washer_dryer/ground_truth.json` | The multi-room connector — hallway + washer/dryer alcove, irregular |

## Competitor app export

`media/competitor_benchmark/magicplan/Bedroom + Drawing Space Report.pdf` — the real, unmodified PDF export from magicplan (version 2026.34.1), covering `bedroom_1` and `common-space`. Measurements hand-transcribed into `media/competitor_benchmark/magicplan/measurements.json` for programmatic use by `pipeline/competitor_parser.py` (the PDF itself isn't structured data — see that file's note on why opening widths weren't transcribed).

## Format notes

- **LiDAR export**: 3D Scanner App "All Data" format — `frame_NNNNN.json` (pose, intrinsics, timestamp), `frame_NNNNN.jpg` (RGB, only every ~6th frame is saved), `depth_NNNNN.png` (uint16 mm depth), `conf_NNNNN.png` (confidence), `world_map.arkit`, `info.json` (device/app metadata).
- **Ground truth JSON**: hand-measured with laser/tape, schema varies per room (simple `floor_dimensions_cm` for box rooms like `bedroom_1`; a `perimeter` wall-segment list for irregular rooms) — see `docs/compliance_matrix.md` and each file's own structure.
