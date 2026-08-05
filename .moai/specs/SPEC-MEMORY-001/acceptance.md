# SPEC-MEMORY-001 — Acceptance Criteria (v1.1.0)

> Requirements are in `spec.md`. Implementation detail is in `plan.md`.
> **AC-1 through AC-6b and AC-9 are behavioural, not storage-specific. They passed live
> against the v1.0.2 build and carry over essentially unchanged.** AC-7 is rewritten;
> AC-3's fault variants are re-typed; AC-10 through AC-14 are new at v1.1.0.

**Status at revision:** 243 tests passing, 100% coverage on both gated modules, and a live
smoke run confirming AC-1, AC-2 (similarity **0.76**), AC-3, AC-4, AC-5, AC-6b and AC-9.
The bar for this revision is *do not lose that*.

A recurring theme runs through AC-5, AC-6b, AC-7 and AC-13: **an assertion that cannot
distinguish the working case from the broken one is not an acceptance criterion.** Each of
those four exists because a plausible implementation fails while every count, every status
line and every individual turn still looks correct.

---

## AC-1 — Cold start (empty store) — *carries over*

Covers M1, M2, M3.

**Given** a freshly created `coderunner_app_data` volume containing no collection, and
memory enabled (`CODERUNNER_MEMORY=1`, per C4)

**When** the user submits their first computational task

**Then**

- the collection and the `meta` side-collection are created, with `schema_version`,
  `next_seq` and `min_seq` persisted;
- retrieval reports zero records;
- **no embedding call is issued at all** — the empty-store short-circuit at
  `recall.py:135-136` means a cold start costs zero additional latency (M3);
- no recall block is injected;
- the message list sent to the model is byte-for-byte identical to the pre-feature
  behaviour.

**And** on success exactly one record exists, whose embedding is non-empty, whose `dim`
equals the runtime-derived value in `meta` — confirming the dimension was **not**
hardcoded — and whose `seq` is the first value allocated from `next_seq`.

---

## AC-2 — Reuse on a semantically similar task — *carries over; passed live at 0.76*

Covers M3, M4.

**Given** a stored record for `"What is the current weather in Seoul in Celsius?"`

**When** the user asks `"Tell me the temperature in Busan right now"` and the cosine
similarity is at or above 0.65 (C5)

**Then**

- exactly **one** `system`-role message containing the prior task, approach, script and
  output is present in the attempt-1 request;
- it is positioned **immediately before** the current user message;
- the block carries the adapt-or-ignore framing (`memory.py:352-355`).

**And** `Conversation.messages` is **unchanged** by the injection — assert length and
content before and after, proving the block is ephemeral (`main.py:466-470`).

**And** the model is still invoked and the executed script is the one emitted in **this**
turn, not the stored one (C2).

**And** attempts 2..N and the grounded-answer pass (`main.py:502`) receive
`conv.messages` with **no** recall block (C8).

> **Live result to preserve:** the smoke run scored this pair at **0.76** and the model
> said *"we'll use the same approach as before"* before **adapting** the script for a
> different city. That is C2 working exactly as specified — reuse without replay.

---

## AC-3 — Degradation: memory subsystem unavailable — *carries over; fault types re-typed*

Covers M5. **This is the mandatory degradation scenario.**

**Given** the embedding model is not present, so `client.embed` raises
`ollama.ResponseError`

**When** a turn runs

**Then**

- **exactly one** status line is printed via `status()`;
- no exception propagates;
- no recall block is injected;
- no record is captured;
- the turn produces the same thought → code → execution → grounded-answer sequence as with
  the feature entirely absent, and the process exits 0.

### AC-3 parameterised variants

The **outcomes are unchanged from v1.0.2**; only the injected exception types move from
`sqlite3` to the Milvus layer.

