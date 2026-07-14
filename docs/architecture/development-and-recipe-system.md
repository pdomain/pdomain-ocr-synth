# Development and recipe system

## Agent Index

- **Kind:** architecture
- **Status:** active
- **Owner:** CT
- **Created:** 2026-07-14
- **Last verified:** 2026-07-14
- **Provenance:** verified from the shipped source, tests, Make targets, and cited commits during the docgraph migration
- **Disposition:** Current truth promoted from implemented M01 and M02 plans and CLI/spec documentation.
- **Promotes:** implemented M01/M02 plans and specs 01/03.

The repository ships a Make- and `uv`-based development workflow and a typed,
recipe-driven CLI. The current recipe-author workflow is in
[Recipe workflow](../usage/recipe-workflow.md); this document records the
implementation contracts and why they exist.

## Development workflow

`make setup` runs `uv sync` and installs pre-commit hooks. `make lint`,
`make format`, `make typecheck`, `make test`, `make build`, and `make ci` are
the supported gates. `make ci` performs setup, pre-commit, formatting,
type-checking, tests, and package build. `AI=1` captures verbose output in
`.ci-ai.log`. `make schema` regenerates the committed JSON Schema from the
Pydantic models. The managed workflows in `.github/workflows/` use the same
locked environment and Make targets.

Dependency state comes from `pyproject.toml` and `uv.lock`. The current
`upgrade-deps` target upgrades the lock and syncs it; it does not implement the
deferred dev-local protection described by spec 13. Fonts are user-supplied
licensed assets, and the interactive `make fetch-fonts` path is deliberately
outside automated setup.

## Recipe model and loading

`src/pdomain_ocr_synth/recipe/models.py` defines the Pydantic recipe graph.
`load_recipe()` in `recipe/loader.py` reads YAML with PyYAML, validates it, and
resolves recipe-relative paths through `recipe/paths.py`. Resolved models are
frozen so a run cannot silently mutate configuration. The loader retains the
source path for snapshots and provenance.

The checked-in `docs/specs/recipe.schema.json` is generated from those models;
it is an interoperability artifact, not a second schema authority. Runtime
validation in `validation.py` distinguishes malformed recipes, missing required
assets, optional missing fonts, unsupported catalog values, and network-aware
checks. A schema-accepted future provider or transform can therefore still be
rejected as not implemented.

## CLI contract

`pdomain-ocr-synth` is the supported command surface. It provides `init`,
`list`, `validate`, `lint`, `describe`, `schema`, `fetch`, `preview`, `render`,
`publish`, `audit`, and `clean`. Each subcommand owns its options; `fetch`, for
example, accepts cache controls but not render count, output, seed, worker, or
dry-run controls. `preview` and `render` share render-family options, while
`publish --render-first` accepts the relevant overrides for its chained run.

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

- Code: `Makefile`, `pyproject.toml`, `.pre-commit-config.yaml`,
  `.github/workflows/ci.yml`, `src/pdomain_ocr_synth/cli.py`,
  `src/pdomain_ocr_synth/recipe/`, `src/pdomain_ocr_synth/recipe_init.py`, and
  `src/pdomain_ocr_synth/validation.py`.
- Tests: `tests/test_cli.py`, `tests/test_recipe_loader.py`,
  `tests/test_validation.py`, `tests/test_recipe_schema_artifact.py`, and
  `tests/test_package.py`.
- Commits: `445c493`, `dde147a`, `29c26c9`, `14bdbde`, `1f3bd61`, and
  `332e36a`.
- Verified: 2026-07-14 by repository inspection during the docgraph migration.
