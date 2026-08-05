# V5 Verification — Milvus Lite upsert and pruning semantics

Run 2026-08-04 in `coderunner-ai:latest`, `pymilvus 3.0.1` + `milvus_lite`, aarch64.

**Blocking**: V5a and V5b gate implementation, as V1 gated the Dockerfile work. The SQLite design
rested on `ON CONFLICT(task_hash) DO UPDATE` and `ORDER BY id ASC`; **neither has a Milvus
equivalent**, and the naive substitutes fail silently.

---

## V5a — Dedupe by `task_hash`: SOLVED, and better than the SQLite design

**Make `task_hash` the VARCHAR primary key.** Dedupe then becomes structural rather than a clause.

```
after insert 5  : 5 rows
after upsert h2 : 5 rows  | upsert_count 1
h2 row          : {'task_hash': 'h2', 'seq': 99, 'task': 'REPLACED'}
```

`client.upsert()` replaces in place. Row count does not grow; the row is genuinely updated.

**This removes the id-reallocation hazard entirely.** The SQLite design needed
`ON CONFLICT … DO UPDATE` specifically because `INSERT OR REPLACE` reallocates the `AUTOINCREMENT`
id and silently breaks `/memory forget <id>`. With the hash as primary key there is no surrogate id
to reallocate.

**Consequence for `/memory forget <id>`**: the user-facing id must stay a small integer. Keep a
monotonic `seq INT64` field for display and ordering; `forget N` resolves `seq == N` → `task_hash`,
then deletes by primary key. One extra query, no ambiguity.

---

## V5b — Oldest-first pruning: TWO SILENT TRAPS

### 🔴 Trap 1: `order_by` is accepted and **ignored**

Inserted in deliberately shuffled order so that insertion order ≠ sorted order:

```
inserted in order          : [50, 10, 90, 30, 70, 20, 80, 40, 60, 0]
query limit=5, no order_by : [50, 10, 90, 30, 70]
query limit=5, order_by=seq: [50, 10, 90, 30, 70]   ← IDENTICAL. NOT SORTED.
```

`order_by="seq"` **does not raise**. It is swallowed by the dynamic-kwargs path and silently
discarded, returning insertion order.

This is the most dangerous finding in the migration. An implementer writing
"query oldest N, then delete them" would get **arbitrary** rows — and the code would look correct,
pass a count-only assertion (`count == cap`), and quietly evict the wrong records forever. It is the
same shape as trap A: a failure that ships looking healthy.

**Any test for pruning MUST assert *which* rows survived, never just how many.**

### 🔴 Trap 2: `query()` is hard-capped, and `query_iterator` is broken

```
query(..., limit=16384) on 100k rows → returned exactly 16384 (LIMIT-CAPPED)
query_iterator(batch_size=3) on 10 rows → returned 3 of 10, then stopped
  [WARNING] failed to get mvccTs from milvus server, use client-side ts instead
```

So there is **no reliable way to enumerate the full collection**. You cannot read all `seq` values
to compute "the oldest N".

### The only sound approach: an externally-maintained watermark

`delete(filter=...)` works correctly, is fast, and returns the deleted primary keys:

```
delete(filter="seq < 1000") on 100k rows : 0.26 s → 99,000 rows
delete(filter="seq < 2")    on 5 rows    : ['h0','h1'] → 3 rows
row_count via get_collection_stats()      : accurate, cheap, uncapped
```

Therefore:

1. Assign a **monotonic `seq`** at insert from a persisted counter (`next_seq`).
2. Persist `min_seq` and `next_seq` in a side `meta` collection (or file) — they cannot be recovered
   from the collection, because it cannot be fully enumerated.
3. When `get_collection_stats()["row_count"] > cap`, delete in batches:
   `delete(filter=f"seq < {min_seq + batch}")`, advance `min_seq`, re-check `row_count`, repeat
   until at or below cap.
4. Gaps are harmless — the loop converges on `row_count`, not on arithmetic.

`get_collection_stats()` is the trustworthy signal throughout; `query()` is not.

---

## Cost at the 100,000 cap

| Operation | Cost |
| --- | ---: |
| Insert 100k (batches of 5,000) | 29.8 s |
| Delete 1,000 by filter | 0.26 s |
| `get_collection_stats()` row_count | negligible |
| `query()` ceiling | **16,384 rows** |

---

## Requirements this imposes on the SPEC

1. **`task_hash` is the VARCHAR primary key.** Dedupe is structural; `upsert()` is the write path.
2. **`seq INT64`** monotonic field for user-facing ids and pruning order.
3. **`meta` side-collection** persisting `next_seq`, `min_seq`, `schema_version`, `embed_model`,
   `dim` — none recoverable from the main collection.
4. **Pruning is a converging delete-by-filter loop driven by `get_collection_stats()`**, never a
   sorted query.
5. **`order_by` must never appear in the codebase.** Add an explicit comment at the pruning site
   recording that it is a silent no-op, or someone will "simplify" the loop back into a bug.
6. **AC-7 must assert survivor identity**, not just row count. A count-only assertion passes while
   the wrong records are evicted.
7. `FLAT` / `COSINE`, pinned (V4 D3).

---

# V5e — `count()` write-visibility, and upsert field semantics

Raised by `manager-spec` as risk **R16**: `count()` is called up to three times per turn
(`recall.py:135` cold-start short-circuit, `:201` `retrieval_degraded()`, `:233`
`vector_for_capture()`). If a post-write count were stale, **AC-1, AC-6b and M5's
one-status-line invariant would all break silently** — three criteria that currently pass.

