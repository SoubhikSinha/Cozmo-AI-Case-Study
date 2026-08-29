# Cozmo AI Case Study

Input-layer scaffold for the 3-tier capture pipeline (Photos / Video / LiDAR).
Reconstruction, stitching, and damage detection are not yet implemented.

## Setup
```
pip install -e .
```

## Usage
```
python -m pipeline.cli capture photo path/to/room_photos --room-id living_room
python -m pipeline.cli capture video path/to/walkthrough.mov --room-id living_room
python -m pipeline.cli capture lidar path/to/3d_scanner_export --room-id living_room
```
Each prints a JSON `Capture` (see `pipeline/core/types.py`) to stdout, or writes
it to `--out <file>`.

## Capture route (Route 2 — stock protocol)
- Photo/Video: native iPhone Camera app.
- LiDAR: "3D Scanner App" by Laan Labs (App Store id1419913995), exported via
  "All Data" (not "Point Cloud" — that's pre-fused and hides per-frame poses).

## Tests
```
pytest tests/
```
