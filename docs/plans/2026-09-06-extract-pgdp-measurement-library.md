# PGDP measurement library extraction plan

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-06
- **Last verified:** 2026-09-06
- **Provenance:** authored from the 2026-09-06 split design, direct inspection of
  `src/pdomain_ocr_synth/pgdp/`, `tests/`, `schemas/`, `pyproject.toml`, and `cli.py`, and the
  measured five-book corpus runs
- **Disposition:** Active migration plan. Task 0 is a hard gate on everything after it.
- **Read when:** executing or reviewing the measurement-library extraction.
- **Search terms:** extraction, migration, pgdp measurement, byte identity, baseline, package split.

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development`
> (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Spec:** [Splitting measurement, labeling, and
synthesis](../specs/2026-09-06-measurement-labeling-synthesis-split-design.md)

## Goal

Move the 16,018-line PGDP measurement library out of `pdomain-ocr-synth` into its own installable
package, proving byte-for-byte that the move changed no output.

## Tech Stack

Python 3.13, uv, hatchling with hatch-vcs, pytest, ruff, basedpyright, pre-commit, Pillow, numpy,
and pydantic.

## Global Constraints

- The new distribution is named `pdomain-pgdp-measure` and imports as `pdomain_pgdp_measure`.
  The owner confirmed this on 2026-09-06, so it is settled, not a placeholder. Its console script
  is `pgdp-measure` and its subcommands are `rank`, `profile`, `align`, `typography`, and
  `glyphs`, dropping the `-pgdp` suffix because the package name already carries it.
- Runtime dependencies are exactly `pillow>=10.0`, `numpy>=1.26`, and `pydantic>=2.0`. Adding any
  other runtime dependency fails this plan.
- Wire contract strings do not change: `pgdp-rank/v1`, `pgdp-profile/v2`, `pgdp-alignment/v3`,
  `pgdp-typography/v1`, `pgdp-glyphs/v1`.
- Report bytes do not change. Task 0's baseline is the acceptance test for Task 6.
- Python floor is 3.13, matching `pdomain-ocr-synth`.
- Never run `python -m pytest`. Use `uv run pytest -n auto` or `make test`.
- Run `make ci AI=1` before every commit.
- Commit locally. Do not push.

## Architecture

The library is already decoupled. `src/pdomain_ocr_synth/pgdp/` imports nothing from the rest of
the package, and the only seam is eleven lazy import lines inside handler functions in `cli.py`.
The move is therefore a relocation plus a CLI transplant, gated on a byte-identity comparison
against a baseline captured before anything moves.

Three repositories are touched. The new package receives the library, its tests, its schemas, and
its fixtures. `pdomain-ocr-synth` loses them and gains a dependency during the transition. No
third repository changes in this plan.

## File Structure

**New package `pdomain-pgdp-measure`:**

- `src/pdomain_pgdp_measure/` — the 33 modules moved verbatim from
  `src/pdomain_ocr_synth/pgdp/`, with internal relative imports unchanged.
- `src/pdomain_pgdp_measure/cli.py` — new. The five PGDP subcommands, transplanted.
- `schemas/` — the eight JSON Schema files moved verbatim.
- `tests/` — the 37 `test_pgdp_*.py` and `test_cli_*_pgdp.py` files, plus
  `tests/fixtures/pgdp_alignment/`, `pgdp_geometry/`, `pgdp_glyphs/`, `pgdp_typography/`.

**Modified in `pdomain-ocr-synth`:**

- `src/pdomain_ocr_synth/cli.py` — five subparsers and eleven lazy imports removed.
- `tests/test_cli.py` and `tests/test_spec_docs.py` — PGDP references removed.
- `pyproject.toml` — dependency added, then later removed at cutover.

## Task 0: Capture the byte-identity baseline

**This task gates every task after it.** Without a baseline captured at current `HEAD`, there is
nothing to compare the moved code against, and the extraction becomes unverifiable.

The existing reports in `/workspaces/pdomain/.m15b-evidence/`, `.m15d-evidence/`, and
`.m15f-evidence/` **cannot serve as the baseline.** They were generated on 2026-08-31 at commit
`8bc8ee10`, seventeen commits before the three band-identification fixes. Comparing against them
would compare two changes at once.

Capturing this baseline also answers an open question for free: it re-runs the chain on the
current alignment, which accepts 713 pages against the 665 the old reports carry.

**Files:**

- Create: `/workspaces/pdomain/.extraction-baseline/` (outside both repositories)
- Create: `/workspaces/pdomain/.extraction-baseline/capture.sh`

**Interfaces:**

- Produces: one directory per book per stage, and `baseline-manifest.txt`, a sorted list of
  `sha256  path` lines that Task 5 compares against.

- [x] **Step 1: Record the exact commit the baseline is captured at**

```bash
mkdir -p /workspaces/pdomain/.extraction-baseline
cd /workspaces/pdomain/pdomain-ocr-synth
git rev-parse HEAD > /workspaces/pdomain/.extraction-baseline/BASELINE_COMMIT
git status --porcelain > /workspaces/pdomain/.extraction-baseline/BASELINE_TREE_STATE
```

Expected: `BASELINE_TREE_STATE` is empty. A dirty tree invalidates the baseline. Stop and clean it
if it is not empty.

- [x] **Step 2: Write the capture script**

**A book is isolated by cutting the ranking, not by a command-line flag.** Neither `rank-pgdp` nor
`profile-pgdp` takes a book selector — `corpus_root` is their only positional argument. So the
corpus is ranked once with every page of every project, and that ranking is cut down to one
project before profiling. This is the chain that produced the M15b through M15f reports; the
cutter below is `.m15b-evidence/build_wholebook_ranking.py`, which wrote the
`ranking-wholebook-<ID>.json` files those runs consumed.

First create `/workspaces/pdomain/.extraction-baseline/cut_book_ranking.py`:

```python
"""Cut a full ranking down to one project, keeping every page, for whole-book runs.

Usage: cut_book_ranking.py <full-ranking.json> <project_id> <output.json>
"""

