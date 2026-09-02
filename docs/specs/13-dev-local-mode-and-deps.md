# 13 — Dev-local mode and dependency upgrades

## Agent Index

- **Kind:** spec
- **Status:** draft
- **Owner:** CT
- **Created:** 2026-05-07
- **Last verified:** 2026-07-14
- **Provenance:** agent-verified from repository evidence during the 2026-07-14 docgraph migration
- **Disposition:** Retained as deferred design pending implementation.

This spec captures a workspace-wide hazard around `uv sync` and how
`pdomain-ocr-synth` must behave once the Makefile gains an `upgrade-deps`
target (already stubbed in M01) so it does not silently undo a
contributor's local development setup.

Status: **spec only**. Implementation is **deferred until the Makefile
`dev-local` recipe lands**; the requirement is hooked into M01 (see
[development and recipe architecture](../architecture/development-and-recipe-system.md)) so that
whichever milestone introduces the dev-local recipe across the
workspace also lands the detection logic here.

## Current implementation status

This draft is not implemented. `Makefile` has no sibling-editable probe,
dev-local marker check, `PDOMAIN_DEV_LOCAL` guard, refusal path, or
`upgrade-deps-local` target. Its current `upgrade-deps` target runs `uv lock
--upgrade` followed by an unconditional sync.

The claimed workspace-wide editable dependency invariant is not established by
this repository, and the archived M01 plan did not deliver the trigger assumed
below. Revalidate that external contract before implementing this safeguard.

## Background

Across the workspace, several `pd-*` repos can be put into a
**dev-local** mode where the project's `.venv` resolves sibling `pd-*`
projects as **editable installs from the local checkout** (instead of
the canonical published wheels), pins to **GPU extras**, or pulls
`python-doctr` from a git ref. This is how cross-repo work happens —
e.g. exercising an unreleased `pdomain-book-tools` change from
`pdomain-ocr-training`, or running a synth recipe against a local
`pdomain-ocr-training` profile writer.

The hazard: a plain `uv sync --group <something>` (the last step of
`make upgrade-deps`) will resolve against `pyproject.toml` /
`uv.lock` and **silently revert** that environment back to the
canonical, published, CPU-only configuration. Editable sibling installs
disappear, GPU extras drop out, doctr-from-git collapses to the pinned
release. The contributor only finds out when their next test run
unexpectedly fails to pick up changes in a sibling repo.

`pdomain-ocr-synth` does not (today) install editable sibling pd-* repos —
its only direct workspace coupling is the **output contract** `pdomain-ocr-training`
reads (originally harmonized against the retired `pd-ocr-trainer`'s
`dataset_store.py`; see [Output and
publishing](../architecture/output-and-publishing.md)), not a runtime dependency.
However:

