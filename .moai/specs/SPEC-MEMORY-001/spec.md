---
id: SPEC-MEMORY-001
version: "1.1.0"
status: "draft"
created: "2026-08-02"
updated: "2026-08-03"
author: "Chun Kang"
priority: "HIGH"
---

## HISTORY

### v1.1.0 (2026-08-03) — Vector store changed from SQLite to Milvus Lite

User-directed change of storage substrate. Feasibility study, benchmarks and the five
decisions: `.moai/docs/SPEC-MEMORY-001-V4-milvus-benchmark.md` (**V4**). Upsert and
pruning semantics: `.moai/docs/SPEC-MEMORY-001-V5-milvus-semantics.md` (**V5**).

**This is a revision to working software, not a redesign.** At the time of revision the
v1.0.2 implementation is complete and passing: 243 tests, 100% coverage on both gated
modules, and a live smoke run confirming AC-1, AC-2 (recall fired at similarity **0.76**
on the Seoul→Busan pair; the model said *"we'll use the same approach as before"* and
**adapted** the script rather than replaying it), AC-3, AC-4, AC-5, AC-6b and AC-9.
**M2, M4 and M5 are carried forward unchanged.** Only the storage substrate (M1) and the
retrieval mechanics (M3) are affected.

- **C6 overturned.** "Pure Python cosine, no numpy" no longer holds. numpy arrives as a
  transitive dependency of `pymilvus[milvus_lite]` and the cosine scan is replaced
  entirely. The original decision was correct **on the evidence then available** — the
  pure-Python scan was benchmarked against itself, never against Milvus Lite. V4 §2
  measured Milvus Lite as faster at **every** scale including the original 500-record cap
  (0.78 ms vs 13 ms). Full supersession record at C6 in §4.
- **Out-of-scope item 6 overturned.** Indexing is in scope. The finding is
  counter-intuitive and must be pinned: **FLAT beats HNSW here** (V4 §3).
- **M1 rewritten.** Milvus Lite collection on the existing `coderunner_app_data` volume;
  cap **100,000** (D2); truncation tightened (**D4**); `FLAT`/`COSINE` pinned (D3).
- **V5a and V5b discharged before implementation, and they changed the design.**
  `task_hash` becomes the **VARCHAR primary key**, making dedupe structural via
  `upsert()`. A monotonic `seq INT64` carries the user-facing id and the pruning order,
  and a `meta` side-collection persists `next_seq` / `min_seq` — neither is recoverable
  from the main collection, because **the collection cannot be enumerated**.
- **Two new silent traps recorded** (§3.3, §3.4), both of the same family as trap A —
  failures that ship looking healthy. `order_by` is accepted and **ignored**; `query()`
  is hard-capped at 16,384 rows and `query_iterator` is broken.
- **AC-7 rewritten to assert survivor identity rather than row count** — a count-only
  assertion passes while the wrong records are evicted (V5 §V5b).
- **New constraints C9–C12** recording D2–D5.
- **V5c and V5d specified as non-blocking**; **V5e** added by the author (§3.4).
- **`plan.md` §7's 20,000-record revisit trigger is obsolete**, superseded by V4.
- **Documentation obligation grows materially** — from "we now write to a volume" to a
  footprint approaching **1 GB** on the volume plus **+481 MB** on the image
  (**273 MB → 754 MB**, measured after the build; see the correction below).
- **Image-growth figure corrected after the build (2026-08-04).** Every claim in this SPEC
  that the image "roughly doubles" by "~352 MB" was an *inference* from V4 §1's
  site-packages measurement, not a measurement of the image. The built image measures
  **754 MB against a 273 MB baseline — +481 MB, roughly 2.8×, i.e. tripled.** V4's 352 MB
  figure is correct **as a site-packages measurement** and is retained wherever
  site-packages is what is meant (`plan.md` §1.1, `acceptance.md` AC-14); the image delta
  is larger because of pip metadata, layer overhead and on-disk expansion of the wheels.
  **Do not re-derive the image figure from V4 §1.** Corrected at §2.2, §4.1, `plan.md`
  T15′ and R15, `acceptance.md`'s definition of done, `requirements.txt:7-16`, and V4 §1
  itself.

### v1.0.2 (2026-08-03) — Miss-still-captures defect caught before it shipped

- The retrieval miss path was nearly implemented as "return nothing", which would have
  capped the store at a single record: a miss is exactly what a **new** task looks like,
  so refusing to capture on a miss would freeze the store at its first entry while every
  individual turn continued to look correct. M3 gained an explicit "capture regardless of
  hit or miss" requirement and **AC-6b** was added to catch it.

### v1.0.1 (2026-08-02) — Blocking verifications discharged; threshold revised on evidence

