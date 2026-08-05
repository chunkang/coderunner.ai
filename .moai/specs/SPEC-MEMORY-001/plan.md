# SPEC-MEMORY-001 — Implementation Plan (v1.1.0)

> Requirements are in `spec.md`. Verification is in `acceptance.md`.
> Benchmarks: `.moai/docs/SPEC-MEMORY-001-V4-milvus-benchmark.md` (**V4**).
> Upsert/pruning semantics: `.moai/docs/SPEC-MEMORY-001-V5-milvus-semantics.md` (**V5**).
> `file:line` citations in this document refer to the **pre-migration working tree**
> (2026-08-03), in which the v1.0.2 SQLite implementation is complete and passing. **They
> are deliberately not updated to the post-migration tree**, because the whole purpose of
> §0.1 and §6.2 is to say what that tree contained and what became of it. Several therefore
> name code that no longer exists — `memory.py` was 843 lines and is now 567, and every
> `memory.py:` citation above line 568 points into the deleted `MemoryStore`. Live
> citations to the shipped implementation live in `spec.md` §5 and `acceptance.md`, and
> those **were** re-verified against the current tree on 2026-08-04.

---

## 0. Starting position — this is a substitution, not a rewrite

**243 tests pass, 100% coverage on both gated modules, and the live smoke run passed**
AC-1, AC-2 (similarity 0.76), AC-3, AC-4, AC-5, AC-6b and AC-9. The plan below preserves
that work wherever the storage change does not invalidate it.

Two properties of the existing code make the substitution cheap, and both were deliberate:

1. **The store is already reached through a narrow, duck-typed interface.** Across
   `recall.py` and `memory.py`'s command handler, exactly eight operations are used:
   `open`, `count`, `insert`, `recent`, `delete`, `clear`, `stats`, `close` — plus the free
   function `search()`. Nothing outside `memory.py` touches `sqlite3`.
2. **Every store-dependent test goes through one fixture**, `tmp_store` at
   `conftest.py:102-112`. Repointing that fixture at the new backend repoints the whole
   suite. The tests assert *behaviour* — counts, dedupe, prune, ordering, degradation —
   not SQLite internals, with the ~15 exceptions catalogued in §6.2.

### 0.1 What survives, what is replaced

`memory.py` is 843 lines. Under **C12/D5** it stays stdlib-only and keeps its role; only
the storage class inside it moves out.

| Region | Lines | Fate |
|---|---:|---|
| Header, constants, env helpers, vector maths, hashing, `MemoryConfig`, `SolutionRecord` (`memory.py:1-284`) | ~284 | **SURVIVES.** Only the four truncation constants change value (C11). |
| Schema SQL + `MemoryStore` (`memory.py:291-573`) | ~283 | **REPLACED** by `vectorstore.py`. |
| `Hit` (`memory.py:581-587`) | ~7 | **SURVIVES** — a pure dataclass. |
| `search()` (`memory.py:589-618`) | ~30 | **REPLACED** — becomes a method on the new store. |
| Recall block formatting + `inject_recall()` (`memory.py:621-683`) | ~63 | **SURVIVES verbatim.** |
| `handle_memory_command()` family (`memory.py:685-824`) | ~140 | **SURVIVES** — talks to the store through the eight-method interface. |
| `_row_to_record()` (`memory.py:826-843`) | ~18 | **REPLACED** — decodes a SQLite row tuple. |

**Roughly 500 of 843 lines survive unchanged; roughly 330 are replaced.**

`recall.py` (269 lines) survives **almost entirely**. Its only required change is the
`search(...)` call site at `recall.py:144-151`. In particular `embed_text()`
(`recall.py:42-78`), `Recall` (`recall.py:92-107`), `recall_for_task()`'s ordering and
short-circuit (`recall.py:110-168`), `retrieval_degraded()` (`recall.py:171-201`),
`vector_for_capture()` (`recall.py:204-235`) and `remember_success()` (`recall.py:238-269`)
are **unchanged** — they are the M2/M3/M5 behaviours that the smoke run validated.

`main.py` (684 lines) needs **no logic change at all** beyond the import at `main.py:46-51`
and the truncation/cap figures reported by `/memory`. `_open_memory_store()`
(`main.py:366-380`), the warning suppression (`main.py:388-424`), the injection
(`main.py:463-468`) and the capture call (`main.py:522`) all operate on the interface, not
the backend.

