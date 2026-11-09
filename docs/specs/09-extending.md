# 09 — Extending

## Agent Index

- **Kind:** spec
- **Status:** partial
- **Owner:** CT
- **Created:** 2026-05-05
- **Last verified:** 2026-11-07
- **Provenance:** rechecked 2026-11-07 against corpus/registry.py, text_transforms/registry.py,
  degradation/pipeline.py, and pyproject.toml. Inline and degradation entry-point sections remain proposals.
- **Disposition:** Retained because shipped behavior and unresolved intent both remain.

This design considers corpus providers, text transforms, and degradation
stages as extension points.

## Current implementation status

Corpus providers and text transforms load package entry points through
`src/pdomain_ocr_synth/corpus/registry.py` and
`src/pdomain_ocr_synth/text_transforms/registry.py`.

Inline module-path extensions are not supported. Degradation stages have an
internal registry but no entry-point loader. Per-extension schema negotiation,
validation hooks, isolation, and the advertised testing helpers are also
unimplemented. Broken third-party entry points are skipped rather than
reported through the clear migration feedback described below.

## Inline (per-recipe) extensions

Deferred proposal: load one-off code next to the recipe by module path, relative to the recipe directory.
The YAML below is not accepted as a runnable extension by the current recipe model and registries.

```yaml
text_transforms:
  - python:
      module: ./transforms.py
      callable: my_transform
      options:
        threshold: 0.5

corpus:
  - type: python
    module: ./providers.py
    callable: pull_my_corpus
    options:
      tag: irish

degradation:
  - kind: python
    module: ./degradations.py
    callable: my_stage
    probability: 0.5
    options: {}
```

The proposed inline extensions would apply only within their recipe, without changing the global registry.
No such isolation mechanism is implemented.

## Package extensions (entry points)

Corpus and text-transform registries discover these package entry-point groups:

```toml
[project.entry-points."pdomain_ocr_synth.corpus_providers"]
my_corpus = "my_pkg.providers:MyCorpus"

[project.entry-points."pdomain_ocr_synth.text_transforms"]
my_transform = "my_pkg.transforms:my_transform"

```

Discovery is lazy, when a registry lists its entries or misses a lookup. A new corpus discriminator
still requires a recipe-model change; entry-point loading does not extend the Pydantic corpus union.

Degradation entry-point discovery remains a proposal; the current runtime does not load this group:

```toml
[project.entry-points."pdomain_ocr_synth.degradation_stages"]
my_stage = "my_pkg.degradation:my_stage"
```

## Interface — corpus provider

```python
from typing import Iterable
from pdomain_ocr_synth.corpus import ProviderContext

class MyCorpus:
    type_name = "my_corpus"
    schema_version = 1

    def fetch(self, ctx: ProviderContext, options: dict) -> Iterable[str]:
        """
        Yield UTF-8 strings (one logical chunk per yield — typically a
        document or a page). The framework concatenates and tokenizes
        downstream.
        """
        ...

    def cache_key(self, options: dict) -> str:
        """Stable key for the on-disk cache. Distinct configs → distinct keys."""
        ...
```

`ProviderContext` exposes:

| Attr | Type | Purpose |
|------|------|---------|
| `recipe_dir` | `Path` | For resolving relative paths |
| `cache_dir` | `Path` | Where to write cache files |
| `cache` | `CacheStore` | Cache metadata and content access; `cache_dir` returns its root |
| `http` | `object` or `None` | Optional caller-supplied HTTP object; no client is guaranteed |
| `offline` | `bool` | If true, raise instead of fetching |
| `logger` | `Logger` | Structured logger |

## Interface — text transform

```python
from random import Random

def my_transform(text: str, options: dict, rng: Random) -> str:
    """Pure function: text in, text out. Use rng for any randomness."""
    ...
```

Transforms must be deterministic given the rng. They run on the full
concatenated corpus (post-fetch, pre-tokenization).

## Interface — degradation stage

These are the internal registry's callable shapes. Loading them through package entry points remains unimplemented.

