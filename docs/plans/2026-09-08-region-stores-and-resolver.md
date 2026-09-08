# Region Stores and Resolver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the three stores that keep a machine's region proposals beside a person's decisions,
and the single read path that resolves them into the regions a caller sees.

**Architecture:** Confirmed regions are `Block` objects already carried in the page content blob, so
they need no new store. Proposals go into their own append-only journal per run, never into the page
blob, because the page blob is only ever written by a human action. Decisions are a second
append-only journal joining the two. One resolver reads all three and returns confirmed regions
first, then proposals above a confidence threshold, then nothing.

**Tech Stack:** Python 3.13, frozen dataclasses, JSONL journals with an OS append lock, pytest, ruff,
basedpyright.

**Spec:** [Annotation provenance and
persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md).

## Agent Index

- **Kind:** plan
- **Status:** active
- **Owner:** CT
- **Created:** 2026-09-08
- **Last verified:** 2026-09-08
- **Provenance:** authored 2026-09-08 from the design above and direct inspection of
  `pdomain-ocr-labeler-spa` `core/labeler_sidecars.py`, `core/project_state.py`,
  `core/page_state.py`, `core/typography_review.py`, `core/persistence/page_store.py`,
  `api/words.py`, `api/pages.py`, `core/jobs/runner.py`, its Makefile and `pyproject.toml`, and
  `tests/conftest.py` plus `tests/integration/conftest.py`
- **Disposition:** Active. First half of slice 2 of the labeling track. The routes and the proposal
  run job are the fourth plan and build on this.
- **Read when:** implementing the region proposal store, the decision journal, or the resolver that
  serves both the labeler and the execution engine.
- **Search terms:** RegionProposal, ProposalRun, RegionDecision, resolve_regions, decision journal,
  append-only JSONL, confidence threshold, page blob invariant.

## Global Constraints

- Python floor is `>=3.13,<3.14`. Warnings are errors.
- Run any target with `AI=1` to capture verbose output to `.ci-ai.log`, for example
  `make AI=1 test`. Run `make AI=1 ci` before committing.
- **The page blob is only ever written by a human action.** Nothing in this plan may call
  `save_page_content_to_store` from a proposal path. Task 4 tests that invariant directly.
- **Region identity is never positional.** The existing sidecar maps key on
  `"{line_index}_{word_index}"`, and line numbering is not stable across the band-identification
  fixes. Regions carry their own opaque identifier, and proposal-to-region matching is done on page
  and box.
- Journals are append-only. An existing record is never rewritten; supersession is a later record
  referring to an earlier one. Follow `core/typography_review.py`'s `TypographyCorrectionLog`, which
  fsyncs before `append` returns and takes an operating-system append lock so writers across worker
  processes serialize.
- `RegionRole`, `LabelSource`, and `KnowledgeState` come from `pdomain-book-contracts` and must
  already be released by the first plan before Task 1 starts.

---

## File Structure

| file | responsibility |
| --- | --- |
| `core/regions/models.py` | `RegionProposal`, `ProposalRun`, `RegionDecision`, `Disposition`, `ResolvedRegion` |
| `core/regions/proposal_log.py` | append-only journal of proposal runs and their proposals |
| `core/regions/decision_log.py` | append-only journal of what a person decided about each proposal |
| `core/regions/resolver.py` | `resolve_regions`, the one read path both callers share |
| `tests/unit/core/regions/test_region_models.py` | model round-trips and validation |
| `tests/unit/core/regions/test_proposal_log.py` | append, read back, immutability, run conditioning |
| `tests/unit/core/regions/test_decision_log.py` | append, read back, rejection recorded |
| `tests/unit/core/regions/test_resolver.py` | the resolution table, including the unattended row |

---

### Task 1: The record models

Three records and one enum. Proposals hold what a machine said, decisions hold what a person
decided, and a run ties a batch of proposals to the model that made them and the page state it read.