import json
import sys
from pathlib import Path

full = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
project_id = sys.argv[2]
project = next(p for p in full["projects"] if p["project_id"] == project_id)
payload = {
    **full,
    "limits": {
        **full["limits"],
        "project_limit": 1,
        "pages_per_project": len(project["pages"]),
    },
    "projects": [project],
    "diagnostics": [],
}
Path(sys.argv[3]).write_text(
    json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    encoding="utf-8",
)
print(project_id, len(project["pages"]))
```

Then create `/workspaces/pdomain/.extraction-baseline/capture.sh`. Run one book per invocation,
because a single Bash call is capped at ten minutes.

```bash
#!/usr/bin/env bash
# Capture one book's full measurement chain at the current commit.
# Usage: capture.sh <BOOK_ID> [OUT_DIR]
set -euo pipefail

BOOK="$1"
OUT="${2:-/workspaces/pdomain/.extraction-baseline}"
CORPUS=/workspaces/pdomain-data/pgdp-corpus
SYNTH=/workspaces/pdomain/pdomain-ocr-synth
# The OCR witness records are one JSONL per book, produced by pdomain-source-data.
GEOM="/workspaces/pdomain-data/typography/geometry-v1/${BOOK}.jsonl"
[ -f "$GEOM" ] || { echo "missing geometry records: $GEOM" >&2; exit 1; }

cd "$SYNTH"
mkdir -p "$OUT/$BOOK"

# The corpus-wide ranking is shared by every book. Build it once per OUT dir.
FULL="$OUT/ranking-full-allpages.json"
if [ ! -f "$FULL" ]; then
  uv run pdomain-ocr-synth rank-pgdp "$CORPUS" \
    --output "$FULL" --project-limit 5000 --pages-per-project 5000
fi

python3 "$OUT/cut_book_ranking.py" "$FULL" "$BOOK" "$OUT/$BOOK/ranking.json"

uv run pdomain-ocr-synth profile-pgdp "$CORPUS" \
  --ranking "$OUT/$BOOK/ranking.json" --output "$OUT/$BOOK/profile.json" --whole-book

uv run pdomain-ocr-synth align-pgdp "$CORPUS" \
  --profile "$OUT/$BOOK/profile.json" --output "$OUT/$BOOK/alignment.json"

uv run pdomain-ocr-synth typography-pgdp "$CORPUS" \
  --alignment "$OUT/$BOOK/alignment.json" --profile "$OUT/$BOOK/profile.json" \
  --output "$OUT/$BOOK/typography.json" --geometry "$GEOM"

uv run pdomain-ocr-synth glyphs-pgdp "$CORPUS" \
  --alignment "$OUT/$BOOK/alignment.json" --profile "$OUT/$BOOK/profile.json" \
  --output "$OUT/$BOOK/inventory/" --geometry "$GEOM"

echo "captured $BOOK"
```

Then `chmod +x /workspaces/pdomain/.extraction-baseline/capture.sh`.

The corpus-wide rank takes about 13 seconds and yields 328 ranked projects and 84,944 pages. The
five books carry 98, 237, 312, 312, and 426 pages, matching the M15b whole-book rankings exactly.

**The ranking is a frozen input, not something Task 5 regenerates.** `/workspaces/pdomain-data/pgdp-corpus`
is live and gained two projects during this capture, moving `projects_seen` from 330 to 332 and
`projects_ranked` from 328 to 330. Those counts sit in the ranking header, so its sha256 changes,
and that sha is chained into `profile.json`, then `alignment.json`, then `typography.json` and
`inventory/manifest.json`. A single new project in the corpus therefore breaks byte identity at
five files without a single measured value changing.

So Task 5 copies `ranking-full-allpages.json` from the baseline rather than re-ranking. The
`if [ ! -f "$FULL" ]` guard above exists for exactly this: seed the file and the rank is skipped.
`rank-pgdp` still gets its own identity check, described in Task 5, comparing per-project entries
rather than the corpus-wide header.

- [x] **Step 3: Capture all five books**

```bash
/workspaces/pdomain/.extraction-baseline/capture.sh projectID67a80fde44d34
```

One background Bash call per book, for `projectID67a80fde44d34`, `projectID64a479f51ce5b`,
`projectID657550412c8dc`, `projectID609bfa0449bdf`, and `projectID603d7d5e04ca0`.

The ten-minute cap applies to foreground calls only, so all five ran concurrently in the
background. On a 20-core box each stage stayed under 1 GB resident. Wall clock was 230, 579, 625,
724, and 1032 seconds, the last being the 426-page book.

- [x] **Step 4: Confirm every book exited clean**

```bash
D=/workspaces/pdomain/.extraction-baseline
for B in projectID67a80fde44d34 projectID64a479f51ce5b projectID657550412c8dc \
         projectID609bfa0449bdf projectID603d7d5e04ca0; do
  echo "$B $(grep -o 'exit=[0-9]*' "$D/$B.log" | tail -1) $(find "$D/$B" -type f | wc -l)"