---

## 1. Module layout under C12/D5

| File | Third-party imports | Status |
|---|---|---|
| `memory.py` | **none — stdlib only** | Existing. Loses the SQLite store; keeps everything else. |
| `recall.py` | `ollama` (type reference only) | Existing. One call site changes. |
| **`vectorstore.py`** | **`pymilvus` — and nothing else may import it** | **NEW.** The single seam holding every Milvus call. |
| `tests/`, `conftest.py`, `pytest.ini`, `requirements-dev.txt` | `pytest`, `pytest-cov`, `pymilvus[milvus_lite]` | Existing; extended. |

### 1.1 Why a third module rather than swapping the internals of `memory.py`

D5 requires a stdlib-only core so the bare-interpreter tests survive. Importing `pymilvus`
anywhere in `memory.py` would drag numpy and a 352 MB dependency tree into every primitive
test and **break the stdlib-only AST assertion at `tests/test_memory_primitives.py:25-48`**
— a test that exists precisely to keep that boundary honest.

`vectorstore.py` mirrors what `recall.py` already does for `ollama`: one thin module, one
foreign dependency, faked at the seam everywhere else.

### 1.2 The stdlib-only test is re-scoped, not deleted *(D5)*

`tests/test_memory_primitives.py:25-48` walks `memory.py`'s AST and asserts every imported
root is in `sys.stdlib_module_names`. **It survives verbatim** — `memory.py` stays
stdlib-only.

Add a **companion** assertion enforcing the other half of the seam:

- `recall.py` **must not** import `pymilvus`;
- `vectorstore.py` is the **only** first-party module that may;
- **no first-party module may import `numpy`** — it is accepted as a transitive
  dependency, not adopted (out-of-scope item 7).

### 1.3 What must *not* change

`run_python()` copies **only** `TOOLS_MODULE` into each sandbox. `memory.py`, `recall.py`
and now `vectorstore.py` must **not** be added to that copy. No change is required — just
do not add one. See risk R6.

---

## 2. Collection design

Settled by **V5a/V5b**. Do not deviate without re-running those verifications.

```
collection "solutions"
  task_hash    VARCHAR   PRIMARY KEY     <- dedupe is STRUCTURAL; upsert() replaces in place
  seq          INT64                     <- monotonic; user-facing id AND pruning order
  embedding    FLOAT_VECTOR(dim)         <- index FLAT, metric COSINE, both PINNED (C10)
  task         VARCHAR   <= 2000         (C11)
  thought      VARCHAR   <= 1000         (C11, was 4000)
  code         VARCHAR   <= 4000         (C11, was 8000)
  stdout       VARCHAR   <= 1000         (C11, was 4000)
  chat_model   VARCHAR
  embed_model  VARCHAR                   <- half the eligibility filter
  dim          INT64                     <- other half of the eligibility filter
  created_at   VARCHAR                   <- ISO-8601 UTC

collection "meta"                        <- side collection; NOT derivable from "solutions"
  schema_version, next_seq, min_seq, embed_model, dim
```

**Index and metric are pinned explicitly.** `FLAT` measured *faster* than HNSW at 100k
(133 ms vs 190 ms median) and far better at the tail at 200k (291 ms vs **1,742 ms** p90).
HNSW's only edge is disk at 200k, which does not apply at the 100k cap (V4 §3).

**`meta` must be persisted, not derived.** `next_seq` and `min_seq` cannot be recovered
from the main collection because it cannot be enumerated — see §3.2.

### 2.1 Truncation constants (C11)

Change the four values at `memory.py:38-41`; everything else about truncation, including
`_truncate()` at `memory.py:213-214` and its tests, is unaffected.

| Constant | v1.0.x | v1.1.0 |
|---|---:|---:|
| `MAX_TASK_CHARS` | 2000 | **2000** (unchanged) |
| `MAX_THOUGHT_CHARS` | 4000 | **1000** |
| `MAX_CODE_CHARS` | 8000 | **4000** |
| `MAX_STDOUT_CHARS` | 4000 | **1000** |

≈8 KB per record. **Recall quality is unaffected: only the task text is embedded** (V4 D4),
and `MAX_TASK_CHARS` is unchanged — so no stored vector differs by one bit because of this.

### 2.2 Configuration constants

Read once at import, per the convention at `main.py:51-58` / `tech.md` §4. Environment
variable **names are unchanged** — `docker-compose.yml:74-84` needs only the one default
edit in T-VS13.

