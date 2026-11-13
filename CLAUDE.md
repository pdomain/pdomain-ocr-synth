# CLAUDE — pdomain-ocr-synth

## Agent Index

- **Kind:** process
- **Status:** active
- **Owner:** CT
- **Created:** 2026-05-09
- **Last verified:** 2026-11-12
- **Provenance:** agent-verified from repository evidence during the 2026-07-14 docgraph migration;
  guidance and linked local entry points checked on 2026-11-07. The status paragraph and the
  milestone rule were pointed at the roadmap on 2026-11-12.
- **Disposition:** Retained as authoritative repository guidance.

Start with [`AGENTS.md`](AGENTS.md) for the guidance chain and
[`DOCGRAPH.md`](DOCGRAPH.md) for documentation governance.

Recipe-driven synthetic OCR training-data generator; produces labeled
image+text pairs for historical and specialty typography (first target:
Cló Gaelach / early Irish). Shipped behavior is in `docs/architecture/`.
The only schedule is [the roadmap](docs/plans/README.md). PGDP measurement
left this repo on 2026-09-07 for `pdomain-pgdp-measure`; this repo renders
and publishes. Its future labeled-dataset input contract is still unspecified.

## Commands

| recipe | does |
|---|---|
| `AI=1 just setup` | `uv sync --locked --group all-dev` + pre-commit hooks |
| `AI=1 just test` | `uv run pytest -n auto` |
| `AI=1 just lint` / `AI=1 just lint-fix` | ruff fixes + Markdown lint; `lint-fix` also fixes Markdown |
| `AI=1 just format` | ruff format only |
| `AI=1 just ci` | setup → pre-commit → lint-check → typecheck → test → build → strict docgraph |
| `AI=1 just schema` | regenerate `docs/specs/recipe.schema.json` from pydantic models |
| `just fetch-fonts` | download Gaelic fonts (interactive — do not run non-interactively) |
| `AI=1 just gaelic-preview` | render 50 preview samples for the Gaelic recipe (requires M07) |
| `AI=1 just build` | wheel + sdist into `dist/` |

`AI=1 just <recipe>` captures verbose output to `.ci-ai.log`. It prints
`PASS: <recipe>` on success, or a failure line and filtered failure sections.
Remove `AI=1` only if you need full verbose output for debugging.

## Rules

- Always run `AI=1 just ci` before committing.
- Use just recipes first; fall back to `uv run …` only when no recipe exists.
- Never `python -m pytest`. Always `uv run pytest -n auto` or `just test`.
  Bare `python`/`python3`/`.venv/bin/python` miss the venv.
- The schedule is [the roadmap](docs/plans/README.md). Do not add scope beyond it.
- Before writing any code, read the relevant milestone spec and plan end-to-end and propose a plan.
- If pydantic recipe models change, run `just schema` to regenerate `docs/specs/recipe.schema.json`.
- Never commit fonts — they are user-provided and license-sensitive; `just fetch-fonts` is interactive by design.
- Recipes live in `recipes/` as YAML; schema is in `docs/specs/recipe.schema.json`.
- Output contract is captured in
  [`docs/architecture/output-and-publishing.md`](docs/architecture/output-and-publishing.md)
  under "The trainer profile contract, captured" — confirm from `../pdomain-ocr-training/`
  before changing the output adapter. `pd-ocr-trainer`, the repo the contract was
  originally measured from, is retired; `pdomain-ocr-training` supersedes it and reads
  this same profile shape.

## Specs

Shipped behavior is in `docs/architecture/`. The schedule is `docs/plans/README.md`.
Other files in `docs/plans/` and `docs/specs/` are records, not a second schedule.

## Sibling repos

- `../pdomain-ocr-training/` — consumes synth output; reads the profile directory layout
  this repo must match. Supersedes the retired `pd-ocr-trainer`. Layout-model training stays there.
- `../pdomain-ocr-labeler-spa/` — human review of pages, regions, and glyphs.
- `../pdomain-book-contracts/` — shared annotation types.
- `../pdomain-book-tools/` — shared OCR and page primitives, including the glyph-annotation model.
- `../pdomain-pgdp-measure/` — the PGDP measurement library, extracted from this repo on
  2026-09-07. It owns scan geometry, alignment, typography, and glyph cutting, and the
  `pgdp-measure` CLI. This repo cut over in one step and keeps no dependency on it.