All three blocking verifications (V1, V2, V3) were executed before implementation began.
Full data: `.moai/docs/SPEC-MEMORY-001-V1-verification.md`.

- **V1 CONFIRMED — T12 is load-bearing.** Docker propagates image-directory ownership into
  an empty named volume: a path present in the image and chowned before `USER runner`
  yields a volume owned `1000:1000` and writable; a path *absent* from the image yields a
  **root-owned** volume and `Permission denied`. The contemplated entrypoint-time `mkdir`
  fallback is **unnecessary**. AC-5 must assert *ownership*, not merely that the store
  opened — a test checking only "it opened" cannot fail.
- **V2 CONFIRMED — subscript access is mandatory, not stylistic.** `embed()` exists at the
  `ollama>=0.3.0` floor (`_client.py:250`), so `requirements.txt:2` stays untouched. But
  0.3.0 returns a `TypedDict` (plain `dict`) while 0.6.2 returns a pydantic
  `SubscriptableBaseModel`: `resp["embeddings"][0]` works on both, `resp.embeddings`
  **raises AttributeError on 0.3.0**.
- **V3 CONFIRMED — R1 closed, and C5 found defective.** Cold 906 ms, warm mean 49 ms,
  median 40 ms, dim 768, `keep_alive="10m"` accepted. However the measurement scored
  **AC-2's own pair at 0.7540** against the then-current 0.75 threshold — a margin of
  0.004. Unrelated pairs measured 0.297–0.395 with nothing in 0.40–0.75.
- **C5 revised 0.75 → 0.65** on that evidence.

### v1.0.0 (2026-08-02) — Initial draft

- Initial specification authored by Chun Kang.
- Three design decisions fixed by the user before drafting: semantic retrieval via
  Ollama embeddings; reuse by few-shot prompt injection only (never replay);
  successful runs only (no failure trail, no usage statistics).
- Three open questions resolved by the user at plan approval: memory defaults **on**;
  similarity threshold with a post-smoke-run revisit; the readline-history one-liner
  included as an incidental, separately-revertible compose line.
- Five EARS requirement modules (M1–M5), nine acceptance criteria, thirteen out-of-scope
  items.

---

# SPEC-MEMORY-001 — Solution Memory

**Title:** Solution Memory — persist successful agentic turns and reuse them as few-shot context

## 1. Scope statement

When an agentic turn succeeds, persist the task, the model's reasoning, the executed
script and the real stdout to an **embedded Milvus Lite vector store** on a Docker named
volume, together with an Ollama-generated embedding of the task. On a subsequent turn,
semantically retrieve the single most similar past solution above a similarity threshold
and inject it as an **ephemeral few-shot system message** immediately before the user's
message, leaving the model free to reason and adapt.

The feature is an enhancement, never a dependency: any fault in the memory subsystem
leaves CodeRunner.AI behaving exactly as it does today.

## 2. Verified environment

### 2.1 Base image (measured 2026-08-02, `coderunner-ai:latest`)

```
python      3.11.15
ollama      0.6.2           (requirements.txt:2 floors at >=0.3.0)
```

Embedding API surface, verified by introspection **and** against the `>=0.3.0` floor by V2:

```python
resp = client.embed(model=EMBED_MODEL, input=text, keep_alive="10m")
vector = list(resp["embeddings"][0])
```

**Subscript access is mandatory, not stylistic.** `ollama==0.3.0` returns a `TypedDict`
(a plain `dict` at runtime) and `resp.embeddings` raises `AttributeError` there; `0.6.2`
returns a pydantic `SubscriptableBaseModel` where both forms work. Subscript is the only
access pattern valid across the whole permitted range. A reviewer who "tidies" this to
attribute access silently breaks every environment resolving below 0.4.0, and the failure
lands in `recall.py`'s broad `except` — surfacing as permanent silent degradation, exactly
the R7 mode. Implemented at `recall.py:42-78`.

Embedding model: `nomic-embed-text:latest` — 274 MB, pulled in 12.3 s, **dim 768**
(measured, not assumed). Cold embed 906 ms, warm median 40 ms.

### 2.2 Milvus Lite (measured 2026-08-03/04, same image, aarch64, `pymilvus 3.0.1`)

Full data in **V4** and **V5**. The points that constrain implementation:

- `pip install pymilvus` alone is **insufficient** — `MilvusClient("<path>")` raises
  `ConnectionConfigException`. The extra is required: `pip install "pymilvus[milvus_lite]"`
  (V4 §1). A one-word omission that produces total, immediate failure.
