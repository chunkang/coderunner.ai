# SPEC-SKILL-001 — Acceptance criteria

> Requirements are in `spec.md`. Task decomposition is in `plan.md`.

---

## AC-METER — the meter measures, and says so when it cannot

### Scenario 1: a round trip's real cost is recorded

**Given** a turn that completes one model round trip against a server reporting its six fields,
**When** the round trip ends,
**Then** `prompt_eval_count`, `eval_count`, `total_duration`, `load_duration`,
`prompt_eval_duration` and `eval_duration` are all recorded for that round trip, attributed to their
source per `spec.md` U1,
**And** no figure is derived from a character count or from a client-side timer.

### Scenario 2: absent counts are recorded as absent

**Given** a server or client that reports no counts, or no durations, on the final chunk,
**When** the turn ends,
**Then** the turn is recorded as **unmeasured in that dimension**,
**And** it contributes to no rate or average,
**And** no estimate is substituted (`spec.md` S1, N2).

*This is the criterion, not the edge case. A meter that quietly fills a gap with an approximation is
worse than one that reports the gap, because the approximation survives into a table where nothing
distinguishes it from data.*

### Scenario 3: the meter cannot break a turn

**Given** a meter that raises for any reason mid-turn,
**When** the turn continues,
**Then** the turn completes exactly as it does today,
**And** at most one status line is emitted — the same degradation contract solution memory already
meets (`product.md` §4 feature 20).

### Scenario 4 (edge): the empty session

**Given** a session in which no turn has yet completed,
**When** the accounting is read,
**Then** it reports zero measured turns rather than a zero cost.

*Zero turns and zero tokens are different facts and a report that conflates them passes every other
criterion here while being useless.*

### AC-METER also requires

1. The meter module holds **no third-party import**, asserted by walking its AST — the assertion
   `memory.py` already carries and `tech.md` §1.2 explains.
2. It is registered in **both** `pytest.ini`'s `--cov` list **and**
   `conftest.py:205`'s `PER_FILE_COVERAGE_TARGETS` at **100 %**.
3. It appears on `Dockerfile:43`'s `COPY` line **and** in every list
   `tests/test_source_seam.py` asserts set equality over. *That test exists because `keychain.py`
   was added to one and not the other, one day after a comment warned it could happen.*
4. `stream_llm()` is exercised by a fake client. Its own docstring records that it "has never been".

---

## AC-BASELINE — the ordering is demonstrated, not asserted

### Scenario 5: the pre-registration is committed before the first trial

**Given** `verification-T2.md` §1 carrying the reduction target and the Stage 2 false-reuse
threshold,
**When** the commit history is read,
**Then** a commit exists containing that rule **and no results**,
**And** its timestamp precedes every recorded trial.

*`SPEC-PROMPT-001` v1.1.1 records what it cost to be unable to demonstrate this: its record claimed
twice, in bold, that the pre-registration had been committed first. It had not — rule and results sat
in one working tree, indistinguishable in git from a single pass written after the numbers landed.
The cheap fix is unavailable in retrospect.*

### AC-BASELINE also requires

5. Every recorded row carries the **server's own model readback**, not the configured tag. A rate
   without the model that produced it is not a measurement (`SPEC-MODEL-001` U3).
6. The baseline carries the **per-source breakdown** `spec.md` U1 requires, because that breakdown —
   not a preference — is what selects between T3, T4 and T5 (`plan.md` R2).
7. Cost and latency are recorded in the same row and pre-registered **separately**, because since
   v1.1.0 the SPEC promises both and a target met in one and missed in the other is a likely
   outcome (`plan.md` R1). **No claim in one dimension may imply the other** (`spec.md` U4).

---

## AC-LATENCY — reuse is faster, and the comparison is honest

*Added at v1.1.0. The author's instruction was that a reused skill should **work faster**, and speed
is a different claim from cost with a different way of going wrong.*

### Scenario 6: a removed round trip is attributable

**Given** a turn in which the grounded-answer pass is skipped (T4),
**When** its latency is compared against the same turn shape today,
**Then** the record shows the skip itself (`spec.md` E4),
**And** the improvement is attributed to a removed `total_duration` rather than inferred from a
smaller total.

### Scenario 7: model-load time is excluded

**Given** a latency comparison between two runs,
**When** the figures are published,
**Then** `load_duration` is reported separately for each and excluded from the comparison,
**And** no comparison is drawn between a cold run and a warm one (`spec.md` U5, N6).

*This is the criterion, not the edge case. `load_duration` can dominate every other term on a cold
container, so a warm-versus-cold comparison shows a large improvement that no change caused — and it
would be reported in good faith. `tech.md` §6.4 records the same class of error for the vector store,
where same-process search measures 133 ms and cold-container search 298 ms.*

### Scenario 8: a cost saving that is not a speed saving is reported as such

**Given** a change that reduces `prompt_eval_count` but does not materially reduce
`prompt_eval_duration` — the cached-prefix case (`spec.md` §5 item 4),
**When** the result is written up,
**Then** it is reported as a **context-budget** saving,
**And** it is **not** presented as, or alongside, a speed improvement.

*`spec.md` U4 exists for this scenario. Under v1.0.0 this was a labelling rule; under v1.1.0 it is
also an admission that the task under-delivered against what was asked for, and the record says so.*

---

## AC-SKILL — distillation shortens the block without removing its guards

### Scenario 9: a skill is smaller than the record it renders