| Variant | Injected fault | Change at v1.1.0 |
|---|---|---|
| **AC-3a** | `ollama.ResponseError` from `client.embed` | unchanged |
| **AC-3b** | `httpx.ConnectError` from `client.embed` | unchanged |
| **AC-3c** | `httpx.ReadTimeout` from `client.embed` | unchanged |
| **AC-3d** | Store path unwritable — open fails | re-typed to the Milvus exception |
| **AC-3e** | Store files corrupt — open or read fails | re-typed |
| **AC-3f** | Volume absent — parent directory cannot be created | unchanged (`OSError`) |
| **AC-3g** | Store locked by another process | **deferred to V5d.** The SQLite form used `BEGIN EXCLUSIVE` past `busy_timeout`; the Milvus Lite equivalent is unknown. Re-enable once V5d reports. |
| **AC-3h** | `client.embed` returns a malformed response with no `embeddings` key | unchanged |
| **AC-3i** | **NEW** — `pymilvus` importable but `milvus_lite` extra missing, so `MilvusClient(path)` raises `ConnectionConfigException` (V4 §1) | new |

Precedent being matched: `tools.py:91-92`, `tools.py:95-96`, `main.py:603-604`.

**And** M5's one-line invariant holds in every variant: a retrieval warning suppresses a
subsequent capture warning for the same turn (`main.py:416`, `main.py:424`). This was fixed
and mutation-tested at v1.0.2 and **must not regress**.

---

## AC-4 — Persistence across the `--rm` boundary — *carries over*

Covers M1.

**Given** a session in which one task succeeded and was captured

**When** the container exits (`coderunner:263`), `cleanup()` runs
(`coderunner:222-230`), and `./coderunner` is launched again

**Then** `/memory` reports a record count of at least 1 and the same store path, proving
the record outlived the ephemeral container.

**And** `next_seq` and `min_seq` are read back from the `meta` side-collection with the
values they held at exit. **They cannot be recovered from the main collection** (trap D),
so a fresh process that fails to persist them would restart sequence allocation from zero
and begin colliding with existing records.

**And** the previously pulled models are still present, confirming `app_data` did not
disturb `coderunner_ollama_data` and that `cleanup()`'s use of `stop` rather than `down`
still preserves both volumes.

---

## AC-5 — Volume writability by the `runner` user — *carries over; passed live*

Covers M1. **Exists specifically to catch trap A** (`spec.md` §3.1).

**Given** a never-before-created `coderunner_app_data` volume

**When** the container starts as `runner` (`Dockerfile:46`)

**Then**

- the mount directory `/home/runner/.coderunner` is owned by `runner` (`1000:1000`), not
  root;
- the store opens read-write on the **first** attempt;
- the degradation path of M5 is **not** taken;
- `/memory` reports an enabled, writable store.

**Explicitly:** a run in which memory silently degrades on every turn **fails** this
criterion, even though no error is raised and the product otherwise behaves correctly.
V1 proved a test asserting only "it opened" passes in both the working and the broken case.

---

## AC-6 — Retrieval below threshold is a miss — *carries over*

Covers M2, M3.

**Given** a store containing only weather-lookup records

**When** the user asks `"Explain the difference between a list and a tuple"` — a
DIRECT-protocol question with low similarity to anything stored

**Then**

- no recall block is injected, the best similarity being below 0.65 (C5);
- the turn returns via the no-code-block early return;
- **no record is captured**, because DIRECT-protocol turns are excluded by M2.

Note the reason for the non-capture: it is the **DIRECT protocol**, not the retrieval miss.
A miss on its own never suppresses capture — see AC-6b.

---

## AC-6b — A missed retrieval still captures, and still costs one embedding — *carries over; passed live*

Covers M2, M3. Added at v1.0.2 after the miss path was nearly implemented as "return
nothing", which would have capped the store at a single record.

**Given** a non-empty store whose best candidate scores **below** 0.65 for the current task

**When** the turn runs the CODE protocol and the generated script executes successfully

**Then**

- no recall block is injected (the miss);
- the retrieval result still **carries the computed query embedding** back to the caller
  (`recall.py:157-164`);
