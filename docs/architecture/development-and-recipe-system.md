# Development and recipe system

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-11-12
- **Provenance:** verified from the shipped source, tests, Make targets, and cited commits during the docgraph
  migration; the GitHub Actions sentence was re-checked on 2026-11-06 against commit `0068970` and the absence of
  `.github/workflows/`. Recipe mutability, validation, and CLI behavior were rechecked against code on 2026-11-07.
- **Disposition:** Current truth promoted from implemented M01 and M02 plans and CLI/spec documentation.
- **Promotes:** implemented M01/M02 plans and specs 01/03.

The repository ships a `just` and `uv` development workflow and a typed,
recipe-driven CLI. The current recipe-author workflow is in
[Recipe workflow](../usage/recipe-workflow.md); this document records the
implementation contracts and why they exist. How a loaded recipe becomes an
image is [Synthesis pipeline](synthesis-pipeline.md).

## Development workflow

`just setup` runs `uv sync --locked --group all-dev` and installs pre-commit hooks.
`just lint` fixes imports and lint issues; `just format` formats Python only.
`just lint-check` checks formatting and lint without changing files.
`just ci` runs setup, pre-commit, lint-check, typecheck, test, build, and strict docgraph.
`AI=1 just <recipe>` captures the full output in `.ci-ai.log` and prints one result line.
On failure, it also prints filtered failure sections.

`just schema` regenerates the committed JSON Schema from the Pydantic models.
GitHub Actions workflows were removed on 2026-09-13 in
commit `0068970`. `just ci` is the local gate.

Dependency state comes from `pyproject.toml` and `uv.lock`. The current
`upgrade-deps` recipe refuses when either supported local-mode marker exists,
then upgrades the lock and syncs it. The broader dev-local detection in spec 13 remains deferred.
The supported markers are `.pdomain-local-mode` and `.pdomain-dev-local` under
`UV_PROJECT_ENVIRONMENT`, or `.venv` when that variable is unset.
Fonts are user-supplied licensed assets, and the interactive `just fetch-fonts` path is deliberately
outside automated setup.

## Recipe model and loading

`src/pdomain_ocr_synth/recipe/models.py` defines the Pydantic recipe graph.
`load_recipe()` in `recipe/loader.py` reads YAML with PyYAML, validates it, and
resolves recipe-relative paths through `recipe/paths.py`. Resolved models are
frozen against attribute reassignment, but nested lists and dictionaries remain mutable. The loader retains the
source path for snapshots and provenance.

The checked-in `docs/specs/recipe.schema.json` is generated from those models;
it is an interoperability artifact, not a second schema authority. Runtime
validation in `validation.py` distinguishes malformed recipes, missing required
assets, optional missing fonts, and unsupported catalog values. Validation does not access the network;
its `offline` argument is currently a no-op. A schema-accepted future provider or transform can therefore still be
rejected as not implemented.

## CLI contract

`pdomain-ocr-synth` is the supported command surface. It provides `init`,
`list`, `validate`, `lint`, `describe`, `schema`, `fetch`, `preview`, `render`,
`publish`, `audit`, and `clean`. Each subcommand owns its options; `fetch`, for
example, accepts cache controls but not render count, output, seed, worker, or
dry-run controls. `preview` and `render` share render-family options, while
`publish --render-first` uses the recipe's count and seed and accepts only the publish command's options,
including its local-output override. It does not expose the render command's count, seed, worker, or cache controls.

Recipes remain the only persistent configuration surface. CLI flags are
bounded run-time overrides or operational controls. This split makes snapshots
and repeated runs explainable without creating a second configuration format.
Use `pdomain-ocr-synth <command> --help` as the exhaustive parser-generated
reference; [Recipe workflow](../usage/recipe-workflow.md) documents the normal
path.

## Implementation deviations

The shipped tooling grew beyond the M01 draft: basedpyright, stricter Ruff,
format checking, `AI=1` capture, hatch-vcs packaging, and managed workflow
checks were added. No repository-local devcontainer was added. PyYAML remained
the parser, so error locations come from Pydantic rather than ruamel round-trip
metadata. Offline validation evolved with corpus behavior, while a fresh Gaelic
recipe may still fail validation until its user-supplied font assets exist.

The scaffold command creates a recipe directory with `recipe.yaml`, `README.md`,
and `corpora/`, `fonts/`, and `textures/` directories. The repository's bundled
Gaelic example remains a single `recipes/gaelic.yaml` file plus adjacent asset
directories, which is also supported.

## Evidence

- Code: `justfile`, `pyproject.toml`, `.pre-commit-config.yaml`,
  `src/pdomain_ocr_synth/cli.py`,
  `src/pdomain_ocr_synth/recipe/`, `src/pdomain_ocr_synth/recipe_init.py`, and
  `src/pdomain_ocr_synth/validation.py`.
- Tests: `tests/test_cli.py`, `tests/test_recipe_loader.py`,
  `tests/test_validation.py`, `tests/test_recipe_schema_artifact.py`, and
  `tests/test_package.py`.
- Commits: `445c493`, `dde147a`, `29c26c9`, `14bdbde`, `1f3bd61`, and
  `332e36a`.
- Verified: 2026-11-07 against the recipe models, CLI parser and handlers, validation, and Make targets.

## Further runtime contracts

[Recipe runtime contracts](recipe-runtime-contracts.md) records preset expansion, random-state ownership,
working extension points, lint, and audit. The broader unbuilt proposals remain in their partial specs.