## GH issues

Cross-cut work tasks are tracked as GH issues in
**`ConcaveTrillion/ocr-container-meta`** (not in this repo's own tracker).
Plans under `docs/plans/` in the workspace root are synced there
via `/decompose-spec --sync`. Milestone naming: `spec: <plan-basename> (#N)`.

When shipping a plan task:

- Before starting: `gh issue view <N> --repo ConcaveTrillion/ocr-container-meta`
- After completing: `gh issue close <N> --repo ConcaveTrillion/ocr-container-meta`
- List open tasks:
  `gh issue list --repo ConcaveTrillion/ocr-container-meta --milestone "spec: <name> (#N)" --state open`

## docs/ folder

This repo follows the workspace docs/ template — see [`docs/README.md`](docs/README.md). Active
folders: `architecture/`, `decisions/`, `plans/`, `process/`, `research/`,
`runbooks/`, `specs/`, `templates/`, `usage/`. Retired docs live in Git history.
There is no `docs/archive/` tree.

**Superpowers redirect.** When a superpowers skill (e.g. `brainstorming`,
`writing-plans`) instructs you to save to `docs/superpowers/specs/<file>.md`
or `docs/superpowers/plans/<file>.md`, save to `docs/specs/<file>.md` or
`docs/plans/<file>.md` instead. There is no `docs/superpowers/` subdirectory
in this repo.

<!-- workspace-process:start -->

## Before coding

These steps are workspace defaults for any coding task. **User-level settings
override them** — a user's own `~/.claude/CLAUDE.md`, `settings.json`, or a
direct instruction in the conversation takes precedence and may waive or
change any step below.

### Working principles

- **Use skills.** Invoke the relevant superpowers skill before starting —
  process skills first (`brainstorming`, `systematic-debugging`,
  `writing-plans`, `test-driven-development`), then implementation skills.
  If a skill applies, using it is not optional.
- **Write clearly.** Follow `docs/process/writing-style.md` for direct user
  updates, handoffs, final summaries, docs, reports, issue text, PR text, and
  user-facing copy. Keep agent communication short, clear, and easy to scan.
- **Delegate by default.** Dispatch subagents for non-trivial work: per-repo
  agents for repo changes, `Explore` for code searches. This keeps large tool
  output out of the parent context.
- **Parallelize.** Run independent tasks as concurrent subagents — multiple
  agent calls in a single message. Set `model: sonnet` on implementers and
  reviewers.

### Steps

1. **Check the working tree.** `git status --short`. Surface or resolve stray
   uncommitted work before starting — don't build on it.
2. **Read repo guidance.** This repo's `CLAUDE.md` and `CONVENTIONS.md` for
   repo-specific rules.
3. **Consult `docs/` for authoritative context** (whichever folders exist):
   `plans/` (the work plan), `specs/` (design specs — follow any `Spec:`
   pointer from the issue), `research/` (prior investigations), `decisions/`
   (ADRs / constraints), `architecture/` (shipped design).
4. **Check live issue status.** `gh issue view <N> --repo <owner/repo>` —
   confirm it isn't already closed; note its milestone.
5. **Check for in-flight work.** Open PRs and existing branches touching the
   same area, to avoid colliding with work-in-progress.
6. **Consult agent memory.** `.claude/agent-memory/<repo>/feedback_*.md` for
   corrections not yet promoted to `CONVENTIONS.md`.
7. **Locate code with `Explore` first.** Use an `Explore` subagent to find
   relevant files before broad `Read`/grep.
8. **Isolate in a worktree.** Never work directly in the interactive checkout
   at `/workspaces/ocr-container/<repo>/`. Use the `using-git-worktrees` skill
   to set up an isolated worktree. When delegating to a full-power
   implementation agent, pass `isolation: "worktree"` on the `Agent` call
   (skip for `-docs` agents and the `driver` agent). When an agent returns a
   worktree path + branch, use the `finishing-a-development-branch` skill to
   decide how to integrate.
9. **TDD.** Write the failing test first where the plan calls for it.
10. **Verify before committing.** Focused verification plus `just ci`.
11. **Commit locally; do not push** without explicit say-so.

<!-- workspace-process:end -->
