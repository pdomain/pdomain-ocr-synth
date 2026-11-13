# Recipe loading, extension points, lint, and audit

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Owner:** CT
- **Created:** 2026-11-13
- **Last verified:** 2026-11-13
- **Provenance:** promoted from partial specs 02, 05, 07, and 09 and plan 10 after fresh source/test inspection.
  Evidence names below are inspected tests, not a claim that sibling suites or manual visual checks ran.
- **Disposition:** Current runtime contracts; unfinished features remain in their partial specs and the roadmap.

Recipe loading resolves local configuration before rendering. Extension points, lint, and audit add behavior
without changing the recipe-to-image sequence described in [Synthesis pipeline](synthesis-pipeline.md).

## Loading and preset expansion

The loader requires a YAML mapping, resolves recipe-relative paths, expands degradation presets, and validates
the resulting Pydantic model. It keeps the source path separately for provenance.

A degradation preset is local to one recipe. Its stages expand in order at the reference site.
Unknown names fail during loading. Expansion is one pass; nested presets are not a supported feature.
This does not turn a schema-accepted stage into an implemented stage.

Transform steps each receive a separate random generator derived from the recipe seed and step index.
One transform cannot consume another step's random state.
Transform probability is implemented by each callable, rather than by a shared pipeline gate.
Degradation differs: its ordered stages use the sample's shared random generator.
A stage's random draws can therefore affect later degradation gates.

## The supported plugin boundary

Corpus providers and text transforms have working package entry-point registries.
This does not establish the broader plugin system proposed in spec 09.

A corpus provider exposes its type name, schema version, fetch method, and cache-key method.
Its fetch call receives recipe-directory and cache access, an offline flag, logging, and optional HTTP access.
The context is an interface for cooperative providers, not a sandbox or a guarantee that a plugin obeys offline mode.

Provider discovery is lazy. Failures while discovering or importing an entry point are skipped.
Registering a distinct provider under an existing type name raises an error.
These behaviors must not be confused with a general promise that every plugin failure is isolated.

Transform callables receive text, options, and their step generator, and return text.
Recipe-local Python loaders, degradation entry-point discovery, registry schema negotiation,
and public testing helpers remain deferred. Their contracts remain in [spec 09](../specs/09-extending.md).

## Semantic validation and recipe lint

Loading validates model shape. Semantic validation reports runtime support and asset problems.
It performs no network requests, so the accepted offline flag does not suppress an additional network phase.

The lint CLI combines semantic validation findings with recipe-lint warnings.
The seven warning checks cover degradation probabilities, font diversity, transform configuration,
small sample counts, zero-weight fonts, all-optional fonts, and the default seed of zero.
Strict lint makes warnings fail; validation errors retain their stronger exit status.
The JSON report keeps the same findings regardless of strictness.

## Audit is a separate output contract

Rendering appends an audit row to the output's audit log and normally mirrors it to the global cache log.
The row records the recipe identity and source digest, seed, output directory, run outcome, and schema version.
It is operational evidence, not a substitute for the per-sample manifest.

The global log is under the configured corpus cache root, or
`~/.cache/pdomain-ocr-synth/audit.jsonl` by default.
`PD_OCR_SYNTH_NO_AUDIT=1` disables both logs.
`PD_OCR_SYNTH_NO_GLOBAL_AUDIT=1` disables only the global mirror.
Audit reads close the file and skip unsupported schema versions with a warning.
Timestamp comparisons normalize offsets before filtering.

The usage reference documents [audit filters and summaries](../usage/recipe-workflow.md).
Image digest tests pin renderer output; they do not make audit timestamps or wall time deterministic.
Updating golden image digests still requires a human visual check.
The pending manual and cross-version checks remain in [plan 10](../plans/10-stretch.md).

## Evidence

- Code: `src/pdomain_ocr_synth/recipe/loader.py`, `recipe/paths.py`,
  `text_transforms/pipeline.py`, `corpus/context.py`, `corpus/registry.py`,
  `text_transforms/registry.py`, `degradation/pipeline.py`, `lint.py`, `audit.py`, and `cli.py`.
- Tests: `tests/test_recipe_loader.py`, `tests/test_text_transforms.py`,
  `tests/test_degradation.py`, `tests/test_lint.py`, `tests/test_audit.py`,
  `tests/test_audit_global.py`, `tests/test_cli_audit.py`, and `tests/test_render_visual_regression_e2e.py`.
- Verified: 2026-11-13 from source and fresh independent analyzer records at base `d4baa99`.
  The local baseline suite passed 788 tests with 314 skips. Skipped font and opt-in tests remain skipped.