1. Future milestones may add an editable `pdomain-book-tools` or
   `pdomain-ocr-training` install for integration tests (e.g. round-tripping
   a synth recipe through the trainer's dataset reader).
2. The standardized fix should be uniform across all `pd-*` Makefiles
   so contributors see the same UX everywhere. Diverging here would
   itself be the bug.

So this spec captures the contract now, even though the synth repo
won't exercise the dev-local code paths until a later milestone needs
editable siblings.

## Required behavior

The behavior below applies to **whatever `upgrade-deps`-style target
runs `uv sync`** in this repo's Makefile. It is written so the same
text drops cleanly into peer repos (`pdomain-book-tools`, `pdomain-ocr-cli`,
`pdomain-ocr-training`, `pd-ocr-labeler`, `pdomain-ocr-labeler-spa`,
`pdomain-prep-for-pgdp`, `pd-png-optimizer`).

### 1. Detect dev-local vs canonical before `uv sync`

Before the implicit `uv sync` step in `upgrade-deps` (or any other
target that calls `uv sync` on an existing `.venv`), the Makefile MUST
detect whether the current `.venv` is in **dev-local** or **canonical**
mode and branch on the result. No `uv sync` may run unconditionally
against an existing `.venv` from `upgrade-deps`.

### 2. Detection mechanism (ordered fallbacks)

Detection probes in this order, taking the first signal found:

1. **Primary — sibling editable probe.** Run
   `uv pip show pdomain-book-tools` and look for an
   `Editable project location:` line whose value is a path under the
   workspace root (i.e. a sibling `pdomain-book-tools/` checkout).
   `pdomain-book-tools` is the cross-repo contract anchor: every other pd-*
   that participates in dev-local mode pins it editable, so its
   editable status is a reliable proxy for the whole environment.
   If `uv pip show pdomain-book-tools` fails or returns no
   `Editable project location:` line, fall through to (2).
2. **Fallback — venv marker file.** If `.venv/pdomain-dev-local` exists
   (a zero-byte sentinel written by `make upgrade-deps-local` /
   the dev-local setup recipe), treat as dev-local. This covers
   environments where `pdomain-book-tools` legitimately is not installed
   (e.g. a synth-only contributor) but the developer has explicitly
   opted into dev-local extras (GPU, doctr-from-git).
3. **Last resort — env var.** If `PDOMAIN_DEV_LOCAL=1` is set in the
   shell, treat as dev-local. Useful for CI runs that
   programmatically opt into dev-local without pre-creating the
   marker.

If none of (1)/(2)/(3) signal dev-local, the venv is **canonical**.

### 3. UX contract

- **Default `make upgrade-deps`:** when dev-local is detected, the
  target MUST refuse with a clear message and exit non-zero **before**
  running `uv sync`. Recommended message:

  > Detected dev-local venv (editable pdomain-book-tools / marker /
  > PDOMAIN_DEV_LOCAL). `make upgrade-deps` would revert this environment
  > to canonical published deps. Use `make upgrade-deps-local`
  > instead, or remove the marker / unset PDOMAIN_DEV_LOCAL to opt into a
  > canonical refresh.

  The message MUST name the detection signal that triggered the
  refusal so the contributor can remediate it.

- **Sibling target `make upgrade-deps-local`:** runs `uv lock
  --upgrade` then re-applies the dev-local installation recipe
  (editable siblings, GPU extras, doctr-from-git as applicable to
  this repo). For pdomain-ocr-synth specifically the dev-local recipe is
  TBD until a milestone needs it; until then `upgrade-deps-local`
  may simply alias the canonical sync with a banner noting that
  no dev-local extras apply yet.

- **Canonical mode:** behavior of `make upgrade-deps` is unchanged
  from today — `uv lock --upgrade` followed by
  `uv sync --group all-dev`.

### 4. Cross-platform

Detection and refusal logic MUST work on Linux, macOS, and any
Windows shell currently supported by the Makefile (treat `bash` as
the lowest common denominator; do not depend on GNU-only utilities
beyond `grep` / `test`). The marker file path uses POSIX-style
`.venv/pdomain-dev-local`; on Windows uv venvs the equivalent path under
`.venv\` is acceptable.

## Why pdomain-book-tools as the anchor

The probe deliberately targets `pdomain-book-tools` rather than this
repo's own metadata because:

- `pdomain-book-tools` is the foundation library every other `pd-*` depends
  on, so its editable install is the single most reliable signal that
  the venv is wired for cross-repo work.
- Anchoring on a sibling means the same Makefile snippet works
  identically across the workspace — no per-repo customization of the
  primary probe, which is the whole point of standardizing.
- Probing `pdomain-ocr-synth` itself is uninformative: a contributor doing
  pure synth work may still install `pdomain-ocr-synth` editable inside
  its own venv without that implying any dev-local intent.

The marker file and env var exist to cover legitimate cases where
`pdomain-book-tools` is absent but dev-local intent is real.

## Out of scope for this spec

- The exact shell snippet for the detection (left to the Makefile
  PR that lands the implementation; the contract above is the spec).
- The `dev-local` recipe contents for pdomain-ocr-synth (no editable
  siblings yet — added when a future milestone introduces them).
- Migrating other workspace repos; this spec describes pdomain-ocr-synth's
  share of the standardized fix.

## Adversarial Review

- **Stage and source:** Migration-time design-stage review of the document, repository history,
  code, tests, and linked plans. Evidence included d19975b: captured the deferred dev-local
  contract, Makefile:64 upgrade-deps unconditionally runs uv lock --upgrade then uv sync --group
  all-dev, Makefile: no upgrade-deps-local target, pyproject.toml and uv.lock: canonical
  dependency sources and
  [Development and recipe system](../architecture/development-and-recipe-system.md).
- **Accepted findings:** The hazard is plausible and the intended safeguard is explicit, but the
  document itself says spec only and deferred, and no current editable sibling dependency makes
  the path exercised here. The Makefile directly contradicts the MUST-level behavior by syncing
  unconditionally. Draft best represents worthwhile but uncommitted future design.
- **Effect on this document:** Status: `draft`. Retained as deferred design, not current
  behavior.
- **Implementation deviations:** No sibling editable probe, .venv/pdomain-dev-local marker
  check, PDOMAIN_DEV_LOCAL check, refusal path, signal-specific message, or upgrade-deps-local
  target exists. The claimed workspace-wide invariant that every participating pd-* repo pins
  pdomain-book-tools editable is external and not established by this repository. The archived
  M01 plan did not deliver this requirement, so its implementation trigger is stale.
- **Residual risks:** Before any editable sibling/GPU/git-ref development mode is introduced,
  revalidate the workspace standard and add a small tested guard around upgrade-deps. Until
  then, retain the hazard and UX requirement but discard assumptions about exact sibling anchors
  that are not current in this repo.
