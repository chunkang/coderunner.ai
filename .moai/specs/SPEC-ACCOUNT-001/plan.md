# SPEC-ACCOUNT-001 — Implementation Plan (v1.0.0)

> Requirements are in `spec.md`. Acceptance criteria are in `acceptance.md`. The measurement record
> is `verification-A1.md`.

## 0. Starting position

**This plan begins with a stop.** `SPEC-PROMPT-001` T3 has not run. Until
`.moai/specs/SPEC-PROMPT-001/verification-T3.md` §5 records **M-a** or **M-c**, no task below is
authorised, and if it records **M-b** none of them ever will be (`spec.md` S1, N1).

That is not ceremony. Under M-b the model refuses account access from its own safety training, every
requirement in `spec.md` §6.2 is addressed to something that will not act on it, and the correct
response is `SPEC-MODEL-001`. Discovering that after writing a worked IMAP example is discovering it
at the maximum possible cost.

**The second thing to be clear about: this SPEC may shrink to documentation, and would still be
worth doing.** If `SPEC-PROMPT-001` already fixed the routing and the model already writes working
IMAP, the only operational task left is a worked example — possibly not even that. §4's accounting
and §5's capture finding are owed to the user **regardless**, because the exposure exists whether or
not any prompt mentions mail. A SPEC whose implementation collapses to two documentation sections
and still ships those sections is doing its job.

| Present | Evidence |
|---|---|
| `imaplib`, `email`, `smtplib` in the standard library — no dependency needed | measured 2026-08-08, `spec.md` §2.1 |
| A credential grammar with `getpass`, redaction, and keychain sourcing already wired | `params.py:72-80`; `main.py:823`; `SPEC-KEYCHAIN-001` |
| A capability section in `SYSTEM_PROMPT` to add **one entry** to | created by `SPEC-PROMPT-001` T4 |
| A probe harness that answers exactly this class of question | `SPEC-PROMPT-001` T1, reused here |
| An existing `never` capture policy needing no schema change | `settings.py:68`; `main.py:1099-1101` |
| A precedent for stating an exposure plainly and building the feature anyway | `SPEC-KEYCHAIN-001` §4; `product.md` §6.13 |

| Absent, and this SPEC must supply it | Evidence |
|---|---|
| Any statement anywhere that mail content is captured under the default policy | traced at `spec.md` §2.3; stated nowhere in the product |
| Any measurement of whether an 8B model writes working IMAP | none; the author's prior is recorded as a prior |
| A test mailbox, and any way to use one in CI | see §1 |

**Two things to be clear-eyed about before starting.**

**The most valuable output of this SPEC is probably §5, not the feature.** The capture finding is a
traced fact about lines that already exist. It is true today, for anyone whose generated script
prints anything sensitive, and nobody has written it down. The feature makes it routine; the
documentation makes it known. If the implementation is cut, §5 must not be.

**The most likely way to get this SPEC wrong is to soften §4.** Every element of it is already
documented and accepted elsewhere, which makes each one individually easy to wave through — "that is
just `tech.md` §7.2", "that is just §6.11". The finding is the **composition**, and a composition is
exactly what disappears when each part is checked against its own prior acceptance.

---

## 1. Preconditions

**P1 — the gate.** `SPEC-PROMPT-001/verification-T3.md` §5 records M-a or M-c. Under M-b, stop and
open `SPEC-MODEL-001` (`spec.md` S1).

**P2 — the probe target.** As `SPEC-PROMPT-001` §1: Ollama is not reachable from the authoring host
(measured 2026-08-08 — no binary, `localhost:11434` → `http_code=000`). The probe runs against the
compose `ollama` sidecar serving `llama3.1:8b` (`docker-compose.yml:46`, `:78`), and the tag, digest
and host are recorded in `verification-A1.md` §1.

**P3 — a test mailbox, and it is not a CI resource.** A1 and A5 need a real IMAP account with a real
app password. Stated now, as a precondition, because it is the constraint most likely to stall this
SPEC mid-flight:

- It **must** be a dedicated throwaway account. Not the author's mail. §4.4's own recommendation
  applied to the people who wrote it.
- It **must not** be provisioned into CI. Putting a live mail credential into CI to test a feature
  whose entire accounting is about credential exposure is self-defeating (`spec.md` §8 item 7).
- Therefore **A5 is manual and not-CI, planned as such from the start** — the discipline
  `SPEC-KEYCHAIN-001`'s HISTORY established when it named three of its ten done-items as never run.
  It is R8 below, and it is an entry in the definition of done rather than a surprise in it.

**P4 — `SPEC-PROMPT-001` T5 has landed** before anything touches `tools.py` (`spec.md` S3). Today
`tools.py:90-91` swallows its own failures (`tech.md` §8.7); adding a second helper to that module
before the first is repaired is the pattern that produced §8.7.

---