The run record is what makes a detector swap measurable. Because it names the model and version and
the exact content hash of each page it read, replacing PP-DocLayout later is a new run over the same
pages rather than a migration, and the two can be scored against identical human answers.

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/core/regions/__init__.py`
- Create: `src/pdomain_ocr_labeler_spa/core/regions/models.py`
- Test: `tests/unit/core/regions/test_region_models.py`

**Interfaces:**

- Consumes: `RegionRole` and `KnowledgeState` from `pdomain_book_contracts.annotation`.
- Produces: `RegionProposal`, `ProposalRun`, `RegionDecision`, `Disposition`, `ResolvedRegion`, each
  with `to_dict` and `from_dict`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/regions/test_region_models.py
"""Unit tests for the region proposal, run, and decision records."""

from __future__ import annotations

import pytest


def test_a_proposal_round_trips() -> None:
    from pdomain_book_contracts.annotation import RegionRole

    from pdomain_ocr_labeler_spa.core.regions.models import RegionProposal

    proposal = RegionProposal(
        proposal_id="p1",
        run_id="r1",
        page_index=0,
        role=RegionRole.POETRY,
        box=(10, 20, 300, 400),
        confidence=0.82,
        evidence={"signal": "indent", "ragged_right": True},
    )
    restored = RegionProposal.from_dict(proposal.to_dict())
    assert restored == proposal
    assert restored.role is RegionRole.POETRY
    assert restored.evidence["ragged_right"] is True


def test_a_proposal_rejects_an_inverted_box() -> None:
    from pdomain_book_contracts.annotation import RegionRole

    from pdomain_ocr_labeler_spa.core.regions.models import RegionProposal

    with pytest.raises(ValueError, match="L <= R"):
        RegionProposal(
            proposal_id="p1",
            run_id="r1",
            page_index=0,
            role=RegionRole.POETRY,
            box=(300, 20, 10, 400),
            confidence=0.5,
            evidence={},
        )


def test_a_proposal_rejects_a_confidence_outside_zero_to_one() -> None:
    from pdomain_book_contracts.annotation import RegionRole

    from pdomain_ocr_labeler_spa.core.regions.models import RegionProposal

    with pytest.raises(ValueError, match="confidence"):
        RegionProposal(
            proposal_id="p1",
            run_id="r1",
            page_index=0,
            role=RegionRole.POETRY,
            box=(10, 20, 300, 400),
            confidence=1.4,
            evidence={},
        )


def test_a_run_records_what_it_was_conditioned_on() -> None:
    from pdomain_ocr_labeler_spa.core.regions.models import ProposalRun

    run = ProposalRun(
        run_id="r1",
        model_id="pp-doclayout-plus-l",
        model_version="1.0.0",
        created_at="2026-09-08T10:00:00+00:00",
        page_content_hashes={0: "a" * 64, 1: "b" * 64},
        page_kind_decision_ref="pk-run-7",
        page_kind_was_confirmed=False,
    )
    restored = ProposalRun.from_dict(run.to_dict())
    assert restored == run
    assert restored.page_content_hashes[1] == "b" * 64
    assert restored.page_kind_was_confirmed is False


def test_a_decision_records_a_rejection_distinctly_from_an_acceptance() -> None:
    from pdomain_ocr_labeler_spa.core.regions.models import Disposition, RegionDecision

    accepted = RegionDecision(
        decision_id="d1",
        run_id="r1",
        proposal_id="p1",
        disposition=Disposition.ACCEPTED,
        region_id="reg-1",
        actor="default",
        decided_at="2026-09-08T10:05:00+00:00",
    )
    rejected = RegionDecision(
        decision_id="d2",
        run_id="r1",
        proposal_id="p2",
        disposition=Disposition.REJECTED,
        region_id=None,
        actor="default",
        decided_at="2026-09-08T10:06:00+00:00",
    )
    assert RegionDecision.from_dict(accepted.to_dict()) == accepted
    assert RegionDecision.from_dict(rejected.to_dict()) == rejected
    assert rejected.region_id is None


def test_an_accepted_decision_must_name_the_region_it_produced() -> None:
    from pdomain_ocr_labeler_spa.core.regions.models import Disposition, RegionDecision

    with pytest.raises(ValueError, match="region_id"):
        RegionDecision(
            decision_id="d1",
            run_id="r1",
            proposal_id="p1",
            disposition=Disposition.ACCEPTED,
            region_id=None,
            actor="default",
            decided_at="2026-09-08T10:05:00+00:00",
        )


def test_disposition_maps_onto_a_knowledge_state() -> None:
    from pdomain_book_contracts.annotation import KnowledgeState

    from pdomain_ocr_labeler_spa.core.regions.models import Disposition

    assert Disposition.ACCEPTED.knowledge_state is KnowledgeState.POSITIVE
    assert Disposition.EDITED.knowledge_state is KnowledgeState.POSITIVE
    assert Disposition.REJECTED.knowledge_state is KnowledgeState.VERIFIED_NEGATIVE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/regions/test_region_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pdomain_ocr_labeler_spa.core.regions'`

- [ ] **Step 3: Write the implementation**

Create `src/pdomain_ocr_labeler_spa/core/regions/__init__.py` as an empty module docstring file, then
`src/pdomain_ocr_labeler_spa/core/regions/models.py`:

