# LiDAR Box-Fit Accuracy — Diagnosis (bedroom_1 length/breadth)

*Same rigor as `docs/fix_loop_diagnosis.md`: real evidence before any fix. Result of this
investigation is "no safe fix found" — documented honestly rather than shipping a guess.*

## Symptom
bedroom_1's reconstructed footprint is 389x284cm vs. ground truth 351x348cm (a nearly-square
room). One axis is inflated (+38cm), the other compressed (-64cm) — not a uniform scale error.
This is the direct cause of 2 of 3 head-to-head losses against magicplan (33.3% beat-or-tie).

## Hypotheses tested

**1. Room not axis-aligned to the point cloud's XZ frame (PCA rotation).** Measured directly:
rotating the cloud onto its principal axis before bounding gives 404x259cm — worse on one axis,
better on the other, no net improvement. Ruled out.

**2. Point bleed through the open door inflating one axis.** bedroom_1's real door sits on the
wall at z=max (the `wall-2` in this reconstruction). Checked the z-histogram: a real tail of
points extends to z=+4.5m (consistent with seeing through the open door), but it's already sparse
(768/94/17/6 points per bin past z=1.5m) and the 95th-percentile trim already cuts off right where
the main mass ends (~1.3m), *before* that tail. The trim is working as designed here. Ruled out as
the dominant cause.

**3. Non-uniform point density per wall (confirmed).** Histogramming both axes shows the point
cloud isn't uniformly dense across the room: real, non-noise near-wall points on the sparser side
of an axis get discarded as "the trimmed 5%" purely because that region was captured with fewer
points (grazing-angle depth capture, uneven walking coverage) — not because those points are
outliers. On the axis where coverage happens to be denser near the true wall, the same fixed 5/95
percentile keeps more of the real boundary, or clips real noise less aggressively, whichever
happens to dominate. Net effect: a **fixed global percentile threshold produces an asymmetric,
per-axis bias whenever point density isn't uniform** — which real handheld captures never
guarantee.

## Why no fix is being shipped here
The only "fixes" available at this rung (tweak the percentile, e.g. 3/97 instead of 5/95) would be
calibrated against this one room's ground truth — the same n=1-overfitting anti-pattern already
flagged and avoided for the ceiling-height percentile and the video walking-speed constant. A
percentile tweak might improve bedroom_1 and quietly worsen a room with different coverage
characteristics; there's no way to tell without more real rectangular ground-truth rooms than the
one this project has.

The real fix is the upgrade path already named in `room_reconstruction.py`'s own comment: replace
percentile-based bounding with per-wall RANSAC plane fitting (or similar wall-detection geometry),
which is density-independent by construction. That's a substantially larger task than this fix
round's scope — a new fix-loop candidate for future work, not something to patch blind here.

## Disposition
No code change. Documented as an honest, evidenced limitation. `opening_widths` (this session's
other target) had a real, scoped, non-overfit fix and was shipped; this one doesn't, and shipping
an unverified percentile tweak would trade a disclosed limitation for an undisclosed new bias.