## 2. Task decomposition

Six tasks. A1 is the critical path and it is a decision gate for D1.

| # | Task | Artefact | Depends on |
|---|---|---|---|
| **A1** | **Measure the residue, and decide D1.** Reuse `SPEC-PROMPT-001`'s harness against `llama3.1:8b` with that SPEC's prompt shipped. Two sub-variants: **W0** without a worked IMAP example, **W1** with one. Three metrics per cell, and the third is the one that matters: (i) refusal rate; (ii) rate at which a fenced block is produced; (iii) **rate at which the emitted IMAP actually authenticates, searches and returns messages against the P3 test mailbox**. N ≥ 10 per cell. Record the failure taxonomy, not just the rate — date syntax, missing TLS, MIME/charset, folder naming — because *which* detail the model drops decides whether an example or a helper fixes it. **GATE (S2):** a low pass rate at **W1** opens the `tools.py` helper contingency; nothing else does. **E4:** record the author's stated prior as confirmed or overturned. | `verification-A1.md` §2–§4 | P1, P2, P3 |
| **A2** | **Write §4's accounting into the product.** `README.md` gets §4.4 verbatim and unsoftened. `product.md` gets a new §6.x exposure section in §6.13's shape. `tech.md` §7.2 gets the composition. **The composition is the finding** — five properties, each individually accepted, on one turn for the first time — and the failure mode is checking each against its own prior acceptance until nothing is left. Include §4.5: what would actually reduce this (OAuth read-only scope; static screening), named as declined-with-reason rather than omitted. **Owed regardless of A1's outcome.** | `README.md`, `product.md`, `tech.md` | P1 |
| **A3** | **Write §5's capture consequence.** The traced finding (`spec.md` §2.3, §5.1) and the category shift in the user's own words (§5.2): *the policy was designed around credentials leaking into stdout; this makes the payload the captured thing; a user who chose `sensitive_excluded` will reasonably believe their mail was excluded — only the password was.* Point at the existing `never` (`settings.py:68`) which needs **no** schema change (N5). **No documentation anywhere may state that mail content is redacted or excluded under any policy but `never`** (N9). Optionally surface the active policy in `/params` (`settings.py:424-436`, O2). **Owed regardless of A1's outcome.** | `README.md`, `product.md`, possibly `settings.py` | P1 |
| **A4** | **Implement the intervention A1 selected.** Expected: one worked IMAP example in the capability section `SPEC-PROMPT-001` created, **below** the `@param` passage (`SPEC-PROMPT-001` N3), teaching **generic IMAP over TLS with Gmail as the instance** (D2, N7) — not Gmail-specific code. Credentials via `# @param`, password typed `secret` (E2). Summarise-don't-dump guidance included and **labelled as guidance, not a control** (U5, O1). Re-verify `SPEC-KEYCHAIN-001` N2's citation in the same commit (E3). **If A1 selected the helper instead**, P4 applies and N4 governs the documentation: a helper does **not** bound what the credential is used for. | `main.py` | **A1 gate**, P4 if helper |
| **A5** | **Manual IMAP round-trip. Not CI. Named as manual from the start.** Against the P3 mailbox: a real session, a real `@param secret` prompt, a real authentication, a real search, real messages. Then verify by inspection that the app password is **redacted** from captured stdout and that mail content is **not** — which is `spec.md` §5.1 observed rather than traced. Record it in the SPEC HISTORY with what was and was not exercised. **This cannot run in CI and never will** (P3, §8 item 7). | SPEC HISTORY; `verification-A1.md` §5 | A4 |
| **A6** | **Gates and floor.** If tests were added, raise `MIN_PASSED` (`.github/workflows/ci.yml:316`, currently **544**) to a count read from a real `junitxml` run — **measured, not computed** (E6). Add source-level assertions that hold with no model and no mailbox: `SYSTEM_PROMPT` contains no `os.environ` and no `keychain` (N2); `requirements.txt` is unchanged (U3); `settings.py`'s `SCHEMA_VERSION` is unchanged (N5). | `.github/workflows/ci.yml`, `tests/` | A4 |

**Critical path:** P1 → P2/P3 → **A1 (gate)** → A4 → A5 → A6.
A2 and A3 depend only on P1 and should land early — they are owed whatever A1 says, and landing them
first means a cut implementation still ships the parts the user is owed.

---

## 3. Risks