- **the turn IS captured**, so the store grows — a miss is exactly what a *new* task looks
  like, and refusing to capture it would leave the store frozen at its first entry while
  appearing to work normally;
- the total embedding-call count for the whole turn is **exactly 1**, because capture
  reuses the retrieval vector (`recall.py:205-236`) rather than computing a second one.

**Explicitly:** a run in which misses are never captured **fails** this criterion, even
though every individual turn behaves correctly and no error is raised. Same
self-concealing class as trap A.

> **Live result:** the smoke run recorded a miss that still captured, 3 → 4 records.

---

## AC-7 — Bounds are enforced, and the RIGHT records survive — *REWRITTEN at v1.1.0*

Covers M1, M2. **This is the criterion that catches trap C** (`spec.md` §3.3) **and R14**
(`plan.md` §3.4). It is rewritten because the v1.0.x form asserted row counts, and **a
count-only assertion passes while the wrong records are evicted.**

### AC-7a — Oldest-first pruning, asserted by survivor identity

**Given** `CODERUNNER_MEMORY_MAX_RECORDS=10` and ten records inserted with **known,
distinct task texts**, in a **deliberately shuffled order** so that insertion order does
not coincide with any lexical or hash ordering

**When** an 11th distinct task succeeds

**Then**

- `get_collection_stats()["row_count"]` is 10;
- **and the surviving records are exactly the ten most recently inserted, identified by
  task text and `seq`** — the first-inserted record, and only that one, is gone.

**Explicitly:** asserting only `row_count == 10` **does not satisfy this criterion.** V5
proved `order_by="seq"` is accepted and silently ignored, returning insertion order
unsorted; an implementation that queries "the oldest N" and deletes them passes a
count-only assertion while evicting arbitrary records. The shuffled insertion order exists
solely so that a wrong implementation cannot pass by coincidence.

### AC-7b — Dedupe preserves the user-facing id and the creation time

**Given** a stored record whose `seq` is 4 and whose `created_at` is `T0`

**When** the identical task is submitted again and succeeds

**Then**

- the row count does not increase — `upsert()` replaced in place (V5a);
- **the record's `seq` is still 4**, so `/memory forget 4` continues to address the same
  record;
- **`created_at` is still `T0`** — the row's creation time is a fact about when it was
  first learned, not last seen;
- `task`, `thought`, `code`, `stdout` and `embedding` are updated to the new values.

**Explicitly:** `upsert()` overwrites every non-key field including `seq` (V5a's trace
returned `seq: 99` on the replaced row). An implementation that does not point-query the
existing row before upserting will silently reallocate the display id — the exact defect
the v1.0.x design rejected `INSERT OR REPLACE` to avoid — that code is now deleted along with the whole SQLite `MemoryStore`. **No
count-based assertion detects this.**

### AC-7c — Truncation at the tightened C11 limits

**Given** a task whose stdout is 50,000 characters

**When** the record is stored

**Then** the persisted `stdout` is exactly **1,000** characters.

Equivalent assertions: task **2,000**, thought **1,000**, code **4,000**.

**And** the stored embedding is bit-identical to the embedding of the untruncated task,
confirming C11's claim that **recall quality is unaffected — only the task text is
embedded, and `MAX_TASK_CHARS` did not change.**

### AC-7d — Convergence at the real cap

**Given** `CODERUNNER_MEMORY_MAX_RECORDS=100000` and a store already at the cap

**When** further records are inserted

**Then** the pruning loop converges on `get_collection_stats()["row_count"]`, tolerating
sequence gaps, and **never** issues a sorted query.

---

## AC-8 — Configuration robustness — *carries over; defaults updated*

Covers M5.

**Given** `CODERUNNER_MEMORY_TOP_K=abc`, `CODERUNNER_MEMORY_MIN_SIMILARITY=""`, and
`CODERUNNER_MEMORY_MAX_RECORDS=0`

**When** the module is imported

**Then**