| Constant (`memory.py`) | Env var | v1.0.x | **v1.1.0** | Clamp range |
|---|---|---:|---:|---|
| `DEFAULT_EMBED_MODEL` | `CODERUNNER_EMBED_MODEL` | `nomic-embed-text:latest` | unchanged | non-empty |
| `DEFAULT_TOP_K` (`memory.py:46`) | `CODERUNNER_MEMORY_TOP_K` | 1 | unchanged | `(1, 5)` |
| `DEFAULT_MIN_SIMILARITY` (`memory.py:47`) | `CODERUNNER_MEMORY_MIN_SIMILARITY` | 0.65 | unchanged *(C5)* | `(0.0, 1.0)` |
| `DEFAULT_MAX_RECORDS` (`memory.py:48`) | `CODERUNNER_MEMORY_MAX_RECORDS` | 500 | **100,000** *(C9)* | **`(10, 200000)`** |
| `MAX_TASK_CHARS` (`memory.py:38`) | — | 2000 | unchanged | — |
| `MAX_THOUGHT_CHARS` (`memory.py:39`) | — | 4000 | **1000** *(C11)* | — |
| `MAX_CODE_CHARS` (`memory.py:40`) | — | 8000 | **4000** *(C11)* | — |
| `MAX_STDOUT_CHARS` (`memory.py:41`) | — | 4000 | **1000** *(C11)* | — |

**`MAX_RECORDS_RANGE` must be widened before `DEFAULT_MAX_RECORDS` is raised.** Its v1.0.x
ceiling is `(10, 50000)` at `memory.py:53` — **below the new 100,000 default**. Because
`env_int()` clamps *after* falling back (`memory.py:91-101`), leaving the ceiling alone
would silently clamp the new default down to 50,000: the cap would be half what the SPEC,
the compose file and the documentation all say, with no error and no warning. The two
constants must move together, and a test should assert
`DEFAULT_MAX_RECORDS <= MAX_RECORDS_RANGE[1]` so the pairing cannot drift again.

The new ceiling is set at 200,000 rather than exactly 100,000 so an operator can raise the
cap without editing source — V4 §3 measured 200k as viable (260 ms median, 291 ms p90 with
FLAT), just disk-expensive at 1,233 MB.

---

## 3. The two silent traps, and the code that must exist because of them

### 3.1 `order_by` is accepted and ignored *(trap C)*

```
inserted in order          : [50, 10, 90, 30, 70, 20, 80, 40, 60, 0]
query limit=5, order_by=seq: [50, 10, 90, 30, 70]   ← insertion order. NOT SORTED. No error.
```

The natural pruning implementation — "query the oldest N, delete them" — therefore deletes
**arbitrary** records, passes `count == cap`, and destroys the user's most valuable
memories while `/memory` reports exactly the right number.

**Required:** `order_by` appears nowhere in the codebase, and the pruning site carries a
comment saying why. Enforced by **AC-13** (a source-level assertion) and by **AC-7**, which
asserts *which* records survived.

### 3.2 The collection cannot be enumerated *(trap D)*

`query()` is hard-capped at **16,384** rows; `query_iterator` returned 3 of 10 rows and
stopped. So "read all seqs and compute the oldest N" is unavailable, and worse, it *appears
to work* below 16,384 rows — a bug that ships green and surfaces only on a large store.

`get_collection_stats()["row_count"]` is accurate, cheap and uncapped. It is the only
trustworthy count signal.

### 3.3 The pruning algorithm

The only sound design (V5):

```
prune(cap):
    # order_by is a silent no-op in Milvus Lite (V5b) and query() is capped at 16,384
    # rows, so the oldest records CANNOT be selected by reading them. This loop converges
    # on row_count instead. Do not "simplify" it into a sorted query.
    while get_collection_stats()["row_count"] > cap:
        delete(filter=f"seq < {min_seq + batch}")
        min_seq += batch            # persist to meta
        # gaps are harmless: convergence is on row_count, not arithmetic
```

`delete(filter=...)` is correct and fast — **0.26 s per 1,000 rows at the 100k cap** — and
returns the deleted primary keys.

### 3.4 The upsert path, and where the id-stability hazard moved

`upsert()` overwrites **every** non-key field, `seq` included. V5a's own trace shows the
replaced row returning `{'task_hash': 'h2', 'seq': 99, ...}` — whatever `seq` the caller
supplied.