| R | Risk | P | Impact | Mitigation |
|---|---|---|---|---|
| **R1** | **M-b upstream** — the model refuses regardless of prompt | Med | Total; this SPEC is void as specified | P1. The gate is before every task, not inside one |
| **R2** | **M-c** — complies but writes IMAP that does not work. Silent: the script runs, prints nothing useful, the model narrates an empty result | **Med–High** *(this is the author's prior, `spec.md` §3.2, labelled as a prior)* | Med — the feature ships and does not work | A1 measures pass rate, not refusal rate. S2 opens the helper contingency on that number and on nothing else |
| **R3** | **§4 gets softened.** Each of the five properties is individually documented and individually accepted, so each is individually easy to wave through | **High** | **High** — the composition is the finding and it is precisely what disappears under element-wise review | §4.4 is required **verbatim** (U4). A2 is a task with **AC-EXPOSE**. §4.3 is written as three refusals of the "they could have anyway" argument |
| **R4** | **Mail content captured to solution memory under the default policy**, verbatim, into a store generated code can read and that is fed back to the model | **High — this is certain, not a risk** | High | A3, §5. The mitigation is documentation plus an existing policy the user must choose, and `spec.md` §3.5 says plainly that this is weak |
| **R5** | **Credential + egress + no screening + poisonable memory + recall injection, on one turn** | Med | High | §4.1. Not mitigated by this SPEC — §4.5 names what would (OAuth scope; static screening) and §8 items 1 and 6 record why both are out |
| **R6** | **Gmail changes underneath us.** App passwords need 2FA, grant read **and** send with no read-only scope, and Google has revised this surface repeatedly | Med | Med | D2/N7: generic IMAP, Gmail as instance. Fastmail, Proton Bridge and Dovecot then work without a second SPEC |
| **R7** | **A helper is added on the strength of the prior rather than the measurement** | Med | Med — a new module, a new gate entry, a new `Dockerfile` name, in a module `tech.md` §8.7 already criticises | S2 requires a low pass rate **at W1**. E4 requires the prior to be recorded as confirmed or overturned. P4 requires T5 first |
| **R8** | **A5 cannot run in CI and gets quietly dropped** | Med | Med — the one end-to-end verification vanishes | P3 and the definition of done both name it as manual and not-CI **in advance**. `SPEC-KEYCHAIN-001`'s HISTORY is the precedent for naming what was not run |
| **R9** | **The guidance is mistaken for a control.** "Print summaries, not raw bodies" reads like a safeguard | Med | Med — a user relaxes on a false assurance | U5 requires the guidance to be labelled as guidance **everywhere it appears**, including in the prompt itself |
| **R10** | **Someone proposes a `schema_version` bump to add a mail policy** | Low | High — `settings.py:202-207` makes a bump a one-way door; an older build then loses capture entirely | N5, and `spec.md` §3.5 carries `SPEC-KEYCHAIN-001` §3.4's measurement rather than re-deriving it |
| **R11** | **The test mailbox is a real account.** Convenient, and it puts real correspondence into a store this SPEC documents as poisonable and persistent | Med | High, and it lands on the implementer | P3: dedicated throwaway account, stated as a precondition. §4.4's own recommendation, applied to its authors |

---

## 4. Definition of done

Eleven items. Items 2, 3, 9 and 11 are the ones most likely to be reported as done without having
been done.

1. `SPEC-PROMPT-001/verification-T3.md` §5 records M-a or M-c, and this SPEC's HISTORY quotes that
   outcome and its numbers.
2. Every acceptance criterion in `acceptance.md` has been **observed** passing, not reasoned to pass.
3. **`verification-A1.md` §2–§4 contain figures produced by runs, with N per cell, and no figure a
   run did not produce** (U6, N8). The pass-rate column is filled — not only the refusal-rate column,
   which is the easier measurement and the less useful one.
4. **The author's prior on D1 is recorded as confirmed or overturned** (E4), in `verification-A1.md`
   §5 and in this SPEC's HISTORY.
5. §4.4's honest summary appears **verbatim and unsoftened** in `README.md`, and no text anywhere
   states or implies the contrary (U4, AC-EXPOSE).
6. §4.5 is present: OAuth read-only scope and static screening named as **declined with reasons**,
   not omitted.
7. §5.2's sentence — *a user who chose `sensitive_excluded` will reasonably believe their mail was
   excluded; only the password was* — or one that says the same thing as plainly, is in `README.md`
   (U5, AC-CAPTURE).
8. **No documentation anywhere states that mail content is redacted or excluded under any policy but
   `never`** (N9). Checked by grep, not by memory.
9. **A5 was performed against a real mailbox, and its result is recorded in the SPEC HISTORY —
   including that it is manual and not-CI and will not be re-run automatically.** If it was not
   performed, that is stated **as not performed and not as not needed**, and the SPEC does not move
   to `completed`.
10. `requirements.txt` is unchanged (U3); `settings.py`'s `SCHEMA_VERSION` is unchanged (N5); the
    `@param` passage is unchanged and `SPEC-KEYCHAIN-001` N2's citation is re-verified (N2, E3).
11. **Anything not run is named as not run and not as not needed.** In particular: which IMAP
    providers were exercised (expected: one), whether the redaction observation in A5 covered both
    the password and the content, and whether A1's pass-rate assessment was automated or eyeballed.