- no `ValueError` escapes;
- each value falls back to its default or clamps to its documented minimum — `top_k` → 1,
  `min_similarity` → 0.65, `max_records` → 10;
- `/memory` reports the **effective** values, not the raw environment strings.

**Contrast to assert against:** `main.py:53-54` uses bare `int(os.environ.get(...))` and
crashes at import time (`main.py:67-68`), before the banner and before any Rich rendering (`tech.md` §4.2).

**And given** `CODERUNNER_MEMORY_MAX_RECORDS` unset

**Then** the effective cap is **100,000** (C9) — **not 50,000**.

**And** `DEFAULT_MAX_RECORDS <= MAX_RECORDS_RANGE[1]` holds as a standalone assertion.

**Explicitly:** the v1.0.x clamp ceiling was `(10, 50000)`; the constant now reads `(10, 200000)` at `memory.py:89`, **below** the
new default, and `env_int()` clamps *after* falling back (`memory.py:123-132`). Raising
`DEFAULT_MAX_RECORDS` without widening the range would silently halve the cap — the
documentation, the compose file and this SPEC would all say 100,000 while the running
system enforced 50,000, with no error and no warning. Asserting the relationship between
the two constants, rather than only the resulting value, is what stops them drifting apart
again later.

**And given** `CODERUNNER_EMBED_MODEL=""`

**Then** the default `nomic-embed-text:latest` is used — including the `:latest` suffix,
without which `grep -qx` in `have_model()` (`coderunner:174-177`) would never match and 274 MB would be
re-pulled on every launch (`docker-compose.yml:76-80`).

---

## AC-9 — User control — *carries over; `forget` resolution specified*

Covers M5.

**Given** a store with 3 records

**When** the user enters, in order: `/memory`, `/memory list 2`, `/memory forget <seq>`,
`/memory clear --yes`

**Then**

- each input is handled locally and **`agentic_turn()` is never invoked**;
- the record count progresses 3 → 3 → 2 → 0;
- `/memory` reports the store path, total count, eligible count, embedding model,
  dimension, and on-disk size.

**And** `/memory forget <seq>` resolves `seq == <n>` to a `task_hash` and deletes **by
primary key** (V5a), removing exactly the record the user saw in `/memory list`.

**And** `/memory list n` returns the *n* most recently inserted records in newest-first
order, derived from `next_seq` by range filter and sorted **in Python** — **not** by
`order_by`, which is a silent no-op (trap C).

**And** the reported on-disk size is the **recursive** total of the Milvus file set, not
the size of a single file. Under-reporting here would understate precisely the footprint
that `spec.md` §4.1 obliges the documentation to be honest about.

**And when** the user enters `/memory clear` **without** `--yes`

**Then** nothing is deleted and the required form is printed.

**And when** the user enters `/memory forget 99999` for a non-existent id

**Then** a not-found message is printed, nothing is deleted, and no exception is raised.

---

## AC-10 — The Milvus score is a cosine similarity, cross-checked against a pure-Python oracle — *NEW*

Covers M3, C10.

**Given** two known unit-normalised vectors whose cosine similarity is computable exactly
in pure Python via `dot()` (`memory.py:206-216`)

**When** one is stored and the other is used as a search query

**Then** the score returned by Milvus equals the pure-Python `dot()` result within a
float32 tolerance, and is **higher-is-better** across the full range.

**And** a pair with a known similarity of ~0.3 scores **below** a pair with a known
similarity of ~0.9 — establishing the direction of the metric, not merely its magnitude.

