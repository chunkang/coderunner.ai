# ==============================================================================
#  CodeRunner.AI  ::  Solution Memory — embedding seam and turn orchestration
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Project : SPEC-MEMORY-001
#  Purpose : The single place that touches the embedding backend, plus the
#            per-turn retrieve/capture orchestration built on memory.py.
#
#  This module is deliberately thin. Everything that can be tested without a
#  backend lives in memory.py, which carries zero third-party imports; this file
#  is the seam where a fake client gets injected (plan.md 1.1).
#
#  IT DOES NOT IMPORT `pymilvus`, DIRECTLY OR VIA vectorstore.py (AC-14). The
#  store arrives as a parameter and is used through eight duck-typed methods,
#  which is why the whole storage substrate could be replaced at v1.1.0 with a
#  single changed call site in this file — and why this suite still runs with no
#  live Ollama and no live Milvus.
# ==============================================================================

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx
import ollama

from memory import MemoryConfig, SolutionRecord, l2_normalise, utc_now_iso

#: V3 measured a 906 ms cold load against ~40 ms warm, and confirmed the
#: backend accepts this value. Passed on every embed call so the embedding
#: model stays resident between turns (M5, optional requirement).
EMBED_KEEP_ALIVE = "10m"


# ==============================================================================
# The embedding seam
# ==============================================================================


def embed_text(client: Any, model: str, text: str) -> list[float] | None:
    """Embed ``text``, returning an L2-normalised vector, or ``None`` on any fault.

    RESPONSE ACCESS IS BY SUBSCRIPT, AND THAT IS NOT STYLISTIC. Verification V2
    established that across the `ollama>=0.3.0` range declared at
    requirements.txt:2 the response changes shape: 0.3.0 returns a TypedDict (a
    plain `dict` at runtime) whose `.embeddings` attribute does not exist and
    raises AttributeError, while 0.6.2 returns a pydantic
    `SubscriptableBaseModel` on which both forms work. `resp["embeddings"][0]`
    is the ONLY form valid on both. "Tidying" this to attribute access would
    break every environment resolving below 0.4.0, and the failure would land
    in the broad `except` below — surfacing as permanent silent degradation,
    which is exactly risk R7. It also matches the duck-typing already at
    main.py:144.

    Returning ``None`` rather than raising is M5: no memory-subsystem fault may
    abort a turn. The caller emits exactly one status line and carries on.
    """
    if not text or not text.strip():
        return None

    try:
        response = client.embed(model=model, input=text, keep_alive=EMBED_KEEP_ALIVE)
        raw = response["embeddings"][0]
        vector = [float(value) for value in raw]
    except ollama.ResponseError:
        return None  # AC-3a — embedding model not pulled (trap B, spec.md 3.2)
    except httpx.HTTPError:
        return None  # AC-3b/AC-3c — sidecar unreachable, or the call stalled
    except (KeyError, IndexError, TypeError, ValueError):
        return None  # AC-3h — malformed response, no usable 'embeddings'
    except Exception:
        return None  # M5 backstop: nothing from this subsystem may escape

    if not vector or not any(vector):
        return None  # empty or degenerate all-zero embedding
    return l2_normalise(vector)


# ==============================================================================
# Turn orchestration
# ==============================================================================


#: Similarity floor used to rank candidates before the threshold is applied.
#: Cosine over normalised vectors is bounded below by -1.0, so this admits
#: every eligible record and lets the caller report the true best score.
_RANK_ALL = -1.0


@dataclass
class Recall:
    """The outcome of one retrieval attempt, plus the reusable query vector.

    ``record`` is ``None`` for a MISS — the store was searched and nothing
    cleared the threshold. It is not an error, and callers must distinguish a
    hit from a miss with ``recall.record is not None``: a dataclass instance is
    always truthy, so ``if recall:`` cannot tell them apart.

    ``query_vector`` is populated on hits and misses alike. That is what lets
    the capture path reuse it and honour M2's one-embedding-per-turn limit.
    """

    record: SolutionRecord | None
    similarity: float
    query_vector: list[float]


