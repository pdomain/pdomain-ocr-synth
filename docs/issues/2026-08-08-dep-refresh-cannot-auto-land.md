---
Status: active
Owner: CT
Created: 2026-08-08
Last verified: 2026-08-08
Kind: issue
Level: I1
---

# Weekly dep-refresh shares peers' branch-accumulation design, but has never run

## Agent Index

- **Kind:** issue
- **Status:** active
- **Level:** I1
- **Last verified:** 2026-08-08
- **Resolution:** Open
- **Severity:** Low — zero current impact; latent/preventive risk with the same
  shape that left peer repos carrying stray branches
- **Affected version:** `pdomain-ocr-synth` at commit `a625f2d0`;
  `.github/workflows/dep-refresh.yml` added at commit `52287c9` (2026-05-31)
- **Read when:** editing `.github/workflows/dep-refresh.yml` or branch
  protection on `master`, or before assuming the weekly dep-refresh PR will
  land on its own.
- **Search terms:** dep-refresh, auto-merge, delete_branch_on_merge, dated
  branch, GITHUB_RUN_ID, gh pr merge --auto, branch protection, required
  status checks, DEP_REFRESH_TOKEN.
- **Relates to:** design at
  `pdomain-ui:docs/specs/2026-07-16-dep-refresh-auto-land-design.md` and
  sibling report `pdomain-ops:docs/issues/2026-08-08-dep-refresh-cannot-auto-land.md`
  (different repos; not governed links in this graph).

## Summary

`.github/workflows/dep-refresh.yml` in this repo uses the same accumulation-prone
shape documented for peer repos — a fresh dated branch
(`dep-refresh/$(date +%Y-%m-%d)-$GITHUB_RUN_ID`) every run, plus
`delete_branch_on_merge: false` — yet this repo currently shows zero stray
`dep-refresh` branches and zero open dep-refresh PRs. That is not evidence the
design is safe here: the GitHub Actions API confirms the workflow has never
executed a single time, scheduled or manual, since it was added on 2026-05-31.
Zero is dormancy, not cleanup. Separately, this repo's merge gate is sound —
its one required status context matches a check its CI actually produces —
which is not true of two sibling repos that carry the identical dated-branch
defect.

## Impact

- No user-facing breakage today: zero stray branches, zero open PRs, master
  protection resolves cleanly for real PRs (confirmed on merged PR #2, see
  Evidence).
- Latent risk: once the schedule fires or someone runs `workflow_dispatch`,
  the dated-branch-plus-no-delete design will accumulate exactly as it did on
  `pdomain-ops` (seven stray branches, three stuck-open PRs) across the first
  several productive weeks.
- A human already worked around the dormant automation once: commit
  `322aa2d` ("chore: refresh dependencies for master", 2026-07-12) is a
  direct, human-authored push to `master` — not a merged PR from the
  workflow — updating `uv.lock` and workflow pins by hand.
- Whether the workflow can complete a run at all is an open question: this
  repo has no repo-level `DEP_REFRESH_TOKEN` secret (see Evidence), and that
  secret drives the workflow's checkout, push, and `gh pr create`/`merge`
  steps.

## Environment / versions

```text
pdomain-ocr-synth, branch master, commit a625f2d0 (evidence gathered 2026-08-08)
.github/workflows/dep-refresh.yml added at commit 52287c9 (2026-05-31)
  schedule: '0 2 * * 0' (Sunday 02:00 UTC) + workflow_dispatch
.github/workflows/ci.yml: name "ci", single job id "ci" with `name: ci`
GitHub API observations taken 2026-08-08 via gh CLI against pdomain/pdomain-ocr-synth
```

## Evidence

### 1. The workflow has never executed — zero runs, not zero accumulation

```console
$ gh run list --repo pdomain/pdomain-ocr-synth --workflow dep-refresh.yml --limit 10
(no output)

$ gh api repos/pdomain/pdomain-ocr-synth/actions/workflows/286365113/runs --jq '.total_count'
0

$ gh api repos/pdomain/pdomain-ocr-synth/actions/workflows/286365113 --jq '{name,state,created_at}'
{"name":"dep-refresh","state":"active","created_at":"2026-05-31T12:04:20.000Z"}
```

The workflow is `active` (not disabled) and has existed through roughly nine
weekly cron opportunities (2026-05-31 → 2026-08-08), yet its total run count
is `0`. No scheduled or manually dispatched run has ever started.

### 2. No stray branches or PRs exist, consistent with "never run"