**Given** a stored `SolutionRecord` whose script approaches the 4,000-character cap
(`memory.py:51`),
**When** it is injected as a skill,
**Then** the rendered block is recorded alongside the size the full record would have had,
**And** the saving is the difference between two observed values (`spec.md` E3).

### Scenario 10: the guards survive distillation

**Given** any skill rendering,
**When** the block is inspected,
**Then** it carries the `adapt or ignore` framing,
**And** it carries the `Authored by:` line rendered from the **record**, never the session.

*Both were specified by measurements this SPEC did not take — `SPEC-MEMORY-001` R3's
false-positive guard and `SPEC-MODEL-001` T3 option M-c. Removing either to save tokens would spend
another SPEC's evidence.*

### AC-SKILL also requires

8. No change to the collection schema, the truncation caps, or the `0.65` similarity floor
   (`spec.md` N4).
9. **No stored code is executed and no model call is skipped** at Stage 1 (`spec.md` N1).

---

## AC-GROUND — no turn ends with less on screen than it does today

### Scenario 11: skipping the grounded pass still answers the user

**Given** a successful turn whose stdout is judged self-explanatory,
**When** the grounded-answer round trip is skipped,
**Then** the user sees an answer, not only an execution panel,
**And** the turn's rendered output is no less informative than the same turn is today.

*This is `SPEC-ILLUSTRATE-001` S4's constraint, borrowed deliberately. `product.md` §2.1 promises an
answer "grounded in a value that was actually computed"; a token optimisation that quietly withdraws
the promise is a regression with a benchmark attached.*

### Scenario 12 (edge): stdout that is not self-explanatory

**Given** a turn whose stdout is a bare number, an empty string, or a traceback fragment,
**When** the skip is evaluated,
**Then** the grounded pass **runs**.

*The default is to spend the tokens. T4's deliverable is the measurement of when not to, and its
honest outcome may be "not shipped".*

---

## AC-HISTORY — bounding history must not break self-correction

### Scenario 13: a two-attempt turn still recovers

**Given** a turn whose first script fails and whose second attempt corrects it,
**When** history bounding is active,
**Then** the second attempt still receives the stderr it is diagnosing,
**And** the turn succeeds as it does today.

*The retry loop reads history to diagnose. A window that drops the failure being corrected turns
self-correction into a slower first attempt, and the message list being shorter is not evidence that
it did not.*

---

## AC-GATE — Stage 2 is decided by a rule, not a preference

The gate is `spec.md` §3.5 and it is decidable on T2's and T3–T5's recorded numbers:

| | Outcome | Condition | What happens |
|---|---|---|---|
| **S-a** | Proceed | Measured false-reuse rate is at or below the pre-registered threshold, **and** Stage 1's measured saving falls short of the target | T6 drafts the C2 amendment, quoting the measured rate |
| **S-b** | Do not ship | Measured false-reuse rate exceeds the threshold | **Stage 2 does not ship.** C2 stands. Delivered value is the meter plus Stage 1 |
| **S-c** | Do not attempt | Stage 1's measured saving already meets the target | Stage 2 is **not attempted**. A security-relevant constraint is not amended for a saving already banked |

### AC-GATE also requires

10. **T6's artefact is an amendment document, not a diff to `main.py`.** If code implementing replay
    lands before `SPEC-MEMORY-001` carries the amendment, `spec.md` N1 has been violated
    (`plan.md` R4).
11. The amendment states the security cost in `tech.md` §7.2's own terms: **under C2 a poisoned
    record can mislead the model's reasoning; under replay it can execute.** Generated code runs as
    the same `runner` uid that owns the store (`product.md` §6.11).

---

## Definition of done

1. A new meter module exists, is stdlib-only by AST assertion, and is gated at **100 %** in both
   `pytest.ini` and `conftest.py`.
2. AC-METER through AC-GATE have each been **observed** — not inferred from a green suite.
3. **AC-METER Scenario 2 and AC-HISTORY Scenario 13 have each been observed FAILING at least once**,
   deliberately, against a knowingly-broken implementation: a meter that estimates from characters
   for Scenario 2, and a window that drops the corrected failure for Scenario 10. Both are green
   under every other test in this repository, which is the whole reason they have criteria.
   *A gate never observed failing is not known to be a gate.*
4. `verification-T2.md` §1 was committed **containing no results**, before the first trial, and the
   commit is identifiable in the history.
5. Every published reduction figure cites its baseline, the run that produced it, and the server's
   own model readback.
6. `MIN_PASSED` (`ci.yml:367`) has been raised to a number taken from a real `--junitxml` run, in
   the same change that added the tests.
7. **No claim anywhere states or implies that Stage 2 shipped, or that C2 was amended, unless
   `SPEC-MEMORY-001` carries the amendment.**
8. The illustration defect's token cost is reported **separately** (`spec.md` O2), so this SPEC and
   `SPEC-ILLUSTRATE-001` cannot both bank it.
9. **Every published latency figure excludes `load_duration` and states it separately**, and no
   comparison spans a cold run and a warm one.
10. **If cost and latency disagree, both are published.** The SPEC promises speed since v1.1.0; a
    result that delivers only context budget is reported as that, in those words, rather than as a
    partial success in the dimension that was asked for.
11. **S-b and S-c are recorded plainly if they occur.** A SPEC that measures its own preferred design
   out of contention has done the measurement correctly, and this item exists so that outcome is
   written down rather than quietly reopened.
