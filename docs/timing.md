# Reconstruction Timing (bedroom_1, on this machine)

Wall-clock time for `reconstruct_room()` only (adapter load / file I/O excluded, since that's disk-speed-bound, not pipeline design). Measured via `time.perf_counter()` in `scripts/run_benchmark.py`, regenerated every run -- not a one-off manual measurement.

| Run | Seconds |
|---|---|
| lidar_reconstruct_bedroom_1 | 4.272 |
| photo_reconstruct_bedroom_1 | 0.000 |
| photo_reconstruct_bedroom_1_recapture | 0.000 |
| video_reconstruct_bedroom_1 | 0.000 |