```console
$ gh api repos/pdomain/pdomain-ocr-synth/branches --jq '.[].name'
codex/pdomain-prefix-finalization
master

$ gh pr list --repo pdomain/pdomain-ocr-synth --state all --search "dep refresh" --limit 20
(no output)

$ gh pr list --repo pdomain/pdomain-ocr-synth --state all --limit 30
#2  chore(lint): adopt v2 lint-first selectors ...  MERGED  2026-05-11
```

`codex/pdomain-prefix-finalization` is an unrelated feature branch. The only
merged PR in the repo's history predates the dep-refresh workflow by three
weeks and is unrelated to it. This corroborates finding 1: there is nothing
to clean up because nothing has run.

### 3. A human bypassed the dormant automation once

```console
$ git log -1 --format="%ad %H %an <%ae> %s" --date=short 322aa2d
2026-07-12 322aa2d29baf6e4365cb96871605c87e178cc3d7 ConcaveTrillion <concavetrillion@gmail.com> chore: refresh dependencies for master
```

That commit touches `uv.lock` and workflow SHA pins directly on `master`, with
no associated PR (`gh pr list --search "322aa2d"` returns nothing) and a human
author, not `github-actions[bot]`. It is a manual stand-in for the automated
refresh, done nine days after the workflow's first missed weekly window.

### 4. The merge gate is sound here (unlike two peer repos)

```console
$ gh api repos/pdomain/pdomain-ocr-synth/branches/master/protection --jq '.required_status_checks.contexts'
["ci"]

$ gh api repos/pdomain/pdomain-ocr-synth/commits/13899e9865f116a751ce6d69fd60f6ce1c55aca2/check-runs --jq '.check_runs[].name'
ci
```

The head commit checked is merged PR #2's. `.github/workflows/ci.yml` names
its single job `ci` explicitly (`jobs.ci.name: ci`), and the produced
check-run is named exactly `ci` — matching the one required context. Two
peer repos (`pdomain-ops`, `pdomain-ocr-training`) require contexts their CI
does not produce, which permanently blocks every PR regardless of dep-refresh
hygiene; this repo does not have that defect.

### 5. `delete_branch_on_merge` is `false`

```console
$ gh api repos/pdomain/pdomain-ocr-synth --jq '.delete_branch_on_merge'
false
```

Unchanged from the peers' broken configuration — a merged `dep-refresh`
branch would not be deleted automatically if one ever landed.

### 6. `DEP_REFRESH_TOKEN` is not a visible repo secret (inconclusive)

```console
$ gh secret list --repo pdomain/pdomain-ocr-synth
PD_INDEX_DISPATCH_TOKEN    2026-05-07T01:04:13Z
```

`.github/workflows/dep-refresh.yml` checks out with
`token: ${{ secrets.DEP_REFRESH_TOKEN }}` and later uses it as `GH_TOKEN` for
`gh pr create`/`gh pr merge`. This repo lists only `PD_INDEX_DISPATCH_TOKEN`
as a repository secret. Organization-level secret inheritance could not be
checked (`gh api orgs/pdomain/actions/secrets` returned 403, needs org-admin
scope), so this does not confirm the token is unavailable — `pdomain-ops`
did produce real dep-refresh branches and PRs, so the token resolves
somewhere in this org. Flagged as an open question, not a confirmed defect.

### 7. GitHub Actions is disabled for this repository

```console
$ gh api repos/pdomain/pdomain-ocr-synth/actions/permissions --jq '.enabled'
false

$ gh run list --repo pdomain/pdomain-ocr-synth --limit 1 \
    --json createdAt,workflowName
2026-07-12  Dependency Graph
```

Nothing has run here since 2026-07-12, and nothing can. The setting is
repository-wide, so it stops every workflow, not just this one.

The same is true of four sibling repos, all stopping on the same date:
`pdomain-ocr-labeler-spa`, `pdomain-ocr-trainer-spa`, `pdomain-ocr-training`,
and `pdomain-prep-for-pgdp`. The seven repos where Actions remains enabled
have all continued running weekly through 2026-08-02. A single date across
five repos points at one deliberate action, not five coincidences.

2026-07-12 is also the date of the `main` to `master` default-branch rename
and of a batch closure of stale dependency pull requests across several
repos. Whether the disabling was intentional and temporary, or a side effect
of that day's work, is not answerable from repository-scoped data.

## Root-cause hypotheses

1. **(Confirmed) The workflow has not run because Actions is disabled for the
   whole repository**, not because the schedule is misconfigured. Evidence #7
   settles this: `enabled: false`, and the last run of any workflow was
   2026-07-12. The cron in `dep-refresh.yml` is correct and identical to the
   seven repos that still run weekly. Nothing in this repo's workflow files
   needs changing to restore the schedule.

   This also means the repository has had **no CI of any kind** for nearly a
   month, which is a larger problem than the one this report was opened for.
   Every pull request opened here since 2026-07-12 has been merged, or is
   waiting, without a single check having run.
