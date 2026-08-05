# V4 Verification — Milvus Lite feasibility and benchmark

Run 2026-08-03/04 inside `coderunner-ai:latest` (`python:3.11-slim`, **aarch64**), `pymilvus 3.0.1`.

**Purpose**: the user directed a change of vector store from the SQLite + pure-Python cosine design
to Milvus. This measures whether that is justified and at what cost, overturning constraint **C6**
and out-of-scope item **6**, both of which were decided on evidence that this supersedes.

---

## 1. Feasibility

- `pip install pymilvus` alone is **insufficient** — `MilvusClient("<path>")` raises
  `ConnectionConfigException`. The extra is required: `pip install "pymilvus[milvus_lite]"`.
- `milvus_lite` **does** provide an aarch64 Linux wheel. Verified importable in-container.
- `numpy` arrives as a transitive dependency. It is not used by our code, but it lands in the image.
- Site-packages cost: **352 MB** (vs 171 MB for `pymilvus` alone). The current image is ~273 MB.

### Correction, 2026-08-04 — the image grew by more than site-packages did

The line above originally continued *"…so this roughly doubles it."* **That inference was
wrong, and it propagated into `spec.md` §4.1, `plan.md` R15/T15′ and `acceptance.md`'s
definition of done before anyone built the image.**

Measured on the built image:

| | Size |
| --- | ---: |
| `coderunner-ai:latest` before `pymilvus[milvus_lite]` | **273 MB** |
| `coderunner-ai:latest` after | **754 MB** |
| Delta | **+481 MB, roughly 2.8× — tripled, not doubled** |

**The 352 MB site-packages measurement above is not wrong.** It is a measurement of
`site-packages`, taken in isolation, and it remains the correct figure whenever that is
the subject — e.g. the dependency tree a primitive test would acquire if `pymilvus` leaked
into `memory.py` (`plan.md` §1.1, AC-14). The image delta is larger because it also
carries pip metadata, layer overhead and the on-disk expansion of the wheels.

**Do not re-derive an image figure from the site-packages number on this page.** Anything
user-facing uses 273 MB → 754 MB.

## 2. Search latency — Milvus Lite vs the incumbent pure-Python scan

Fresh collection per size, `flush()` before querying, 5 warm-up searches discarded, 20 measured.

| Records | Milvus Lite (median) | Pure Python (V3/plan.md) | Ratio |
| ---: | ---: | ---: | --- |
| 500 | **0.78 ms** | 13 ms | 17× faster |
| 2,000 | **5.80 ms** | ~52 ms | 9× faster |
| 5,000 | **27.3 ms** | 138 ms | 5× faster |
| 20,000 | **77.7 ms** | 445 ms | 6× faster |
| 50,000 | **238 ms** | ~1,100 ms (extrapolated) | 5× faster |

**Milvus Lite wins at every scale, including the original 500 cap.**

### Correction to an earlier claim

An initial probe reported Milvus as *slower* at 500 records (53.7 ms). That probe was wrong — it
omitted `flush()` and had no warm-up, so it measured ingestion settling rather than search. The
table above supersedes it. The assertion in `plan.md` out-of-scope item 6 that an index would be
"pure overhead" was inherited from the pure-Python benchmark and is **not supported** by direct
measurement of Milvus Lite.

## 3. Index choice — FLAT, not HNSW

| Records | Index | Median | p90 | Disk |
| ---: | --- | ---: | ---: | ---: |
| 100,000 | **FLAT** | **133 ms** | **169 ms** | 618 MB |
| 100,000 | HNSW (M=16, efC=200) | 190 ms | 332 ms | 600 MB |
| 200,000 | **FLAT** | **260 ms** | **291 ms** | 1,233 MB |
| 200,000 | HNSW (M=16, efC=200) | 588 ms | **1,742 ms** | 717 MB |

**HNSW is slower than brute-force FLAT at both scales, and far worse at the tail** — 1.7 s p90 at
200k. The anticipated "explicit ANN index" is the wrong move here.

**Decision: use `FLAT` with `metric_type="COSINE"`.** Do not configure HNSW. HNSW's only advantage
is disk at 200k (717 MB vs 1,233 MB), which does not apply at the chosen 100k cap.

## 4. Disk — the binding constraint

768 dims × 4 bytes = 3 KB per vector before overhead.

At the chosen **100,000** cap:

| Component | Typical | Worst case (old truncation) |
| --- | ---: | ---: |
| Vectors (FLAT) | 618 MB | 618 MB |
| Text at old limits (18 KB/record) | ~300 MB | **1.8 GB** |
| **Volume total** | **~0.9 GB** | **~2.4 GB** |