- An aarch64 Linux wheel exists and is importable in-container (V4 §1).
- **numpy arrives transitively.** Our code does not use it; it lands in the image anyway.
- **Site-packages cost 352 MB** (V4 §1). ~~The image roughly doubles.~~ **CORRECTED
  2026-08-04, measured after the build:** the image goes **273 MB → 754 MB**, i.e.
  **+481 MB, roughly 2.8× — tripled, not doubled.** The 352 MB figure remains correct for
  site-packages in isolation; the image delta exceeds it because of pip metadata, layer
  overhead and the wheels' on-disk expansion. Use the measured image figures in anything
  user-facing.
- Search beats the pure-Python scan at **every** scale, including the original 500-record
  cap: 0.78 ms vs 13 ms at 500; 238 ms vs ~1,100 ms at 50,000 (V4 §2).
- At the 100,000 cap with `FLAT`: **133 ms median, 169 ms p90, 618 MB** (V4 §3).

**Operation costs at the cap** (V5 "Cost at the 100,000 cap"):

| Operation | Cost |
|---|---:|
| Insert 100k (batches of 5,000) | 29.8 s |
| `delete(filter="seq < X")` per 1,000 rows | 0.26 s |
| `get_collection_stats()` row_count | negligible, uncapped, trustworthy |
| `query()` ceiling | **16,384 rows — hard cap** |

## 3. The four traps

Traps A and B are resolved and must not regress. Traps C and D are introduced by the
storage change. All four share one shape: **a failure that ships looking healthy.**

### 3.1 Trap A — the root-owned named volume *(resolved; do not regress)*

A Docker **named** volume mounted at a path that does **not exist in the image** is
created **root-owned**. `runner` then cannot write, the memory subsystem takes its
graceful-degradation path on every turn, and the feature never works — while looking, from
outside, like well-behaved degradation.

**V1 CONFIRMED this and the fix is in the tree** at `Dockerfile:42-46`: `mkdir -p` and
`chown` of `/home/runner/.coderunner` occur before `USER runner`, with the rationale in
the comment at `Dockerfile:36-41`. AC-5 passed live, showing `1000:1000` and no
degradation line. **Unchanged under Milvus Lite** — the same directory now holds a Milvus
file set instead of one SQLite file, and the same ownership requirement applies.

### 3.2 Trap B — the launcher never pulls the embedding model *(resolved; do not regress)*

The launcher gated the `model-pull` service on the **chat** model being missing. On any
machine that already had `llama3.1:8b`, the embedding model would never be fetched and
`client.embed` would raise `ollama.ResponseError` on every turn forever. Fixed in TASK-09;
the `:latest` suffix on the default tag is load-bearing because `grep -qx` matches
fully-qualified tags (`docker-compose.yml:76-80` records this).

### 3.3 Trap C — `order_by` is accepted and silently ignored *(NEW; V5b)*

**This is the most dangerous finding in the migration.** V5 proved it with deliberately
shuffled data:

```
inserted in order          : [50, 10, 90, 30, 70, 20, 80, 40, 60, 0]
query limit=5, no order_by : [50, 10, 90, 30, 70]
query limit=5, order_by=seq: [50, 10, 90, 30, 70]   ← IDENTICAL. NOT SORTED.
```

`order_by="seq"` **does not raise**. It is swallowed by the dynamic-kwargs path and
discarded, returning insertion order.

The obvious pruning implementation — "query the oldest N, then delete them" — therefore
selects **arbitrary** rows. The code looks correct, passes a count-only assertion
(`count == cap`), and evicts the wrong records forever. A user's most valuable memories
disappear while `/memory` reports exactly the expected number of entries.

**Mandated consequences:** `order_by` is prohibited outright (M1); pruning uses a
converging delete-by-filter loop (M1); and **AC-7 asserts survivor identity, never row
count** — the same lesson as AC-5, where "the store opened" passed in both the working and
the broken case.

### 3.4 Trap D — the collection cannot be enumerated *(NEW; V5b)*

```
query(..., limit=16384) on 100k rows   → returned exactly 16384 (LIMIT-CAPPED)
query_iterator(batch_size=3) on 10 rows → returned 3 of 10, then stopped
  [WARNING] failed to get mvccTs from milvus server, use client-side ts instead
```

`query()` is hard-capped at 16,384 rows and `query_iterator` is broken. **There is no
reliable way to read the whole collection**, so "read all `seq` values and compute the
oldest N" is simply unavailable — and any code that tries will appear to work at small
sizes and silently truncate past 16,384. This is why `next_seq` and `min_seq` must be
persisted externally (M1): they cannot be recovered from the data.

`get_collection_stats()["row_count"]` is accurate, cheap and uncapped, and is the only
trustworthy count signal (V5). `query()` is not.