2. **(Confirmed, structural) The branch-naming and delete-on-merge design is
   identical in shape to `pdomain-ops` before its fix.** Once real dependency
   diffs start landing PRs, `dep-refresh/<date>-<run-id>` plus
   `delete_branch_on_merge: false` will accumulate branches and PRs the same
   way, because nothing in this repo's configuration differs from the
   pattern that produced seven stray branches there.
3. **(Unconfirmed, and now secondary) `DEP_REFRESH_TOKEN` may not be
   provisioned for this repo**, which would make the first run fail at
   checkout or push. This cannot be confirmed without org-admin secret
   visibility (see Evidence #6), and it is no longer needed to explain the
   dormancy, which Evidence #7 accounts for on its own. It stays listed
   because it would surface the moment Actions is re-enabled, and is worth
   checking before assuming the restore worked.

## Defects to fix

1. **`dep-refresh.yml` creates a new dated branch every run with no
   reuse/consolidation logic**, identical to the pre-fix `pdomain-ops`
   design. (Primary — latent; will manifest the first time a run actually
   produces a diff.)
2. **`delete_branch_on_merge` is `false`** on `pdomain/pdomain-ocr-synth`, so
   even a successful auto-merge would leave its branch behind.
3. **(Secondary, unconfirmed) `DEP_REFRESH_TOKEN` is not visible as a
   repo-level secret.** Worth an explicit check before relying on the fixed
   workflow, so the first real run doesn't fail silently for an unrelated
   reason.

## What is NOT broken

- **Master branch protection / the merge gate.** The one required context
  (`ci`) matches the check-run name `ci.yml`'s job actually produces,
  confirmed against a real merged PR. This repo does not have the
  dead-required-context defect that blocks `pdomain-ops` and
  `pdomain-ocr-training`.
- **Branch/PR hygiene today.** Zero stray `dep-refresh` branches, zero open
  dep-refresh PRs — there is nothing to clean up right now.
- **The dependency-refresh logic itself** (`update_github_actions.py`, `uv`
  lock upgrade). It has never executed here, so nothing is known to be wrong
  with it — only that it has not run.

## Dependencies

None. Unlike `pdomain-ops`, this repo needs no branch-protection fix first —
the merge gate already works — so the workflow-file change (Next step 1) can
land on its own.

## Outcome / acceptance criteria

- A weekly refresh, once it runs, merges a green result and deletes its
  branch automatically, exercised at least once via `workflow_dispatch`.
- No run ever creates a second concurrent `dep-refresh` branch.
- If `DEP_REFRESH_TOKEN` is genuinely unavailable to this repo, the first run
  fails visibly at checkout/push rather than silently never starting.

## Next steps

Step 0 comes first and is not optional. Nothing else in this list can be
tested until it is done.

0. **Decide whether GitHub Actions should be re-enabled for this repository**
   (Evidence #7). It has been off since 2026-07-12 along with four siblings,
   so this is a workspace-level decision, not a per-repo one, and it should be
   answered for all five together. Until it is answered, this repository has
   no CI, every merge here is unchecked, and the rest of this report is
   untestable. If the disabling was deliberate, say so in the resolution and
   the remaining steps become dormant rather than wrong.

1. Apply the design at
   `pdomain-ui:docs/specs/2026-07-16-dep-refresh-auto-land-design.md`,
   sections B ("One reusable branch") and C ("Enable delete-on-merge"),
   preemptively: replace the dated branch in
   `.github/workflows/dep-refresh.yml` with one reusable `dep-refresh` branch
   force-pushed from a fresh `master` each run, open a PR only when no open
   one exists for it, re-arm `gh pr merge --auto --rebase`, and set
   `delete_branch_on_merge: true` on `pdomain/pdomain-ocr-synth`.
2. Confirm whether `DEP_REFRESH_TOKEN` actually resolves for this repo (org
   secret or a repo secret to add) before or alongside step 1, so the first
   real run doesn't fail for an unrelated, silent reason.
3. After landing, trigger `workflow_dispatch` once to exercise the reusable
   branch flow end-to-end — this repo has no historical run to compare
   against, so a first observed run is the only way to confirm the fix
   actually works here.
4. No stray-branch or stuck-PR cleanup is needed as part of this work; unlike
   `pdomain-ops`, there is nothing to close today.

## Resolution

*Open.* When fixed: set frontmatter + Agent Index `Status: retired`, add the
resolving commit/spec link here, drop the pointer in
`docs/context/current-state.md`, and route the retirement through
`doc-retirer`.
