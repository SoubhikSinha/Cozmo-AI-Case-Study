# Multi-Room Property Manifest

`python -m pipeline.run --property-manifest <path.json> [--out-dir output]`

Reconstructs every room in the manifest and stitches them via
`pipeline.stitching.stitch_rooms` — the real multi-room path, not the
trivial single-room wrapper `--room-dir` uses.

## Format

```json
{
  "property_id": "my-apartment",
  "rooms": [
    {"room_id": "bedroom_1", "tier": "lidar", "room_dir": "media/lidar/bedroom_1/2026_08_29_09_16_57", "device": "iPhone17,1"},
    {"room_id": "hallway_washer_dryer", "tier": "lidar", "room_dir": "media/lidar/hallway_washer_dryer/2026_08_29_09_24_30", "device": "iPhone17,1"}
  ],
  "connectors": [
    {"room_a": "bedroom_1", "wall_a": "wall-1", "room_b": "hallway_washer_dryer", "wall_b": "wall-3"}
  ],
  "drift_correction": true
}
```

- `rooms[]`: one entry per room, same fields as the single-room CLI (`tier`, `room_dir`, `device` — device optional, defaults to `"unknown"`).
- `connectors[]`: which wall on which room touches which wall on which other room. **Not auto-detected** — you declare it, because inferring adjacency from noisy real-world geometry is a separate, harder problem this project doesn't solve yet.
- `drift_correction`: optional, defaults to `true`.

## How to find your real wall IDs

Adjacency has to reference actual wall IDs, and those are only known after reconstruction runs. Workflow:

1. Run each room through the single-room CLI first: `python -m pipeline.run --tier lidar --room-dir <path> --room-id bedroom_1`.
2. Open the resulting `output/bedroom_1.json` — each entry in `walls[]` has an `id` (`wall-0`..`wall-3`) plus `start`/`end` coordinates.
3. Cross-reference against which physical wall you know borders the next room (from memory of the walkthrough, or the rendered `.png`), and write the connector using those two wall IDs.
4. Once you have `connectors[]` for every pair of adjacent rooms, run the manifest.

This is a manual step today. Real captures aren't reliable enough yet to automate it — reconstruction accuracy issues (see `CLAUDE.md`: the LiDAR bounding-box fix, and the still-open opening-detection gap) mean wall IDs/positions on real rooms may shift as those get fixed, so hand-verifying adjacency for now is the honest approach rather than guessing automatically.