**Residual, unmeasured:** whether `get_collection_stats()["row_count"]` is *immediately*
consistent after a write. Three behaviours depend on the count taken during a turn —
AC-1's zero-embed cold start (`recall.py:135`), M5's one-status-line classifier
(`recall.py:172-202`) and AC-6b's capture-on-miss path (`recall.py:234`) — and all three
call it up to three times per turn. If a post-write count is stale, all three break
silently. Tracked as **V5e**, non-blocking (§ `plan.md` 5.1).

## 4. Fixed design constraints

Decided by the user; **not open for re-litigation** during implementation.

| # | Constraint | Decided by | Recorded |
|---|---|---|---|
| C1 | **Retrieval is semantic**, via Ollama embeddings. Not keyword, not FTS5, not exact match. | User, before drafting | M3 |
| C2 | **Reuse is few-shot prompt injection.** The retrieved solution enters the prompt as context; the model still reasons and may adapt. Stored code is never replayed and the LLM is never skipped. | User, before drafting | M4 |
| C3 | **Successful runs only.** No failure trail, no usage statistics in v1. | User, before drafting | M2 |
| C4 | **Memory defaults ON** (`CODERUNNER_MEMORY=1`). | User, at plan approval | M5 |
| C5 | **Similarity threshold 0.65.** Originally 0.75 by judgement; V3 measured AC-2's own pair at **0.7540**, i.e. 0.004 above the cutoff, making the criterion flaky by construction. Unrelated pairs measure 0.297–0.395; nothing occupies 0.40–0.75. The live smoke run scored the same pair at **0.76**, clearing 0.65 by 0.11. **Unchanged at v1.1.0.** | User; revised on V3 evidence 2026-08-02 | M3 |
| **C6** | ~~Pure Python cosine, no numpy.~~ **SUPERSEDED at v1.1.0 → Milvus Lite, embedded** (D1). Not standalone containers, not a hybrid with SQLite; `pip install "pymilvus[milvus_lite]"`. numpy arrives transitively and is accepted. *The original decision was sound on the evidence then available: the pure-Python scan was benchmarked only against itself. V4 §2 measured Milvus Lite faster at every scale including 500 records (0.78 ms vs 13 ms), which is the fact that overturns it.* | Author, approved by user; **superseded by user on V4 evidence 2026-08-03** | M1, M3 |
| C7 | **`top_k = 1`** by default. | Author, approved by user | M3 |
| C8 | **Injection on attempt 1 only.** | Author, approved by user | M4 |
| **C9** | **Record cap 100,000** (was 500). 133 ms median search at that size — well within budget beside a multi-second LLM stream (D2, V4 §3). | User, 2026-08-03 | M1 |
| **C10** | **Index `FLAT`, metric `COSINE` — pinned explicitly, never left to a default.** FLAT measured *faster* than HNSW at 100k (133 vs 190 ms median) and far better at the tail at 200k (291 ms vs **1,742 ms** p90). HNSW's only advantage is disk at 200k, which does not apply at the 100k cap (D3, V4 §3). | User, 2026-08-03 | M1, M3 |
| **C11** | **Truncation tightened**: thought 4,000 → **1,000**; stdout 4,000 → **1,000**; code 8,000 → **4,000**; task unchanged at **2,000**. ≈8 KB/record. **Recall quality is unaffected — only the task text is embedded** (D4, V4 §4-5). | User, 2026-08-03 | M1 |
| **C12** | **Milvus is isolated behind a storage seam.** A stdlib-only core retains the record model, truncation, dedupe hashing, config parsing, `format_recall_block`, `inject_recall` and `handle_memory_command`; **all** `pymilvus` calls live in one thin module, mirroring how `recall.py` already isolates `ollama` (D5). | User, 2026-08-03 | M1, `plan.md` §1 |

### 4.1 Consequence of C4 + C6 — the documentation obligation, materially enlarged

Defaulting memory ON already made this the first thing in CodeRunner.AI that writes user
content to persistent host storage, rendering the "zero residue on the host" positioning
partly untrue:

- `product.md` §2.3 — "Zero-setup, zero-residue on the host"
- `README.md:15` — the no-residue framing

**At v1.1.0 the size of that residue changes by three orders of magnitude.** The amendment
must state, in plain numbers and without softening:

| Component | Figure | Source |
|---|---:|---|
| Volume, typical at the 100,000 cap | **≈0.9 GB** | V4 §4 |
| Volume, worst case with C11 truncation | **≈1.4 GB** | V4 §5 (D4) |
| Vectors alone (FLAT, 100k × 768 dims) | **618 MB** | V4 §3 |
| Volume, observed at 2 records | **32.4 KB** | measured, T16′ |
| **Container image** | **273 MB → 754 MB — +481 MB, roughly 2.8×** | **measured after the build, 2026-08-04** |
| Site-packages alone, for reference | ≈352 MB | V4 §1 |