Making `task_hash` the primary key removes the *engine-level* reallocation hazard that
`ON CONFLICT … DO UPDATE` was chosen to avoid (`memory.py:320-324`). It does **not** remove
the hazard outright: `seq` is now the surrogate id, and our code will clobber it unless it
reads first.

```
insert_or_update(record):
    existing = point_query_by_primary_key(record.task_hash)   # PK lookup, not capped
    if existing:
        seq        = existing.seq          # carry forward — /memory forget <id> stability
        created_at = existing.created_at   # first learned, not last seen
    else:
        seq        = next_seq;  next_seq += 1     # persist to meta
        created_at = utc_now_iso()
    upsert(...)
```

Getting this wrong reproduces exactly the v1.0.x defect the original design went out of its
way to avoid, and **no count-based test will notice**. Covered by **AC-7**.

---

## 4. `vectorstore.py` public surface

Deliberately the same shape the callers already use, so `recall.py` and
`handle_memory_command()` need no restructuring.

```
class VectorStore:
    open(path, dim=None)  -> VectorStore | None     # None on ANY failure (M5)
    close()               -> None
    count()               -> int                    # get_collection_stats()["row_count"]
    insert(record, max_records) -> bool             # truncate + read-back + upsert + prune
    search(query_vec, top_k, min_sim, embed_model, dim) -> list[Hit]
    recent(limit)         -> list[SolutionRecord]
    delete(seq)           -> bool                   # resolve seq -> task_hash, delete by PK
    clear()               -> int
    stats(embed_model=None, dim=None) -> dict
    meta_get(key)         -> str | None
```

`Hit` and `SolutionRecord` are imported from `memory.py` — the record model does not move.

Every method degrades rather than raising, exactly as `MemoryStore` did
(`memory.py:341-348`). That contract is what makes M5 hold, and it is unchanged.

### 4.1 Two details that differ from SQLite and are easy to miss

- **`stats()["bytes"]`.** The SQLite version (`memory.py:569-572` in the pre-migration
  tree) called `self.path.stat().st_size` on a single file. Milvus Lite writes a **file
  set**; the size must be summed recursively or `/memory` will under-report the footprint
  by orders of magnitude — precisely the number §4.1 of `spec.md` obliges us to be honest
  about. Shipped as `_disk_bytes()` using `rglob("*")`.
- **`recent(limit)`.** `memory.py:521-533` used `ORDER BY id DESC LIMIT ?`. `order_by` is a
  no-op (trap C), so `recent()` must derive its window from `next_seq` and use a
  **range filter** (`seq >= next_seq - k`), then sort the returned rows **in Python**. This
  is a small function with a large opportunity to reintroduce trap C.

### 4.2 The retrieval call site in `recall.py`

One change, at `recall.py:144-151`:

```python
candidates = store.search(query_vector, cfg.top_k, _RANK_ALL, cfg.embed_model, len(query_vector))
```

`_RANK_ALL = -1.0` (`recall.py:89`) is retained and still matters: candidates are ranked
**without** the threshold so a miss can report how close the best candidate came, and the
threshold is applied once at `recall.py:161`. That structure is what AC-6b depends on.

The `(embed_model, dim)` eligibility filter becomes a Milvus **scalar filter on the search
call**, not a post-filter. Post-filtering would let a stale vector with a higher raw score
displace a current one before the filter runs — the exact failure
`tests/test_memory_search.py:153` was written to catch.

---

## 5. Task decomposition

### 5.1 Verifications

