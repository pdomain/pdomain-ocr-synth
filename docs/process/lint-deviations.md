# Lint-rule Deviations — pdomain-ocr-synth

## Agent Index

- **Kind:** process
- **Status:** active
- **Owner:** CT
- **Created:** 2026-05-22
- **Last verified:** 2026-07-14
- **Provenance:** agent-verified from repository evidence during the 2026-07-14 docgraph migration
- **Disposition:** Retained as current intent or process guidance.

Standing lint-rule suppressions and per-file overrides in this repo. Each entry
records the rule, tool, affected files, and justification. **Update this file
whenever a suppression changes**: `tests/test_lint_deviations_doc.py` checks
exact locations, markers, and inline rationales across `src/`, `scripts/`, and
`tests/`.

Most suppressions trace to the 2026-05-17 strict-linting rollout, which
expanded `ruff` and switched `basedpyright` to `recommended` mode. The
annotation/docstring backlog (`ANN` / `D`) was deferred per-file rather
than fixed in a single sweep — that cleanup is tracked by
[`pdomain/pdomain-ocr-synth#3`](https://github.com/pdomain/pdomain-ocr-synth/issues/3).

---

## 1. Global `ruff` ignores

Codes in `[tool.ruff.lint]` `ignore` — suppressed repo-wide.

| Code | Rule | Justification |
|------|------|---------------|
| `E501` | line-too-long | Long docstrings, error messages, and URLs; 88-char wrapping adds noise without improving readability. |
| `D203` | 1-blank-before-class-docstring | Conflicts with `D211`; pick one of the pair. |
| `D212` | multi-line-summary-first-line | Conflicts with `D213`; pick one of the pair. |
| `D100` | missing-docstring-in-public-module | Large existing codebase; add incrementally, not in a lint sweep. |
| `D104` | missing-docstring-in-public-package | Same — package `__init__.py` docstring backlog. |
| `D107` | missing-docstring-in-`__init__` | Same — backlog. |
| `D101` | missing-docstring-in-public-class | Docstring backlog; defer. |
| `D102` | missing-docstring-in-public-method | Docstring backlog; add incrementally. |
| `D103` | missing-docstring-in-public-function | Docstring backlog; add incrementally. |
| `D105` | missing-docstring-in-magic-method | `__repr__`, `__eq__`, etc. are self-documenting; require on new code only. |
| `D202` | no-blank-lines-after-docstring | Autofix would touch 200+ locations; defer. |
| `D205` | 1-blank-line-between-summary-and-description | Too noisy across the docstring backlog for one commit. |
| `D413` | missing-blank-line-after-last-section | Large backlog; defer. |
| `PLR0911` | too-many-return-statements | Render-pipeline functions legitimately have high return counts. |
| `PLR0912` | too-many-branches | Render-pipeline functions legitimately have high branch counts. |
| `PLR0913` | too-many-arguments | Render/corpus functions need many params; enforcing forces invasive config-object refactors. |
| `PLR0915` | too-many-statements | Render-pipeline functions legitimately have high statement counts. |
| `PLR2004` | magic-value-comparison | Common in OCR geometry/threshold code. |
| `PLC0415` | import-not-at-top-level | Deferred imports are a deliberate pattern — avoid loading optional-heavy modules (`uharfbuzz`, `freetype-py`, `pillow`) until needed. |
| `ANN401` | dynamically-typed-expressions (`Any`) | Recipe-value samplers and degradation dispatch legitimately accept/return `Any`. |
| `TRY003` | long-message-outside-exception-class | Too noisy for a codebase that uses f-string error messages everywhere. |
| `COM812` | missing-trailing-comma | Conflicts with the `ruff` formatter auto-style. |

`ANN101` / `ANN102` (self/cls annotations) appear commented-out in
`pyproject.toml` — those rules were removed in `ruff >= 0.2`; the entries
are kept only to avoid errors under older `ruff` versions.

---

## 2. Per-file `ruff` ignores

Codes in `[tool.ruff.lint.per-file-ignores]`. The dominant group is the
**ANN/D/G/BLE/TRY/TC deferred backlog** — see issue #3.

### 2.1 Tests — `tests/**/*.py`, `tests/*.py`

Ignored: `S101 S105 S106 S311 T201 ANN D PLR2004 PT011 PT018 PT019 S108
PLR0133 PLR1714 PLW2901 PERF401 TRY BLE RET TC G PLC0206 S110 S112`.

`assert` is the test idiom (`S101`); magic numbers are common (`PLR2004`);
test functions need no annotations/docstrings (`ANN`, `D`); security rules
are relaxed because hardcoded passwords/random (`S105/S106/S311`) are test
fixtures; `pytest.raises(match=)` is not required everywhere (`PT011`);
`/tmp` paths are fine in tests (`S108`); trivial/constant comparisons can
be intentional (`PLR0133`, `PLR1714`); loop-var reassignment is a pattern
(`PLW2901`); list-building loops are fine (`PERF401`); blind/try-except
relaxed for fixture teardown (`TRY`, `BLE`, `S110`, `S112`); `print` is
allowed (`T201`); `RET`, `TC`, `G`, `PLC0206` relaxed as test ergonomics.

### 2.2 Scripts — `scripts/*.py`

Ignored: `T201 D S607 ANN BLE TRY RET TC`. `print()` is the script output
mechanism; no docstrings required; `S607` (partial executable path) is
idiomatic when invoking system tools (`uv`, `git`).

### 2.3 Package `__init__.py` — `**/__init__.py`

Ignored: `D104 F401 TC`. Re-exports without docstrings; `F401` is the
public-API-surface re-export pattern. `publish/__init__.py` additionally
ignores `ANN`.

### 2.4 Private modules — `**/_*.py`

Ignored: `D`. Internal-convention modules; no docstrings required.

### 2.5 Typography modules — `RUF002` / `RUF003`

`src/pdomain_ocr_synth/render/paragraph.py` and
`tests/integration/test_trainer_dataset_contract.py` ignore `RUF002`
(and `paragraph.py` also `RUF003`): typography docs use `×`
(MULTIPLICATION SIGN) as the standard unit notation for line-height
multipliers; replacing it with `x` would be less precise.

### 2.6 ANN/D/G/BLE/TRY/TC deferred backlog — `src/pdomain_ocr_synth/**`

The 2026-05-17 rollout added ~55 per-file-ignores so the strict-lint
config could land without a 90-minute annotation marathon. Every
`src/pdomain_ocr_synth/` production module carries some subset of
`ANN D G BLE TRY TC` — `ANN` (missing annotations), `D` (missing
docstrings), `G` (logging-format), `BLE` (blind except), `TRY`
(tryceratops), `TC` (type-only imports not yet moved to `TYPE_CHECKING`;
~37 files affected). Each is an implicit TODO; removal is tracked
subpackage-by-subpackage in **issue #3**. The `degradation/` and
`output/` subpackages have been fully cleared and no longer carry any
per-file ignore.

Modules carrying **extra** codes beyond the `ANN D G BLE TRY TC` base set,
with the per-module reason:

| File | Extra codes | Reason |
|------|-------------|--------|
| `cli.py` | `T201` | `print()` is the primary CLI output mechanism. |
| `render/run.py` | `T201 PERF401 PLW0603 S108 S101 S311` | CLI output; worker-init module globals; `assert` in worker; `random` is for visual sampling, not crypto. |
| `render/preview.py` | `PLW0603 S101 S311` | Worker-init globals; `assert`/`random` worker patterns. |
| `render/context.py` | `S311` | `random` is intentional for visual sampling, not crypto. |
| `publish/cli_runner.py`, `publish/dataset_card.py` | `PERF401` | List-building loop is intentional. |
| `publish/summary.py`, `publish/recognition.py` | `PLW2901` | Loop-var reassignment is intentional. |
| `publish/auth.py` | `S105` | Env-var **name** strings are not passwords. |
| `corpus/http.py` | `S` | HTTP-client security rules relaxed for the fetch path. |
| `corpus/providers/web.py` | `TRY300` | `else`-after-`try` not warranted for this control flow. |
| `corpus/registry.py` | `S PLW0603 PLW2901` | Provider-dispatch security; registry module globals; loop-var reassignment. |
| `text_transforms/pipeline.py` | `S311` | `random` is for visual sampling, not crypto. |
| `text_transforms/registry.py` | `PLW0603 S112` | Registry module globals; `continue` in `except`. |
| `render/sampling.py`, `render/sample.py`, `corpus/context.py`, `tokenization.py`, `recipe/models.py` | (subset only) | Carry just `TC` and/or `ANN`/`D` — narrower than the base set. |

---

## 3. `basedpyright` rule-level overrides

In `[tool.basedpyright]`.

| Rule | Setting | Justification |
|------|---------|---------------|
| `reportImportCycles` | `none` | Import cycles are structural and resolved via `TYPE_CHECKING` guards; genuine import-order issues would surface as runtime `ImportError`. |

`failOnWarnings` is **deferred** (commented out): `recommended` mode
surfaces warnings from `uharfbuzz` / `freetype-py` / `pillow` stubs that
lag runtime. Enable incrementally as stub coverage improves.

---

## 4. Inline `# pyright: ignore` suppressions

All forms below are tool-native (`# pyright: ignore[reportRuleName]`),
not mypy codes.

### 4.1 `reportConstantRedefinition`

**Files:** `corpus/registry.py`, `text_transforms/registry.py`,
`degradation/pipeline.py`, `render/run.py`, `render/preview.py`.

Module-level once-per-process flags and `_DEFAULT_REGISTRY` /
`_WORKER_*` globals follow ALL_CAPS naming but are intentionally re-bound
(registry install, worker-process initialisation). They are not true
constants; renaming would hurt readability.

### 4.2 `reportArgumentType`

**Files:** `render/sampling.py`, `render/word_crop.py`, `render/line.py`,
`render/page.py`, `render/paragraph.py`, `render/run.py`,
`corpus/filters.py`, `degradation/builtins.py`, `degradation/pipeline.py`,
`output/detection.py`, `publish/hf_hub_transport.py`.

`sample_value()` returns a recipe-value union (`int | float | spec`);
call sites coerce with `int(...)` / `float(...)` but pyright sees the raw
union before narrowing. Also covers degradation-dispatch payloads and
`bbox`/`polygon` tuple coercions where the runtime shape is correct but
the static type is a broader union.

### 4.3 `reportAttributeAccessIssue`

**Files:** `render/word_crop.py`, `render/context.py`, `render/run.py`,
`corpus/runner.py`, `publish/cli_runner.py`, `degradation/pipeline.py`.

Two categories: (a) `uharfbuzz` (`hb.Face`, `hb.Font`, `hb.Buffer`,
`hb.shape`, …) and `freetype-py` expose attributes their bundled stubs
do not declare; (b) worker round-trip code in `render/run.py` re-hydrates
a `Sample` by assigning fields outside `__init__` — structurally correct
but pyright does not see through the pattern.

### 4.4 `reportReturnType`

**Files:** `degradation/builtins.py`, `degradation/pipeline.py`,
`publish/hf_hub_transport.py`.

Degradation-stage functions and HF card-dict builders return a concrete
type that is a member of, but narrower than, the declared protocol
return union.

### 4.5 `reportCallIssue`

**Files:** `publish/hf_hub_transport.py`, `render/run.py`.

`huggingface_hub` card APIs and an `AuditEntry`-`details` construction
call signatures whose stubs lag the runtime API.

### 4.6 `reportIncompatibleVariableOverride` / `reportGeneralTypeIssues`

**File:** `recipe/models.py` (line ~169).

`Recipe.language` is a **required** `str` that narrows a base-model field
typed `str | None`. The narrowing is intentional — the recipe schema
requires `language` — but pyright flags the override. The inline comment
records the rationale.

---

## 5. Inline `# type: ignore` suppressions

None remain. The 2026-07-14 migration converted production and test sites to
the narrow basedpyright-native `# pyright: ignore[reportRuleName]` form. The
exact occurrence ledger below guards against reintroducing mypy-only codes.

---

## 6. Inline `# noqa` suppressions

| File | Code | Justification |
|------|------|---------------|
| `degradation/pipeline.py` | `F401` | Deferred `import builtins` inside `_ensure_builtins_registered()` — the import is for its registration side effect, not a name. |
| `degradation/pipeline.py` | `PLW0603` | `global _BUILTINS_REGISTERED` — module-level one-time registration guard; the `global` is intrinsic to the idempotency pattern. |

## 7. Exact inline suppression inventory

This migration-time inventory is the exact repository occurrence ledger.
`tests/test_lint_deviations_doc.py` requires every live occurrence, rule
marker, and inline safety rationale to appear here.

| Location | Marker | Inline rationale |
|---|---|---|
| `tests/test_corpus_cache.py:186` | `pyright: ignore[reportUnknownParameterType,reportMissingParameterType]` | spy accepts the dynamic call shape from the code under test |
| `scripts/update_github_actions.py:48` | `noqa: S603` | fixed executable and validated argument list; shell execution is disabled |
| `tests/test_audit.py:265` | `pyright: ignore[reportArgumentType]` | test intentionally supplies a value outside the annotated contract |
| `src/pdomain_ocr_synth/recipe/models.py:169` | `pyright: ignore[reportIncompatibleVariableOverride,reportGeneralTypeIssues]` | required field narrows base str \| None |
| `tests/test_publish_idempotency.py:255` | `pyright: ignore[reportAttributeAccessIssue]` | test intentionally mutates protected state to exercise the failure path |
| `tests/test_render_paragraph_box.py:132` | `pyright: ignore[reportAttributeAccessIssue]` | test intentionally mutates protected state to exercise the failure path |
| `tests/test_validation.py:2034` | `noqa: N802` | test name mirrors the exported uppercase validation constant |
| `tests/test_validation.py:2062` | `noqa: N802` | test name mirrors the exported uppercase validation constant |
| `tests/test_cli_preview.py:556` | `pyright: ignore[reportUnknownParameterType,reportMissingParameterType]` | spy accepts the dynamic call shape from the code under test |
| `tests/test_cli_preview.py:623` | `pyright: ignore[reportUnknownParameterType,reportMissingParameterType]` | spy accepts the dynamic call shape from the code under test |
| `tests/test_fonts.py:109` | `pyright: ignore[reportAttributeAccessIssue]` | test intentionally mutates protected state to exercise the failure path |
| `src/pdomain_ocr_synth/output/detection.py:453` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/output/detection.py:491` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `tests/test_degradation.py:59` | `pyright: ignore[reportArgumentType]` | not used by pipeline |
| `tests/test_degradation.py:480` | `pyright: ignore[reportArgumentType]` | not used by pipeline |
| `tests/test_degradation.py:655` | `pyright: ignore[reportArgumentType]` | not used by pipeline |
| `tests/test_publish_orchestrator.py:486` | `pyright: ignore[reportAttributeAccessIssue]` | test intentionally mutates protected state to exercise the failure path |
| `tests/test_publish_transport.py:149` | `pyright: ignore[reportArgumentType]` | test intentionally supplies a value outside the annotated contract |
| `tests/test_spec_docs.py:527` | `noqa: N802` | test name mirrors the exported uppercase contract constant |
| `tests/test_spec_docs.py:605` | `noqa: N802` | test name mirrors the exported uppercase contract constant |
| `tests/test_spec_docs.py:730` | `noqa: N802` | test name mirrors the exported uppercase contract constant |
| `tests/test_spec_docs.py:838` | `noqa: N802` | test name mirrors the exported uppercase contract constant |
| `tests/test_spec_docs.py:1104` | `noqa: RUF003` | mathematical subset notation is intentional in this explanatory comment |
| `tests/test_recipe_loader.py:85` | `pyright: ignore[reportAttributeAccessIssue]` | test intentionally mutates protected state to exercise the failure path |
| `tests/test_tokenization.py:134` | `pyright: ignore[reportArgumentType]` | test intentionally supplies a value outside the annotated contract |
| `tests/test_tokenization.py:142` | `pyright: ignore[reportArgumentType]` | test intentionally supplies a value outside the annotated contract |
| `tests/test_tokenization.py:240` | `pyright: ignore[reportArgumentType]` | test intentionally supplies a value outside the annotated contract |
| `src/pdomain_ocr_synth/text_transforms/registry.py:89` | `pyright: ignore[reportConstantRedefinition]` | process-local registry or worker state is intentionally installed once |
| `tests/test_corpus_runner.py:185` | `pyright: ignore[reportUnknownParameterType,reportMissingParameterType]` | spy accepts the dynamic call shape from the code under test |
| `tests/test_corpus_runner.py:219` | `pyright: ignore[reportUnknownParameterType,reportMissingParameterType]` | spy accepts the dynamic call shape from the code under test |
| `tests/test_cli_render.py:736` | `pyright: ignore[reportUnknownParameterType,reportMissingParameterType]` | spy accepts the dynamic call shape from the code under test |
| `tests/test_cli_render.py:773` | `pyright: ignore[reportUnknownParameterType,reportMissingParameterType]` | spy accepts the dynamic call shape from the code under test |
| `src/pdomain_ocr_synth/render/page.py:167` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/line.py:88` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/line.py:89` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/line.py:92` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/sample.py:116` | `pyright: ignore[reportUnknownVariableType]` | Pillow returns a two-integer size tuple although its stub exposes an unknown type |
| `src/pdomain_ocr_synth/degradation/pipeline.py:127` | `pyright: ignore[reportArgumentType,reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/degradation/pipeline.py:128` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/degradation/pipeline.py:130` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/degradation/pipeline.py:132` | `pyright: ignore[reportArgumentType,reportReturnType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/degradation/pipeline.py:133` | `pyright: ignore[reportReturnType]` | runtime value is the concrete member required by the declared return contract |
| `src/pdomain_ocr_synth/degradation/pipeline.py:147` | `noqa: PLW0603` | module-level one-time registration guard |
| `src/pdomain_ocr_synth/degradation/pipeline.py:152` | `noqa: F401` | import is required for registration or contract stability, not direct use |
| `src/pdomain_ocr_synth/degradation/pipeline.py:155` | `pyright: ignore[reportConstantRedefinition]` | process-local registry or worker state is intentionally installed once |
| `src/pdomain_ocr_synth/render/preview.py:277` | `pyright: ignore[reportConstantRedefinition]` | process-local registry or worker state is intentionally installed once |
| `src/pdomain_ocr_synth/render/preview.py:278` | `pyright: ignore[reportConstantRedefinition]` | process-local registry or worker state is intentionally installed once |
| `src/pdomain_ocr_synth/render/preview.py:279` | `pyright: ignore[reportConstantRedefinition]` | process-local registry or worker state is intentionally installed once |
| `src/pdomain_ocr_synth/render/preview.py:280` | `pyright: ignore[reportConstantRedefinition]` | process-local registry or worker state is intentionally installed once |
| `src/pdomain_ocr_synth/render/preview.py:281` | `pyright: ignore[reportConstantRedefinition]` | process-local registry or worker state is intentionally installed once |
| `src/pdomain_ocr_synth/degradation/builtins.py:71` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/degradation/builtins.py:72` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/degradation/builtins.py:73` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/degradation/builtins.py:525` | `pyright: ignore[reportReturnType]` | runtime value is the concrete member required by the declared return contract |
| `src/pdomain_ocr_synth/render/run.py:776` | `pyright: ignore[reportConstantRedefinition]` | process-local registry or worker state is intentionally installed once |
| `src/pdomain_ocr_synth/render/run.py:777` | `pyright: ignore[reportConstantRedefinition]` | process-local registry or worker state is intentionally installed once |
| `src/pdomain_ocr_synth/render/run.py:778` | `pyright: ignore[reportConstantRedefinition]` | process-local registry or worker state is intentionally installed once |
| `src/pdomain_ocr_synth/render/run.py:808` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:813` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:814` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:815` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:816` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:817` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:818` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:819` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:820` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:872` | `pyright: ignore[reportArgumentType,reportCallIssue]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/run.py:905` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:906` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:907` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:908` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:909` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:910` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:911` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:912` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:913` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:914` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:915` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:916` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/run.py:919` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:920` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/run.py:923` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/run.py:924` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/context.py:28` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/context.py:29` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/context.py:59` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/word_crop.py:83` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/word_crop.py:84` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/word_crop.py:87` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/word_crop.py:165` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/word_crop.py:169` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/word_crop.py:170` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/word_crop.py:172` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/word_crop.py:174` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/word_crop.py:181` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/word_crop.py:191` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/word_crop.py:196` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/corpus/runner.py:70` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/corpus/runner.py:96` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/paragraph.py:138` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/paragraph.py:139` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/paragraph.py:142` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/paragraph.py:144` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/corpus/registry.py:107` | `pyright: ignore[reportConstantRedefinition]` | process-local registry or worker state is intentionally installed once |
| `src/pdomain_ocr_synth/corpus/filters.py:39` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/publish/cli_runner.py:264` | `pyright: ignore[reportAttributeAccessIssue]` | runtime object provides this attribute but its third-party or reconstructed static shape does not |
| `src/pdomain_ocr_synth/render/sampling.py:61` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/sampling.py:62` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/render/sampling.py:63` | `pyright: ignore[reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/publish/hf_hub_transport.py:201` | `pyright: ignore[reportCallIssue,reportReturnType,reportArgumentType]` | runtime schema or explicit coercion narrows the broader static union |
| `src/pdomain_ocr_synth/publish/hf_hub_transport.py:202` | `pyright: ignore[reportArgumentType,reportReturnType]` | runtime schema or explicit coercion narrows the broader static union |