The old truncation limits (task 2,000 / thought 4,000 / code 8,000 / stdout 4,000) were sized for a
**500**-record cap, where the worst case was 8.5 MB. At 100,000 they are unbudgeted.

---

## 5. Decisions taken (user, 2026-08-03/04)

| # | Decision | Rationale |
| --- | --- | --- |
| D1 | **Milvus Lite, embedded** — not standalone containers, not a hybrid with SQLite | Keeps the zero-setup premise; no etcd/MinIO, no extra RAM |
| D2 | **Record cap 100,000** (was 500) | 133 ms median search, well within budget beside a multi-second LLM stream |
| D3 | **Index `FLAT`, metric `COSINE`** | Measured faster than HNSW at both 100k and 200k, and far better at p90 |
| D4 | **Tighter truncation**: thought → 1,000, stdout → 1,000, code → 4,000, task unchanged at 2,000 | ~8 KB/record → worst case ~1.4 GB total rather than 2.4 GB. **Recall quality is unaffected: only the task text is embedded.** |
| D5 | **Isolate Milvus behind a storage seam** | Keeps a stdlib-only core (record model, truncation, dedupe, config parsing, formatting) so most of the 157 bare-interpreter tests survive; all Milvus calls live in one thin module, mirroring how `recall.py` already isolates `ollama` |

## 6. Consequences requiring SPEC revision (→ v1.1.0)

1. **C6 is overturned.** "Pure Python cosine, no numpy" no longer holds — numpy arrives transitively
   and the cosine scan is replaced entirely.
2. **Out-of-scope item 6 is overturned.** ANN indexing is now in scope; the specific finding is that
   FLAT beats HNSW here, so the index choice must be *pinned*, not left to a default.
3. **M1 truncation limits change** per D4.
4. **M3's retrieval mechanics change** — no `iter_candidates`/`dot`/`l2_normalise` scan. The
   `(embed_model, dim)` eligibility filter must be preserved, as a Milvus scalar filter.
5. **The stdlib-only AST test must be re-scoped** to the core module rather than deleted, per D5.
6. **The 20,000-record revisit trigger in `plan.md` §7 is obsolete** — superseded by this benchmark.
7. **Documentation obligation grows materially.** The "zero residue on the host" claim at
   `README.md:15` and `product.md` §2.3 was already due for amendment because memory defaults ON.
   It now needs to state a footprint approaching **1 GB**, plus **+481 MB on the image
   (273 MB → 754 MB)** — see the correction in §1, not the site-packages figure.

## 7. Not yet measured — ALL SUBSEQUENTLY MEASURED (2026-08-04)

Every item below was open when this page was written and has since been closed. Full data in
`.moai/docs/SPEC-MEMORY-001-V5-milvus-semantics.md`. Summarised here so no reader takes this
section at face value:

| Was open | Outcome |
| --- | --- |
| Upsert-by-`task_hash` semantics — the SQLite design used `ON CONFLICT DO UPDATE`, which does not map | **V5a: solved, and better.** Make `task_hash` the VARCHAR **primary key**; `upsert()` replaces in place, row count unchanged. Dedupe becomes structural. But the id hazard **moved rather than vanished** — `upsert()` overwrites every non-key field including `seq`, so a point-query must carry `seq`/`created_at` forward (R14). Omitting it raises `DataNotMatchException` rather than failing quietly. |
| Delete-by-filter cost and oldest-first pruning — `ORDER BY id ASC` has no equivalent | **V5b: two silent traps.** `order_by` is **accepted and ignored** (returns insertion order, no exception). `query()` is **hard-capped at 16,384 rows** and `query_iterator` is broken, so the collection **cannot be enumerated**. Pruning must be a converging `delete(filter=...)` loop driven by `get_collection_stats()`, with `min_seq`/`next_seq` persisted in a `meta` side-collection. Delete is fast: 0.26 s per 1,000 at 100k. |
| Concurrent access — the SQLite design used WAL + `busy_timeout=3000` | **V5d: not supported.** Two simultaneous clients on one file — the loser fails **at open** with `ConnectionConfigException`. A regression from SQLite. `open()` must catch it and return `None` so the second session degrades rather than crashing. |
| Cold-open latency of an existing 100k collection | **V5c: `load_collection()` is MANDATORY.** A persisted collection reopens in state `released` and every `search()` raises `code=101` until loaded — so it works on run one and is **silently dead from session two onward**. `get_collection_stats()` works without load. Costs: load 0.17 s, first search 627 ms, steady state **~298 ms** on a cold container (not §2's 133 ms, which was same-process with a warm cache), total cold start to first result ~1.18 s. |

**Also closed (V5e)**: `get_collection_stats()["row_count"]` is immediately accurate with **no
`flush()`** across insert, upsert and delete — so the up-to-three `count()` calls per turn are safe
and need no defensive flush.
