# TASK-10 Smoke Procedure — SPEC-MEMORY-001

Prepared ahead of execution. Covers the acceptance criteria that **no unit test can assert**,
because they are container-level: **AC-4** (persistence across `--rm`) and **AC-5 half 2**
(no silent degradation in a real session).

Everything here assumes TASK-05–07 have landed and `main.py` is in a working state.

---

## 0. Preconditions

```bash
cd /Users/kurapa/src/kurapa/CodeRunner.AI
git status --porcelain          # expect M main.py, M Dockerfile, M docker-compose.yml, M coderunner
docker start coderunner-ollama; sleep 5
docker exec coderunner-ollama ollama list   # BOTH models must be present
```

### ⚠️ The false-pass trap (found by expert-devops, TASK-09)

`cleanup()` (`coderunner:196-205`) **stops the sidecar on every launcher exit**. So any
`docker exec coderunner-ollama ollama rm …` issued *after* a `./coderunner` run silently
fails — leaving the model present and making "no pull happened" trivially, wrongly true.

**Rule: before every `ollama rm`, run `docker start coderunner-ollama`, wait for health, and
check the exit status of the `rm` itself.** Never trust a bare `rm`.

```bash
ollama_rm() {                       # use this, not a bare docker exec
  docker start coderunner-ollama >/dev/null 2>&1
  for i in $(seq 1 15); do
    [ "$(docker inspect -f '{{.State.Health.Status}}' coderunner-ollama 2>/dev/null)" = healthy ] && break
    sleep 2
  done
  docker exec coderunner-ollama ollama rm "$1" || { echo "RM FAILED — do not trust this run"; return 1; }
}
```

### ⚠️ The stale-image trap (risk R1)

`coderunner:163` builds **only when the image is absent**, and it exists. After TASK-05–08 the
image is stale, and `Dockerfile:26` now copies `memory.py`/`recall.py` — so an unrebuilt run
either raises `ImportError` at startup or degrades permanently in a way that looks **exactly**
like trap A, sending you after the wrong bug.

```bash
docker compose build coderunner    # MANDATORY first line. Not optional.
```

---

## 1. AC-5 half 1 — volume ownership (shell level)

Already verified by expert-devops, but re-run after the rebuild:

```bash
docker volume rm coderunner_app_data 2>/dev/null || true
docker compose run --rm --entrypoint sh coderunner -c '
  id -un
  ls -ldn /home/runner/.coderunner
  touch /home/runner/.coderunner/.probe && echo WRITE_OK || echo WRITE_DENIED
  rm -f /home/runner/.coderunner/.probe
  ls -l /app/memory.py /app/recall.py'
```

**PASS**: `runner`; mode line shows **`1000 1000`**; `WRITE_OK`; both modules in `/app`.
**FAIL**: `0 0` → V1 Case B → TASK-08 is wrong.

---

## 2. AC-1 — cold start, zero embed calls

Volume is empty from step 1.

```bash
./coderunner
  > What is 17 factorial?          # a task that MUST produce code and execute
  > /memory
  > /exit
```

**PASS**:
- the turn completes normally: thought → script → `Execution OK` → grounded answer
- **no `🧠 [Memory]` degradation line anywhere in the session**
- `/memory` reports enabled, writable, **total 1**, embed model `nomic-embed-text:latest`, dim 768

**Note**: cold start must not embed for *retrieval* (empty-store short-circuit), but capture
does embed once. One embed total for this turn is correct.

---

## 3. AC-5 half 2 — the criterion that catches silent degradation

This is the half that matters. Per the V1 verification:

> A test checking only "the DB opened" passes in both the working and the broken case.

**A run in which memory silently degrades on every turn FAILS AC-5, even though nothing errors
and the product otherwise behaves perfectly.** The discriminating signal is the *absence* of a
degradation status line combined with `/memory` reporting a non-zero count.

Confirm from step 2's transcript. If `/memory` reports `total 0` after a successful code turn,
memory is degrading silently — investigate, do not proceed.

---

## 4. AC-4 — persistence across the `--rm` boundary

```bash
docker volume inspect coderunner_app_data --format '{{.Mountpoint}}'
docker volume inspect coderunner_ollama_data --format '{{.Mountpoint}}'
docker start coderunner-ollama >/dev/null 2>&1; sleep 5
docker exec coderunner-ollama ollama list      # both models still present

./coderunner
  > /memory                       # total >= 1, SAME db path
  > /exit
```

**PASS**: count survives; both volumes intact. This also proves `cleanup()`'s deliberate `stop`
rather than `down` (`coderunner:201-203`) still preserves the volumes, and that adding
`app_data` did not disturb `ollama_data`.

---

## 5. AC-2 — reuse on a semantically similar task (the headline scenario)

```bash
./coderunner
  > What's the current weather in Seoul in Celsius?
  > /exit
./coderunner
  > Tell me the temperature in Busan right now
  > /exit
```

