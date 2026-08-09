# SPEC-ACCOUNT-001 — A1 measurement record

> Requirements are in `spec.md`. Task decomposition is in `plan.md`. Acceptance criteria are in
> `acceptance.md`.

---

## STATUS: NOT YET RUN — AND NOT YET AUTHORISED

**Created 2026-08-08 with its structure in place and every result cell empty.** No probe has been
executed. No mailbox has been contacted. Nothing in §2, §3, §4 or §5 has been measured.

**This file is blocked twice over.** `SPEC-ACCOUNT-001` is gated on
`.moai/specs/SPEC-PROMPT-001/verification-T3.md` §5 recording **M-a** or **M-c** (`spec.md` N1, S1),
and that file is itself marked not yet run. Under outcome **M-b** this document is never filled in,
and §5 below records that it was stopped by measurement rather than abandoned.

**There are no placeholder figures in this document and there must never be** (`spec.md` N8). Every
results cell reads `—`. A plausible-looking number written here as an illustration would, on a
second reading by a second person, be indistinguishable from data.

**Two preconditions must be discharged before anything below is filled** (`plan.md` §1):

- **P2 — the probe target.** Ollama is not reachable from the authoring host (measured 2026-08-08:
  no binary at `/usr/local/bin/ollama` or `/opt/homebrew/bin/ollama`; `localhost:11434` →
  `http_code=000`). The probe runs against the compose `ollama` sidecar serving `llama3.1:8b`
  (`docker-compose.yml:46`, `:78`).
- **P3 — a test mailbox, which is not a CI resource.** A real IMAP account with a real app password,
  and it **must** be a dedicated throwaway. Not anyone's real correspondence — `spec.md` §4.4's own
  recommendation, applied to the people implementing it. It is **not** provisioned into CI:
  installing a live mail credential into CI to test a feature whose entire accounting is about
  credential exposure is self-defeating (`spec.md` §8 item 7).

---

## 1. Provenance — what was measured, and against what

*Not yet run. Fill from the run itself, not from configuration files.*