**The image row was corrected on 2026-08-04 and must not be reverted to "~352 MB /
roughly doubles".** That earlier figure was V4 §1's *site-packages* measurement with an
image-growth inference laid on top of it. Both numbers are real; they measure different
things, and the image is the one a user sees. Site-packages remains the right figure when
the subject is the dependency tree a test would acquire (`plan.md` §1.1, AC-14).

This is the single most user-visible consequence of the storage change. A user who
installs CodeRunner.AI on the strength of "zero residue" and later finds a 1 GB Docker
volume and a tripled image has been misled by our documentation, not by the feature.
**T15 must state these figures.** `tech.md` §7.2 must also gain the persistent-surface
note from risk R6.

---

## 5. EARS requirements

Five modules. All five EARS requirement types are represented.
**M2, M4 and M5 are carried forward from v1.0.2 unchanged.**

### M1 — Persistent storage substrate *(REWRITTEN at v1.1.0)*

#### 5.1.1 Collection design (settled by V5a/V5b)

| Field | Type | Role |
|---|---|---|
| `task_hash` | **VARCHAR, PRIMARY KEY** | SHA-256 of the normalised task. Makes dedupe **structural**: `upsert()` replaces in place. |
| `seq` | **INT64** | Monotonic insertion sequence. The **user-facing id** for `/memory forget <id>`, and the **only** ordering available for pruning. |
| `embedding` | FLOAT_VECTOR(`dim`) | The task embedding. |
| `task`, `thought`, `code`, `stdout` | VARCHAR | Truncated per C11. |
| `chat_model`, `embed_model` | VARCHAR | Provenance; `embed_model` is half the eligibility filter. |
| `dim` | INT64 | The other half of the eligibility filter. |
| `created_at` | VARCHAR | ISO-8601 UTC. |

Plus a **`meta` side-collection** persisting `schema_version`, `next_seq`, `min_seq`,
`embed_model`, `dim`. `next_seq` and `min_seq` **cannot be recovered from the main
collection** — trap D means it cannot be enumerated — so they must be persisted, not
derived.

#### 5.1.2 Requirements

| Type | Requirement |
|---|---|
| **Ubiquitous** | The system **shall always** store solution memory in an **embedded Milvus Lite** collection under `CODERUNNER_MEMORY_DB`, on the named volume `coderunner_app_data` mounted at `/home/runner/.coderunner` (`docker-compose.yml:67-68`), so records survive the `--rm` lifecycle (`coderunner:263`). *(C6, D1)* |
| **Ubiquitous** | The system **shall always** install the vector store via `pymilvus[milvus_lite]`, and **shall not** rely on the bare `pymilvus` distribution: `MilvusClient("<path>")` raises `ConnectionConfigException` without the extra (V4 §1). |
| **Ubiquitous** | The system **shall always** create the collection with **`index_type="FLAT"`** and **`metric_type="COSINE"`, both specified explicitly**, and **shall not** rely on any library default. *(C10)* |
| **Ubiquitous** | The system **shall always** use `task_hash` as the **VARCHAR primary key** and write via `client.upsert()`, so that dedupe is structural rather than a clause. *(V5a)* |
| **Ubiquitous** | The system **shall always** persist `schema_version`, `next_seq` and `min_seq` in a `meta` side-collection, and **shall not** attempt to derive them from the main collection. *(V5b trap 2)* |
| **Event-driven** | **WHEN** a record is upserted whose `task_hash` already exists, **THEN** the system **shall** carry forward the existing record's `seq` and `created_at` rather than assigning new ones. *(See the note below — this is where the id-stability hazard now lives.)* |
| **Event-driven** | **WHEN** a record is inserted whose `task_hash` is new, **THEN** the system **shall** assign `seq = next_seq` and increment the persisted `next_seq`. |
| **Event-driven** | **WHEN** `get_collection_stats()["row_count"]` exceeds `CODERUNNER_MEMORY_MAX_RECORDS` (default **100,000**, *C9*), **THEN** the system **shall** prune by a **converging delete-by-filter loop**: `delete(filter=f"seq < {min_seq + batch}")`, advance the persisted `min_seq`, re-read `row_count`, repeat until at or below the cap. Sequence gaps **shall** be tolerated — the loop converges on `row_count`, not on arithmetic. |
| **Ubiquitous** | The system **shall always** use `get_collection_stats()["row_count"]` as the authoritative count, and **shall not** use `query()` for counting or enumeration. `query()` is hard-capped at **16,384** rows and `query_iterator` is broken (trap D). |
| **Unwanted** | The system **shall not** use `order_by` anywhere, in any call. Milvus Lite **accepts it and silently ignores it** (trap C). A comment recording this **shall** be present at the pruning site; without it, a future reader will "simplify" the converging loop straight back into the bug. |
| **Unwanted** | The system **shall not** determine pruning order by a sorted query, nor by `created_at`. `created_at` has second granularity and AC-7 inserts records in a tight loop, so timestamps tie and "the oldest record" becomes non-deterministic; `seq` is the only stable definition of insertion order. |
| **Unwanted** | The system **shall not** store any field beyond its truncation limit — **task 2,000, thought 1,000, code 4,000, stdout 1,000** characters *(C11)* — bounding a record to ≈8 KB and the worst-case volume to ≈1.4 GB at the cap (V4 §5). |
| **Unwanted** | The system **shall not** migrate, read, or convert any pre-existing SQLite `memory.db`. v1.0.x data is development-only and **shall** be abandoned (§6 item 14). |