```python
"""Records that keep a machine's region proposals beside a person's decisions.

Proposals are immutable once written. Decisions join a proposal to what a person
did with it. A run ties a batch of proposals to the model that made them and to
the exact page state each was computed from, which is what lets a later detector
be scored against this one on identical pages.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pdomain_book_contracts.annotation import KnowledgeState, RegionRole


class Disposition(StrEnum):
    """What a person did with one proposal."""

    ACCEPTED = "accepted"
    EDITED = "edited"
    REJECTED = "rejected"

    @property
    def knowledge_state(self) -> KnowledgeState:
        """The knowledge state this disposition asserts about the proposal."""
        if self is Disposition.REJECTED:
            return KnowledgeState.VERIFIED_NEGATIVE
        return KnowledgeState.POSITIVE


@dataclass(frozen=True)
class RegionProposal:
    """One region a machine proposed. Never edited after it is written."""

    proposal_id: str
    run_id: str
    page_index: int
    role: RegionRole
    box: tuple[int, int, int, int]
    confidence: float
    evidence: dict[str, Any]

    def __post_init__(self) -> None:
        left, top, right, bottom = self.box
        if left > right:
            raise ValueError(f"box has L > R ({left} > {right}); require L <= R")
        if top > bottom:
            raise ValueError(f"box has T > B ({top} > {bottom}); require T <= B")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence {self.confidence} is outside 0.0 to 1.0"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "run_id": self.run_id,
            "page_index": self.page_index,
            "role": self.role.value,
            "box": list(self.box),
            "confidence": self.confidence,
            "evidence": dict(self.evidence),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RegionProposal:
        box = d["box"]
        return cls(
            proposal_id=str(d["proposal_id"]),
            run_id=str(d["run_id"]),
            page_index=int(d["page_index"]),
            role=RegionRole(str(d["role"])),
            box=(int(box[0]), int(box[1]), int(box[2]), int(box[3])),
            confidence=float(d["confidence"]),
            evidence=dict(d.get("evidence") or {}),
        )


@dataclass(frozen=True)
class ProposalRun:
    """One pass of one model over one book, and what it was conditioned on."""

    run_id: str
    model_id: str
    model_version: str
    created_at: str
    page_content_hashes: dict[int, str]
    page_kind_decision_ref: str | None
    page_kind_was_confirmed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "model_id": self.model_id,
            "model_version": self.model_version,
            "created_at": self.created_at,
            # JSON object keys are strings; page indices are restored on read.
            "page_content_hashes": {
                str(index): digest
                for index, digest in self.page_content_hashes.items()
            },
            "page_kind_decision_ref": self.page_kind_decision_ref,
            "page_kind_was_confirmed": self.page_kind_was_confirmed,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ProposalRun:
        raw_hashes = d.get("page_content_hashes") or {}
        return cls(
            run_id=str(d["run_id"]),
            model_id=str(d["model_id"]),
            model_version=str(d["model_version"]),
            created_at=str(d["created_at"]),
            page_content_hashes={
                int(index): str(digest) for index, digest in raw_hashes.items()
            },
            page_kind_decision_ref=(
                str(d["page_kind_decision_ref"])
                if d.get("page_kind_decision_ref") is not None
                else None
            ),
            page_kind_was_confirmed=bool(d.get("page_kind_was_confirmed", False)),
        )


@dataclass(frozen=True)
class RegionDecision:
    """What a person decided about one proposal.

    A proposal with no decision is unreviewed. A proposal with a ``REJECTED``
    decision was looked at and refused. Those are opposite facts, and keeping
    them apart is why this record exists at all.
    """

    decision_id: str
    run_id: str
    proposal_id: str
    disposition: Disposition
    region_id: str | None
    actor: str
    decided_at: str

    def __post_init__(self) -> None:
        if self.disposition is not Disposition.REJECTED and self.region_id is None:
            raise ValueError(
                f"a {self.disposition.value} decision must name the region_id it produced"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "run_id": self.run_id,
            "proposal_id": self.proposal_id,
            "disposition": self.disposition.value,
            "region_id": self.region_id,
            "actor": self.actor,
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RegionDecision:
        return cls(
            decision_id=str(d["decision_id"]),
            run_id=str(d["run_id"]),
            proposal_id=str(d["proposal_id"]),
            disposition=Disposition(str(d["disposition"])),
            region_id=str(d["region_id"]) if d.get("region_id") is not None else None,
            actor=str(d.get("actor", "default")),
            decided_at=str(d["decided_at"]),
        )


@dataclass(frozen=True)
class ResolvedRegion:
    """One region as a caller sees it, with where it came from.

    ``confirmed`` is True when a person put it there. The labeler renders the
    two differently; the execution engine only ever sees proposals.
    """

    role: RegionRole
    box: tuple[int, int, int, int]
    confirmed: bool
    confidence: float | None
    proposal_id: str | None
    region_id: str | None
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/core/regions/test_region_models.py -v`
Expected: PASS, all seven tests.

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/regions tests/unit/core/regions
git commit -m "feat(regions): add proposal, run, and decision records"
```

---

### Task 2: The proposal journal

Proposals persist so a model can be scored later. They do not go into the page content blob, because
that blob is only ever written by a human action and proposals come from a job.

The journal is append-only and copies the discipline of `TypographyCorrectionLog`: fsync before
`append` returns, an operating-system append lock so writers across worker processes serialize, and
no record ever rewritten.

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/core/regions/proposal_log.py`
- Test: `tests/unit/core/regions/test_proposal_log.py`