| | Value |
|---|---|
| Date of run | — |
| Model tag | — *(expected `llama3.1:8b`; record what the run reports)* |
| Model digest | — |
| Quantisation | — |
| Reached via | — |
| Ollama version | — |
| Temperature / sampling | — |
| Harness commit | — *(`SPEC-PROMPT-001` T1's harness, reused)* |
| `SYSTEM_PROMPT` commit under test | — *(must be post-`SPEC-PROMPT-001` T4)* |
| Trials per cell (N) | — |

### 1.1 The test mailbox

| | Value |
|---|---|
| Provider | — |
| IMAP host / port | — *(expected `imap.gmail.com:993`)* |
| Dedicated throwaway account? | — **must be yes** (P3, `plan.md` R11) |
| 2-step verification enabled | — *(an app password requires it; `spec.md` §2.6)* |
| Messages seeded, and their shape | — |
| Credential destroyed after the run? | — |

**Record the last row.** An app password created for a measurement and left alive afterwards is a
live full-mailbox credential with no owner, which is the exact thing `spec.md` §4 is about.

---

## 2. Sub-variant W0 — no worked IMAP example

*Not yet run.*

`SPEC-PROMPT-001`'s shipped prompt, with **no** mail-specific example. This cell measures the
residue: how much of the reported defect the general repair already fixed.

Task prompt: `check my gmail for recent 7 days and let me know the interview opportunities`

| Metric | Value |
|---|---|
| Trials (N) | — |
| Routed DIRECT / refused | — |
| Produced a fenced block | — |
| **Emitted code authenticated against the P3 mailbox** | — |
| **Emitted code searched and returned messages** | — |
| **Pass rate (end to end)** | — |

**If the pass rate here is high, this SPEC's implementation is unnecessary** and reduces to §4's
accounting and §5's capture consequence — which are owed regardless (`plan.md` §0). Record that
plainly if it happens; a SPEC that measures itself out of a job has done the measurement correctly.

---

## 3. Sub-variant W1 — with a worked IMAP example

*Not yet run.*

The same prompt plus one worked IMAP example in the capability section, teaching **generic IMAP over
TLS with Gmail as the instance** (`spec.md` D2, N7).

| Metric | W0 | W1 |
|---|---|---|
| Trials (N) | — | — |
| Routed DIRECT / refused | — | — |
| Produced a fenced block | — | — |
| Authenticated | — | — |
| Searched and returned messages | — | — |
| **Pass rate (end to end)** | — | — |

**The W1 pass rate is the number that decides D1** (`spec.md` S2, `acceptance.md` AC-D1 item 2). A
low rate **here** — with the example already present — is the only thing that opens the `tools.py`
helper contingency. A low rate at W0 alone justifies nothing except the example.

---

## 4. Failure taxonomy

*Not yet run.*

**This table is what makes the measurement actionable.** An aggregate pass rate cannot distinguish
"a better example would fix this" from "only a helper will". *Which* detail the model drops is the
distinction.

| Failure mode | W0 count | W1 count | Fixable by a better example? |
|---|---|---|---|
| IMAP search date syntax (`SINCE 01-Aug-2026`, not ISO) | — | — | — |
| Plain `IMAP4` instead of `IMAP4_SSL`, or wrong port | — | — | — |
| MIME multipart not walked; body missing or wrong part taken | — | — | — |
| Encoded subject not decoded (`email.header.decode_header`) | — | — | — |
| Charset mishandled | — | — | — |
| Folder naming (`INBOX` vs Gmail label paths) | — | — | — |
| Credential not declared via `# @param` | — | — | — |
| Password declared with the wrong type (not `secret`) | — | — | — |
| Called `input()` despite the prohibition | — | — | — |
| Other — enumerate | — | — | — |

**The last three rows are not IMAP failures**, and they are here because they would indicate that
`SPEC-INPUT-001`'s grammar is not being reached for under this task shape. That would be a finding
about the parameter machinery, not about mail, and it belongs to whoever owns `SPEC-INPUT-001`.

---

## 5. D1 decision, and the prior

*Not yet decided.*

**Decision:** — *(one of: **worked example only** / **worked example + `tools.py` helper**)*

**Supporting figures:** — *(W1 pass rate, with N; the dominant failure modes from §4)*

**The author's prior, recorded before the measurement** (`spec.md` §HISTORY, §3.2):

> A `tools.py` helper will probably turn out to be needed. IMAP date syntax, MIME multipart walking
> and `decode_header` charset handling are precisely the fiddly details an 8B model drops, and the
> failure is silent — the script runs, prints nothing useful, and the model narrates an empty
> result.

**Prior: CONFIRMED / OVERTURNED —** *(fill in; `spec.md` E4, `acceptance.md` AC-MEASURE-A1 item 7)*

**Why:** —

**Silence on the prior fails AC-MEASURE-A1 item 7.** The prior was written down before the
measurement precisely so that it can be overturned on the record rather than quietly retrofitted to
whatever the numbers turned out to be.

### 5.1 If the gate above closed instead

*If `SPEC-PROMPT-001` recorded **M-b**, record here:*

**Stopped by measurement, not abandoned.** Outcome: — . `SPEC-MODEL-001` opened: — .

---

## 6. A5 — manual IMAP round-trip

*Not yet run. Manual. Not CI. Will not be re-run automatically.*

This is `plan.md` A5 and it is planned as manual **from the start** rather than discovered to be so
(`plan.md` P3, R8) — the discipline `SPEC-KEYCHAIN-001`'s HISTORY established.

| Step | Observed |
|---|---|
| A real session, a real `@param … : secret` prompt at `getpass` | — |
| Real authentication against the P3 mailbox | — |
| Real search, real messages returned | — |
| Capture policy in force during the turn | — |
| **The app password IS redacted from captured stdout** | — |
| **The mail content is NOT redacted, and is present in the store verbatim** | — |
| A keychain-registered password was supplied without prompting, and was redacted identically | — |
| Store inspected at | — *(`/home/runner/.coderunner`, `docker-compose.yml:74-75`)* |

**The two bold rows are `spec.md` §5.1 observed rather than traced.** The trace is six line
citations and is convincing; it is not the same as having looked. Both halves must be checked — a
run that confirms only the second proves nothing about the first (`acceptance.md` AC-CRED item 6).

**Credential destroyed after the run?** —

---

## 7. What these runs do NOT establish

*To be written after the runs, and expected to be longer than §2–§4 combined.*

Candidates known in advance:

- **One provider.** Expected: Gmail alone. `spec.md` D2 specifies generic IMAP precisely so that
  Fastmail, Proton Bridge and Dovecot are reachable — none of which will have been measured.
- **One mailbox, seeded by us.** Real mailboxes are larger, messier, and contain MIME the seeded set
  will not.
- **One model, one quantisation, one host.** Users may set `CODERUNNER_MODEL`
  (`docker-compose.yml:78`).
- **A rate is not a guarantee.** N trials bound a probability. Nothing here claims anything about a
  particular future turn.
- **A5 is one run.** It is an existence proof that the chain works end to end, not a characterisation
  of it, and it will not be re-run by CI ever.
- **Nothing measured here bears on `spec.md` §4.** The composition — credential, egress, no
  screening, poisonable memory, recall injection — is a structural finding about what the system
  permits. No probe confirms or refutes it, and a green run must never be read as having done so.