#### 5.1.3 Where the id-stability hazard went

The SQLite design chose `ON CONFLICT(task_hash) DO UPDATE` over `INSERT OR REPLACE`
specifically because the latter reallocates the `AUTOINCREMENT` id and silently breaks
`/memory forget <id>`. **That code no longer exists** — `MemoryStore` and its schema were deleted when `vectorstore.py` took over; the citation is to the v1.0.x tree.

Making `task_hash` the primary key removes that hazard **at the engine level** — there is
no surrogate primary key left for the engine to reallocate. But it does not remove it
outright: **`seq` is now the surrogate id, and `upsert()` overwrites every non-key field,
including `seq`.** V5a's own trace shows this — the replaced row came back as
`{'task_hash': 'h2', 'seq': 99, ...}`, carrying whatever `seq` the upsert supplied.

So the hazard has moved from the engine to our code, and the mitigation moves with it:
before upserting an existing hash, **point-query that row by primary key** for its `seq`
and `created_at` and carry both forward. A point query by primary key is not affected by
the 16,384-row cap. Getting this wrong reproduces exactly the v1.0.x defect the original
design went out of its way to avoid — `/memory forget 4` starts addressing a different
record after a re-ask — and no count-based test will notice.

### M2 — Capture of successful turns *(UNCHANGED from v1.0.2)*

| Type | Requirement |
|---|---|
| **Event-driven** | **WHEN** `agentic_turn()` reaches its success path and has streamed the grounded answer, **THEN** the system **shall** persist one record containing the task (`user_input`), the model's reasoning (`thought`), the executed script (`code`, from `extract_last_python_block()`), the real stdout (`result.stdout`), the chat model tag, the embedding model tag, the vector dimension, and the task embedding. Wired at `main.py:515-523`. |
| **Ubiquitous** | The system **shall always** reuse the task embedding already computed for retrieval earlier in the same turn, issuing **at most one** embedding call per turn. Structurally guaranteed: `remember_success()` takes no client and therefore *cannot* embed (`recall.py:239-270`). |
| **State-driven** | **WHILE** `CODERUNNER_MEMORY` is `0`, the system **shall** perform no capture and **shall** open no store. |
| **Unwanted** | The system **shall not** persist any record for a turn that failed, timed out, exhausted retries, or returned via the DIRECT protocol. *(C3)* |
| **Unwanted** | The system **shall not** persist failure trails, attempt counts, retrieval hit/miss counters, last-used timestamps, or any other usage statistic. *(C3)* |

### M3 — Semantic retrieval *(REWRITTEN at v1.1.0)*

| Type | Requirement |
|---|---|
| **Event-driven** | **WHEN** a turn begins and the store holds at least one eligible record, **THEN** the system **shall** embed the user's task and **shall** select the top-`CODERUNNER_MEMORY_TOP_K` (default 1, *C7*) records by cosine similarity **via a Milvus vector search**, not by an in-process scan. |
| **Ubiquitous** | The system **shall always** restrict candidates to records whose stored `embed_model` and `dim` match the current configuration, **expressed as a Milvus scalar filter applied by the search itself**, never by post-filtering the result set. This is what stops a changed embedding model producing meaningless comparisons against stale vectors, and post-filtering would let a stale vector displace a current one in the ranking however high its raw score (R8). **Preserving this filter is mandatory.** |
| **Ubiquitous** | The system **shall always** interpret the score returned by Milvus as a cosine similarity in `[-1, 1]`, directly comparable to `CODERUNNER_MEMORY_MIN_SIMILARITY`. **A metric that returns a distance (lower-is-better) shall not be used**, because every threshold comparison in the system is written as a lower bound. *(C10; verified by AC-10.)* |
| **State-driven** | **IF** the store is empty, **THEN** the system **shall** skip the embedding call entirely, so a cold start costs zero additional latency (`recall.py:135-136`). |
| **State-driven** | **IF** the best candidate's similarity is below `CODERUNNER_MEMORY_MIN_SIMILARITY` (default **0.65**, *C5*), **THEN** the system **shall** treat the retrieval as a miss and **shall** inject nothing. **A miss shall still surface the computed query embedding to the caller** so the capture path can reuse it and honour M2's one-embedding-per-turn limit (`recall.py:157-164`). **A miss shall not be expressed by discarding the retrieval result entirely.** |
| **Ubiquitous** | The system **shall always** capture a successful turn regardless of whether retrieval hit or missed. *Rationale, recorded because this was nearly implemented wrongly:* a miss is exactly what a **new** task looks like. If misses were not captured the store would retain its first record and never learn again — the feature would silently cap itself at one entry. The only permitted non-capture conditions are those in M2. |
| **Unwanted** | The system **shall not** use keyword, substring, exact-match, or FTS5 retrieval. *(C1)* |

