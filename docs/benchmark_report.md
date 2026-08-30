# Benchmark Report (bedroom_1)

Only bedroom_1 has ground truth in a shape (rectangular L x B) this benchmark script can automatically compare against reconstructed walls. common-space, kitchen-dining, and hallway_washer_dryer are irregular rooms (see their ground_truth.json files) and are not auto-scored here -- comparing an irregular perimeter against our box-room reconstruction model isn't well-defined without per-wall correspondence, which isn't built yet.

| Gate | Status | Metric | Actual | Threshold | Detail |
|---|---|---|---|---|---|
| ceiling_height | PASS | absolute error (cm) | 0.930 | 1.500 | predicted=271.07cm, ground_truth=272.00cm |
| opening_widths | FAIL | fraction within 2.0cm | 0.000 | 0.850 | miss (predicted=None, ground_truth=99); miss (predicted=None, ground_truth=60); miss (predicted=None, ground_truth=60); miss (predicted=None, ground_truth=150) |
| ceiling_repeatability | PASS | spread across captures (cm) | 0.000 | 1.000 | capture_a=240.00cm, capture_b=240.00cm [CAVEAT: photo tier's ceiling height is a fixed default, not measured -- this comparison is vacuous] |
| repeatability_walls | PASS | worst-wall ratio to threshold (<=1.0 passes) | 0.000 | 1.000 | ok diff=0.00cm (0.00%); ok diff=0.00cm (0.00%); ok diff=0.00cm (0.00%); ok diff=0.00cm (0.00%) [CAVEAT: photo tier's wall lengths are a fixed default, not measured -- this comparison is vacuous] |
| photo_tier_footprint | PASS | relative footprint error | 0.003 | 0.080 | predicted=12.25m2, ground_truth=12.21m2 [CAVEAT: this is bedroom_1's single-room footprint, a proxy -- the real gate is the whole-property stitched footprint, not yet run against real multi-room captures] |
| video_tier_wall_lengths | FAIL | worst-wall relative error | 0.438 | 0.030 | predicted=500.4cm ground_truth=348.0cm err=43.79%; predicted=500.4cm ground_truth=348.0cm err=43.79%; predicted=500.4cm ground_truth=351.0cm err=42.56%; predicted=500.4cm ground_truth=351.0cm err=42.56% |

Overall: SOME GATES FAIL
