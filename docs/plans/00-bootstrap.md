# M00 — Bootstrap

**Goal:** the repo exists, has a remote, and matches the workspace
conventions established by `pd-ocr-trainer` / `pd-ocr-labeler` /
`pdomain-book-tools`. No code yet; this milestone ends with `git clone`
producing a project that *looks* like its peers.

## Deliverables

### Repo & remote

- [x] `git init` inside `pdomain-ocr-synth/` (currently a plain directory in
      the workspace).
- [x] Create empty GitHub repo at `pdomain/pdomain-ocr-synth`
      (matching the pdomain-book-tools owner used by the other projects).
- [x] Add remote and push the initial commit:
      ```bash
      git remote add origin git@github.com:pdomain/pdomain-ocr-synth.git
      git push -u origin main
      ```
- [x] Set the default branch to `main` on GitHub.
- [ ] Add a license file matching peer projects (check what
      `pd-ocr-trainer` ships; mirror it).
      NOTE: no LICENSE file present yet; pyproject.toml declares `license = "Unlicense"` but no file shipped.

### Git config files (mirror the peer pattern)
Copy the *shape* of these from `pd-ocr-trainer/`, adjusting only paths.

- [x] `.gitignore` — Python defaults plus workspace-specific: `.venv/`,
      `dist/`, `htmlcov/`, `.pytest_cache/`, `.ruff_cache/`,
      `recipes/*/cache/`, `recipes/*/preview/`,
      `recipes/**/fonts/`, `recipes/**/textures/`,
      `Makefile.local`. (Most of this already exists in the stub
      `.gitignore`; just add `Makefile.local`.)
- [x] `.gitattributes` — at minimum `* text=auto eol=lf`.
- [x] `.editorconfig` if peers have one (check).

### CLAUDE / DEVELOPMENT / AGENTS
The other projects ship contributor-facing guidance files:

- [ ] `DEVELOPMENT.md` — local setup, common commands, layout map.
      Mirror `pd-ocr-labeler/DEVELOPMENT.md` structure.
      NOTE: not yet created; CLAUDE.md covers most of the same ground.
- [x] `CLAUDE.md` — short, points at `docs/specs/` and `docs/roadmap/`
      so an agent picking up the project knows where to start.
- [x] `AGENTS.md` if peers have one (check `pd-ocr-labeler/AGENTS.md`).

### README pass

- [x] Update the existing `README.md` to mention the GitHub repo URL,
      the install command, and a "see DEVELOPMENT.md for contributors"
      pointer. Keep the spec ToC.

### `pyproject.toml` finalize
The current stub is fine for spec; before pushing add:

- [x] `[project] urls` block with `Homepage`, `Repository`, `Issues`.
- [x] `[project] keywords` for discoverability.
- [x] Owner / maintainers updated to match peer projects.
- [x] Python version aligned (>=3.13 — already set).

## Validation criteria

A new contributor running this works end-to-end:

```bash
git clone git@github.com:pdomain/pdomain-ocr-synth.git
cd pdomain-ocr-synth
ls
```

…and sees the same top-level layout as `pd-ocr-trainer/`: README,
Makefile, pyproject.toml, src/, tests/, docs/, .gitignore,
.gitattributes, DEVELOPMENT.md, CLAUDE.md.

## Out of scope (handled in later milestones)

- `make setup` does not need to actually work yet (M01).
- No source code in `src/` (M01 stub).
- No tests yet (M01).
- Pre-commit hooks (M01).
- CI (M01).

## Risks / open items

- **Repo owner.** If `ConcaveTrillion` isn't the right org for this
  project, decide before pushing. (Peer projects use it; default
  there unless you say otherwise.)
- **License.** All peers should agree on a license; mirror.
- **Initial commit hygiene.** Don't dump everything in one commit;
  split into "initial scaffold," "spec set," "Gaelic recipe + fetch
  script" for a readable history.