### M4 — Reuse by prompt injection *(UNCHANGED from v1.0.2)*

| Type | Requirement |
|---|---|
| **Event-driven** | **WHEN** retrieval returns a hit, **THEN** the system **shall** insert a single `system`-role message containing the formatted prior solution immediately **before** the current user message in the list sent to the model, for **attempt 1 only**. Implemented at `main.py:466-470` via `inject_recall()` (`memory.py:390-404`). *(C8)* |
| **Ubiquitous** | The system **shall always** frame the injected block as reference material the model must adapt or ignore, never as an instruction to reproduce. The exact adapt-or-ignore sentence is a named constant so a test can assert it verbatim (`memory.py:352-355`). |
| **Unwanted** | The system **shall not** mutate `Conversation.messages` with the injected block. `inject_recall()` returns a **new** list (`main.py:466-470`), so the block is ephemeral to one request and cannot accumulate across turns (`product.md` §6.6). |
| **Unwanted** | The system **shall not** execute, replay, or short-circuit the LLM using stored code. Every turn **shall** still stream from the model, and every executed script **shall** be whatever the model emits in that turn. *(C2)* **Confirmed live:** the smoke run showed the model saying *"we'll use the same approach as before"* and then adapting the script for a different city. |
| **Unwanted** | The system **shall not** inject a recall block into retry attempts 2..N, nor into the second, grounded-answer pass (`main.py:502`). |

### M5 — Degradation, configuration and user control *(UNCHANGED from v1.0.2)*

The one-status-line-per-turn invariant was fixed and mutation-tested at v1.0.2. **The
`retrieval_degraded()` classifier (`recall.py:172-202`) must survive the migration
unchanged**: it is what distinguishes a genuine fault from the deliberate cold-start
short-circuit, and without that distinction the system either warns on the first turn of
every fresh install or never warns at all.

| Type | Requirement |
|---|---|
| **Ubiquitous** | The system **shall always** treat solution memory as an enhancement. **IF** the embedding call fails, the embedding model is unavailable, the volume is missing, or **the vector store cannot be opened, is corrupt, or is locked**, **THEN** the system **shall** emit exactly one status line via `status()` and **shall** continue the turn with behaviour identical to the pre-feature product. |
| **Ubiquitous** | The system **shall always** emit **at most one** memory status line per turn. A retrieval warning **shall** suppress a subsequent capture warning for the same turn (`main.py:416`, `main.py:424`). |
| **Unwanted** | The system **shall not** raise, abort a turn, or exit non-zero for any memory-subsystem fault. Precedent: `tools.py:91-92`, `tools.py:95-96`, `main.py:603-604`. |
| **Ubiquitous** | The system **shall always** parse memory configuration through validating helpers that catch `ValueError`, clamp to a documented range, and fall back to the default (`memory.py:110-161`). The system **shall not** replicate the unguarded `int(os.environ.get(...))` pattern at `main.py:67-68`, which raises at import time before any Rich rendering. |
| **Event-driven** | **WHEN** the user enters `/memory`, `/memory list [n]`, `/memory forget <id>`, or `/memory clear --yes`, **THEN** the system **shall** handle it locally and **shall not** invoke `agentic_turn()`. Implemented at `memory.py:447-494`, with its `_emit_*` helpers at `memory.py:497-567`. |
| **Event-driven** | **WHEN** the user enters `/memory forget <id>`, **THEN** the system **shall** resolve `seq == <id>` to a `task_hash` and delete by primary key. *(V5a)* |
| **Event-driven** | **WHEN** the user enters `/memory clear` **without** `--yes`, **THEN** the system **shall** delete nothing and **shall** print the required form. |
| **Optional** | **WHERE** the operator sets `CODERUNNER_MEMORY=0`, the system **shall** disable capture, retrieval and store creation entirely, and the launcher **shall** skip the 274 MB embedding-model download. |
| **Optional** | **WHERE** the embedding backend supports it, the system **shall** pass `keep_alive="10m"` (`recall.py:63`) so the embedding model stays resident between turns. |

