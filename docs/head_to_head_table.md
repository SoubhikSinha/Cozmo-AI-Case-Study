# Head-to-Head: Our Pipeline vs. magicplan (2026.34.1)

LiDAR tier, bedroom_1 (the only benchmark room with ground truth in a shape comparable to both our box-room reconstruction and magicplan's box-room output -- see docs/head_to_head.md for why common-space is excluded).

| Dimension | Ground Truth (cm) | Our Value | Our Error | Their Value | Their Error | Winner |
|---|---|---|---|---|---|---|
| bedroom_1_length | 351.00 | 389.35 | 38.35 | 353.06 | 2.06 | theirs |
| bedroom_1_breadth | 348.00 | 283.96 | 64.04 | 359.41 | 11.41 | theirs |
| bedroom_1_ceiling_height | 272.00 | 271.07 | 0.93 | 277.50 | 5.50 | ours |

**Beat-or-tie rate: 33.3%** of 3 shared dimensions.
