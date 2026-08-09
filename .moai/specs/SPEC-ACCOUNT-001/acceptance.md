# SPEC-ACCOUNT-001 — Acceptance criteria (v1.0.0)

> Requirements are in `spec.md`. Task decomposition is in `plan.md`. The measurement record is
> `verification-A1.md`.

Nine criteria. **AC-GATED** is first and is not a formality — it can fail the whole SPEC before any
other criterion is evaluated.

**Two of the nine — AC-EXPOSE and AC-CAPTURE — are discharged by documentation, and they are the two
that matter most.** That is unusual and it is deliberate. The exposure they describe exists today,
whether or not this feature ships; what this SPEC adds is that a user will meet it routinely and
that somebody wrote it down. If the implementation is cut, those two criteria still stand.

---

## AC-GATED — the SPEC is authorised at all

**Covers:** N1, S1

| # | Criterion | How it is observed |
|---|---|---|
| 1 | `.moai/specs/SPEC-PROMPT-001/verification-T3.md` §5 records an outcome, and it is **M-a** or **M-c** | Read §5 |
| 2 | This SPEC's HISTORY quotes that outcome **and the figures behind it** — not "the gate passed" | Read HISTORY against `verification-T3.md` §3 |
| 3 | **IF §5 records M-b:** no task in `plan.md` §2 was started, `main.py` is untouched by this SPEC, `SPEC-MODEL-001` exists, and this SPEC records that it was **stopped by measurement**, not abandoned | Check the `main.py` diff and the specs directory |
| 4 | **IF §5 is empty:** nothing in this SPEC has begun | `git log` |

**Item 3's wording is the criterion.** "Stopped by measurement" and "abandoned" produce the same
absence of code and completely different records. A future reader must be able to tell that this was
tried and answered, not dropped.

---

## AC-MEASURE-A1 — the residue was measured, and the right thing was measured

**Covers:** U6, S6, N8, E4

| # | Criterion | How it is observed |
|---|---|---|
| 1 | `verification-A1.md` §1 names the model tag, digest, host, sampling settings and harness commit | Read §1 |
| 2 | Both sub-variants ran: **W0** without a worked IMAP example, **W1** with one | Read §2, §3 |
| 3 | **The pass-rate column is filled, not only the refusal-rate column.** For every cell producing a fenced block, the emitted IMAP was run against the P3 test mailbox and scored on whether it authenticated, searched and returned messages | Read §3. A filled refusal column and an empty pass column does **not** discharge this |
| 4 | The **failure taxonomy** is recorded, not just the aggregate — IMAP date syntax, missing TLS, MIME/charset, folder naming, other | Read §4 |
| 5 | Every figure carries N, and N ≥ 10 per cell, or the shortfall is stated | Read the tables |
| 6 | **No placeholder figures** anywhere in the file; unrun cells read as unrun | Read the file before any run |
| 7 | **The author's prior — that a helper will probably be needed — is recorded as confirmed or overturned**, by name, in §5 (E4) | Read §5. Silence on the prior is the failure |

**Item 3 is the whole criterion and item 7 is the point of taking it.** Refusal rate is the easy
measurement; it answers `SPEC-PROMPT-001`'s question, not this one. This SPEC's question is whether
the code works, and a SPEC that measures the easy thing and reports it as the answer has measured
nothing.

**Item 4 is what makes the measurement actionable.** *Which* detail the model drops decides whether
a better example fixes it or only a helper will. An aggregate pass rate cannot distinguish those.

---

## AC-D1 — the intervention was chosen by measurement, not by preference

**Covers:** S2, S3, `spec.md` §3.2

| # | Criterion | How it is observed |
|---|---|---|
| 1 | The intervention implemented at A4 is the one A1's numbers selected, and `verification-A1.md` §5 says which and why | Read §5 against the `main.py` diff |
| 2 | **IF a `tools.py` helper was added:** A1 measured a low pass rate **at W1** — with the worked example already present. A low rate at W0 alone does **not** justify a helper | Read §3's W1 row |
| 3 | **IF a helper was added:** `SPEC-PROMPT-001` T5's fix to `tools.py:90-91` had already landed (S3, P4) | `git log` ordering |
| 4 | **IF a helper was added:** no documentation describes it as bounding what the credential is used for (N4). The credential remains a module-level name; the script may call `imaplib`, `smtplib` or `urllib` directly | Grep the documentation for any claim of containment |
| 5 | **IF no helper was added:** §5 records that the prior was overturned, with the number that overturned it | Read §5 |