| # | Verification | Status | Blocks |
|---|---|---|---|
| **V1** | Docker propagates image-directory ownership into an empty named volume. | **CONFIRMED** (2026-08-02) | — (fix landed, `Dockerfile:28-38`) |
| **V2** | `resp["embeddings"][0]` works at the `ollama>=0.3.0` floor. | **CONFIRMED** — and subscript is the *only* portable form | — (landed, `recall.py:42-78`) |
| **V3** | Cold/warm embed latency; threshold sanity. | **CONFIRMED** — R1 closed; C5 revised to 0.65 | — |
| **V4** | Milvus Lite feasibility, latency, index choice, disk. | **CONFIRMED** — D1–D5 taken | — |
| **V5a** | Dedupe-by-`task_hash` semantics. | **CONFIRMED** — `task_hash` as VARCHAR PK; `upsert()` replaces in place | **discharged** |
| **V5b** | Delete-by-filter and oldest-first pruning. | **CONFIRMED** — two silent traps; converging delete-by-filter loop is the only sound design | **discharged** |
| **V5c** | **Cold-open latency of an existing 100k collection from a fresh container.** All V4 figures are same-process; this is the real startup path, and it runs inside `_open_memory_store()` (`main.py:366-380`) before the banner. | **NOT MEASURED** | **Non-blocking.** Measure during T16′; if it is slow, the mitigation is deferred/lazy open, which does not change the schema. |
| **V5d** | **Concurrency.** The SQLite design used WAL + `busy_timeout=3000` (`memory.py:55-57`). The Milvus Lite equivalent and its contention behaviour are unknown. | **NOT MEASURED** | **Non-blocking.** `container_name: coderunner` (`docker-compose.yml:56`) makes a second concurrent session awkward to start, and any failure lands in the M5 degradation path. |
| **V5e** | **Write-visibility of `get_collection_stats()["row_count"]`.** *Author-added.* Is a count taken immediately after an upsert consistent? Three behaviours depend on it — see below. | **NOT MEASURED** | **Non-blocking**, but verify early in T-VS. |

**Why V5e exists.** `store.count()` is called up to three times per turn:
`recall.py:135` (cold-start short-circuit), `recall.py:201` (`retrieval_degraded`) and
`recall.py:233` (`vector_for_capture`). Under SQLite an insert was visible to the next
count unconditionally. V5 establishes that `get_collection_stats()` is accurate, cheap and
uncapped, but says nothing about staleness immediately after a write. If a post-write count
is stale, **AC-1** (zero-embed cold start), **AC-6b** (capture on miss) and **M5's
one-status-line invariant** all break silently. Cheap to check; protects three criteria
that already pass.

### 5.2 Implementation tasks

Numbering continues from the v1.0.x tasks, which are complete. `T-VS*` are new.

