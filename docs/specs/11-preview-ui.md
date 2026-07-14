# 11 — Preview UI (NiceGUI)

## Agent Index

- **Kind:** spec
- **Status:** active
- **Owner:** CT
- **Created:** 2026-05-05
- **Last verified:** 2026-07-14
- **Provenance:** agent-verified from repository evidence during the 2026-07-14 docgraph migration
- **Disposition:** Retained as current intent or process guidance.

A small, preview-focused NiceGUI surface for tuning recipes by sight. The
picker may create a new recipe through the existing CLI. Modifying an existing
recipe requires the separate diff-and-save flow. The CLI remains the contract;
the UI is a faster feedback loop
for the parts of recipe authoring where seeing the result matters most
— degradation tuning, font sampling, and quick coverage checks.

This spec is deliberately scoped tight. Anything that can be done in
VS Code with the recipe JSON Schema (free YAML editing, IntelliSense)
is out of scope. Auth, publishing, and repository mutations other than
the explicit recipe create/save actions are also out of scope.

## Current implementation status

M11 is not implemented. The optional NiceGUI dependency and deterministic
backend preview primitive exist, but there is no UI package, console script,
page, viewmodel, or UI test. See `src/pdomain_ocr_synth/render/preview.py`,
`tests/test_cli_preview.py`, and the current scoping plan.

The current scoping direction builds the UI under `pdomain_ocr_synth.ui` and
presents over `render.preview.run_preview`; the package name still needs owner
confirmation. Diff-and-save is sequenced as M11.5 and introduces `ruamel.yaml`
under the `ui` extra. The older `pdomain_ocr_synth.preview.app`, direct
`render.run_recipe` integration, and M10 cloud-renderer dependency are not
current implementation guidance.

## Goal

Compress the recipe iteration loop from "edit YAML → re-render →
open file manager" to "open page → click regenerate." When the
recipe is structurally correct but you're tuning numbers, the UI
should be the right tool; for everything else, the CLI is.

## Non-goals

- **Free YAML editing.** Use VS Code with `recipe.schema.json` (M02).
- **Auth, publish, fetch flows.** All CLI.
- **Real-time render on keystroke.** Click-to-render is enough; live
  rendering is too much engineering for the value.
- **Multi-user / hosted mode.** Single-user, runs on `localhost`.
- **Dataset browsing.** Once `pdomain-ocr-synth render` produces output,
  the trainer's UI / file system is the right place to inspect it.

## Architecture

Same MVVM + layered pattern used by `pd-ocr-labeler` and
`pd-ocr-trainer`:

```
state         (immutable Recipe + transient PreviewSession)
  ↓
operations    (load_recipe, render_samples, apply_override)
  ↓
viewmodels    (one per page; binds operations to UI components)
  ↓
views         (NiceGUI components)
```

The UI does not duplicate rendering logic. Its presentation layer calls
`pdomain_ocr_synth.render.preview.run_preview(...)` and displays the resulting
`manifest.jsonl` rows alongside their images.

## Run / install

Optional dependency group in `pyproject.toml`:

```toml
[project.optional-dependencies]
ui = ["nicegui>=2.0", "pillow"]
```

Console script:

```toml
[project.scripts]
pdomain-ocr-synth-preview = "pdomain_ocr_synth.ui.app:main"
```

Invocation:

```bash
pdomain-ocr-synth-preview                       # opens on default port
pdomain-ocr-synth-preview --recipe gaelic       # preselects a recipe
pdomain-ocr-synth-preview --port 8765
```

The UI never starts on its own from `pdomain-ocr-synth render` — keeping
them decoupled lets the headless CLI run without a browser handler.

## Surfaces

Three pages. Nothing more in v1.

### `/` — recipe picker

- Lists recipes via the same logic as `pdomain-ocr-synth list`.
- Each row: name, path, layout mode, sample count, last-rendered
  timestamp (from `<destination>/stats.json` if present).
- Click → `/recipe/<name>`.
- "New recipe" button shells out to `pdomain-ocr-synth init <name>` then
  reloads the picker. This creates a new file; it does not modify an existing
  recipe.

### `/recipe/<name>` — recipe view

Two-pane layout:

- **Left pane: config summary.**
  - Resolved recipe block-by-block (corpus, transforms, fonts,
    rendering, layout, degradation).
  - Read-only display; no inline edit.
  - For `degradation`: each stage rendered as a card with a toggle
    (enable/disable for the next render) and a slider for its
    probability (overrides only this preview session).
  - "Reset overrides" button reverts to recipe values.

- **Right pane: sample grid.**
  - Grid of N samples (default 24, configurable up to 200).
  - Each cell shows: rendered image, ground-truth text overlay,
    font name, applied degradations as small chips.
  - Hover/click → opens `/recipe/<name>/sample/<id>`.
  - Top bar: "Regenerate" (new seed), "Re-render" (same seed),
    "Sample count" input, "Render time" indicator.

If the recipe has overrides applied, a banner at the top reads
"Preview overrides active — not saved to recipe." A "Diff & save"
button opens a side panel showing the YAML diff before writing.

### `/recipe/<name>/sample/<id>` — sample detail