**Item 4 is the false claim this SPEC is most likely to make in good faith.** "We route it through a
helper" reads like a safeguard and is not one. §4's accounting is byte-for-byte identical with or
without a helper.

---

## AC-CRED — the credential path is the existing one, unchanged

**Covers:** U1, U2, E1, E2, N2, N3

| # | Criterion | How it is observed |
|---|---|---|
| 1 | The prompt's worked example declares the password as `# @param … : secret`, and the host and user as `str` | Read the example |
| 2 | `SYSTEM_PROMPT` contains **zero** occurrences of `os.environ` and **zero** of `keychain`, case-insensitive (N2) | An assertion in the test suite, not a review note |
| 3 | The `@param` passage is semantically unchanged, and `SPEC-KEYCHAIN-001` N2's citation is re-verified in the same commit (E3) | Diff the passage; `git show` the commit |
| 4 | A keychain-registered password is still supplied without prompting, and is still redacted exactly like a typed one | Exercise it in A5 |
| 5 | No path delivers the credential other than `# @param … : secret` (N3) | Read the example and the prompt text |
| 6 | Measured in A5: the password **is** redacted from captured stdout | Inspect the store after a real turn |

**Item 6 is the positive half of §5.1 and it must be observed, not assumed.** The finding is that the
password is redacted and the content is not; verifying only the second half proves nothing about the
first.

---

## AC-EXPOSE — the accounting is stated, and stated plainly

**Covers:** U4, E5, `spec.md` §4

| # | Criterion | How it is observed |
|---|---|---|
| 1 | §4.4's honest summary appears in `README.md` **verbatim and unsoftened** | Diff it against `spec.md` §4.4 |
| 2 | It states all four: generated code receives the credential; **there is no screening of that code**; an app password grants **full read and send** with no read-only scope; solution memory is poisonable and is read back to the model | Read it. A version missing any one of the four fails |
| 3 | It states that **every one of those facts was already true**, and that what this feature adds is **routineness** — not capability | Read it |
| 4 | `product.md` gains a new §6.x exposure section in **§6.13's shape** | Read it beside §6.13 |
| 5 | `tech.md` §7.2 records the **composition** — five properties, individually accepted, on one turn for the first time | Read §7.2 |
| 6 | **§4.5 is present:** OAuth with a read-only scope, and static screening, named as **declined with their reasons**, not omitted | Read §4.5's landing site |
| 7 | A dedicated mail account is the recommended configuration (E5, O4), and the documentation states that **not using the feature closes none of the five properties** | Read it |
| 8 | **No text anywhere states or implies that this feature is safe, contained, or that the sandbox protects the credential** | Grep the documentation |

**Item 3 is the sentence that makes the accounting honest rather than alarmist.** This SPEC adds no
capability. Saying so is not a softening — it is the precise claim, and it is what makes item 8
enforceable, because an accounting that overstates is as unusable as one that understates.

**Item 6 exists so a later reader can see that §4 was written by someone who knew what would fix
it.** An exposure section with no "what would actually reduce this" reads as resignation.

---

## AC-CAPTURE — the category shift reaches the user

**Covers:** U5, S4, S5, N9, `spec.md` §5

| # | Criterion | How it is observed |
|---|---|---|
| 1 | `README.md` states that mail **content** is not in the redaction set and is captured verbatim under the default policy | Read it |
| 2 | It states the category shift: the capture policy was designed around **credentials** leaking into stdout; this feature makes the **payload** the captured thing | Read it |
| 3 | **The sentence, or one as plain:** *"A user who chose `sensitive_excluded` will reasonably believe their mail was excluded. Only the password was."* | Read it |
| 4 | The existing `never` policy is named as the answer for users who need capture not to happen, and is reachable **with no `settings.json` schema change** (S5, N5) | Read it; check `settings.py`'s `SCHEMA_VERSION` is unchanged |
| 5 | **No documentation anywhere states that mail content is redacted, excluded, or protected by any policy other than `never`** (N9) | Grep, not memory. This is the most damaging false statement available to this SPEC |
| 6 | Any "print summaries, not raw bodies" instruction is **labelled as guidance, not a control**, everywhere it appears — including inside `SYSTEM_PROMPT` itself (U5, R9) | Read every occurrence |
| 7 | Measured in A5: after a real mail turn under the default policy, mail content **is** present in the store, unredacted | Inspect the store |
| 8 | `settings.json` gained no key and `SCHEMA_VERSION` is unchanged (N5) | Diff `settings.py` |