**Rationale:** every threshold comparison in the system is written as a lower bound
(`recall.py:161`, `search()`'s `>= min_sim`). A metric returning a **distance** would
invert all of them and silently turn the system into one that recalls the *least* similar
record — while still recalling something on every turn, and therefore still looking alive.
Retaining `dot()` and `l2_normalise()` in `memory.py` after the scan is gone exists for
exactly this test.

---

## AC-11 — Index and metric are pinned, not defaulted — *NEW*

Covers M1, C10.

**Given** a freshly created collection

**When** its index parameters are read back

**Then** `index_type` is exactly `"FLAT"` and `metric_type` is exactly `"COSINE"`, and both
were passed explicitly at creation.

**Explicitly:** relying on a library default fails this criterion even if the default
happens to match today. V4 §3 measured HNSW as **slower** than FLAT at 100k
(190 ms vs 133 ms median) and far worse at the tail at 200k (**1,742 ms** vs 291 ms p90),
so the correct choice here is counter-intuitive and a future library default is as likely
to move away from it as toward it.

---

## AC-12 — The eligibility filter survives the migration — *NEW*

Covers M3, R8.

**Given** a store containing one record written under a **different** `embed_model`, whose
raw vector is a **perfect** match for the query, and one record under the **current**
`embed_model` whose similarity is merely adequate

**When** retrieval runs

**Then** the stale record is **not** returned, and the adequate current record **is**.

**And** the `(embed_model, dim)` restriction is applied **as a scalar filter on the Milvus
search call**, not by post-filtering the result set.

**Explicitly:** post-filtering fails this criterion. With `top_k=1` (C7) the stale perfect
match would occupy the only result slot and be discarded afterwards, yielding a miss where
a hit was available — and the system would appear merely unlucky rather than wrong. This is
the failure `tests/test_memory_search.py:153` was written to catch under SQLite, and it
becomes **more** reachable under a backend that ranks before we can inspect.

---

## AC-13 — `order_by` appears nowhere in the codebase — *NEW*

Covers M1, trap C, R13.

**Given** the first-party source files

**When** they are scanned

**Then** the token `order_by` does not appear in any call to the Milvus client.

**And** the pruning site carries a comment recording that `order_by` is accepted and
silently ignored by Milvus Lite, and that the loop must not be "simplified" into a sorted
query.

**Rationale:** V5 proved the parameter is swallowed by the dynamic-kwargs path — it raises
nothing and returns insertion order unsorted. A source-level assertion is unusual, and it
is justified here because the failure it prevents is invisible at runtime: the wrong
records are deleted, the counts are right, and nothing is logged. The comment is part of
the criterion because the next reader, seeing a loop where a one-line sorted query would
"obviously" do, will otherwise reintroduce the bug.

---

## AC-14 — The storage seam holds — *NEW*

Covers C12/D5.

**Given** the first-party source files

**When** their imports are analysed by AST

**Then**

- `memory.py` imports **stdlib only** — the existing assertion at
  `tests/test_memory_primitives.py:25-48` survives **verbatim**;
- `recall.py` imports `ollama` but **not** `pymilvus`;
- `vectorstore.py` is the **only** first-party module importing `pymilvus`;
- **no first-party module imports `numpy`** — it is accepted as a transitive dependency of
  `pymilvus[milvus_lite]`, not adopted (out-of-scope item 7).

**Rationale:** the seam is what preserves the bare-interpreter test suite. Once `pymilvus`
leaks into `memory.py`, every primitive test acquires a 352 MB dependency and the
stdlib-only guarantee is gone for good — a boundary far easier to keep than to restore.

---

## Success criteria and quality gates

### Coverage

| Target | Gate | Current |
|---|---|---|
| `memory.py` | **100%** — must not regress | 100% |
| `recall.py` | **100%** — must not regress | 100% |
| `vectorstore.py` | **≥ 85%** | new |

`vectorstore.py` requires `milvus_lite` in the dev environment;
`requirements-dev.txt` gains `pymilvus[milvus_lite]` so the gate is unconditional. The
`importorskip` guard is a safety net for platforms without a wheel, **not** a licence to
skip the gate in CI.

**Pre-existing `main.py` and `tools.py` coverage remains explicitly out of scope**
(`spec.md` §6 item 9). `structure.md` §6 records that the product had zero tests before
this SPEC; applying a repository-wide gate would fail for reasons unrelated to this work.

### Test-suite preservation

The migration **must not reduce the passing test count** below its current 243 other than
by tests whose subject was deleted. `plan.md` §6.2 catalogues the ~15 SQLite-internal tests
that must be rewritten; everything else carries over, most of it through the single
`tmp_store` fixture at `conftest.py:146-160`.

### Testability constraints

- **`memory.py` tests run with `pytest` alone** — no `rich`, no `ollama`, no `pymilvus`,
  no `numpy`, no Docker, no network.
- **`recall.py` tests run without a live Ollama and without a live Milvus**, using a fake
  client and a fake store.
- **`vectorstore.py` tests run against a real embedded Milvus Lite on `tmp_path`** — it is
  embedded, so this needs no service.
- No test may require a live terminal or a live model.

### Verification status

| # | Subject | Status |
|---|---|---|
| V1 | Named-volume ownership | **CONFIRMED** — fix landed |
| V2 | `ollama>=0.3.0` subscript access | **CONFIRMED** — subscript is the only portable form |
| V3 | Embed latency; threshold | **CONFIRMED** — R1 closed; C5 → 0.65 |
| V4 | Milvus feasibility, latency, index, disk | **CONFIRMED** — D1–D5 taken |
| **V5a** | Dedupe by `task_hash` | **CONFIRMED** — VARCHAR PK + `upsert()` |
| **V5b** | Delete-by-filter and pruning order | **CONFIRMED** — two silent traps; converging loop mandated |
| V5c | Cold-open latency of a 100k collection | **NOT MEASURED — non-blocking.** Measure in T16′ |
| V5d | Concurrency | **NOT MEASURED — non-blocking.** Gates AC-3g |
| V5e | `row_count` write-visibility | **NOT MEASURED — non-blocking.** Verify in T-VS2 |

### Definition of done

- [ ] AC-1 through AC-6b and AC-9 still pass — **no behavioural regression from v1.0.2**
- [ ] **AC-7a asserts survivor identity from shuffled insertion order**, not row count
- [ ] **AC-7b proves `seq` and `created_at` survive a dedupe upsert**
- [ ] AC-7c asserts the tightened C11 limits and that the embedding is unaffected
- [ ] AC-10 cross-checks the Milvus COSINE score against the pure-Python `dot()` oracle
- [ ] AC-11 reads back `FLAT` / `COSINE` as explicitly pinned
- [ ] AC-12 proves the eligibility filter is applied **by the search**, not after it
- [ ] AC-13 proves `order_by` is absent, and the pruning comment is present
- [ ] AC-14 proves the seam holds and no first-party module imports numpy
- [ ] `memory.py` and `recall.py` still at 100%; `vectorstore.py` ≥ 85%
- [ ] V5e checked during T-VS2; V5c and V5d measured during T16′
- [ ] T16′ smoke run passes against a rebuilt image, including AC-2 on the Seoul→Busan pair
- [ ] **T15′ documentation complete — including the amended "zero residue on the host"
      claims at `README.md:15` and `product.md` §2.3, stating the ≈0.9 GB typical /
      ≈1.4 GB worst-case volume and the image growth of 273 MB → 754 MB (+481 MB,
      roughly 2.8×)** (`spec.md` §4.1). *Measured after the build 2026-08-04; this line
      previously said "≈352 MB image growth", which was V4 §1's site-packages figure with
      an image inference on top. Do not revert it.* This is the single most user-visible
      consequence of the change and must not be soft-pedalled
- [ ] `tech.md` §2, §7.2 and §8.5 updated for the new dependency, the enlarged persistent
      surface (R6) and the reproducibility impact
- [ ] The incidental `CODERUNNER_HISTORY` line at `docker-compose.yml:97-100` still carries
      its revert comment and remains independently revertible
- [ ] `memory.py`, `recall.py` and `vectorstore.py` are **not** copied into the sandbox —
      `run_python()` still copies only `TOOLS_MODULE`