| # | Task | File · insertion point | Depends on |
|---|---|---|---|
| **T-VS0** | `requirements.txt`: add `pymilvus[milvus_lite]>=3.0.1`. **The `[milvus_lite]` extra is not optional** — bare `pymilvus` raises `ConnectionConfigException` at `MilvusClient("<path>")` (V4 §1). Add `pymilvus[milvus_lite]` to `requirements-dev.txt` too, so the host test run has it. | `requirements.txt:7`, `requirements-dev.txt` | — |
| **T-VS1** | `vectorstore.py`: module skeleton, `open()`/`close()`, collection creation with **`index_type="FLAT"`, `metric_type="COSINE"` pinned**, `meta` side-collection, `schema_version`. All failures return `None`. | `vectorstore.py` (new) | T-VS0 |
| **T-VS2** | `vectorstore.py`: `count()` via `get_collection_stats()["row_count"]`. **Run V5e here.** | `vectorstore.py` | T-VS1 |
| **T-VS3** | `vectorstore.py`: `insert()` — truncate, **point-query by PK for existing `seq`/`created_at`**, allocate `seq` from persisted `next_seq` when new, `upsert()`, then prune. See §3.4. | `vectorstore.py` | T-VS2 |
| **T-VS4** | `vectorstore.py`: `_prune()` — the converging delete-by-filter loop of §3.3, **with the `order_by` warning comment**. Persist `min_seq`. | `vectorstore.py` | T-VS3 |
| **T-VS5** | `vectorstore.py`: `search()` with the `(embed_model, dim)` **scalar filter on the search call**; map results to `Hit`. Confirm the COSINE score is a similarity, not a distance. | `vectorstore.py` | T-VS1 |
| **T-VS6** | `vectorstore.py`: `recent()` (range filter + Python sort, **never `order_by`**), `delete(seq)` (resolve → PK), `clear()`, `stats()` with **recursive** size summation (§4.1), `meta_get()`. | `vectorstore.py` | T-VS3 |
| **T-VS7** | `memory.py`: delete `MemoryStore`, the schema SQL, `search()`, `_row_to_record()`, `pack_vector`/`unpack_vector` and the `sqlite3` import. Update the four truncation constants (§2.1) and `DEFAULT_MAX_RECORDS` → 100,000, `MAX_RECORDS_RANGE` → `(10, 200000)`. **Keep** `dot()` and `l2_normalise()` — they become the pure-Python oracle for AC-10. | `memory.py:38-41`, `:48`, `:53`, `:291-618`, `:826-843` | T-VS6 |
| **T-VS8** | `recall.py`: change the one `search(...)` call site to `store.search(...)`. **Nothing else in this file changes.** | `recall.py:144-151` | T-VS5, T-VS7 |
| **T-VS9** | `main.py`: update the import at `main.py:46-51`; open a `VectorStore` in `_open_memory_store()` (`main.py:366-380`). No logic change. | `main.py:46-51`, `:366-380` | T-VS7 |
| **T-VS10** | `conftest.py`: repoint the `tmp_store` fixture (`conftest.py:102-112`) at `VectorStore`. **This single change repoints every store-dependent test.** Add an `importorskip` guard for `milvus_lite`. | `conftest.py:97-112` | T-VS6 |
| **T-VS11** | Tests: re-target `tests/test_memory_store.py` → `tests/test_vectorstore.py`; rewrite the ~15 SQLite-internal tests catalogued in §6.2; re-target `tests/test_memory_search.py`. Add the seam-enforcement test of §1.2 and the new criteria AC-10..AC-14. | `tests/` | T-VS10 |
| **T-VS12** | `Dockerfile`: no structural change needed — `COPY` already lists the modules by name at `Dockerfile:26`; add `vectorstore.py`. The trap-A fix at `Dockerfile:28-38` **stays exactly as it is**. | `Dockerfile:26` | T-VS9 |
| **T-VS13** | `docker-compose.yml`: update `CODERUNNER_MEMORY_MAX_RECORDS` default 500 → 100000 (`docker-compose.yml:84`). The volume (`:67-68`), the memory env block (`:74-84`) and the incidental `CODERUNNER_HISTORY` line (`:85-88`) are **unchanged**. | `docker-compose.yml:84` | T-VS12 |
| **T15′** | **Documentation — materially enlarged.** Beyond the v1.0.x obligation, the amendment to `README.md:15` and `product.md` §2.3 must now state the **≈0.9 GB typical / ≈1.4 GB worst-case volume** and the image growth of **273 MB → 754 MB (+481 MB, roughly 2.8×)** — *measured after the build 2026-08-04; **not** the "~352 MB / roughly doubles" figure this row previously carried, which was an inference from V4 §1's site-packages measurement* (`spec.md` §4.1). Update `tech.md` §2 (new dependency), §7.2 (persistent surface, R6) and §8.5 (reproducibility — a new floating dependency). | `README.md`, `/moai:3-sync` | T-VS13 |
| **T16′** | Re-run the full smoke sequence against a rebuilt image: cold start → capture → restart → reuse → `/memory clear --yes`, plus the AC-3 matrix. **Measure V5c and V5d here.** Confirm AC-2 still fires on the Seoul→Busan pair. | manual | T15′ |

---

## 6. Test impact

### 6.1 Current state

| File | Test functions | Fate |
|---|---:|---|
| `tests/test_memory_primitives.py` | 34 | **Survives**, minus the `pack_vector`/`unpack_vector` cases. The stdlib-only AST test at `:25-48` survives **verbatim**. |
| `tests/test_memory_search.py` | 24 | **Re-targeted.** Behavioural assertions survive; the float32 boundary case at `:93-106` needs rework since it uses `pack_vector`/`unpack_vector`. The stale-vector-must-lose case at `:153` becomes **more** important, not less. |
| `tests/test_memory_store.py` | 40 | **Re-targeted** to `test_vectorstore.py`. ~15 rewritten — see §6.2. |
| `tests/test_memory_command.py` | 22 | **Survives** — goes through the `tmp_store` fixture and the eight-method interface. |
| `tests/test_recall.py` | 46 | **Survives** — no `MemoryStore` construction anywhere in the file. |
| `tests/test_main_integration.py` | 32 | **Survives.** |

Total 243 tests (parameterisation included). The great majority carry over.

### 6.2 The SQLite-coupled tests that must be rewritten

Found by inspection; these assert engine internals rather than behaviour:

| Location | Assertion | Replacement |
|---|---|---|
| `test_memory_store.py:79-80` | `meta_get("schema_version")` | Same, against the `meta` side-collection |
| `:83-91` | `PRAGMA journal_mode` = WAL; `PRAGMA busy_timeout` = 3000 | **Delete** until V5d says what the Milvus equivalent is |
| `:94-120` | `PRAGMA table_info(solutions)` column types | Milvus collection schema description |
| `:145-153`, `:158`, `:173-178` | `sqlite3.OperationalError` / `DatabaseError` injection for AC-3d/e/f | Milvus equivalents; **the AC-3 outcomes do not change** |
| `:268` | `INSERT OR REPLACE` reallocates AUTOINCREMENT id | **Becomes the `seq`-carry-forward test of §3.4** — same defect, new location |
| `:379-380` | `UPDATE ... SET embedding=?` to corrupt a BLOB | Corrupt-vector handling at the new layer |
| `:471-476` | Second connection holds `BEGIN EXCLUSIVE` past `busy_timeout` (AC-3g) | Deferred to V5d |
| `:509`, `:519-528` | Raising-connection fakes | Raising-client fakes |

### 6.3 Coverage gates

| Target | Gate |
|---|---|
| `memory.py` | **100%** — currently achieved; must not regress |
| `recall.py` | **100%** — currently achieved; must not regress |
| `vectorstore.py` | **≥ 85%** |

`vectorstore.py` requires `milvus_lite` in the dev environment. T-VS0 adds it to
`requirements-dev.txt` so the gate is unconditional; the `importorskip` guard in T-VS10 is
a safety net for platforms without a wheel, **not** a licence to skip the gate in CI.

---

## 7. Performance — superseded benchmarks

**The 20,000-record revisit trigger from v1.0.x is obsolete.** It said "if the cap ever
exceeds 20,000, re-evaluate numpy or an ANN index". V4 answered that question directly and
the trigger is void.

Search latency, measured in-image (V4 §2, §3):

| Records | Milvus Lite (FLAT) | Pure Python (v1.0.x) | Ratio |
|---:|---:|---:|---|
| 500 | **0.78 ms** | 13 ms | 17× |
| 5,000 | **27.3 ms** | 138 ms | 5× |
| 20,000 | **77.7 ms** | 445 ms | 6× |
| 50,000 | **238 ms** | ~1,100 ms | 5× |
| **100,000 (the cap)** | **133 ms median, 169 ms p90** | — | — |