---

## 6. Out of scope for v1

1. **Replay or execution of stored code.** Retrieved solutions are prompt context only. *(C2)*
2. **Failure storage.** No failed attempts, no stderr archive, no anti-patterns. *(C3)*
3. **Usage statistics.** No hit counters, no last-used timestamps, no success-rate-weighted ranking. *(C3)*
4. **Storing the final grounded answer.** Only task / thought / code / stdout are persisted.
5. **Cross-project or cross-machine sharing.** No export, import, sync, or remote store.
6. ~~**Approximate nearest-neighbour indexing.** A brute-force scan makes an index pure overhead.~~ — **OVERTURNED at v1.1.0.** Indexing is in scope. That assertion was inherited from the pure-Python benchmark and is not supported by direct measurement (V4 §2, "Correction to an earlier claim"). The finding is that **FLAT beats HNSW here**, so the index is pinned rather than defaulted *(C10)*. **HNSW, IVF and any other ANN index remain out of scope** — they were measured and rejected.
7. ~~**numpy.** Decided against on measured evidence.~~ — **OVERTURNED at v1.1.0.** numpy arrives transitively with `pymilvus[milvus_lite]` (V4 §1). It is accepted, not adopted: **no first-party code may import it**, and the stdlib-only test on the core module enforces that *(C12)*.
8. **Retrofitting the existing config-parsing hazard** at `main.py:67-68`.
9. **Tests for pre-existing `main.py` / `tools.py` code.** The coverage gate is scoped to the memory modules.
10. **Prompt-history persistence as a tracked concern.** The one-line compose fix is *included* at `docker-compose.yml:97-100` as an incidental, separately-revertible side effect; no EARS requirement, no acceptance criterion, no test.
11. **Fixing `--doctor`'s heavy side effects** (`product.md` §6.4), the stale-image hazard (§6.3), or the stale connection-help text (§6.10).
12. **Conversation-history trimming** (`product.md` §6.6).
13. **Retrieval during retry attempts**, multi-example few-shot beyond `top_k`, and any re-ranking pass.
14. **Migration from the v1.0.x SQLite store.** *(NEW at v1.1.0.)* No data is converted. The SQLite implementation exists only in an uncommitted working tree; writing a converter for development-only data would be scope creep. Any pre-existing `memory.db` is left untouched and ignored.
15. **Standalone or hybrid Milvus deployments.** *(NEW at v1.1.0.)* Embedded Milvus Lite only — no etcd, no MinIO, no extra containers, no SQLite fallback tier *(C6/D1)*. Extra services would break the zero-setup premise the launcher exists to deliver (`coderunner:36-219`).
16. **Reclaiming sequence gaps or compacting `seq`.** *(NEW at v1.1.0.)* Gaps left by dedupe and pruning are permanent and harmless; the pruning loop converges on `row_count`, not on arithmetic (V5).

---

## 7. Traceability

| Artefact | Location |
|---|---|
| Requirements | this file, §5 (M1–M5) |
| Implementation plan, schema, tasks, risks | `.moai/specs/SPEC-MEMORY-001/plan.md` |
| Acceptance criteria and quality gates | `.moai/specs/SPEC-MEMORY-001/acceptance.md` |
| V1/V2/V3 verification data | `.moai/docs/SPEC-MEMORY-001-V1-verification.md` |
| **V4 — Milvus feasibility and benchmarks** | `.moai/docs/SPEC-MEMORY-001-V4-milvus-benchmark.md` |
| **V5 — Milvus upsert and pruning semantics** | `.moai/docs/SPEC-MEMORY-001-V5-milvus-semantics.md` |
| Source under specification | `main.py`, `memory.py`, `recall.py`, `vectorstore.py` (new), `tools.py`, `Dockerfile`, `docker-compose.yml`, `coderunner`, `requirements.txt`, `README.md` |
| Project context | `.moai/project/product.md`, `.moai/project/structure.md`, `.moai/project/tech.md` |

`.claude/` and `.moai/` are MoAI agent tooling and are **not** product code.

| Module | Primary acceptance criteria |
|---|---|
| M1 — storage substrate | AC-1, AC-4, AC-5, **AC-7 (rewritten)**, **AC-11**, **AC-13**, **AC-14** |
| M2 — capture | AC-1, AC-6, AC-6b, AC-7 |
| M3 — retrieval | AC-1, AC-2, AC-6, AC-6b, **AC-10**, **AC-12** |
| M4 — injection | AC-2 |
| M5 — degradation and control | AC-3, AC-8, AC-9, **AC-14** |