done
```

Expected: `exit=0` for all five, and 104, 217, 222, 196, and 192 files.

- [x] **Step 5: Build the baseline manifest**

```bash
cd /workspaces/pdomain/.extraction-baseline
find . -type f \( -name '*.json' -o -name '*.jsonl' -o -name '*.png' \) -print0 \
  | sort -z | xargs -0 sha256sum | sed 's| \./| |' > baseline-manifest.txt
wc -l baseline-manifest.txt
```

Expected: 927 lines at the 2026-09-06 baseline, covering the five books' reports, glyph
inventories, and atlas PNGs, plus the shared `ranking-full-allpages.json` at the root.

- [x] **Step 6: Prove the baseline is itself reproducible**

Re-run one book into a second directory and compare. If the pipeline is not deterministic today,
byte identity cannot test the move, and this plan stops here.

**Seed the replay directory with the baseline's ranking.** Letting it re-rank tests the corpus,
not the code, and the corpus moves.

```bash
D=/workspaces/pdomain/.extraction-baseline
R=/workspaces/pdomain/.extraction-baseline-replay
mkdir -p "$R"
cp "$D/ranking-full-allpages.json" "$D/cut_book_ranking.py" "$R/"
"$D/capture.sh" projectID67a80fde44d34 "$R"
diff -r "$D/projectID67a80fde44d34" "$R/projectID67a80fde44d34" && echo "DETERMINISM HOLDS"
```

Expected: `DETERMINISM HOLDS`, with no diff output. It held on 2026-09-06 across all 104 files,
atlas PNGs and `glyphs.jsonl` included.

- [x] **Step 7: Record what the re-run says about the stale-alignment question**

```bash
cd /workspaces/pdomain/.extraction-baseline
python3 - <<'PY'
import json, glob, os
for p in sorted(glob.glob('*/alignment.json')):
    d = json.load(open(p))
    for proj in d.get('projects', []):
        pages = proj.get('pages', [])
        acc = sum(1 for pg in pages if pg.get('accepted'))
        print(os.path.dirname(p), 'pages', len(pages), 'accepted', acc)
PY
```

**Result on 2026-09-06: 713 accepted pages, against the 665 the old reports carry.** The
band-identification fixes in `c7c63ab` and `aa5c567` are worth 48 pages, and 38 of them are in the
largest book alone.

| book | pages | old accepted | new accepted | delta |
| --- | ---: | ---: | ---: | ---: |
| projectID603d7d5e04ca0 | 426 | 177 | 215 | +38 |
| projectID609bfa0449bdf | 312 | 226 | 227 | +1 |
| projectID64a479f51ce5b | 237 | 75 | 76 | +1 |
| projectID657550412c8dc | 312 | 155 | 157 | +2 |
| projectID67a80fde44d34 | 98 | 32 | 38 | +6 |
| total | 1385 | 665 | 713 | +48 |

Every typography and glyph number in `.m15b-evidence/` through `.m15f-evidence/` was computed from
the 665-page alignment. This closes the intent-map item "re-run the measurement chain on current
alignment". The full write-up is in `/workspaces/pdomain/.extraction-baseline/NOTES.md`.

- [x] **Step 8: Commit the note, not the data**

The baseline lives outside both repositories and is not committed. Only the finding is.

```bash
cd /workspaces/pdomain/pdomain-ocr-synth
git add docs/plans/2026-09-06-extract-pgdp-measurement-library.md
git commit -m "docs(plan): record the extraction baseline commit and page counts"
```

## Task 1: Create the new package skeleton

**Files:**

- Create: `/workspaces/pdomain/pdomain-pgdp-measure/pyproject.toml`
- Create: `/workspaces/pdomain/pdomain-pgdp-measure/src/pdomain_pgdp_measure/__init__.py`
- Create: `/workspaces/pdomain/pdomain-pgdp-measure/tests/test_package_imports.py`

**Interfaces:**

- Produces: an installable distribution `pdomain-pgdp-measure` exposing the module
  `pdomain_pgdp_measure`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_package_imports.py`:

```python
"""The package imports, and it drags in nothing heavy."""

from __future__ import annotations

import subprocess
import sys


def test_package_imports() -> None:
    import pdomain_pgdp_measure

    assert pdomain_pgdp_measure.__name__ == "pdomain_pgdp_measure"


def test_import_pulls_no_heavy_dependency() -> None:
    """cv2, torch, and doctr must never become dependencies of this package."""
    code = (
        "import sys, pdomain_pgdp_measure;"
        "bad=[m for m in ('cv2','torch','doctr','nicegui') if m in sys.modules];"
        "print(','.join(bad))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == ""
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd /workspaces/pdomain/pdomain-pgdp-measure && uv run pytest tests/test_package_imports.py -v`