**Interfaces:**

- Consumes: `RegionProposal` and `ProposalRun` from Task 1.
- Produces: `RegionProposalLog(project_root: Path)` with `append_run(run: ProposalRun) -> None`,
  `append_proposals(proposals: Sequence[RegionProposal]) -> None`,
  `runs() -> list[ProposalRun]`, and
  `proposals_for_page(page_index: int, *, run_id: str | None = None) -> list[RegionProposal]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/regions/test_proposal_log.py
"""Unit tests for the append-only region proposal journal."""

from __future__ import annotations

from pathlib import Path

from pdomain_book_contracts.annotation import RegionRole

from pdomain_ocr_labeler_spa.core.regions.models import ProposalRun, RegionProposal


def _run(run_id: str = "r1") -> ProposalRun:
    return ProposalRun(
        run_id=run_id,
        model_id="pp-doclayout-plus-l",
        model_version="1.0.0",
        created_at="2026-09-08T10:00:00+00:00",
        page_content_hashes={0: "a" * 64},
        page_kind_decision_ref=None,
        page_kind_was_confirmed=False,
    )


def _proposal(proposal_id: str, run_id: str = "r1", page_index: int = 0) -> RegionProposal:
    return RegionProposal(
        proposal_id=proposal_id,
        run_id=run_id,
        page_index=page_index,
        role=RegionRole.POETRY,
        box=(10, 20, 300, 400),
        confidence=0.7,
        evidence={},
    )


def test_a_run_and_its_proposals_read_back(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.regions.proposal_log import RegionProposalLog

    log = RegionProposalLog(tmp_path)
    log.append_run(_run())
    log.append_proposals([_proposal("p1"), _proposal("p2")])

    assert [r.run_id for r in log.runs()] == ["r1"]
    found = log.proposals_for_page(0)
    assert sorted(p.proposal_id for p in found) == ["p1", "p2"]


def test_a_fresh_log_is_empty_and_does_not_raise(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.regions.proposal_log import RegionProposalLog

    log = RegionProposalLog(tmp_path)
    assert log.runs() == []
    assert log.proposals_for_page(0) == []


def test_proposals_are_filtered_by_page(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.regions.proposal_log import RegionProposalLog

    log = RegionProposalLog(tmp_path)
    log.append_run(_run())
    log.append_proposals([_proposal("p1", page_index=0), _proposal("p2", page_index=1)])

    assert [p.proposal_id for p in log.proposals_for_page(1)] == ["p2"]


def test_a_second_run_does_not_disturb_the_first(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.regions.proposal_log import RegionProposalLog

    log = RegionProposalLog(tmp_path)
    log.append_run(_run("r1"))
    log.append_proposals([_proposal("p1", run_id="r1")])
    log.append_run(_run("r2"))
    log.append_proposals([_proposal("p2", run_id="r2")])

    assert [r.run_id for r in log.runs()] == ["r1", "r2"]
    assert [p.proposal_id for p in log.proposals_for_page(0, run_id="r1")] == ["p1"]
    assert [p.proposal_id for p in log.proposals_for_page(0, run_id="r2")] == ["p2"]
    # Both runs survive, which is what makes one detector scoreable against another.
    assert len(log.proposals_for_page(0)) == 2


def test_appending_never_rewrites_an_existing_record(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.regions.proposal_log import RegionProposalLog

    log = RegionProposalLog(tmp_path)
    log.append_run(_run())
    log.append_proposals([_proposal("p1")])
    first = (tmp_path / ".pd-pages" / "region-proposals.jsonl").read_bytes()

    log.append_proposals([_proposal("p2")])
    second = (tmp_path / ".pd-pages" / "region-proposals.jsonl").read_bytes()

    assert second.startswith(first)


def test_a_malformed_line_is_skipped_rather_than_failing_the_read(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.regions.proposal_log import RegionProposalLog

    log = RegionProposalLog(tmp_path)
    log.append_run(_run())
    log.append_proposals([_proposal("p1")])
    path = tmp_path / ".pd-pages" / "region-proposals.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{not json\n")

    assert [p.proposal_id for p in log.proposals_for_page(0)] == ["p1"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/regions/test_proposal_log.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named '...core.regions.proposal_log'`

- [ ] **Step 3: Write the implementation**

Create `src/pdomain_ocr_labeler_spa/core/regions/proposal_log.py`:

```python
"""Append-only journal of region proposals and the runs that produced them.

Proposals never enter the page content blob. That blob is written only by a
human action, and a proposal is a machine's claim. Keeping them apart is what
makes the page blob trustworthy as ground truth.

Records are never rewritten. A later run supersedes an earlier one for display
purposes only; both stay on disk, because scoring a replacement model against
the one it replaces needs what each of them said.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any, ClassVar

from pdomain_ocr_labeler_spa.core.regions.models import ProposalRun, RegionProposal

log = logging.getLogger(__name__)


class RegionProposalLog:
    """Project-local JSONL journal of immutable region proposals."""

    _RELATIVE_PATH: ClassVar[Path] = Path(".pd-pages") / "region-proposals.jsonl"

    def __init__(self, project_root: Path) -> None:
        self._path = Path(project_root) / self._RELATIVE_PATH

    @property
    def path(self) -> Path:
        return self._path

    def _append(self, records: Sequence[dict[str, Any]]) -> None:
        if not records:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(
            json.dumps(record, sort_keys=True) + "\n" for record in records
        ).encode("utf-8")
        # O_APPEND alone is only atomic below PIPE_BUF, and a batch of proposals
        # goes well past that. Take the same exclusive lock TypographyCorrectionLog
        # takes so writers across worker processes serialize.
        fd = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)

    def append_run(self, run: ProposalRun) -> None:
        """Record one proposal run before its proposals are written."""
        self._append([{"kind": "run", "record": run.to_dict()}])

    def append_proposals(self, proposals: Sequence[RegionProposal]) -> None:
        """Append proposals. Existing records are never touched."""
        self._append(
            [{"kind": "proposal", "record": p.to_dict()} for p in proposals]
        )

    def _read(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    loaded = json.loads(stripped)
                except json.JSONDecodeError:
                    # A torn tail from a killed writer must not hide the records
                    # before it. Skip and keep reading.
                    log.warning(
                        "region-proposals.jsonl: skipping malformed line %d", line_number
                    )
                    continue
                if isinstance(loaded, dict):
                    records.append(loaded)
        return records

    def runs(self) -> list[ProposalRun]:
        """Every run recorded, in the order they were written."""
        return [
            ProposalRun.from_dict(entry["record"])
            for entry in self._read()
            if entry.get("kind") == "run"
        ]

    def proposals_for_page(
        self, page_index: int, *, run_id: str | None = None
    ) -> list[RegionProposal]:
        """Proposals for one page, optionally narrowed to a single run."""
        found: list[RegionProposal] = []
        for entry in self._read():
            if entry.get("kind") != "proposal":
                continue
            proposal = RegionProposal.from_dict(entry["record"])
            if proposal.page_index != page_index:
                continue
            if run_id is not None and proposal.run_id != run_id:
                continue
            found.append(proposal)
        return found
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/core/regions/test_proposal_log.py -v`
Expected: PASS, all six tests.

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/regions/proposal_log.py tests/unit/core/regions/test_proposal_log.py
git commit -m "feat(regions): add the append-only proposal journal"
```

---

### Task 3: The decision journal

A proposal with no decision is unreviewed. A proposal with a rejection was looked at and refused.
Nothing in the suite can currently tell those apart at any annotation level, and that is the gap this
store closes.

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/core/regions/decision_log.py`
- Test: `tests/unit/core/regions/test_decision_log.py`

**Interfaces:**

- Consumes: `RegionDecision` and `Disposition` from Task 1.
- Produces: `RegionDecisionLog(project_root: Path)` with `append(decision: RegionDecision) -> None`,
  `decisions() -> list[RegionDecision]`, and
  `decision_for(proposal_id: str, *, run_id: str) -> RegionDecision | None` returning the most recent
  decision for that proposal.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/regions/test_decision_log.py
"""Unit tests for the append-only region decision journal."""

from __future__ import annotations

from pathlib import Path

from pdomain_ocr_labeler_spa.core.regions.models import Disposition, RegionDecision


def _decision(
    decision_id: str,
    proposal_id: str,
    disposition: Disposition,
    region_id: str | None,
    decided_at: str,
) -> RegionDecision:
    return RegionDecision(
        decision_id=decision_id,
        run_id="r1",
        proposal_id=proposal_id,
        disposition=disposition,
        region_id=region_id,
        actor="default",
        decided_at=decided_at,
    )


