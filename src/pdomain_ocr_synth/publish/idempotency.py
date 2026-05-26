"""Idempotency check for ``pdomain-ocr-synth publish`` (M08).

Per ``docs/specs/10-publishing.md`` § Idempotency:

> Publish is idempotent against repo state:
>
> 1. Compute a content SHA over the local output (image bytes +
>    metadata + recipe snapshot).
> 2. Read the latest commit's ``card_data.pd-ocr-content-sha``.
> 3. If equal → exit 0 with "no changes" and do not commit.

This module is the **decision** half of that contract: given a
locally-computed content SHA and an :class:`HfTransport`, decide
whether a publish would be a no-op. The actual computation of the
local SHA lives in :mod:`pdomain_ocr_synth.publish.content_sha`; the
actual upload short-circuit lives in the upload orchestrator
(future chunk). Splitting this out as a pure function lets the
upload orchestrator stay a thin assembly of:

1. Build staging dir (already implemented).
2. Compute content SHA (already implemented).
3. **Decide idempotency (this module).**
4. If "up_to_date" → exit 0 with the documented message.
5. Otherwise → ``create_repo`` (if needed) + ``upload_folder``.

The matching deliverable in ``docs/roadmap/08-publishing-hf.md``
M08 § Idempotency:

> Before uploading: read the latest commit's ``card_data`` from HF.
> If ``pd-ocr-content-sha`` matches → exit 0 with "no changes".

## States

The check distills the spec's three-step procedure into a
three-valued :class:`IdempotencyState`:

- ``up_to_date`` — remote ``pd-ocr-content-sha`` equals the local
  digest. The publish is a no-op; the runner exits 0.
- ``changed`` — the repo exists but its card either has no
  ``pd-ocr-content-sha`` (e.g. brand-new repo without a README, or
  a card from a different tool) or has one that disagrees with the
  local digest. The runner proceeds with upload.
- ``repo_missing`` — :meth:`HfTransport.repo_exists` returned
  ``False``. The runner falls through to ``create_repo`` + first-
  time upload.

## Why a transport-typed argument and not "an HfApi instance"

The spec's idempotency check uses ``HfApi.list_repo_commits`` to
read ``card_data``, but the abstraction we drive against in tests
is the :class:`HfTransport` Protocol — see
:mod:`pdomain_ocr_synth.publish.transport`. The Protocol exposes a
:meth:`HfTransport.read_remote_card_data` that is the minimal seam
the idempotency check needs, and the SDK adapter (lands later) is
free to choose between ``list_repo_commits`` and
``HfApi.dataset_info`` under the hood. Tests drive against
:class:`FakeTransport`; production drives against the real adapter;
this module doesn't care.

## What this module does *not* do

- It does **not** compute the local content SHA. Callers pass in an
  already-computed digest from
  :func:`pdomain_ocr_synth.publish.content_sha.compute_content_sha`. That
  separation lets the dry-run path reuse the same primitive without
  needing a transport at all (dry-run reports the digest; only the
  real upload calls the idempotency check).
- It does **not** touch the staging dir. Once the digest is
  computed, the staging dir is no longer needed for this decision —
  passing the digest as a string keeps the function signature
  small and the dependency graph tight.
- It does **not** decide exit codes. The runner (next chunk) maps
  :class:`IdempotencyDecision` onto exit 0 vs. continued execution.
  Embedding exit codes here would couple this leaf module to the
  CLI dispatcher.
- It does **not** handle :class:`TransportError` itself. A network
  / auth failure during the idempotency check is the same failure
  the upload would hit; the runner catches it once at the top of
  the publish flow rather than every primitive having its own
  catch-and-translate. This matches the pattern the dry-run runner
  already uses (it propagates :class:`StagingError` /
  :class:`PreflightError`).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pdomain_ocr_synth.publish.content_sha import CONTENT_SHA_KEY
from pdomain_ocr_synth.publish.transport import HfTransport


class IdempotencyState(StrEnum):
    """Outcome of the idempotency check.

    Subclasses :class:`enum.StrEnum` so callers can pattern-match
    against the string literals (``"up_to_date"`` / ``"changed"`` /
    ``"repo_missing"``) without importing the enum, mirroring the
    convention :class:`pdomain_ocr_synth.publish.auth.ResolvedToken.source`
    uses.
    """

    UP_TO_DATE = "up_to_date"
    CHANGED = "changed"
    REPO_MISSING = "repo_missing"


@dataclass(frozen=True, slots=True)
class IdempotencyDecision:
    """Result of an idempotency check.

    A frozen dataclass so the runner can safely log it without worrying
    about downstream mutation, and so test assertions can compare
    decisions structurally rather than re-deriving each field.

    Attributes
    ----------
    state:
        See :class:`IdempotencyState`.
    repo_id:
        The ``OWNER/NAME`` the check ran against. Echoed so callers
        building log lines don't have to thread it through separately.
    local_sha:
        The locally-computed digest the caller passed in. Verbatim;
        no normalization. Empty string is treated as a programmer-
        side bug — see :func:`check_idempotency`.
    remote_sha:
        The value the transport returned for ``pd-ocr-content-sha``,
        or ``None`` if the repo is missing, the card is empty, or the
        key is absent. The runner uses this to format the
        "would publish: <local> ≠ <remote>" log line; tests assert on
        it to lock the "missing remote SHA → ``changed``" branch.

    Methods
    -------
    is_up_to_date:
        Convenience boolean for the runner's short-circuit. Equivalent
        to ``decision.state is IdempotencyState.UP_TO_DATE`` but reads
        more naturally at call sites.
    """

    state: IdempotencyState
    repo_id: str
    local_sha: str
    remote_sha: str | None

    @property
    def is_up_to_date(self) -> bool:
        """True iff the publish would be a no-op.

        Used by the runner to short-circuit before ``create_repo`` /
        ``upload_folder``. Implemented as a property (not a method) so
        boolean call-sites read like English: ``if decision.is_up_to_date:``.
        """

        return self.state is IdempotencyState.UP_TO_DATE


def check_idempotency(
    transport: HfTransport,
    repo_id: str,
    local_content_sha: str,
) -> IdempotencyDecision:
    """Decide whether a publish to ``repo_id`` would be a no-op.

    Implements the three-step procedure from
    ``docs/specs/10-publishing.md`` § Idempotency. The local content
    SHA is supplied by the caller (already computed by
    :func:`pdomain_ocr_synth.publish.content_sha.compute_content_sha`);
    this function consults the transport for the remote side.

    Parameters
    ----------
    transport:
        Anything satisfying :class:`HfTransport`. In tests this is a
        :class:`pdomain_ocr_synth.publish.transport.FakeTransport`; in
        production it will be the real SDK adapter.
    repo_id:
        Canonical ``OWNER/NAME``. Not validated here — repo-id
        validation lives elsewhere (a future small chunk).
    local_content_sha:
        Hex digest the caller computed over the staging dir. Must be
        non-empty: an empty digest indicates a programmer-side bug
        (the caller forgot to call ``compute_content_sha``), and
        silently treating it as "matches anything"  would let real
        bugs masquerade as idempotent no-ops.

    Returns
    -------
    IdempotencyDecision
        Structured result. The runner branches on :attr:`is_up_to_date`
        for the short-circuit and uses the rest of the fields for log
        formatting.

    Raises
    ------
    ValueError
        If ``local_content_sha`` is empty. This is a programmer error,
        not a runtime / network condition; raising loudly keeps a
        bug from silently corrupting an idempotency decision.
    pdomain_ocr_synth.publish.transport.TransportError
        Propagated from :meth:`HfTransport.repo_exists` or
        :meth:`HfTransport.read_remote_card_data`. The runner catches
        this once at the top of the publish flow.
    """

    if not local_content_sha:
        raise ValueError(
            "check_idempotency requires a non-empty local_content_sha; "
            "did you forget to call compute_content_sha?"
        )

    # Step 1 of the spec is "compute a content SHA over the local
    # output" — done by the caller. We start at step 2: read the
    # remote side. But first we must distinguish "no remote at all"
    # (the very first publish; the runner will create_repo + upload)
    # from "remote exists but its card is uninformative" (the runner
    # will still upload, but for a different reason).
    if not transport.repo_exists(repo_id):
        return IdempotencyDecision(
            state=IdempotencyState.REPO_MISSING,
            repo_id=repo_id,
            local_sha=local_content_sha,
            remote_sha=None,
        )

    card = transport.read_remote_card_data(repo_id)
    remote_sha = card.get(CONTENT_SHA_KEY)
    # Coerce to str only when present. A non-string remote_sha (e.g.
    # YAML parsed an unquoted hex into something exotic) would still
    # not equal our string, so it falls through to ``changed`` —
    # which is the safe direction (worst case: a redundant re-upload).
    if isinstance(remote_sha, str) and remote_sha == local_content_sha:
        return IdempotencyDecision(
            state=IdempotencyState.UP_TO_DATE,
            repo_id=repo_id,
            local_sha=local_content_sha,
            remote_sha=remote_sha,
        )

    return IdempotencyDecision(
        state=IdempotencyState.CHANGED,
        repo_id=repo_id,
        local_sha=local_content_sha,
        remote_sha=remote_sha if isinstance(remote_sha, str) else None,
    )