Milvus Lite wins at **every** scale, including the original 500-record cap. The v1.0.x
claim that an index would be "pure overhead" was inherited from a benchmark of pure Python
against itself and was never tested against Milvus (V4 §2, "Correction to an earlier
claim").

`dot()` and `l2_normalise()` are **retained in `memory.py`** despite the scan being gone —
they become the pure-Python oracle that AC-10 uses to prove Milvus's COSINE score really is
a cosine similarity. That is a better use for them than deletion, and it preserves their
existing tests.

---

## 8. Risks and trade-offs

R1–R3, R6, R8–R10 carry over. R4, R5, R7, R11 are revised. R13–R17 are new.

| # | Risk | Assessment | Mitigation |
|---|---|---|---|
| **R1** | Embedding latency per turn. | **Closed by V3.** Cold 906 ms, warm median 40 ms. | Empty-store short-circuit (cold start pays zero); `keep_alive="10m"`; exactly one embed per turn. |
| **R2** | 274 MB embedding-model download. | One-time, into the existing `coderunner_ollama_data` volume. | Skipped when `CODERUNNER_MEMORY=0`, enforced at launcher level. |
| **R3** | **False-positive retrieval poisons the prompt.** | Still the sharpest *behavioural* risk. Unchanged by the storage swap. | Threshold 0.65 (C5, measured); `top_k=1` (C7); adapt-or-ignore framing (`memory.py:352-355`); attempt-1-only injection (C8); `/memory forget <id>`. Smoke run confirmed the model **adapted** rather than replayed. |
| **R4** | ~~Unbounded growth (cap 500, ≈8.5 MB).~~ **REVISED:** the cap is now 100,000 and the volume approaches **1 GB**. | Bounded but large. This is a real change to the product's footprint, not a rounding error. | C11 truncation (≈8 KB/record); converging prune loop; `/memory clear --yes`; `docker volume rm coderunner_app_data`. **T15′ must state the figures.** |
| **R5** | ~~Pure-Python vs numpy.~~ **CLOSED.** Superseded by V4; C6 overturned. | — | — |
| **R6** | **New persistent surface reachable by generated code.** Model-written scripts run as `runner` and can read, poison or delete the store. | Not a privilege escalation — generated code can already overwrite `/app/main.py` (`tech.md` §7.2). New in *persistence*. **Now larger:** ~1 GB of the user's task history rather than ~8.5 MB. | Blast radius bounded by C2 — stored content is only ever *shown* to the model, never executed. Record in `tech.md` §7.2 (T15′). |
| **R7** | **Silent permanent degradation** — trap A. | **Closed by V1 + AC-5**, which passed live showing `1000:1000`. | Do not regress `Dockerfile:28-38`. |
| **R8** | Embedding-model change invalidates stored vectors. | Certain if `CODERUNNER_EMBED_MODEL` changes. | The `(embed_model, dim)` filter — now a **Milvus scalar filter on the search call** (M3). Mismatched rows become inert, not wrong. Preserving this is mandatory; **AC-12**. |
| **R9** | `--doctor` gets slower. | Pre-existing wart (`product.md` §6.4), now also pulls 274 MB. | Out of scope. |
| **R10** | **Privacy.** Task history persists unencrypted on a host volume. | **Materially larger at v1.1.0** — approaching 1 GB. | `/memory list`, `/memory clear --yes`, `CODERUNNER_MEMORY=0`, `docker volume rm`. Documented in T15′. |
| **R11** | ~~SQLite concurrency (WAL + busy_timeout).~~ **REVISED: unknown under Milvus Lite.** | **V5d, non-blocking.** Milvus Lite may hold an exclusive lock and *error* rather than wait. | `container_name: coderunner` makes concurrent sessions awkward; any failure lands in the M5 degradation path, so the worst case is a warning and a working session. Measure in T16′. |
| **R13** | **`order_by` silently ignored** *(trap C, NEW)*. Pruning selects arbitrary records, passes a count assertion, and evicts the user's best memories. | **Highest-probability implementation bug in this revision**, and self-concealing. | Prohibition in M1; comment mandated at the pruning site; **AC-7 asserts survivor identity**; **AC-13** asserts `order_by` is absent from the source. |
| **R14** | **`seq` clobbered on upsert** *(NEW)*. `/memory forget 4` starts addressing a different record after a re-ask. | The v1.0.x defect, relocated from engine to application (§3.4). No count-based test catches it. | Point-query by PK before upsert; carry `seq` and `created_at` forward; **AC-7**. |
| **R15** | ~~Image roughly doubles — 352 MB of site-packages on a ~273 MB image.~~ **REVISED 2026-08-04 on a post-build measurement: the image roughly TRIPLES — 273 MB → 754 MB, +481 MB, ≈2.8×.** V4 §1's 352 MB is a *site-packages* figure and stays correct as such; the image delta is larger because of pip metadata, layer overhead and the wheels' on-disk expansion. | Larger than the risk register originally recorded. Accepted by the user with the benchmark in hand, but the accepted figure was the understated one. | Nothing to mitigate; **document the measured figure** (T15′). Layer ordering already puts `pip install` before the source copy (`Dockerfile:31-34`), so source edits do not re-run it. |
| **R16** | **`count()` staleness** *(trap D residual, V5e)*. Three passing criteria depend on a post-write count being consistent. | Unmeasured. Cheap to check. | V5e early in T-VS2. If stale, an explicit flush or a locally cached count is the fallback — neither changes the schema. |
| **R17** | **Cold-open latency of a 100k collection** *(V5c)*. `_open_memory_store()` runs before the banner (`main.py:366-380`); a multi-second open would stall startup. | Unmeasured; all V4 figures are same-process. | Measure in T16′. Mitigation if needed is lazy/deferred open, which is local to `vectorstore.py`. |

---

## 9. Follow-up notes

- **Threshold (C5) stays 0.65.** V3 measured AC-2's pair at 0.7540 against a 0.75 cutoff —
  a 0.004 margin — with unrelated pairs at 0.297–0.395 and nothing in 0.40–0.75. The live
  smoke run scored the same pair at **0.76**, clearing 0.65 by 0.11. Still worth revisiting
  after T16′ with a larger sample; `nomic-embed-text`'s `search_query:` / `search_document:`
  prefixes remain unused and would shift absolute scores — a separate decision.
- **V5c, V5d and V5e are non-blocking but should be measured during T16′.** None can change
  the collection schema; all three have mitigations local to `vectorstore.py`.
- **The 20,000-record trigger in the v1.0.x plan is void.** Do not act on it.
