# Fix Loop Bundle

One-page declaration + diagnosis: `docs/fix_loop_report.md`, `docs/fix_loop_diagnosis.md`

| Artifact | Path |
|---|---|
| Before (pre-fix) pipeline output + gate result + commands | `before/` |
| After (post-fix) pipeline output + gate result + commands | `after/` |
| Isolated code diff | `code_diff.patch` |
| Before/after comparison + plain-English summary | `diff.md` |

Regenerate: see `before/command.txt` and `after/command.txt`. Both verified to reproduce byte-identical results from a clean `git clone` (see `docs/fix_loop_report.md`, "Regenerable evidence").