Expected: FAIL, `ModuleNotFoundError: No module named 'pdomain_pgdp_measure'`.

- [ ] **Step 3: Write the packaging metadata**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "pdomain-pgdp-measure"
dynamic = ["version"]
description = "Font-free measurement of PGDP scans: geometry, alignment, typography, glyphs"
authors = [{ name = "CT" }]
requires-python = ">=3.13"
dependencies = [
    "pydantic>=2.0",
    "pillow>=10.0",
    "numpy>=1.26",
]

[project.scripts]
pgdp-measure = "pdomain_pgdp_measure.cli:main"

[tool.hatch.version]
source = "vcs"

[tool.hatch.build]
exclude = [".venv/**", ".venv-container/**"]

[tool.hatch.build.targets.wheel]
packages = ["src/pdomain_pgdp_measure"]
```

Create `src/pdomain_pgdp_measure/__init__.py` as an empty file for now. Task 2 fills it.

- [ ] **Step 4: Run the tests and watch them pass**

```bash
cd /workspaces/pdomain/pdomain-pgdp-measure && uv sync && uv run pytest tests/ -v
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/pdomain/pdomain-pgdp-measure
git init && git add -A
git commit -m "feat: scaffold the pgdp measurement package"
```

## Task 2: Move the library modules

**Files:**

- Create: `src/pdomain_pgdp_measure/*.py` — 33 modules
- Delete: `src/pdomain_ocr_synth/pgdp/*.py` in the synth repository, in Task 6 not here

**Interfaces:**

- Consumes: the skeleton from Task 1.
- Produces: `pdomain_pgdp_measure.rank_corpus`, `.write_report`, `.alignment.build_alignment_report`,
  `.typography.build_typography_report`, `.glyphs.build_glyph_inventory`,
  `.glyphs.write_glyph_inventory`, `.profiling.profile_selection`, `.profiling.profile_methods`,
  `.profile_input.load_profile_snapshot`, `.profile_input.read_profile_snapshot`,
  `.profile_models.ProfileReport`, `.image_measurement.SnapshotSpoolError`, `.report.write_report`.

- [ ] **Step 1: Copy the modules verbatim**

```bash
SRC=/workspaces/pdomain/pdomain-ocr-synth/src/pdomain_ocr_synth/pgdp
DST=/workspaces/pdomain/pdomain-pgdp-measure/src/pdomain_pgdp_measure
cp "$SRC"/*.py "$DST"/
ls "$DST"/*.py | wc -l
```

Expected: `33`.

- [ ] **Step 2: Rewrite absolute self-references**

The modules use relative imports internally, so most need no change. Catch any absolute ones.

```bash
cd /workspaces/pdomain/pdomain-pgdp-measure
grep -rn 'pdomain_ocr_synth' src/pdomain_pgdp_measure/ || echo "NONE FOUND"
```

If any appear, rewrite `pdomain_ocr_synth.pgdp` to `pdomain_pgdp_measure`:

```bash
sed -i 's/pdomain_ocr_synth\.pgdp/pdomain_pgdp_measure/g' src/pdomain_pgdp_measure/*.py
grep -rn 'pdomain_ocr_synth' src/pdomain_pgdp_measure/ || echo "CLEAN"
```

Expected: `CLEAN`.

- [ ] **Step 3: Copy the schemas and fixtures**

```bash
SYNTH=/workspaces/pdomain/pdomain-ocr-synth
DST=/workspaces/pdomain/pdomain-pgdp-measure
mkdir -p "$DST/schemas" "$DST/tests/fixtures"
cp "$SYNTH"/schemas/*.json "$DST/schemas/"
cp -r "$SYNTH"/tests/fixtures/pgdp_* "$DST/tests/fixtures/"
ls "$DST/schemas" | wc -l && ls "$DST/tests/fixtures" | wc -l
```

Expected: `8` and `4`.

- [ ] **Step 4: Verify the package imports**

```bash
cd /workspaces/pdomain/pdomain-pgdp-measure
uv run python -c "
from pdomain_pgdp_measure import rank_corpus, write_report
from pdomain_pgdp_measure.alignment import build_alignment_report
from pdomain_pgdp_measure.typography import build_typography_report
from pdomain_pgdp_measure.glyphs import build_glyph_inventory, write_glyph_inventory
print('ALL SYMBOLS RESOLVE')
"
```

Expected: `ALL SYMBOLS RESOLVE`.

- [ ] **Step 5: Commit**

```bash
cd /workspaces/pdomain/pdomain-pgdp-measure
git add -A && git commit -m "feat: move the pgdp measurement modules, schemas, and fixtures"
```

## Task 3: Move the tests

**Files:**

- Create: `tests/test_pgdp_*.py` — 32 files
- Create: `tests/test_cli_*_pgdp.py` — 5 files

**Interfaces:**

- Consumes: the modules from Task 2.

- [ ] **Step 1: Copy the test files**

```bash
SYNTH=/workspaces/pdomain/pdomain-ocr-synth
DST=/workspaces/pdomain/pdomain-pgdp-measure
cp "$SYNTH"/tests/test_pgdp_*.py "$DST/tests/"
cp "$SYNTH"/tests/test_cli_*_pgdp.py "$DST/tests/"
ls "$DST"/tests/test_*.py | wc -l
```

Expected: `38`, being the 37 moved files plus `test_package_imports.py`.

- [ ] **Step 2: Rewrite the imports**

```bash
cd /workspaces/pdomain/pdomain-pgdp-measure
sed -i 's/pdomain_ocr_synth\.pgdp/pdomain_pgdp_measure/g; s/from pdomain_ocr_synth import/from pdomain_pgdp_measure import/g' tests/*.py
grep -rn 'pdomain_ocr_synth' tests/ || echo "CLEAN"
```

Expected: `CLEAN`. If the CLI tests still reference `pdomain-ocr-synth` as a command name, leave
them failing; Task 4 fixes them.

- [ ] **Step 3: Run the non-CLI tests**

```bash
cd /workspaces/pdomain/pdomain-pgdp-measure
uv run pytest tests/ -n auto --ignore-glob='*test_cli_*' -q
```

Expected: all pass. Every fixture-backed test must pass here, because those fixtures are the
reviewed evidence and a failure means the move corrupted something.

- [ ] **Step 4: Commit**

```bash
cd /workspaces/pdomain/pdomain-pgdp-measure
git add -A && git commit -m "test: move the pgdp test suite and its reviewed fixtures"
```

## Task 4: Transplant the CLI

**Files:**

- Create: `src/pdomain_pgdp_measure/cli.py`
- Modify: `tests/test_cli_*_pgdp.py` — five files, command name only

**Interfaces:**

- Consumes: every symbol listed in Task 2's Produces block.
- Produces: console script `pgdp-measure` with subcommands `rank`, `profile`, `align`,
  `typography`, and `glyphs`.

The subcommands lose their `-pgdp` suffix, because the package name already says PGDP. Flags and
positional arguments do not change.

- [ ] **Step 1: Write the failing test**

Create `tests/test_cli_surface.py`:

```python
"""The CLI exposes exactly the five measurement subcommands."""

from __future__ import annotations

import pytest

from pdomain_pgdp_measure.cli import build_parser


def test_parser_exposes_the_five_subcommands() -> None:
    parser = build_parser()
    actions = [a for a in parser._actions if a.dest == "command"]  # noqa: SLF001
    assert len(actions) == 1
    assert set(actions[0].choices) == {
        "rank",
        "profile",
        "align",
        "typography",
        "glyphs",
    }


@pytest.mark.parametrize(
    ("command", "required"),
    [
        ("profile", ["--ranking", "--output"]),
        ("align", ["--profile", "--output"]),
        ("typography", ["--alignment", "--profile", "--output"]),
        ("glyphs", ["--alignment", "--profile", "--output"]),
    ],
)
def test_required_flags_survive_the_move(command: str, required: list[str]) -> None:
    parser = build_parser()
    sub = parser._subparsers._group_actions[0].choices[command]  # noqa: SLF001
    flags = {opt for action in sub._actions for opt in action.option_strings}  # noqa: SLF001
    for flag in required:
        assert flag in flags
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd /workspaces/pdomain/pdomain-pgdp-measure && uv run pytest tests/test_cli_surface.py -v`

Expected: FAIL, `ModuleNotFoundError: No module named 'pdomain_pgdp_measure.cli'`.

- [ ] **Step 3: Write the CLI**

Create `src/pdomain_pgdp_measure/cli.py`. Copy the five subparser definitions from
`pdomain-ocr-synth`'s `src/pdomain_ocr_synth/cli.py`, which define them at lines 296, 319, 340,
356, and 394, and the five handler functions those parsers dispatch to, which begin near lines
1622, 1671, 1756, 1814, and 1857. Rename the subcommands by dropping the `-pgdp` suffix. Keep the
lazy-import style: each handler imports what it needs inside the function, so `--help` costs no
heavy import.

Preserve the comment at `cli.py:33-34` about `DEFAULT_EVIDENCE_PAGES_PER_BOOK` mirroring
`typography_models`, and keep the test that pins the two together.

```python
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))
```

- [ ] **Step 4: Run the surface test and watch it pass**

Run: `cd /workspaces/pdomain/pdomain-pgdp-measure && uv run pytest tests/test_cli_surface.py -v`

Expected: PASS.

- [ ] **Step 5: Point the moved CLI tests at the new command**

```bash
cd /workspaces/pdomain/pdomain-pgdp-measure
sed -i 's/pdomain-ocr-synth rank-pgdp/pgdp-measure rank/g;
        s/pdomain-ocr-synth profile-pgdp/pgdp-measure profile/g;
        s/pdomain-ocr-synth align-pgdp/pgdp-measure align/g;
        s/pdomain-ocr-synth typography-pgdp/pgdp-measure typography/g;
        s/pdomain-ocr-synth glyphs-pgdp/pgdp-measure glyphs/g' tests/test_cli_*_pgdp.py
uv run pytest tests/ -n auto -q
```

Expected: the full suite passes. Some tests invoke the parser directly rather than by command
string; fix those by hand to call `build_parser()` from the new module.

- [ ] **Step 6: Run the full gate**

```bash
cd /workspaces/pdomain/pdomain-pgdp-measure
uv run ruff check . && uv run ruff format --check . && uv run basedpyright && uv run pytest -n auto
```

Expected: all clean.

- [ ] **Step 7: Commit**

```bash
cd /workspaces/pdomain/pdomain-pgdp-measure
git add -A && git commit -m "feat: add the pgdp-measure CLI with the five measurement subcommands"
```

## Task 5: Reproduce the baseline byte for byte

**This is the acceptance test for the whole extraction.** Nothing is removed from
`pdomain-ocr-synth` until this passes.

**Files:**

- Create: `/workspaces/pdomain/.extraction-verify/`

**Interfaces:**

- Consumes: `baseline-manifest.txt` from Task 0.

- [ ] **Step 1: Write the verification script**

Create `/workspaces/pdomain/.extraction-verify/verify.sh`, identical to Task 0's capture script
except that it calls `pgdp-measure` from the new package and writes into
`/workspaces/pdomain/.extraction-verify/`.

```bash
#!/usr/bin/env bash
set -euo pipefail
BOOK="$1"
CORPUS=/workspaces/pdomain-data/pgdp-corpus
OUT=/workspaces/pdomain/.extraction-verify
MEASURE=/workspaces/pdomain/pdomain-pgdp-measure
# Identical to the baseline's resolution. A mismatch here invalidates the comparison.
GEOM="/workspaces/pdomain-data/typography/geometry-v1/${BOOK}.jsonl"
[ -f "$GEOM" ] || { echo "missing geometry records: $GEOM" >&2; exit 1; }

cd "$MEASURE"
mkdir -p "$OUT/$BOOK"

# The baseline's frozen ranking and cutter. Do not re-rank: the corpus is live,
# and a new project changes the ranking header sha that every later stage chains.
BASE=/workspaces/pdomain/.extraction-baseline
FULL="$OUT/ranking-full-allpages.json"
cp -n "$BASE/ranking-full-allpages.json" "$FULL"
cp -n "$BASE/cut_book_ranking.py" "$OUT/"
python3 "$OUT/cut_book_ranking.py" "$FULL" "$BOOK" "$OUT/$BOOK/ranking.json"
uv run pgdp-measure profile "$CORPUS" \
  --ranking "$OUT/$BOOK/ranking.json" --output "$OUT/$BOOK/profile.json" --whole-book
uv run pgdp-measure align "$CORPUS" \
  --profile "$OUT/$BOOK/profile.json" --output "$OUT/$BOOK/alignment.json"
uv run pgdp-measure typography "$CORPUS" \
  --alignment "$OUT/$BOOK/alignment.json" --profile "$OUT/$BOOK/profile.json" \
  --output "$OUT/$BOOK/typography.json" --geometry "$GEOM"
uv run pgdp-measure glyphs "$CORPUS" \
  --alignment "$OUT/$BOOK/alignment.json" --profile "$OUT/$BOOK/profile.json" \
  --output "$OUT/$BOOK/inventory/" --geometry "$GEOM"
echo "verified $BOOK"
```

- [ ] **Step 2: Run all five books**

One background Bash call per book, exactly as in Task 0. On a 20-core box all five run
concurrently under 1 GB each; measured wall clock was 230, 579, 625, 724, and 1032 seconds.

- [ ] **Step 3: Check `rank` separately, because the corpus moves**

The frozen ranking means Step 2 never exercises `rank`. Test it on its own, comparing per-project
entries rather than the corpus-wide header, which legitimately changes as the corpus grows.

```bash
mkdir -p /workspaces/pdomain/.extraction-rank-check
cd /workspaces/pdomain/pdomain-pgdp-measure
uv run pgdp-measure rank /workspaces/pdomain-data/pgdp-corpus \
  --output /workspaces/pdomain/.extraction-rank-check/rank-check.json \
  --project-limit 5000 --pages-per-project 5000
python3 - <<'PY2'
import json
a = json.load(open('/workspaces/pdomain/.extraction-baseline/ranking-full-allpages.json'))
b = json.load(open('/workspaces/pdomain/.extraction-rank-check/rank-check.json'))
ba = {p['project_id']: p for p in a['projects']}
bb = {p['project_id']: p for p in b['projects']}
shared = sorted(set(ba) & set(bb))
differ = [k for k in shared
          if json.dumps(ba[k], sort_keys=True) != json.dumps(bb[k], sort_keys=True)]
print('added to corpus since baseline:', sorted(set(bb) - set(ba)))
print('removed since baseline:', sorted(set(ba) - set(bb)))
print('shared projects:', len(shared), 'differing:', len(differ), differ[:5])
PY2
```

Expected: `differing: 0`. Projects added or removed since the baseline are corpus drift, not a
finding. Any shared project whose entry differs is a real behaviour change in `rank`.

- [ ] **Step 4: Compare against the baseline**

```bash
cd /workspaces/pdomain/.extraction-verify
find . -type f \( -name '*.json' -o -name '*.jsonl' -o -name '*.png' \) -print0 \
  | sort -z | xargs -0 sha256sum | sed 's| \./| |' > verify-manifest.txt
diff /workspaces/pdomain/.extraction-baseline/baseline-manifest.txt verify-manifest.txt \
  && echo "BYTE IDENTICAL — EXTRACTION IS CLEAN"
```

Expected: `BYTE IDENTICAL — EXTRACTION IS CLEAN`, with no diff output.

**If the diff is non-empty, stop.** Do not proceed to Task 6, and do not adjust the baseline to
match. A difference means the move changed behaviour, and the difference itself is the finding.
Report which files differ and at which stage the chain first diverges.

- [ ] **Step 5: Record the result**

Write the outcome into the new package's `docs/architecture/` or `README.md`, naming the baseline
commit from Task 0 and stating that all five books reproduced byte for byte.

- [ ] **Step 6: Commit**

```bash
cd /workspaces/pdomain/pdomain-pgdp-measure
git add -A && git commit -m "docs: record byte-identical reproduction of the pre-move baseline"
```

## Task 6: Remove the library from pdomain-ocr-synth

Only start this after Task 5 printed `BYTE IDENTICAL`.

**Files:**

- Delete: `src/pdomain_ocr_synth/pgdp/` — 33 modules
- Delete: `tests/test_pgdp_*.py` and `tests/test_cli_*_pgdp.py` — 37 files
- Delete: `tests/fixtures/pgdp_*` — 4 directories
- Delete: `schemas/` — 8 files
- Modify: `src/pdomain_ocr_synth/cli.py` — remove five subparsers and eleven lazy imports
- Modify: `tests/test_cli.py`, `tests/test_spec_docs.py`
- Modify: `pyproject.toml`

**Interfaces:**

- Consumes: nothing. This task only removes.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
def test_pgdp_subcommands_are_gone() -> None:
    """Measurement moved to pdomain-pgdp-measure; synth must not offer it."""
    from pdomain_ocr_synth.cli import build_parser

    parser = build_parser()
    actions = [a for a in parser._actions if a.dest == "command"]  # noqa: SLF001
    choices = set(actions[0].choices)
    assert not {c for c in choices if c.endswith("-pgdp")}
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd /workspaces/pdomain/pdomain-ocr-synth && uv run pytest tests/test_cli.py::test_pgdp_subcommands_are_gone -v`

Expected: FAIL. Five `-pgdp` subcommands are still registered.

- [ ] **Step 3: Remove the code**

```bash
cd /workspaces/pdomain/pdomain-ocr-synth
git rm -r -q src/pdomain_ocr_synth/pgdp schemas
git rm -q tests/test_pgdp_*.py tests/test_cli_*_pgdp.py
git rm -r -q tests/fixtures/pgdp_alignment tests/fixtures/pgdp_geometry \
              tests/fixtures/pgdp_glyphs tests/fixtures/pgdp_typography
```

Then edit `src/pdomain_ocr_synth/cli.py` by hand: delete the five `add_parser` blocks and their
five handler functions, and the module docstring lines at 15 and 16 naming M14 and M15, and the
comment at 33 to 34 about `DEFAULT_EVIDENCE_PAGES_PER_BOOK`.

```bash
grep -in 'pgdp' src/pdomain_ocr_synth/cli.py || echo "CLI IS CLEAN"
```

Expected: `CLI IS CLEAN`.

- [ ] **Step 4: Clean the two shared tests**

```bash
grep -n 'pgdp' tests/test_spec_docs.py tests/test_cli.py
```

Remove each PGDP reference. `test_spec_docs.py` asserts documented commands exist, so its command
list must lose the five entries.

- [ ] **Step 5: Run the tests and watch them pass**

```bash
cd /workspaces/pdomain/pdomain-ocr-synth
uv run pytest -n auto
```

Expected: all pass, with roughly 37 fewer test files.

- [ ] **Step 6: Update the packaging and the docs that name the schemas**

`make schema` regenerates `docs/specs/recipe.schema.json` and is unaffected, since that is the
recipe schema and not a PGDP one. Check whether any Make target or `pyproject.toml` entry
references `schemas/`:

```bash
grep -rn 'schemas/' Makefile pyproject.toml .github/workflows/ || echo "NO REFERENCES"
```

Fix any that appear.

- [ ] **Step 7: Run the full gate**

```bash
cd /workspaces/pdomain/pdomain-ocr-synth && make ci AI=1
```

Expected: `✅ ci passed`.

- [ ] **Step 8: Commit**

```bash
cd /workspaces/pdomain/pdomain-ocr-synth
git add -A
git commit -m "refactor: remove the pgdp measurement library, now its own package"
```

## Task 7: Repoint the documentation

**Files:**

- Modify: `docs/architecture/pgdp-ranking-and-review-queue.md`,
  `pgdp-observed-geometry-profiling.md`, `pgdp-source-line-alignment.md`,
  `pgdp-font-free-typography.md`, `pgdp-glyph-inventory.md`
- Modify: `docs/plans/README.md`, `docs/context/current-state.md`, `docs/context/intent-map.md`
- Modify: `docs/usage/recipe-workflow.md`
- Modify: `docs/plans/2026-09-05-pgdp-per-book-glyph-inventory.md`

**Interfaces:**

- Consumes: nothing.

- [ ] **Step 1: Decide where the five architecture docs live**

They describe contracts the new package now owns, so they move to it. Their `Promotes:` lines and
tombstones stay accurate. Move them, and leave a short pointer section in
`docs/plans/README.md` naming the new repository.

```bash
SYNTH=/workspaces/pdomain/pdomain-ocr-synth
DST=/workspaces/pdomain/pdomain-pgdp-measure/docs/architecture
mkdir -p "$DST"
cd "$SYNTH"
git mv docs/architecture/pgdp-ranking-and-review-queue.md "$DST/" 2>/dev/null || \
  cp docs/architecture/pgdp-*.md "$DST/"
```

Handle the remaining four the same way. In the new package they need their relative links
rewritten, since `../specs/` and `../context/` targets do not exist there yet.

- [ ] **Step 2: Update every command string in the usage doc**

```bash
cd /workspaces/pdomain/pdomain-ocr-synth
grep -n 'rank-pgdp\|profile-pgdp\|align-pgdp\|typography-pgdp\|glyphs-pgdp' docs/usage/recipe-workflow.md
```

Replace each with the `pgdp-measure` form, or move the section wholesale to the new package's own
usage doc if the section is entirely PGDP.

- [ ] **Step 3: Update the roadmap**

In `docs/plans/README.md`, the M15 slice table's "current truth" column now points into another
repository. State that plainly and give the new repository's name.

- [ ] **Step 4: Move the M15f plan**

It is the one live PGDP plan, and its open Gate 3 belongs with the code.

```bash
cd /workspaces/pdomain/pdomain-ocr-synth
git mv docs/plans/2026-09-05-pgdp-per-book-glyph-inventory.md \
  /workspaces/pdomain/pdomain-pgdp-measure/docs/plans/ 2>/dev/null || true
```

Append a tombstone to `docs/context/decisions.md` recording the move and naming the new path.

- [ ] **Step 5: Verify the doc graph**

```bash
cd /workspaces/pdomain/pdomain-ocr-synth
uv run --no-project --with docgraph docgraph reindex
uv run --no-project --with docgraph docgraph check --strict
```

Expected: no dangling references, no missing frontmatter.

- [ ] **Step 6: Run the gate and commit**

```bash
make ci AI=1
git add -A
git commit -m "docs: repoint PGDP documentation at the measurement package"
```

## Task 8: Decide the transition dependency

The spec leaves open whether `pdomain-ocr-synth` keeps a dependency on the measurement package
during the transition, or cuts over at once. After Task 6 the synth repository imports nothing
from it, so the honest default is no dependency.

- [ ] **Step 1: Confirm nothing imports it**

```bash
cd /workspaces/pdomain/pdomain-ocr-synth
grep -rn 'pdomain_pgdp_measure' src/ tests/ || echo "NO IMPORTS — NO DEPENDENCY NEEDED"
```

- [ ] **Step 2: Leave `pyproject.toml` without the dependency**

Add nothing. A dependency the package does not import is a claim it cannot support, the same
reasoning that removed the `nicegui` extra on 2026-09-06.

- [ ] **Step 3: Report the decision to the owner**

State that the cutover was clean and no transition dependency was needed, so that open decision in
the spec can be closed.

## Verification

The extraction is complete when all of these hold:

- [ ] Task 5 printed `BYTE IDENTICAL — EXTRACTION IS CLEAN` for all five books.
- [ ] `make ci AI=1` passes in `pdomain-ocr-synth`.
- [ ] The full gate passes in `pdomain-pgdp-measure`.
- [ ] `docgraph check --strict` reports no dangling references in either repository.
- [ ] `grep -rn 'pgdp' src/pdomain_ocr_synth/` returns nothing.
- [ ] The new package's import test confirms cv2, torch, doctr, and nicegui stay unimported.
- [ ] Task 0's page counts are reported to the owner, whatever they showed.

## Risks

**The baseline may not reproduce.** Task 0 Step 6 tests this before any code moves. If determinism
does not hold today, this plan cannot verify itself and must stop.

**The corpus may be unavailable.** Every task from 0 onward needs
`/workspaces/pdomain-data/pgdp-corpus`. Confirmed present on 2026-09-06 with 324 projects,
including all five aligned books. Re-confirm before starting, since it is an external mount.

**The `--geometry` records are external and per-book.** The OCR witness reads records produced
by `pdomain-source-data`, at `/workspaces/pdomain-data/typography/geometry-v1/<BOOK>.jsonl`, one
file per book. Both scripts resolve that path the same way and fail loudly if the file is absent,
because a baseline captured with the witness and a verification captured without it would differ
for reasons unrelated to the move. Confirmed present for all five books on 2026-09-06.

**Task 7 is the least mechanical.** Moving documentation across repositories breaks relative links
in both directions, which is the same failure that archiving three handoffs caused on 2026-09-06.
Run `docgraph check --strict` in both repositories, not just one.