**PASS**: the second turn shows a recall status line and the injected block references the
Seoul solution. **Record the reported similarity** — V3 measured this exact pair at **0.7540**
against the 0.65 threshold, so it should fire with ~0.10 of margin.

**Also confirm the model still reasons** — the executed script must be the one emitted this
turn, adapted for Busan, **not** a replay of the Seoul script. Replay is explicitly out of
scope (constraint C2); if the stored code runs verbatim, something is badly wrong.

---

## 6. AC-6 / AC-6b — miss behaviour, and that the store keeps learning

```bash
./coderunner
  > Compute the 200th Fibonacci number      # unrelated to weather; a MISS
  > /memory
  > /exit
```

**PASS**: no recall block injected, **and the record IS captured** (`total` increments).

This is the scenario the AC-6/M2 correction exists for. A miss is what a *new* task looks like;
if misses were not captured the store would hold its first record and never learn again. If
`total` does not increment here, PART A regressed.

---

## 7. AC-3 in the container — real degradation

```bash
ollama_rm nomic-embed-text:latest      # use the guarded helper from §0
./coderunner
  > What is 2 to the power of 100?
  > /exit
```

**PASS**: exactly one yellow status line, turn completes normally, exit 0, no traceback.

Restore afterwards:
```bash
docker start coderunner-ollama >/dev/null 2>&1; sleep 5
docker exec coderunner-ollama ollama pull nomic-embed-text:latest
```

---

## 8. AC-9 — `/memory` commands end to end

```bash
./coderunner
  > /memory
  > /memory list 2
  > /memory forget <id>          # count decrements by 1
  > /memory clear                # WITHOUT --yes: must delete NOTHING
  > /memory
  > /memory clear --yes          # count -> 0
  > /memory
  > /exit
```

**PASS**: counts move as expected; `clear` without `--yes` is a no-op; `agentic_turn()` is never
invoked for any `/memory*` input; `forget 99999` prints not-found and raises nothing.

---

## 9. C5 threshold revisit — report and propose ONLY

**User decision: TASK-10 records and proposes. It does NOT change the default.**
Any change to 0.65 is the user's call at Phase 3 review.

Record, from the runs above:
- similarity for each genuine match (expect the Seoul/Busan pair near 0.754)
- similarity for each genuine non-match (V3 measured unrelated pairs at 0.297–0.395)
- whether the two populations straddle 0.65 with margin

Note that V3's five task strings were an indication, not a distribution, and that
`nomic-embed-text`'s `search_query:` / `search_document:` prefixes were **not** used — adopting
them would shift absolute scores and is a separate decision.

---

## 10. Documentation obligations — the binding half

The tempting reading of T15 is "add six rows to the env table at `README.md:19-23`". **That is
the minor half.**

The binding half, mandatory under constraint C4 because memory defaults **ON**:

- [ ] **Amend the "zero residue on the host" claim at `README.md:15`** — the product now writes
      user content to persistent host storage at `/var/lib/docker/volumes/coderunner_app_data/_data`.
- [ ] **Amend `product.md` §2.3**, same claim, same reason.
- [ ] Add the new persistent-surface note to `tech.md` §7.2 (risk R6): generated code runs as
      `runner` and can therefore read, poison, or delete `memory.db` — previously nothing
      survived the container. Blast radius is bounded because stored content is only ever
      *shown* to the model, never executed (constraint C2).
- [ ] Six new env vars in the `README.md` table.
- [ ] A "Solution memory" section: DB location, record cap, `/memory` commands.
- [ ] Note that `OLLAMA_HOST` and `CODERUNNER_HISTORY` were **already** undocumented
      (`product.md` §6.8).

`product.md` and `tech.md` amendments route through `/moai:3-sync` per `plan.md` T15.

---

## 11. Reconciliation list — five items, not the two the plan anticipated

| # | Finding | Action |
| --- | --- | --- |
| 1 | `plan.md` §3 / T6 place the config constants in `main.py` after `:58`; implementation centralises them in a `from_env` loader in `memory.py`. Arguably better — it brings config parsing under the coverage gate — but the plan documents a location the code does not use. | Update `plan.md` §3 and T6 to match |
| 2 | `env_str` helper exists but is absent from `plan.md` §4's public-surface listing | Add it |
| 3 | `plan.md` §3 gives `MEMORY_DB` as `~/.coderunner/memory.db`; compose pins the absolute `/home/runner/.coderunner/memory.db`. Identical in-container. | Word consistently |
| 4 | `MemoryConfig`, `MemoryStore.count()`, `meta_get()`, `utc_now_iso()`, and `MemoryStore.open(..., busy_timeout_ms=)` are additions to the plan's public surface | Document in `plan.md` §4 |
| 5 | AC-6b (miss on a non-empty store still captures) was added during implementation | Ensure it is written into `acceptance.md` |

---

## Definition of done

`acceptance.md` §"Definition of done", **minus** the V1/V2/V3 line — those are discharged
(`.moai/docs/SPEC-MEMORY-001-V1-verification.md`).
