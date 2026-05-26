# M01 — Dev tooling parity

**Goal:** every developer command another workspace project supports
works in this one. After this milestone, the project has zero behavior
but full development ergonomics — a contributor can `make setup &&
make test && make lint` and get green on the empty package.

This milestone is intentionally heavy-weighted. Every later milestone
benefits from skipping ahead until tooling is solid.

## Deliverables

### `Makefile` parity with `pd-ocr-trainer`

Adopt the same target catalog, with the same emoji + help-text style:

- [x] `help` — auto-generated from `##` comments
- [x] `setup` — `uv sync --group all-dev` then
      `uv run pre-commit install` (the dev-env target)
- [x] `install` / `uninstall` — `uv tool install --reinstall .` /
      `uv tool uninstall pdomain-ocr-synth` (puts the CLI on PATH for
      end-users, separate from dev setup)
- [x] `remove-venv`, `reset`, `reset-full`, `upgrade-deps`
- [x] `upgrade-deps` MUST honor the dev-local detection contract in
      [13 — Dev-local mode and dependency upgrades](../specs/13-dev-local-mode-and-deps.md):
      probe `uv pip show pdomain-book-tools` for `Editable project location`,
      fall back to a `.venv/pd-dev-local` marker, last-resort
      `PD_DEV_LOCAL=1` env var; refuse-with-message when dev-local is
      detected, leave canonical-mode behavior unchanged, and ship a
      sibling `upgrade-deps-local` target. Deferred until the
      Makefile / `dev-local` recipe lands; this milestone owns it.
- [x] `test`, `test-verbose`, `test-single` (parameterized)
- [x] `lint`, `lint-fix`, `format`, `pre-commit-check`
- [x] `ci` — what GitHub Actions runs (lint + test)
- [x] `build`, `clean`, `clean-cache`
- [x] `release-patch`, `release-minor`, `release-major`, `_do-release`
- [x] **Project-specific:** `gaelic-preview` (already in stub),
      `fetch-fonts` (wraps `scripts/fetch-fonts-gaelic.sh`)

Reference: `pd-ocr-trainer/Makefile`. Keep the help-text formatting
identical so the look is consistent across the workspace.

### `pyproject.toml` dependency groups

Match the peer pattern of multiple optional groups:

- [x] `[dependency-groups]` (uv-style) or
      `[project.optional-dependencies]`:
  - `testing` — pytest, pytest-cov, pytest-xdist
  - `linting` — ruff, pre-commit
  - `all-dev` — superset; what `make setup` uses
- [x] Pinned `python-doctr`-equivalent: pin `huggingface_hub`,
      `datasets`, `pillow`, `uharfbuzz`, `freetype-py`, `httpx`,
      `pyyaml`, `pydantic`, `beautifulsoup4`, `lxml`, `numpy`,
      `opencv-python`, `tqdm` in `dependencies`.
- [x] Add `[tool.coverage]` config (mirror peer).

### `.pre-commit-config.yaml`

- [x] Hooks matching peer projects:
  - `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`,
    `check-added-large-files`
  - `ruff` (lint + format)
- [x] `make pre-commit-check` wires it to CI.

### `src/pd_ocr_synth/` skeleton

- [x] `__init__.py` with `__version__`
- [x] `__main__.py` for `python -m pd_ocr_synth`
- [x] `cli.py` — argparse / typer stub with `--version`, `--help`,
      and unimplemented subcommands that print "not implemented yet"
      and exit 2.
- [x] Console script registered in `pyproject.toml`:
      `pdomain-ocr-synth = "pd_ocr_synth.cli:main"`.

### `tests/`

- [x] `tests/conftest.py` with shared fixtures (`tmp_path`-style helpers)
- [x] `tests/test_smoke.py` — `pdomain-ocr-synth --version` returns 0
- [x] `tests/test_cli.py` — every subcommand prints help with `--help`
- [x] Markers config in `pyproject.toml`: `unit`, `integration`, `slow`,
      `gpu`

### CI: `.github/workflows/ci.yml`

- [x] Mirror `pd-ocr-trainer`'s workflow exactly:
  - Trigger: PRs and pushes to `main`
  - Setup uv, sync deps
  - Run `make ci`
- [x] Cache uv downloads.
- [x] Single Linux runner (no GPU, no Mac/Windows for now).

### Setup is `make setup`

We deliberately do **not** ship a `dev-env-setup.sh`. The peer
`pd-ocr-trainer/dev-env-setup.sh` is a legacy artifact from before
the uv-based Makefile (it uses `python3 -m venv` + `pip install
-r requirements.txt`). For pdomain-ocr-synth, `make setup` is the
complete dev environment setup, and `make fetch-fonts` is the
optional follow-up. `make install` is reserved for actually
installing the CLI as a uv tool — semantic separation that matches
`pd-ocr-labeler`'s convention. A single source of truth (the
Makefile) keeps developer expectations from drifting.

### Devcontainer integration (optional but matches workspace)

- [ ] If the workspace devcontainer auto-discovers projects, ensure
      `pdomain-ocr-synth` is included in any post-create steps. Otherwise
      defer to a workspace-level change. **Deferred — low priority.**

## Validation criteria

```bash
git clone .../pdomain-ocr-synth
cd pdomain-ocr-synth
make setup        # green; venv built; pre-commit installed
make test         # green; smoke + cli help tests pass
make lint         # green
make build        # green; produces dist/
pdomain-ocr-synth --version   # prints "pdomain-ocr-synth 0.0.1"
pdomain-ocr-synth render gaelic
# → "render: not implemented yet" (exit 2)
```

CI on a freshly opened PR runs `make ci` and is green.

## Out of scope

- Recipe loading, validation, rendering — all deferred to M02+.
- Any actual subcommand behavior beyond stubs.
- GPU CI — irrelevant for synth (CPU rendering).

## Risks / open items

- **`uv` group syntax drift.** If peer projects already migrated from
  `[project.optional-dependencies]` to `[dependency-groups]` (uv 0.5+),
  match the more recent style.
- **Pre-commit hook drift.** Lock to the same hook versions as peers
  to keep formatting consistent across the workspace.
- **Codecov / coverage upload.** If peers do this in CI, mirror it;
  if not, skip.