**Verdict: NOT a risk. `get_collection_stats()["row_count"]` is immediately accurate with no
`flush()`.**

```
empty                       : 0
after insert, NO flush      : 1     <-- the real per-turn path
after flush                 : 1
after insert +0.5s, no flush: 2
after flush                 : 2
after upsert, NO flush      : 2     <-- dedupe holds; count does not grow
after flush                 : 2     seq -> 999 (row replaced in place)
after delete, NO flush      : 0
after flush                 : 0
```

Insert, upsert and delete are all reflected immediately. **R16 is closed**; no `flush()` is
required on the per-turn path for counting to be correct.

## Bonus finding — R14's failure mode is LOUD, not silent

A partial `upsert()` that omits a non-key field does **not** silently null it. It raises:

```
pymilvus.exceptions.DataNotMatchException:
  Insert missed an field `seq` to collection without set nullable==true or set default_value
```

This is materially better than feared. The **R14 hazard is real** — `upsert()` overwrites every
non-key field, so `seq` and `created_at` must be carried forward by a point-query on `task_hash`
before the write — but forgetting to do so **cannot fail quietly**. The engine rejects the call.

Contrast with trap C (`order_by`) and trap D (`query()` cap), which fail silently and are the
genuinely dangerous ones.

**Consequence for the implementation**: the read-before-upsert in `remember_success()` is
mandatory, and its absence surfaces as a hard exception in testing rather than as a
`/memory forget <id>` that quietly addresses the wrong record.

---

---

# V5c — Cold open of a persisted collection: `load_collection()` IS MANDATORY

Measured on a real 100,000-record collection persisted to a Docker volume, then opened from a
**fresh container**.

```
count(100000) via get_collection_stats()  : OK, 0.001 s   <-- works WITHOUT load()
search() before load()                    : MilvusException (code=101)
   "Collection 'solutions' is in state 'released'; call load() before search/get/query"
load_collection("solutions")              : 0.17 s
first search after load                   : 627 ms
subsequent searches (cold container)      : ~298 ms mean
TOTAL cold startup to first result        : ~1.18 s
volume on disk                            : 590 MB   (V4 estimated 618 MB — close)
```

## Why this is a trap, not a detail

A collection created in-process is **implicitly loaded**, so everything works on the **first** run.
On every subsequent run — a fresh container opening the persisted volume — the collection returns in
state `released` and every `search()` raises. That exception lands in `recall.py`'s broad `except`,
`retrieval_degraded()` reports a fault, and **memory is silently dead from session two onward while
session one looked perfect**.

It is invisible to any test that creates its collection in the same process, which is every unit
test in the existing suite.

**Requirements:**
1. Call `load_collection()` on every open of an existing collection, before the first search.
   Idempotent; safe unconditionally.
2. **Do not** add a load merely to count — `get_collection_stats()` works without it, and the
   cold-start short-circuit at `recall.py:135` calls `count()` before any search.
3. Comment the load site with the reason.
4. **Test**: create in one client, close, open a NEW client on the same path, and *serve a search*.
   Asserting the store merely opened and counted is not sufficient — the same insufficiency as AC-5.

**Latency for documentation**: use **~298 ms** for steady-state search on a cold container, not V4's
133 ms, which was same-process with a warm cache.

---

# V5d — Milvus Lite does NOT support concurrent access

Two genuinely simultaneous clients on the same database file:

```
A: FAILED ConnectionConfigException: (code=1, message=Open local milvus failed)
B: OPEN OK rows=100
B: t=1s..4s search OK          <-- B unaffected throughout
```

The loser fails **at open**, not on a later operation. This is a **regression from the SQLite
design**, where WAL + `busy_timeout=3000` allowed readers to coexist. There is no Milvus Lite
equivalent and no locking scheme is warranted.

**Requirement**: `VectorStore.open()` must catch `pymilvus.exceptions.ConnectionConfigException`
(and `MilvusException` generally) and return `None`, exactly as the SQLite version caught
`sqlite3.OperationalError`. The existing degradation path catches sqlite3 types, which no longer
occur — **if the new types are not caught, a second concurrent session crashes the REPL at startup
instead of degrading**.

With it caught, the second session runs with memory disabled and emits one startup warning via the
M5 path. That is the correct outcome.

**Exposure**: `coderunner:229` launches with `--name coderunner`, so a second *launcher* run
collides on the container name before reaching Milvus. But `docker compose run --rm -T coderunner`
— how the smoke tests drive the app — sets no name, so two can genuinely overlap.

**Test** by monkeypatching `MilvusClient` to raise; do not attempt real concurrency in the unit
suite.

---

## Method note

Two self-inflicted errors while running these probes, both worth recording because they are easy to
repeat:

1. A probe file named `concurrent.py` sat on `sys.path` and **shadowed the stdlib `concurrent`
   package** that `pymilvus` imports, producing a misleading "partially initialized module
   (circular import)" error.
2. Mounting a fresh named volume at `/data` — a path absent from the image — produced a
   **root-owned** volume that `runner` could not write, surfacing as
   `ConnectionConfigException: Open local milvus failed`. **This is trap A exactly**, encountered
   accidentally. Note that it presents with the *same exception* as the V5d concurrency failure, so
   the two are not distinguishable by exception type alone.