**Item 7 turns §5.1 from a trace into an observation.** The trace is six line citations and is
convincing; it is not the same as having looked. `SPEC-KEYCHAIN-001` records a check that "had been
inspecting nothing" and would have passed against the one form its SPEC forbade — the lesson is that
a reading is not a measurement.

**Item 6's "including inside `SYSTEM_PROMPT` itself"** is deliberate: the guidance's first reader is
the model, and its second is the developer who later mistakes it for a safeguard.

---

## AC-NODEP — nothing was added that did not need to be

**Covers:** U3, N5, N6, N7

| # | Criterion | How it is observed |
|---|---|---|
| 1 | `requirements.txt` is unchanged (U3) | Diff |
| 2 | `settings.py`'s `SCHEMA_VERSION` is unchanged and `settings.json` gained no key (N5) | Diff |
| 3 | No heuristic detects "mail-shaped" turns from parameter names or generated code (N6) | Read the diff |
| 4 | The prompt teaches **generic IMAP over TLS**, with Gmail as the worked instance — not Gmail-specific code paths (N7, D2) | Read the example. `X-GM-RAW` or Gmail-only folder names would fail this |
| 5 | `docker-compose.yml` is unchanged | Diff |

---

## AC-ROUNDTRIP — it was actually done, against a real mailbox

**Covers:** `spec.md` §7 item 1; `plan.md` A5, P3

| # | Criterion | How it is observed |
|---|---|---|
| 1 | A real session against a real IMAP account: a real `@param secret` prompt, a real authentication, a real search, real messages returned | Performed manually. Recorded in the SPEC HISTORY |
| 2 | The account used was a **dedicated throwaway**, not anyone's real correspondence (P3, R11) | Stated in the record |
| 3 | Both halves of §5.1 were observed: the password redacted, the content **not** | Inspect the store after the turn |
| 4 | The record states that this is **manual and not-CI**, and that it will not be re-run automatically (R8) | Read the record |
| 5 | **IF A5 was not performed**, it is named as **not performed and not as not needed**, and the SPEC does not move to `completed` | Read HISTORY |
| 6 | The record states which providers were exercised — expected: **one** — and does not generalise beyond them | Read the record |

**Item 5 is the criterion this repository already has a precedent for.** `SPEC-KEYCHAIN-001` shipped
with three of ten done-items unrun, named them, and **kept its status at `draft`**. That is the
standard: not that everything was run, but that the status matches the evidence.

---

## AC-FLOOR — the CI floor is a measurement

**Covers:** E6

| # | Criterion | How it is observed |
|---|---|---|
| 1 | If tests were added, `MIN_PASSED` (`.github/workflows/ci.yml:316`) was raised to a count read from a real `junitxml` run, and the run is identified | Read the commit message or HISTORY |
| 2 | The count was **not** computed as the old floor plus an expected delta | The identified run's own total matches |
| 3 | If no tests were added, the floor is unchanged and that is stated | Diff the workflow |

---

## Definition of done

See `plan.md` §4. Eleven items. The four most likely to be reported as done without having been
done:

- item 3 — the **pass-rate** column filled, not only the refusal-rate column;
- item 4 — the author's prior recorded as **confirmed or overturned**, by name;
- item 9 — A5 performed against a real mailbox, or named as not performed **and not as not needed**;
- item 11 — what was not run, named.

If A1 shows the implementation is unnecessary, **AC-EXPOSE and AC-CAPTURE still apply.** They
document an exposure that exists whether or not this feature ships, and the only new thing about it
is that somebody wrote it down.