```python
from PIL import Image
from random import Random

def my_stage(image: Image.Image, options: dict, rng: Random) -> Image.Image:
    """Image in, image out. Use rng for any randomness."""
    ...
```

Stages may also accept and return ground-truth metadata when geometry
changes. The richer signature:

```python
from pdomain_ocr_synth.render.sample import RenderedSample

def my_stage(sample: RenderedSample, options: dict, rng: Random) -> RenderedSample:
    """For stages that affect geometry (skew, perspective, scale)."""
    ...
```

`RenderedSample` carries the image plus all bounding boxes; geometric
stages must update boxes consistently. Pixel-only stages (blur, noise,
JPEG) use the simpler `Image -> Image` form.

## Validation hooks

Deferred proposal: let a custom extension opt into recipe validation. The hook below is not called by the current CLI:

```python
def validate(options: dict, ctx: ValidationContext) -> list[ValidationIssue]:
    """Return zero or more issues. Empty list = OK."""
```

The proposed hook would run during `pdomain-ocr-synth validate` to surface problems before rendering.

## Versioning the registry

The corpus provider protocol declares `schema_version`:

```python
class MyCorpus:
    type_name = "my_corpus"
    schema_version = 1
```

The current loader does not compare a provider's version with the recipe's version.
Rejecting mismatches with a migration prompt remains deferred.

## Testing your extension

The proposed `pdomain_ocr_synth.testing` module is not shipped. Its intended helpers are:

- `make_recipe(...)` — minimal recipe builder
- `dummy_rng()` — deterministic RNG
- `tiny_corpus(text)` — in-memory provider for tests
- `tmp_destination()` — pytest fixture for isolated output dirs

A custom extension's test suite should cover:

1. The happy path (input produces expected output).
2. Determinism under a fixed seed.
3. Validation surfacing user errors with helpful messages.
4. Behavior when `offline=True` (for providers).

## Boundaries (what extensions can't do)

- Frozen Pydantic models block attribute reassignment, but nested lists and dictionaries remain mutable.
  Extensions should not mutate that configuration.
- The proposed restriction to `cache_dir`, `recipe_dir`, and `output.destination` is not enforced by a sandbox.
- Providers must honor `ctx.offline` themselves; the registry does not prevent their network calls.

The filesystem and network restrictions are intended extension obligations, not guarantees supplied by
`validate` or `--dry-run`.

## Adversarial Review

- **Stage and source:** Migration-time post-implementation review of the document, repository
  history, code, tests, and linked plans. Evidence included c2c25da: M03 corpus registry
  scaffold, 7dae047: web provider and HTTP infrastructure, bbe9d8e: Wikisource provider,
  src/pdomain_ocr_synth/corpus/registry.py, src/pdomain_ocr_synth/text_transforms/registry.py,
  src/pdomain_ocr_synth/degradation/pipeline.py.
- **Accepted findings:** Two package extension mechanisms exist: corpus providers and text
  transforms lazily load the documented entry-point groups. The overall spec is not implemented
  because inline module-path extensions, degradation-stage entry-point discovery, extension
  validation hooks, registry schema negotiation, and the advertised pdomain_ocr_synth.testing
  helpers are absent.
- **Effect on this document:** Status: `partial`. Retained for unresolved intent; the original
  design is not fully shipped truth.
- **Implementation deviations:** The corpus Provider protocol differs from the prose example and
  runtime fetch path; text transforms use the registry contract but no general inline-python
  recipe shape exists. Degradation has an internal registry/pipeline but no importlib
  entry-point loader for pdomain_ocr_synth.degradation_stages. Recipe schema_version validates
  the recipe format, not per-extension schema compatibility. Extension loading silently skips
  broken third-party entry points, so the promised clear validation/migration feedback is not
  delivered.
- **Residual risks:** Decide whether third-party extensibility remains a product goal. If yes,
  narrow and implement the missing degradation, validation, versioning, isolation, and testing
  contracts. If no, supersede this broad plugin design with documentation of only the two
  supported registries.
