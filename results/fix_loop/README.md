# Fix Loop Bundle

One-page declaration + diagnosis: `docs/fix_loop_report.md`, `docs/fix_loop_diagnosis.md`

| Artifact | Path | Tracked in git? |
|---|---|---|
| Before (pre-fix) pipeline output + gate result + commands | `before/` | No -- regenerate locally (see below) |
| After (post-fix) pipeline output + gate result + commands | `after/` | No -- regenerate locally (see below) |
| Isolated code diff | `code_diff.patch` | Yes |
| Before/after comparison + plain-English summary | `diff.md` | Yes |

`before/` and `after/` are gitignored on purpose: a fresh clone should start with nothing pre-run, exactly like a tester following `README.md` against their own captures. Regenerate both locally with `before/command.txt` and `after/command.txt`'s exact commands (checking out the commit before the fix for `before/`, and current `main` for `after/`) -- both were verified to reproduce byte-identical results from a clean `git clone` when this bundle was built (see `docs/fix_loop_report.md`, "Regenerable evidence").
