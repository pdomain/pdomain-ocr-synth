# 05 — Text transforms

## Agent Index

- **Kind:** spec
- **Status:** partial
- **Owner:** CT
- **Created:** 2026-05-05
- **Last verified:** 2026-07-14
- **Provenance:** agent-verified from repository evidence during the 2026-07-14 docgraph migration
- **Disposition:** Retained because shipped behavior and unresolved intent both remain.

Transforms run on the concatenated corpus text **before** tokenization. They
are an ordered list; each transform sees the output of the previous one.

## Current implementation status

Ordered transforms, seeded execution, Gaelic conversions, aliases, and
third-party entry-point registration ship in
`src/pdomain_ocr_synth/text_transforms/` and `tests/test_text_transforms.py`.

`u_v_swap`, `i_j_swap`, and `ct_st_ligature_marker` are not implemented.
Recipe-relative Python transforms and renderer consumption of `ct`/`st`
markers are also unsupported. Probability granularity varies by transform;
the universal per-token wording below is not a current guarantee.

```yaml
text_transforms:
  - normalize_whitespace
  - apply_lenition_dots:
      mode: aggressive
  - tironian_et:
      probability: 0.7
  - long_s_medial:
      probability: 0.85
```

A bare string uses defaults. A mapping `{name: {options}}` overrides them.

## Built-in: generic

### `normalize_whitespace`
Collapses runs of whitespace; preserves paragraph breaks. No options.

### `lowercase` / `uppercase`
Self-explanatory. No options.

### `strip_punctuation`
Removes Unicode `P*` categories. Useful for dictionary-style word lists.

### `nfc` / `nfd` / `nfkc` / `nfkd`
Unicode normalization forms.

### `regex_replace`
General-purpose substitution.

```yaml
- regex_replace:
    pattern: '\bMr\.\s'
    replacement: 'Mr '
    flags: ''
```

### `keep_only`
Drop all characters not in the allowed set:

```yaml
- keep_only:
    chars: "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ '"
```

Useful as a last-resort guard against codepoints no font in the recipe
covers.

### `min_token_length` / `max_token_length`
Drops words shorter/longer than the limit after whitespace tokenization.
Acts as a corpus filter, not an in-place edit.

## Built-in: Gaelic / pre-reform Irish

### `apply_lenition_dots`

Convert digraphs (`bh`, `ch`, `dh`, `fh`, `gh`, `mh`, `ph`, `sh`, `th`) to
the corresponding dotted consonants (`ḃ`, `ċ`, `ḋ`, `ḟ`, `ġ`, `ṁ`, `ṗ`, `ṡ`,
`ṫ`).

```yaml
- apply_lenition_dots:
    mode: aggressive          # aggressive | conservative
    probability: 1.0
```

| Mode | Behavior |
|------|----------|
| `conservative` | Only converts when followed by a vowel and not part of a known English digraph |
| `aggressive` | Converts every matched digraph |

If the corpus is already in pre-reform spelling, skip this transform.

### `tironian_et`

Replace `agus` (Irish "and"), `and`, or `et` with the Tironian sign `⁊`,
with optional probability so the corpus stays mixed.

```yaml
- tironian_et:
    replace_words: ["agus", "and", "et"]
    probability: 0.7
    case_sensitive: false
```

### `long_s_medial`

Replace `s` with `ſ` (long s) in word-medial position only — never word-
final, never before another `s`. Models early-modern typographic
conventions.

```yaml
- long_s_medial:
    probability: 0.85
```

### `seimhiu_to_dot` / `dot_to_seimhiu`

Bidirectional: convert between séimhiú-h notation (`bh`) and dotted
notation (`ḃ`). `apply_lenition_dots` is a thin alias for `seimhiu_to_dot`
with default options.

## Built-in: scriptio continua / antique conventions

### `u_v_swap` / `i_j_swap`

Random interchange of `u`↔`v` and `i`↔`j` per early-modern conventions.

```yaml
- u_v_swap:
    probability: 0.3
    contexts:
      - word_initial             # apply v→u only word-initially, etc.
```

### `ct_st_ligature_marker`

Tag `ct` and `st` so the renderer can substitute the OpenType `liga`
feature even when the font's default doesn't enable it. (No visible
character change; sets internal markers consumed by the renderer.)

## Probabilities and ordering

- A transform with `probability: p` is applied per-token (or per-match)
  with that probability, drawn from the recipe seed.
- Order matters. `normalize_whitespace` should run first so later
  transforms see consistent input.
- Codepoint-level transforms (`apply_lenition_dots`, `long_s_medial`)
  should run after digraph-aware transforms.

## Custom transforms

A transform is a Python callable
`(text: str, options: dict, rng: Random) -> str`, registered with the
`pdomain_ocr_synth.text_transforms` entry point. See
[09 — Extending](09-extending.md) for the full contract.

For one-off transforms, drop a `transforms.py` next to the recipe file and
reference it inline:

```yaml
text_transforms:
  - python:
      module: ./transforms.py
      callable: my_transform
      options:
        foo: bar
```

The module is loaded relative to the recipe directory and is not
auto-installed system-wide.

## Adversarial Review

- **Stage and source:** Migration-time post-implementation review of the document, repository
  history, code, tests, and linked plans. Evidence included 5d23fc1,
  src/pdomain_ocr_synth/text_transforms/builtins.py,
  src/pdomain_ocr_synth/text_transforms/pipeline.py,
  src/pdomain_ocr_synth/text_transforms/registry.py, src/pdomain_ocr_synth/validation.py,
  tests/test_text_transforms.py.
- **Accepted findings:** All generic and Gaelic transforms needed by the bundled recipe shipped,
  including ordering, seeded probabilities, aliases, registry loading, and tests. The
  antique-convention group and inline Python loader remain catalog-only and are rejected by
  validation, so the spec is only partially implemented.
- **Effect on this document:** Status: `partial`. Retained for unresolved intent; the original
  design is not fully shipped truth.
- **Implementation deviations:** u_v_swap, i_j_swap, and ct_st_ligature_marker are
  unimplemented. Recipe-relative python transforms are unimplemented; third-party entry-point
  registration is the actual extension seam. ct/st marker consumption by the renderer does not
  exist. Probability semantics vary by transform implementation rather than following one
  universal per-token rule.
- **Residual risks:** Implement or explicitly abandon the antique-convention transforms and
  inline loader. Preserve transform order, deterministic RNG flow, Gaelic conversion semantics,
  and entry-point registry architecture. Clarify per-transform probability granularity in
  permanent reference docs.