def test_a_decision_reads_back(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.regions.decision_log import RegionDecisionLog

    log = RegionDecisionLog(tmp_path)
    log.append(_decision("d1", "p1", Disposition.ACCEPTED, "reg-1", "2026-09-08T10:00:00+00:00"))

    found = log.decision_for("p1", run_id="r1")
    assert found is not None
    assert found.disposition is Disposition.ACCEPTED
    assert found.region_id == "reg-1"


def test_an_unreviewed_proposal_has_no_decision(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.regions.decision_log import RegionDecisionLog

    log = RegionDecisionLog(tmp_path)
    assert log.decision_for("p-nobody-looked", run_id="r1") is None


def test_a_rejection_is_distinguishable_from_never_looking(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.regions.decision_log import RegionDecisionLog

    log = RegionDecisionLog(tmp_path)
    log.append(_decision("d1", "p1", Disposition.REJECTED, None, "2026-09-08T10:00:00+00:00"))

    rejected = log.decision_for("p1", run_id="r1")
    unreviewed = log.decision_for("p2", run_id="r1")
    assert rejected is not None
    assert rejected.disposition is Disposition.REJECTED
    assert unreviewed is None


def test_the_most_recent_decision_wins_and_the_earlier_one_survives(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.regions.decision_log import RegionDecisionLog

    log = RegionDecisionLog(tmp_path)
    log.append(_decision("d1", "p1", Disposition.REJECTED, None, "2026-09-08T10:00:00+00:00"))
    log.append(_decision("d2", "p1", Disposition.ACCEPTED, "reg-1", "2026-09-08T11:00:00+00:00"))

    current = log.decision_for("p1", run_id="r1")
    assert current is not None
    assert current.decision_id == "d2"
    # Supersession is a later record, not an edit: both are still on disk.
    assert [d.decision_id for d in log.decisions()] == ["d1", "d2"]


def test_decisions_from_different_runs_do_not_collide(tmp_path: Path) -> None:
    from pdomain_ocr_labeler_spa.core.regions.decision_log import RegionDecisionLog

    log = RegionDecisionLog(tmp_path)
    first = _decision("d1", "p1", Disposition.ACCEPTED, "reg-1", "2026-09-08T10:00:00+00:00")
    second = RegionDecision(
        decision_id="d2",
        run_id="r2",
        proposal_id="p1",
        disposition=Disposition.REJECTED,
        region_id=None,
        actor="default",
        decided_at="2026-09-08T11:00:00+00:00",
    )
    log.append(first)
    log.append(second)

    from_first = log.decision_for("p1", run_id="r1")
    from_second = log.decision_for("p1", run_id="r2")
    assert from_first is not None and from_first.disposition is Disposition.ACCEPTED
    assert from_second is not None and from_second.disposition is Disposition.REJECTED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/regions/test_decision_log.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named '...core.regions.decision_log'`

- [ ] **Step 3: Write the implementation**

Create `src/pdomain_ocr_labeler_spa/core/regions/decision_log.py`:

```python
"""Append-only journal of what a person decided about each region proposal.

This is the store that makes a rejection a fact rather than an absence. Without
it, a proposal nobody accepted and a proposal somebody refused look identical,
and a trainer needs to tell them apart.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
from pathlib import Path
from typing import Any, ClassVar

from pdomain_ocr_labeler_spa.core.regions.models import RegionDecision

log = logging.getLogger(__name__)


class RegionDecisionLog:
    """Project-local JSONL journal of immutable region decisions."""

    _RELATIVE_PATH: ClassVar[Path] = Path(".pd-pages") / "region-decisions.jsonl"

    def __init__(self, project_root: Path) -> None:
        self._path = Path(project_root) / self._RELATIVE_PATH

    @property
    def path(self) -> Path:
        return self._path

    def append(self, decision: RegionDecision) -> None:
        """Append one decision. Existing records are never rewritten."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(decision.to_dict(), sort_keys=True) + "\n").encode("utf-8")
        fd = os.open(self._path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)

    def decisions(self) -> list[RegionDecision]:
        """Every decision recorded, in the order they were written."""
        if not self._path.exists():
            return []
        found: list[RegionDecision] = []
        with self._path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    loaded: Any = json.loads(stripped)
                except json.JSONDecodeError:
                    log.warning(
                        "region-decisions.jsonl: skipping malformed line %d", line_number
                    )
                    continue
                if isinstance(loaded, dict):
                    found.append(RegionDecision.from_dict(loaded))
        return found

    def decision_for(self, proposal_id: str, *, run_id: str) -> RegionDecision | None:
        """The most recent decision about one proposal within one run.

        Later records supersede earlier ones. Both stay on disk, so a change of
        mind is itself reviewable.
        """
        current: RegionDecision | None = None
        for decision in self.decisions():
            if decision.proposal_id == proposal_id and decision.run_id == run_id:
                current = decision
        return current
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/core/regions/test_decision_log.py -v`
Expected: PASS, all five tests.

- [ ] **Step 5: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/regions/decision_log.py tests/unit/core/regions/test_decision_log.py
git commit -m "feat(regions): add the append-only decision journal"
```

---

### Task 4: The resolver, and the page blob invariant test

One function serves both callers. The labeler calls it with a threshold of zero and renders
proposals differently from confirmed regions. The execution engine calls it with a real threshold and
takes the answer. There is no second pipeline.

The row that matters most is the one where both human stores are empty and a threshold is set,
because that is the execution engine running with nobody watching.

This task also carries the invariant test. Writing proposals must leave the page content blob
untouched, and content addressing makes that a single hash comparison.

**Files:**

- Create: `src/pdomain_ocr_labeler_spa/core/regions/resolver.py`
- Test: `tests/unit/core/regions/test_resolver.py`

**Interfaces:**

- Consumes: `RegionProposal`, `RegionDecision`, `Disposition`, `ResolvedRegion` from Task 1;
  `RegionProposalLog` from Task 2; `RegionDecisionLog` from Task 3.
- Produces:
  `resolve_regions(...) -> list[ResolvedRegion]`, with this signature:

```python
def resolve_regions(
    confirmed: Sequence[ResolvedRegion],
    proposals: Sequence[RegionProposal],
    decisions: Mapping[str, RegionDecision],
    *,
    threshold: float,
) -> list[ResolvedRegion]: ...
```

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/core/regions/test_resolver.py
"""Unit tests for the one read path both the labeler and the engine use."""

from __future__ import annotations

from pathlib import Path

from pdomain_book_contracts.annotation import RegionRole

from pdomain_ocr_labeler_spa.core.regions.models import (
    Disposition,
    RegionDecision,
    RegionProposal,
    ResolvedRegion,
)


def _proposal(proposal_id: str, confidence: float) -> RegionProposal:
    return RegionProposal(
        proposal_id=proposal_id,
        run_id="r1",
        page_index=0,
        role=RegionRole.POETRY,
        box=(10, 20, 300, 400),
        confidence=confidence,
        evidence={},
    )


def _confirmed(region_id: str) -> ResolvedRegion:
    return ResolvedRegion(
        role=RegionRole.BLOCKQUOTE,
        box=(10, 20, 300, 400),
        confirmed=True,
        confidence=None,
        proposal_id=None,
        region_id=region_id,
    )


def test_a_confirmed_region_wins_over_a_proposal() -> None:
    from pdomain_ocr_labeler_spa.core.regions.resolver import resolve_regions

    resolved = resolve_regions(
        [_confirmed("reg-1")], [_proposal("p1", 0.99)], {}, threshold=0.0
    )
    assert [r.region_id for r in resolved] == ["reg-1"]
    assert resolved[0].role is RegionRole.BLOCKQUOTE
    assert resolved[0].confirmed is True


def test_a_proposal_above_the_threshold_is_returned_when_nothing_is_confirmed() -> None:
    from pdomain_ocr_labeler_spa.core.regions.resolver import resolve_regions

    resolved = resolve_regions([], [_proposal("p1", 0.7)], {}, threshold=0.5)
    assert len(resolved) == 1
    assert resolved[0].confirmed is False
    assert resolved[0].proposal_id == "p1"
    assert resolved[0].confidence == 0.7


def test_a_proposal_below_the_threshold_is_dropped() -> None:
    from pdomain_ocr_labeler_spa.core.regions.resolver import resolve_regions

    assert resolve_regions([], [_proposal("p1", 0.2)], {}, threshold=0.5) == []


def test_nothing_confirmed_and_nothing_above_threshold_returns_nothing() -> None:
    from pdomain_ocr_labeler_spa.core.regions.resolver import resolve_regions

    assert resolve_regions([], [], {}, threshold=0.5) == []


def test_a_rejected_proposal_is_never_returned_even_above_the_threshold() -> None:
    from pdomain_ocr_labeler_spa.core.regions.resolver import resolve_regions

    rejected = RegionDecision(
        decision_id="d1",
        run_id="r1",
        proposal_id="p1",
        disposition=Disposition.REJECTED,
        region_id=None,
        actor="default",
        decided_at="2026-09-08T10:00:00+00:00",
    )
    assert resolve_regions([], [_proposal("p1", 0.99)], {"p1": rejected}, threshold=0.5) == []


def test_the_unattended_row_where_both_human_stores_are_empty() -> None:
    """The execution engine's path: no confirmed regions, no decisions, a real threshold."""
    from pdomain_ocr_labeler_spa.core.regions.resolver import resolve_regions

    proposals = [_proposal("p1", 0.9), _proposal("p2", 0.3)]
    resolved = resolve_regions([], proposals, {}, threshold=0.5)
    assert [r.proposal_id for r in resolved] == ["p1"]
    assert all(r.confirmed is False for r in resolved)


def test_the_labeler_row_where_the_threshold_is_zero_shows_every_proposal() -> None:
    from pdomain_ocr_labeler_spa.core.regions.resolver import resolve_regions

    proposals = [_proposal("p1", 0.9), _proposal("p2", 0.01)]
    resolved = resolve_regions([], proposals, {}, threshold=0.0)
    assert [r.proposal_id for r in resolved] == ["p1", "p2"]


def test_writing_proposals_leaves_the_page_content_blob_untouched(tmp_path: Path) -> None:
    """The page blob is only ever written by a human action.

    Content addressing makes this a single comparison: the journal write must
    not change what the blob store holds.
    """
    from pdomain_ocr_labeler_spa.core.regions.models import ProposalRun
    from pdomain_ocr_labeler_spa.core.regions.proposal_log import RegionProposalLog

    blobs_dir = tmp_path / ".pd-pages" / "blobs"
    blobs_dir.mkdir(parents=True)
    (blobs_dir / ("a" * 64)).write_bytes(b'{"type": "Page"}')

    def _snapshot() -> dict[str, bytes]:
        return {p.name: p.read_bytes() for p in sorted(blobs_dir.iterdir())}

    before = _snapshot()

    log = RegionProposalLog(tmp_path)
    log.append_run(
        ProposalRun(
            run_id="r1",
            model_id="pp-doclayout-plus-l",
            model_version="1.0.0",
            created_at="2026-09-08T10:00:00+00:00",
            page_content_hashes={0: "a" * 64},
            page_kind_decision_ref=None,
            page_kind_was_confirmed=False,
        )
    )
    log.append_proposals([_proposal("p1", 0.9)])

    assert _snapshot() == before
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/core/regions/test_resolver.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named '...core.regions.resolver'`

- [ ] **Step 3: Write the implementation**

Create `src/pdomain_ocr_labeler_spa/core/regions/resolver.py`:

```python
"""The one read path both the labeler and the execution engine use.

Callers never touch the three stores directly. They ask for a page's resolved
regions and get confirmed regions where they exist, then proposals above a
confidence threshold, then nothing.

The labeler passes a threshold of zero and renders proposals visibly differently.
The execution engine passes a real threshold and takes the result as the answer.
Because there is one function, there is no second pipeline to keep in step.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pdomain_ocr_labeler_spa.core.regions.models import (
    Disposition,
    RegionDecision,
    RegionProposal,
    ResolvedRegion,
)


def resolve_regions(
    confirmed: Sequence[ResolvedRegion],
    proposals: Sequence[RegionProposal],
    decisions: Mapping[str, RegionDecision],
    *,
    threshold: float,
) -> list[ResolvedRegion]:
    """Resolve one page's regions from the three stores.

    Args:
        confirmed: Regions a person put there, already lifted from the page.
        proposals: What a machine said about this page.
        decisions: The decision for each proposal id, where one exists. A
            proposal absent from this mapping is unreviewed, which is a
            different fact from a recorded rejection.
        threshold: Minimum confidence a proposal needs to stand in for a missing
            confirmed region. Zero shows everything, which is what the labeler
            wants.

    Returns:
        Confirmed regions first, in the order given, then the surviving
        proposals in the order given.
    """
    resolved = list(confirmed)

    for proposal in proposals:
        decision = decisions.get(proposal.proposal_id)
        if decision is not None and decision.disposition is Disposition.REJECTED:
            # A refusal is a fact. Never fall back to a proposal a person
            # already looked at and turned down.
            continue
        if decision is not None and decision.region_id is not None:
            # Already promoted into a confirmed region, which is in `confirmed`.
            continue
        if proposal.confidence < threshold:
            continue
        resolved.append(
            ResolvedRegion(
                role=proposal.role,
                box=proposal.box,
                confirmed=False,
                confidence=proposal.confidence,
                proposal_id=proposal.proposal_id,
                region_id=None,
            )
        )

    return resolved
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/core/regions/test_resolver.py -v`
Expected: PASS, all eight tests.

- [ ] **Step 5: Run the fast suite and the gate**

Run: `make AI=1 test`
Expected: PASS with no regression in the existing 105 unit files.

Run: `make AI=1 ci`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/pdomain_ocr_labeler_spa/core/regions/resolver.py tests/unit/core/regions/test_resolver.py
git commit -m "feat(regions): resolve confirmed regions over proposals above a threshold"
```

---

## What this plan does not do

- It adds no routes. Region CRUD, membership, accept, reject, and the proposal-run job are the
  fourth plan, which builds directly on these four modules.
- It does not lift `Block` objects into `ResolvedRegion`. The adapter that reads confirmed regions
  off a page belongs with the routes, because that is the first caller that needs it.
- It does not compute proposals. The proposal engine is slice 4 and needs its own design, and it is
  gated on the page-template spread from the second plan.
- It does not add explicit word membership. That arrives with the routes, where setting membership
  is its own operation.
- It does not touch the glyph or word stores. Word provenance rides on `ReviewMetadata.source` from
  the first plan.

## Related

- [Annotation provenance and
  persistence](../specs/2026-09-07-region-provenance-and-persistence-design.md) — the design.
- [Annotation vocabularies in
  book-contracts](2026-09-08-annotation-vocabularies-in-book-contracts.md) — must land first.
- [Annotation preconditions in book-tools and
  measure](2026-09-08-annotation-preconditions-in-book-tools-and-measure.md) — independent of this.
- [Labeling track roadmap](2026-09-07-labeling-track-roadmap.md) — the seven slices.