def recall_for_task(
    client: Any, store: Any, task: str, cfg: MemoryConfig
) -> Recall | None:
    """Retrieve the best prior solution for ``task``.

    Returns ``None`` ONLY when no retrieval happened at all — memory disabled,
    store unavailable, empty store, or the embedding call failed. A completed
    search that cleared nothing is a MISS, and comes back as a ``Recall`` whose
    ``record`` is ``None``: see the note on the miss branch below.

    The empty-store short-circuit comes FIRST and is the point of the whole
    function's ordering: M3 requires that a cold start issue no embedding call
    at all, so it costs zero additional latency. Checking the store before
    embedding is what delivers that, and AC-1 asserts the call count is exactly
    zero rather than merely small.

    `dim` is derived from the returned vector, never hardcoded: the
    nomic-embed-text model page does not publish a dimension, so assuming one
    would be unverified, and deriving it is also what survives a model swap
    (plan.md 2).
    """
    if store is None or not cfg.enabled:
        return None
    if not task or not task.strip():
        return None
    if store.count() == 0:
        return None  # cold start: no embed call at all (M3, AC-1)

    query_vector = embed_text(client, cfg.embed_model, task)
    if not query_vector:
        return None  # AC-3a/b/c/h — degraded, caller emits one status line

    # Ranked WITHOUT the threshold, so a miss can still report how close the
    # best candidate came. The threshold is applied below, once. That structure
    # is what AC-6b depends on, and it survived the v1.1.0 storage change
    # unchanged: only the callee moved, from a free function over an in-process
    # scan to a Milvus vector search behind the storage seam.
    candidates = store.search(
        query_vector,
        cfg.top_k,
        _RANK_ALL,
        cfg.embed_model,
        len(query_vector),
    )

    # A miss — nothing eligible, or nothing above the threshold — still carries
    # the query vector back. The capture path reuses it, so a missed turn costs
    # exactly one embed call and the store keeps learning. Discarding it here
    # would cap the store at its first record forever (M3).
    if not candidates:
        return Recall(record=None, similarity=0.0, query_vector=query_vector)

    best = candidates[0]
    if best.similarity < cfg.min_sim:
        return Recall(
            record=None, similarity=best.similarity, query_vector=query_vector
        )

    return Recall(
        record=best.record, similarity=best.similarity, query_vector=query_vector
    )


def retrieval_degraded(
    store: Any,
    task: str,
    cfg: MemoryConfig,
    result: Recall | None,
) -> bool:
    """True when retrieval ATTEMPTED an embedding and that embedding failed.

    `recall_for_task()` collapses four situations into ``None``, and only one of
    them is a fault. M5 requires a status line for the fault and silence for the
    rest, so the caller needs to tell them apart:

    * ``result is not None``      -> retrieval completed (hit or miss). Fine.
    * memory disabled / no store  -> deliberately off. Not a fault; reporting it
      every turn would be noise, and an unavailable store is already reported
      once at startup.
    * empty store                 -> the cold-start short-circuit, a deliberate
      zero-embed optimisation (M3). Warning here would fire on the first turn of
      every fresh install.
    * non-empty store, no result  -> an embed WAS attempted and failed. Report.

    Must be evaluated before capture, while the record count still reflects the
    state retrieval saw.
    """
    if result is not None:
        return False
    if store is None or not cfg.enabled:
        return False
    if not task or not task.strip():
        return False
    return store.count() > 0


def vector_for_capture(
    client: Any,
    store: Any,
    task: str,
    cfg: MemoryConfig,
    result: Recall | None,
) -> list[float] | None:
    """The vector to persist with this turn, embedding only if retrieval did not.

    This is the seam that keeps M2's "at most one embedding call per turn" true
    in every case, including the two that are easy to get wrong:

    * **Cold start.** Retrieval short-circuits an empty store without embedding
      (AC-1), so there is no cached vector and this is where the turn's single
      embed call happens. Gating capture on the retrieval result instead would
      leave the store permanently empty — every subsequent turn would keep
      short-circuiting, and the feature would never begin working while looking
      entirely healthy.
    * **Degraded backend.** Retrieval already tried and failed on a non-empty
      store. Retrying here would make every turn cost two failed round trips
      for as long as Ollama is down, so it deliberately does not.

    A non-empty store with no cached vector therefore means "the embed already
    failed", and a count of zero means "retrieval never embedded at all".
    """
    if result is not None:
        return result.query_vector  # hit or miss alike — reuse, no extra call
    if store is None or not cfg.enabled:
        return None
    if store.count() > 0:
        return None  # retrieval ran and its embedding failed; do not retry
    return embed_text(client, cfg.embed_model, task)


def remember_success(
    store: Any,
    task: str,
    thought: str,
    code: str,
    stdout: str,
    vector: Sequence[float] | None,
    cfg: MemoryConfig,
) -> bool:
    """Persist one successful turn (M2). ``False`` if anything prevents it.

    Takes no client, by design. That is the structural guarantee behind M2's
    "at most one embedding call per turn": this function *cannot* embed, so the
    vector must be the one `recall_for_task()` already computed.
    """
    if store is None or not cfg.enabled or not vector:
        return False

    embedding = [float(value) for value in vector]
    record = SolutionRecord(
        id=None,
        created_at=utc_now_iso(),
        task=task,
        thought=thought,
        code=code,
        stdout=stdout,
        chat_model=cfg.chat_model,
        embed_model=cfg.embed_model,
        dim=len(embedding),
        embedding=embedding,
    )
    return store.insert(record, cfg.max_records)


# T8(b) EXPERIMENT — no test exercises this, so recall.py drops below its 100%
# floor. Deliberate. REVERT.
def _t8_experiment_uncovered(value: int) -> int:
    if value > 0:
        return value * 2
    return -value