- Large image view.
- Full manifest record: corpus key + offset, font + size + DPI, ink
  RGB, background RGB, every applied degradation with its drawn
  parameters.
- "Open in VS Code" link uses `vscode://file/...` to jump to the
  recipe at the relevant section.
- Side-by-side: clean (pre-degradation) and final image, if
  available — useful for spotting where degradation went too far.

## State model

```
PreviewSession
├── recipe: Recipe                 # frozen, loaded from disk
├── overrides: RecipeOverride      # transient; never persisted unless saved
│   ├── stage_enabled: dict[str, bool]
│   └── stage_probability: dict[str, float]
├── last_render: RenderResult
│   ├── tmp_dir: Path
│   ├── samples: list[SampleRecord]
│   ├── seed: int
│   └── wall_time_ms: int
└── selected_sample: str | None
```

Sessions are per browser tab. A page reload discards overrides
(intentional — overrides shouldn't accumulate silently).

## Interactions

### Regenerate / Re-render

- **Regenerate:** new random seed; everything in the grid changes.
- **Re-render:** keep the seed; same input sampling. Useful when
  toggling a single degradation stage to see "this stage on vs. off"
  on the same input.

### Stage toggle / slider

- Toggle off → stage is removed from the pipeline for the next
  render.
- Slider adjusts probability between 0.0 and 1.0; the recipe value
  becomes the slider's default tick.

### "Diff & save"

- Opens a panel with a YAML-style diff (recipe → recipe + overrides).
- "Apply" writes the modified recipe to disk via the recipe loader's
  round-trip (preserves comments where possible — use `ruamel.yaml`).
- "Cancel" closes the panel without saving.

This is the only feature that modifies an existing recipe. The picker also has
the separate, explicit "New recipe" action described above.

## Integration with existing CLI

- The UI imports `pdomain_ocr_synth.render.preview.run_preview` and
  pre-existing recipe loaders. No duplicate code paths.
- The UI never invokes `pdomain-ocr-synth fetch` automatically — if a
  recipe needs network corpora, the CLI must have been run first or
  the cache must already exist. A clear banner says "corpora not
  cached; run `pdomain-ocr-synth fetch <recipe>`" when applicable.
- The UI does not call `pdomain-ocr-synth render` — preview sample counts
  are small (≤200) and the temp directory is short-lived.

## Tests

- Unit: viewmodels can produce expected operations from synthetic
  state changes.
- Integration: spin up the NiceGUI app on a random port,
  programmatically click "Regenerate" via NiceGUI's testing
  utilities, assert grid populated.
- Visual smoke: `make preview-ui-smoke` opens the app, screenshots
  the recipe picker; CI artifact for human review.

## Performance

- Preview render of 50 word-crop samples on CPU should land in a few
  seconds; the UI shows a progress bar via NiceGUI's
  `ui.linear_progress`.
- A `--workers N` flag is plumbed through to the underlying renderer
  (matches the CLI flag).
- Larger grids (200 samples) are acceptable but slower; UI should
  warn before rendering counts over 200.

## Out of scope (recap)

- YAML editor.
- Live edit-as-you-type rendering.
- Auth, publish, fetch.
- Multi-recipe diffing (could be a follow-up).
- Cloud-rendered previews.

## Decisions required before M11.1

1. **Package name.** Confirm the recommended `pdomain_ocr_synth.ui` package or
   choose another name that does not collide with
   `pdomain_ocr_synth.render.preview`.
2. **NiceGUI version.** Keep the current `nicegui>=2.0` minimum or align with
   the sibling labeler's constraint.
3. **Default port.** Confirm the recommended port `8765` or choose another
   localhost default.
4. **Test marker.** Confirm the recommended `ui` marker or choose `nicegui` or
   `preview_ui`.

## Adversarial Review

- **Stage and source:** Migration-time design-stage review of the document, repository history,
  code, tests, and linked plans. Evidence included 852c878: initial M11 spec/plan baseline,
  docs/plans/11-preview-ui.md: milestone not started, docs/plans/11-preview-ui-scoping.md:
  current scoping and package-layout decisions, docs/plans/README.md: M11 not started,
  pyproject.toml: ui optional dependency contains nicegui,
  src/pdomain_ocr_synth/render/preview.py.
- **Accepted findings:** M11 is one of the repository's two remaining milestones. NiceGUI is
  declared as an optional dependency and the deterministic CLI preview renderer provides a base,
  but no UI package, preview console script, pages, viewmodels, or UI tests exist. The design
  remains worthwhile active intent, refined by the later scoping plan.
- **Effect on this document:** Status: `active`. Retained as current intent; unshipped details
  are not current usage.
- **Implementation deviations:** The migration replaced the older `render.run_recipe` and
  `pdomain_ocr_synth.preview.app` instructions with the scoping plan's `render.preview.run_preview`
  and recommended `pdomain_ocr_synth.ui.app` direction. It also separates new-recipe creation from
  modification of an existing recipe and removes the M10 cloud-renderer dependency.
- **Residual risks:** Confirm the package name, NiceGUI version constraint, default port, and test
  marker before M11.1. Preserve recipe browsing, sample inspection, deterministic rerender, and
  transient degradation overrides through the sequenced implementation chunks.
