---
id: SPEC-ACCOUNT-001
version: "1.0.0"
status: "draft"
created: "2026-08-08"
updated: "2026-08-08"
author: "Chun Kang"
priority: "MEDIUM"
---

## HISTORY

### v1.0.0 (2026-08-08) — Initial specification

**GATED. This SPEC does not proceed until `SPEC-PROMPT-001` T3 records outcome M-a or M-c in
`.moai/specs/SPEC-PROMPT-001/verification-T3.md` §5.** Under outcome **M-b** — the model refuses
account access from its own safety training regardless of what the prompt says — this SPEC is void
as specified and `SPEC-MODEL-001` is opened instead. That is not a formality: under M-b every
requirement below is addressed to a model that will not act on it, and the correct response is to
change the model, not the words.

Written from the same refusal that produced `SPEC-PROMPT-001`. A user asked CodeRunner to read their
own mailbox with their own credentials and was told *"I can't help you with accessing your personal
email account."* `SPEC-PROMPT-001` establishes the general cause — three contradictory routing rules
settled in practice by a three-domain example set — and repairs it. **This SPEC exists only for
whatever the general repair leaves behind**, and its first task is to find out how much that is.

**The feature is legitimate and this SPEC builds it.** A local single-user tool, the user's own
mailbox, the user's own app password, typed once and thereafter held by the operating system
(`SPEC-KEYCHAIN-001`). Every part already exists: `imaplib`, `email` and `smtplib` are standard
library — *(measured 2026-08-08: all four present in `sys.stdlib_module_names`, `IMAP4_SSL`
available; the in-image measurement on Python 3.11.14 stands)* — and `# @param NAME: secret = "…"`
already collects a password through `getpass` and adds it to the redaction set. No dependency is
added. Nothing is invented.

**What is new is a composition, and §4 states it without softening.** Five properties of this
system are individually documented and individually accepted: model-written code receives the
credential as a plain module-level name; the sandbox has full network egress, by design; there is no
static screening of generated code of any kind; solution memory is persistent and writable by
generated code; and recall text from that store is injected into the prompt. **This is the first
change that puts all five on the same turn.** Each of the five has a citation. The composition has
none, because nothing has needed one until now.

**And there is a consequence in the capture policy that is a category shift rather than a degree.**
`SPEC-INPUT-001`'s capture policy was designed around **credentials** leaking into captured stdout,
and it handles that case: an app password declared `secret` is in the redaction set and is replaced
by exact substring match (`params.py:398-431`). Mail **content** is not a declared parameter, is
never in that set, and is therefore captured verbatim under the **default** policy. This feature
makes the **payload** — third-party personal correspondence — the captured thing. *A user who chose
`sensitive_excluded` will reasonably believe their mail was excluded. Only the password was.* §5
states that in those words and §3.5 decides what is done about it.

**One design question is deferred to a measurement rather than answered by preference.** Does an 8B
model, once permitted, write IMAP that actually works? IMAP search date syntax, `IMAP4_SSL`, RFC822
fetch, MIME multipart walking, `email.header.decode_header` for encoded subjects and charset
handling are exactly the fiddly-detail cases small models drop. **The author's prior is that a
`tools.py` helper will turn out to be needed. That is a prior and it is labelled as one; it is not a
measurement and it does not decide anything here.** A1 measures it, and D1 is settled by A1's number
(§3.3). `verification-A1.md` exists with its structure in place and its results empty.

**Not measured, and named as not measured.** No probe has been run for this SPEC either. Ollama is
not reachable from the authoring host (`SPEC-PROMPT-001` §2.6, measured 2026-08-08). No IMAP
round-trip has been performed against any mailbox. **A5 is planned as manual and as not-CI from the
outset** rather than discovered to be so later, in the discipline `SPEC-KEYCHAIN-001`'s HISTORY
established when it named three of its ten definition-of-done items as never run.

---

# SPEC-ACCOUNT-001 — User account access over IMAP with `@param secret` credentials

**Title:** Let the model read the user's own mailbox with the user's own credential, using only the
standard library and the parameter grammar that already exists — with the exposure that buys stated
in full, and the capture consequence stated in the user's own terms

## 1. Scope statement

Extends `SPEC-PROMPT-001`. That SPEC makes the prompt's stated capability surface match the
sandbox's actual one. This one adds **one entry** to the capability section it created: reading a
mailbox over IMAP, with credentials declared through `# @param … : secret`.

The mechanism is entirely existing machinery:

- `imaplib` and `email` are standard library. **No dependency is added** — `requirements.txt` is
  unchanged and `tech.md` §2 treats each of its six lines as load-bearing.
- The credential is declared `# @param app_password: secret = "…"`, collected through `getpass`
  (`main.py:823`), kept out of readline history (`SPEC-INPUT-001` N3), spliced into the script as a
  `repr()`-produced literal (`params.py:372-390`), and added to the redaction set
  (`params.py:398-413`).
- If the user has registered it with `./coderunner --set-secret`, it is supplied without prompting
  (`SPEC-KEYCHAIN-001`). **The model is not told this and must not be** — `SPEC-KEYCHAIN-001` N2,
  adopted here as N2.

**Nothing about the model's job changes** except that it now knows this is permitted and has one
worked example of how.

**This SPEC is `MEDIUM` and gated for a reason §4 states in full:** it does not make anything
private, and it composes five accepted exposures onto one turn for the first time. A user who needs
their mailbox not to be reachable by model-written code does not get that from this SPEC and must
not be told otherwise.

---

## 2. Verified environment

### 2.1 What the standard library already provides

*Measured 2026-08-08 on the authoring host (Python 3.14.3); the in-image measurement on 3.11.14
stands and is the one that governs, since `Dockerfile` pins the image's interpreter.*

| Module | In `sys.stdlib_module_names` | Relevance |
|---|---|---|
| `imaplib` | **yes** | `IMAP4_SSL` present — `imap.gmail.com:993` needs nothing else |
| `email` | **yes** | MIME parsing, `email.header.decode_header` for encoded subjects |
| `smtplib` | **yes** | Not used by this SPEC; recorded because it is reachable |
| `poplib` | yes | Not used |
| `mailbox` | yes | Not used |

**So the honest statement is that this feature adds no capability to the sandbox at all.** Every
byte of it was reachable from generated code before this SPEC and is reachable after. What changes
is that the model is told it is permitted, and shown once how. That framing matters for §4: this
SPEC does not open a door, it puts a sign on a door that was never locked.

### 2.2 The parameter machinery this SPEC reuses unchanged

| Fact | Evidence |
|---|---|
| Declaration grammar and the `secret` type | `params.py:72-80`, `params.py:43-55` |
| `secret` routes to `getpass`, so the value is not echoed and not in readline history | `main.py:823`; `SPEC-INPUT-001` N3 |
| Value reaches the script as a `repr()`-produced literal through one site | `params.py:309-324`, `:327-342`, `:372-390` |
| The redaction set is built **only** from declared `secret` values | `params.secret_values()`, `params.py:398-413` |
| Redaction is exact substring replacement, longest first | `params.redact()`, `params.py:417-431` |
| Keychain sourcing fills `values` before collection, so a sourced secret is redacted exactly like a typed one | `SPEC-KEYCHAIN-001` §4.4 |

### 2.3 The capture path, traced end to end

*This trace is the whole of §5 and it is given as line citations so it can be re-walked rather than
believed.*

| Step | Site | What happens |
|---|---|---|
| 1 | `settings.py:75` | `DEFAULT_POLICY = POLICY_SENSITIVE` — the default is `sensitive_excluded` |
| 2 | `main.py:1054` | `policy = param_session.policy.value if … else ""` |
| 3 | `main.py:1061` | redaction runs **only** `if secrets and policy == settings.POLICY_SENSITIVE` |
| 4 | `main.py:1063-1065` | `params.redact(result.stdout, secrets)` — `secrets` is `params.secret_values()`, i.e. **declared `secret` values only** |
| 5 | `main.py:1099` | `never` skips capture — `if param_declared and policy == settings.POLICY_NEVER` |
| 6 | `main.py:1103-1109` | otherwise `_capture_turn(…, result.stdout, …)` persists stdout |

**The consequence, stated as a fact about lines rather than as an opinion:** at step 4 the redaction
set contains the app password and nothing else. Mail content was never a declared parameter, so it
is not in `secrets`, so `redact()` does not touch it, so at step 6 it is persisted verbatim.

`params.redact()`'s own docstring already concedes it cannot recover a value the script
**transformed** before printing. Mail content is a stronger case than that: it was never a candidate
for redaction at all.

### 2.4 Where the captured content goes, and who can reach it

| Fact | Evidence |
|---|---|
| The store lives in a **named** volume that survives `--rm` | `docker-compose.yml:74-75`, `:114-115`; `coderunner:263` |
| Generated code runs as the same `runner` uid as the REPL, and the store directory is chowned to it | `Dockerfile:42-46`; `tech.md` §7.2 |
| A model-written script can read the whole task history, poison it with fabricated records, or delete it | `product.md` §6.11 |
| Stored content is only ever **shown** to the model as text, never executed | `product.md` §6.11, constraint C2 |
| Recall text is injected into the prompt on attempt 1 | `main.py:1008` |

**The fourth row is a real bound and it is repeated rather than overstated.** A poisoned record
cannot itself run. It can steer what the model writes on a turn that holds a live mail credential
and unrestricted egress. That second sentence is what this SPEC adds; the first is `product.md`'s
and stands.

### 2.5 The sandbox controls that are absent, quoted rather than paraphrased

`tech.md` §7.2, verbatim:

> **No network restriction.** The container has full egress, and this is **by design**: the system
> prompt explicitly states *"Network access IS allowed for scraping"* … Generated code therefore
> inherits full outbound internet access **and** can reach `http://ollama:11434` directly on the
> compose network

> **No static screening of generated code.** `extract_last_python_block()` is a regex extraction
> with **no AST inspection, no import allowlist, no denylist, no length cap, and no user
> confirmation step**. Whatever the model emits between the fences is written to disk and run

Both are pre-existing, both are deliberate, and neither is changed by this SPEC. They are quoted
because §4 is unreadable without them.

### 2.6 Gmail specifics, and what they cost

| Fact | Consequence |
|---|---|
| IMAP host is `imap.gmail.com:993`, TLS | `imaplib.IMAP4_SSL` handles it with no dependency |
| An **app password** requires 2-step verification enabled on the account | A user without 2FA cannot use this feature at all, and will meet that as an authentication failure rather than as an explanation |
| **An app password grants full mailbox access — read and, over SMTP, send-as. There is no read-only scope.** | The credential handed to model-written code cannot be narrowed. This is not a design choice this SPEC makes; it is one it cannot avoid |
| IMAP search date syntax is `SINCE 01-Aug-2026`, not ISO | The single most likely thing an 8B model gets wrong. A1 measures it |
| Google has revised this surface repeatedly | A SPEC that hard-codes Gmail is exposed to a third party's product decisions. Hence D2: **generic IMAP, Gmail as the worked example** |

**OAuth is out of scope, and the reason is stated rather than the exclusion merely asserted.** OAuth
would permit a genuinely read-only scope, which is the one thing that would materially reduce §4's
exposure. It is excluded because it requires a client secret, a browser redirect the container
cannot perform, a token store, a refresh path, and at least one dependency — and because
`tech.md` §2 and `SPEC-KEYCHAIN-001` §8 item 4 both treat a new dependency as a decision requiring
its own justification. **This is the most valuable thing this SPEC declines to do, and it is
recorded as declined rather than as unconsidered** (§8 item 1).

---

## 3. Design decisions

### 3.1 D0 — This SPEC's first task is to find out how much is left

`SPEC-PROMPT-001` may fix the reported refusal outright. Its D1 repairs the clause that routes
network tasks to DIRECT; its D2 establishes that the prompt teaches by example.

**So A1 measures the residue before anything is designed for it.** If, with `SPEC-PROMPT-001`
shipped, the model already takes CODE on the Gmail task and writes working IMAP, this SPEC reduces
to documentation — §4's accounting and §5's capture consequence, which are owed to the user
regardless of how the routing turned out, because the exposure exists whether or not a prompt
mentions it.

That is the honest shape of a gated SPEC: it may shrink to nothing operational and still have
something it must say.

### 3.2 D1 — Prompt example, not a `tools.py` helper — decided by A1, with the prior labelled

**Recommendation: a worked IMAP example in `SYSTEM_PROMPT`, alongside `wttr.in` and the Wikipedia
REST API — not a helper.** Contingent, and A1 decides.

The reasoning follows directly from `SPEC-PROMPT-001`'s diagnosis. The prompt's effective capability
surface is measured to be its example set. An example is therefore the intervention most consistent
with how this prompt is already known to work, and it costs no new module, no new gate entry, no new
`Dockerfile` line and no new test surface.

**Three candidates, ranked:**

| | Candidate | Assessment |
|---|---|---|
| 1 | **Worked IMAP example in the prompt** | Zero new surface. Consistent with the diagnosed mechanism. Does not repeat §8.7 |
| 2 | **`tools.py` mail helper** | Fallback, **iff** A1 measures a low pass rate with the example present. Justified by measured need or not at all |
| 3 | Prompt prose without an example | Rejected by `SPEC-PROMPT-001` U3/N4. A rule the model does not act on is the defect, not the fix |

**The author's prior, labelled as a prior:** a helper will probably turn out to be needed. IMAP date
syntax, MIME multipart walking and `decode_header` charset handling are precisely the fiddly details
an 8B model drops, and the failure is silent — the script runs, prints nothing useful, and the model
narrates an empty result. **This is a prior. It is not a measurement, it does not decide D1, and it
is written down so that if A1 contradicts it the record shows the prior was held and overturned
rather than quietly retrofitted.**

**One argument for the helper that must not be made.** A helper does **not** bound what the
credential is used for. The value remains a module-level name in `run.py` and the same script can
call `imaplib` directly, or `smtplib`, or `urllib`. A helper bounds the **common path** and never
the **possible** path, and §4's accounting is identical either way. Anyone reaching for "a helper
makes it safer" should read §2.5 first.

**The counter-precedent, stated because it is on point.** The last helper added to `tools.py`
shipped a regex HTML parser and an `except Exception: pass`, and `tech.md` §8.7 criticises both.
`SPEC-PROMPT-001` T5 fixes the swallowed exception and explicitly declines the regex rewrite with
its reason. **Adding a second helper before the first is repaired is the pattern that produced
§8.7**, which is why T5 precedes A4 across the two SPECs (§7 item 5).

### 3.3 D2 — Generic IMAP, with Gmail as the worked example

**Recommendation.** The prompt teaches IMAP over TLS with a host, a user and a password, and uses
Gmail as the concrete instance — not Gmail-specific code paths.

**Cost.** A generic example is slightly less likely to work first time against Gmail than a
Gmail-tuned one, because Gmail's folder naming and its `X-GM-RAW` search extension are not standard
IMAP. A1 measures whether that cost is real.

**What it buys.** §2.6's last row: Google has revised app passwords, "less secure apps" and IMAP
access repeatedly. A SPEC whose worked example is *an instance of a general mechanism* survives that;
one whose example *is* the mechanism does not. It also means Fastmail, Proton Bridge and a
self-hosted Dovecot work without a second SPEC.

### 3.4 D3 — Credentials by `# @param … : secret`, and nothing else

**Recommendation.** The host, the username and the app password are declared exactly as
`SPEC-INPUT-001` specifies. The password is `secret`; the host and user are `str`.

This is not a new decision so much as a refusal to make one. Every property `SPEC-INPUT-001`
established then holds unchanged: literal safety, stdin untouched, `code` never reassigned before
capture, redaction at three sinks. Keychain sourcing works for the password with no additional
mechanism, because eligibility keys on `type == secret` and one predicate governs the mask, the
redaction set, the `getpass` route and the policy gate (`SPEC-KEYCHAIN-001` §3.1).

**Explicitly rejected: teaching the model to read `os.environ`.** `SPEC-KEYCHAIN-001` N2 forbids it,
`SPEC-INPUT-001` §3.7 already rejected it on separate grounds, and `SPEC-KEYCHAIN-001` §4.4 works
out the consequence in full — under env-direct, `params.secret_values()` returns an empty list and
**`sensitive_excluded` governs nothing at all**. That is a silent, total loss of the policy. Adopted
here as N2 and N3.

### 3.5 D4 — Capture policy: document, guide, and point at `never`. No schema bump.

**Recommendation.** Three things, and the SPEC is explicit that only the first is a control:

1. **Document the consequence** — §5, in the user's own terms, in `README.md` and `product.md`, in
   `SPEC-KEYCHAIN-001` §4.3's register. **This is the only thing here that is guaranteed to work.**
2. **Guide the model** to print derived summaries — sender, subject, date, a one-line judgement —
   rather than raw bodies. **This is guidance, not a control**, and it is labelled as guidance
   everywhere it appears (U5). A model that ignores it produces a turn that captures raw bodies and
   nothing detects that.
3. **Point the user at `never`**, which already exists (`settings.py:68`), already skips capture
   entirely (`main.py:1099-1101`), and needs **no** schema change.

**Rejected: a new policy value, or auto-forcing `never` on mail-shaped turns.** Either requires
`settings.json` to carry something new. `SPEC-KEYCHAIN-001` §3.4 measured what that costs and the
finding is decisive in both directions: an unknown key in a `schema_version: 1` file is ignored
**silently** (`settings.py:216-224`), so adding one without a bump writes a setting nothing reads;
and bumping to `2` is a **one-way door for older builds** — `settings.py:202-207` refuses a file
declaring a higher version than the build knows and falls back to `never`, so a user who runs a new
image once and then an old one **loses capture entirely** until they delete the file. Neither price
is worth paying to relabel a policy.

**Rejected: detecting "mail-shaped" turns.** It would require inspecting generated code or parameter
names, which is a heuristic over model output — the same class of thing `tech.md` §7.2 records as
absent, and a poor one. A turn that declares `app_password` is not reliably a mail turn and a mail
turn need not declare it.

**Cost, stated plainly.** Under the default policy, a user who reads their mail through CodeRunner
and does not change that policy will accumulate their correspondence in a store that model-written
code can read. The mitigation offered is a sentence in the documentation and a policy they have to
choose. **That is a weak mitigation and calling it anything else would be false.** It is chosen
because the alternatives cost more than they buy, not because it is good.

### 3.6 D5 — No change to the sandbox's controls

**Recommendation.** This SPEC adds no import allowlist, no egress restriction and no confirmation
step, and does not propose any.

Worth stating because it is the obvious response to §4 and it is out of scope for a reason. Each of
those is a change to the sandbox's fundamental contract, would affect every turn of every session
rather than mail turns, and would be specified against `tech.md` §7.1 and §7.2 as a whole. Bundling
one into a feature SPEC is how a control gets designed to fit one use case and then constrains
every other.

**But "out of scope" is not "unnecessary".** §4 is what it is *because* those controls are absent,
and if a reader concludes from §4 that the sandbox needs screening, that reader is not wrong — they
are reading a different SPEC's requirement, and §8 item 6 records it as such rather than burying it.

---

## 4. The security accounting

Modelled on `SPEC-KEYCHAIN-001` §4, which is modelled on `tech.md` §7.3: state what is removed, what
is retained, what is added, and do not let context cancel the addition.

### 4.1 The composition, which is the actual finding

Five properties, each already documented, each already accepted:

| # | Property | Evidence | Status before this SPEC |
|---|---|---|---|
| 1 | Model-written code receives the credential as a plain module-level name in `run.py` | `params.py:327-342`, `:372-390` | Accepted — `SPEC-INPUT-001`. It is the feature |
| 2 | The sandbox has **full network egress**, by design, actively encouraged by the prompt | `tech.md` §7.2; `main.py:143-153` | Accepted — deliberate |
| 3 | There is **no static screening of generated code**: no AST inspection, no import allowlist, no denylist, no length cap, no confirmation step | `tech.md` §7.2; `main.py:447` | Accepted — documented |
| 4 | Solution memory is persistent, survives `--rm`, and is writable and poisonable by generated code running as the same uid | `product.md` §6.11; `docker-compose.yml:74-75`, `:114-115`; `Dockerfile:42-46` | Accepted — `SPEC-MEMORY-001`, §6.11 |
| 5 | Recall text from that store is injected into the prompt on attempt 1 | `main.py:1008` | Accepted — it is the feature |

**This is the first change that puts all five on the same turn.** Nothing structurally prevents a
generated script from authenticating with `imaplib` and then sending the mailbox — or the credential
— to an arbitrary host. The only thing between the user and that outcome is the model's intent and
its competence.

**The influence channel is real and it is bounded.** `product.md` §6.11 states the bound and it is
repeated exactly, not improved on: *"stored content is only ever shown to the model as text, never
executed (constraint C2), so a poisoned record can mislead the model's reasoning but cannot itself
run."* True, and it survives this SPEC. What this SPEC adds is that the reasoning being misled now
happens on a turn holding a live mail credential with unrestricted egress. A poisoned record cannot
run; it can change what does.

### 4.2 Removed, retained, added

**REMOVED — nothing.** This SPEC removes no exposure. Stated explicitly because §4 of
`SPEC-KEYCHAIN-001` had a removed column and a reader will look for one here.

**RETAINED — the credential is readable by the script, and it must be.** The script needs it to
authenticate. That is not a defect; it is the feature, it was true under `SPEC-INPUT-001` and it is
true here.

**ADDED — one thing, and it is not a mechanism:**

**The mailbox becomes a routine target of model-written code.** Every element of §4.1 predates this
SPEC and every one of them was reachable before it. What this SPEC adds is that a user will now do
this **regularly and by design**, rather than never. Frequency is the new fact. An exposure taken
once by an adventurous user and an exposure taken on every "check my mail" are the same exposure and
not the same risk.

**And one that is a mechanism, in §5: mail content enters solution memory under the default
policy.**

### 4.3 The mitigating context, and why it is not a defence

The credential is the user's own. The mailbox is the user's own. The tool is local, single-user, and
runs on the user's machine. Nobody else is exposed by this feature and there is no multi-tenant
boundary to cross.

Three reasons that is context and not a defence — the structure `SPEC-KEYCHAIN-001` §4.2 used, and
it is used again because it is right:

1. **"Their own credential" is not "their own code".** The user is not writing the script that
   receives the credential. An 8B model is, from a prompt, with recall text that another script may
   have written. Consent to the *feature* is not review of the *code*.
2. **The blast radius is not the tool.** An app password is full mailbox access, read and send-as,
   with no read-only scope (§2.6). If it leaves the machine, what is exposed is the mailbox and
   everything reachable through it — password resets included — not a CodeRunner session.
3. **"They could have done it anyway" ends every accounting.** It is true here: `imaplib` was always
   importable and egress was always open. `tech.md` §7.2 declines that argument for the memory store
   in its own words — *"This is not a privilege escalation … What is new is durability."* The same
   discipline: name the capability, name what is new, and do not let the first cancel the second.
   **Here, what is new is routineness.**

### 4.4 Honest summary

This paragraph is the requirement (U4). It goes into `README.md`, `product.md` and `tech.md` §7.2
**unsoftened**, and no documentation anywhere may state or imply the contrary.

> Account access hands your mail credential to code that a language model writes, in a sandbox with
> full outbound network access and **no screening of what that code does** — no import allowlist, no
> review step, no confirmation. The credential is an app password, which grants **full mailbox
> access, read and send**, because no read-only scope exists for it. Solution memory can be modified
> by generated code and is shown back to the model in later sessions, so a poisoned record can
> influence what a later credential-bearing turn writes.
>
> Every one of those facts was already true of this product. This feature is the first to put them
> **all on the same turn, routinely**. It adds no capability that generated code did not already
> have; what it adds is that you will now use it.
>
> Use a dedicated mail account if you can. If you cannot accept the above, do not use this feature —
> and note that not using it does not close any of the five properties above, because none of them
> were opened by it.

### 4.5 What would actually reduce this, named so it is not mistaken for unconsidered

Two things would materially change §4, and both are out of scope with their reasons in §8:

- **OAuth with a read-only scope** (§2.6, §8 item 1). It is the only thing that would narrow the
  credential itself.
- **Static screening or an import allowlist for generated code** (§3.6, §8 item 6). It is the only
  thing that would narrow what the code can do with it.

Neither is refused on the merits. Both are larger than this SPEC and both would be specified against
the sandbox contract as a whole. Recording them here means a later reader can see that §4 was
written by someone who knew what would fix it.

---

## 5. The capture-policy consequence

This section exists because the trace at §2.3 produces a result most readers will not expect, and
because the words used to describe it to the user are themselves a requirement.

### 5.1 The finding

**The app password is redacted. The mail content is not.**

`params.secret_values()` (`params.py:398-413`) builds the redaction set from declared `secret`-typed
values only. `params.redact()` (`params.py:417-431`) replaces exactly those, by substring match. At
`main.py:1061` redaction runs only under `sensitive_excluded`, and at `main.py:1103-1109`
`_capture_turn()` persists `result.stdout`.

Mail content is not a declared parameter. It is not in the set. It is not redacted. Under the
**default** policy (`settings.py:75`), a turn that prints interview-opportunity emails writes sender
addresses, subject lines and body excerpts verbatim into a store that survives `--rm`
(`docker-compose.yml:74-75`, `:114-115`), is readable by any later generated script running as
`runner` (`product.md` §6.11), and is fed back to the model as recall text (`main.py:1008`).

### 5.2 The category shift, in the words that must reach the user

**`SPEC-INPUT-001`'s capture policy was designed around credentials leaking into captured stdout.
This feature makes the payload — third-party personal correspondence — the captured thing.**

That is a change of category, not of degree, and it has a direct consequence for what the policy
names can truthfully be said to mean:

| Statement | Before | After a mail turn |
|---|---|---|
| "Under `sensitive_excluded`, my secrets are not in solution memory" | true, modulo the transform limit at `params.py:417-431` | **still true** |
| "Under `sensitive_excluded`, sensitive material from this turn was excluded" | true enough to say | **false.** The password was excluded. The mail was not |
| "Under `never`, this turn was not stored" | true | **still true** — `never` skips capture entirely (`main.py:1099-1101`) |
| "My mail is not on disk after the session" | not applicable | **false** under any policy but `never` |

**A user who chose `sensitive_excluded` will reasonably believe their mail was excluded. Only the
password was.** That sentence, or one that says the same thing as plainly, is required in
`README.md` (U5).

### 5.3 What is done about it

D4 (§3.5): document, guide, and point at `never`. Only the first is guaranteed; the second is
guidance and is labelled as guidance; the third requires the user to act. No schema bump.

**This is a weak mitigation and the SPEC says so** (§3.5). The alternatives — a new policy value, a
`schema_version` bump, or heuristic detection of mail-shaped turns — each cost more than they buy,
and `SPEC-KEYCHAIN-001` §3.4 measured why.

---

## 6. EARS requirements

All five requirement types are represented.

### 6.1 Ubiquitous — always true

| # | Requirement |
|---|---|
| **U1** | A credential for account access **shall always** reach the generated script by the `SPEC-INPUT-001` path — declared `# @param … : secret`, collected via `getpass`, spliced as a `repr()`-produced literal, and present in the redaction set. It **shall never** be read by generated code from `os.environ`. |
| **U2** | Every property established by `SPEC-INPUT-001` and `SPEC-KEYCHAIN-001` **shall always** continue to hold unchanged: literal safety, stdin untouched, `code` never reassigned before capture, redaction at three sinks, keychain eligibility keyed on `type == secret`. This SPEC changes what a script is *for*, never how a value is *handled*. |
| **U3** | **No new dependency shall be added.** `imaplib` and `email` are standard library (§2.1); `requirements.txt` is unchanged. |
| **U4** | Documentation **shall always** state §4.4's honest summary unsoftened: that generated code receives the credential, that there is no screening of that code, that an app password grants full read **and send** access with no read-only scope, and that solution memory is poisonable and is read back to the model. No text anywhere **shall** state or imply the contrary. |
| **U5** | Documentation **shall always** state §5.2's finding in the user's own terms — that mail **content** is not covered by the redaction set and that a user who chose `sensitive_excluded` had their password excluded and not their mail. Any prompt-level instruction to summarise rather than print raw bodies **shall always** be labelled as **guidance, not a control**, wherever it appears. |
| **U6** | Every figure in `verification-A1.md` **shall always** be a figure a run produced, with the variant and trial count it came from. What was not run **shall** be named as not run, not as not needed. |

### 6.2 Event-driven — WHEN … THEN …

| # | Requirement |
|---|---|
| **E1** | **WHEN** the user asks for something in an account they hold credentials for, **THEN** the model **shall** take the CODE protocol, declare the host, user and password with `# @param`, and connect over TLS — rather than routing to DIRECT or refusing. |
| **E2** | **WHEN** the model declares a mail credential, **THEN** it **shall** use `secret` as the declared type, so that one predicate continues to govern the mask (`params.py:297`), the redaction set (`params.py:408`), the `getpass` route (`main.py:823`), the policy gate (`main.py:988`) and keychain eligibility. |
| **E3** | **WHEN** a worked IMAP example is added to `SYSTEM_PROMPT`, **THEN** it **shall** be inserted below the `@param` passage (`SPEC-PROMPT-001` N3) and `SPEC-KEYCHAIN-001` N2's citation **shall** be re-verified in the same commit. |
| **E4** | **WHEN** A1 measures the pass rate of emitted IMAP code with the example present, **THEN** D1 **shall** be decided by that number, and the author's stated prior (§HISTORY, §3.2) **shall** be recorded as confirmed or overturned rather than quietly dropped. |
| **E5** | **WHEN** documentation describes this feature, **THEN** it **shall** name a dedicated mail account as the recommended configuration, and **shall** state that not using the feature closes none of §4.1's five properties. |
| **E6** | **WHEN** tests are added, **THEN** `MIN_PASSED` (`.github/workflows/ci.yml:316`) **shall** be raised to a count read from a real `junitxml` run, measured and not computed. |

### 6.3 State-driven — IF/WHILE … THEN …

| # | Requirement |
|---|---|
| **S1** | **IF** `SPEC-PROMPT-001` T3 records outcome **M-b**, **THEN** this SPEC **shall not** proceed as specified, `SPEC-MODEL-001` **shall** be opened, and this document **shall** record that it was stopped by measurement rather than abandoned. |
| **S2** | **IF** A1 measures a low pass rate for emitted IMAP code **with the worked example present**, **THEN** the `tools.py` helper contingency (D1 candidate 2) **shall** be opened — and **only** then. A helper **shall not** be added on the strength of the author's prior. |
| **S3** | **IF** a `tools.py` helper is opened, **THEN** `SPEC-PROMPT-001` T5's fix to `tools.py:90-91` **shall** already have landed. A second helper **shall not** be added to a module whose first helper still swallows its own failures (`tech.md` §8.7). |
| **S4** | **IF** the capture policy is `sensitive_excluded` or `always`, **THEN** mail content printed to stdout **shall** be captured verbatim, and the documentation **shall** have told the user so before they ran the turn — not after. |
| **S5** | **IF** the user needs their mail not to be captured, **THEN** the existing `never` policy **shall** be the answer, and it **shall** be reachable and documented without a `settings.json` schema change. |
| **S6** | **WHILE** `verification-A1.md` contains no results, D1 **shall** remain undecided and no prompt example or helper **shall** be implemented. |

### 6.4 Unwanted — shall not

| # | Requirement |
|---|---|
| **N1** | This SPEC **shall not** proceed while `SPEC-PROMPT-001` T3's gate is unrecorded or records M-b. |
| **N2** | Generated code **shall not** be instructed or expected to read `os.environ`, and no prompt text **shall** reveal that a host keychain exists. `SPEC-KEYCHAIN-001` N2, both clauses, adopted verbatim. |
| **N3** | The credential **shall not** be delivered by any path other than `# @param … : secret`. `SPEC-KEYCHAIN-001` §4.4 measured the consequence of env-direct delivery: `params.secret_values()` returns empty and `sensitive_excluded` **governs nothing at all**, silently. |
| **N4** | Documentation **shall not** describe a `tools.py` mail helper — if one is ever added — as bounding what the credential is used for. The value remains a module-level name and the script may call `imaplib`, `smtplib` or `urllib` directly (§3.2). |
| **N5** | `settings.json`'s `schema_version` **shall not** be bumped, and no key **shall** be added to it. An unknown key in a v1 file is ignored **silently** (`settings.py:216-224`); a bump is a one-way door that costs older builds their capture entirely (`settings.py:202-207`). |
| **N6** | Mail-shaped turns **shall not** be detected heuristically from parameter names or generated code in order to change policy. That is a heuristic over model output, which is the class of control `tech.md` §7.2 records as absent. |
| **N7** | The prompt **shall not** hard-code Gmail-specific behaviour. Generic IMAP with Gmail as the worked instance (D2), because §2.6's last row is a third party's product decision. |
| **N8** | `verification-A1.md` **shall not** contain placeholder figures. Empty cells, explicitly marked not-yet-run. |
| **N9** | No documentation **shall** state that mail content is redacted, excluded, or protected by any capture policy other than `never`. §5.1 is a traced fact and contradicting it in prose would be the most damaging false statement this SPEC could make. |

### 6.5 Optional — where possible

| # | Requirement |
|---|---|
| **O1** | **Where** the prompt guides the model to print derived summaries rather than raw bodies, it **should** do so — while being labelled guidance and not a control (U5). It reduces the volume of §5.1's capture on the common path and reduces nothing on any other. |
| **O2** | **Where** `/params` prints its report (`settings.py:424-436`), it **may** name the current capture policy alongside the parameters, since that is where a user asking "what happened to my data" will look. |
| **O3** | **Where** the probe records an outcome, it **should** store the model's verbatim reply and the emitted code, so that an M-a/M-c distinction can be re-made later without re-running. |
| **O4** | **Where** a user has a dedicated mail account, documentation **should** show that configuration first, since it is the only recommendation in §4 that materially changes the blast radius without new machinery. |

---

## 7. In scope

1. **A1 — the measurement.** Reuse `SPEC-PROMPT-001`'s harness. With that SPEC shipped, measure on
   the Gmail task: refusal rate, and — where a fenced block is produced — whether the emitted IMAP
   **works** against a real test mailbox. Two sub-variants: with and without a worked IMAP example.
   Recorded in `verification-A1.md`.
2. **§4's security accounting** and **§5's capture consequence**, written into the product's
   documentation. **Owed regardless of A1's outcome**, because the exposure exists whether or not
   the prompt mentions mail.
3. **`main.py` — `SYSTEM_PROMPT` only**, and only the intervention A1 selects: one worked IMAP
   example in the capability section `SPEC-PROMPT-001` created, below the `@param` passage
   (`SPEC-PROMPT-001` N3), with the summarise-don't-dump guidance labelled as guidance.
4. **Documentation:** `README.md` (§4.4 verbatim, §5.2's sentence, the `never` pointer, the
   dedicated-account recommendation); `product.md` (a new feature row, and a new §6.x exposure
   section in §6.13's shape); `tech.md` §7.2 (the composition and the capture consequence).
5. **`SPEC-PROMPT-001` T5 is a prerequisite of anything touching `tools.py`** (S3), and is recorded
   here as an inter-SPEC ordering constraint rather than assumed.
6. **`.github/workflows/ci.yml:316`** — `MIN_PASSED` raised from a measured run, if tests are added.

## 8. Out of scope

1. **OAuth, and with it any read-only mail scope.** It is the single most valuable thing this SPEC
   declines. Excluded because it needs a client secret, a browser redirect the container cannot
   perform, a token store, a refresh path, and at least one dependency — against `tech.md` §2's
   treatment of every dependency as load-bearing and `SPEC-KEYCHAIN-001` §8 item 4's refusal of new
   Python dependencies. **Declined, not unconsidered** (§4.5).
2. **Sending mail.** `smtplib` is stdlib and reachable (§2.1); this SPEC does not advertise it. An
   app password already grants send-as (§2.6), so the capability exists — advertising it is a
   separate decision with a separate accounting.
3. **Any other account type** — calendars, cloud drives, bank feeds, social APIs. IMAP is chosen
   because it is stdlib, credential-based and needs no OAuth dance. Each of the others is its own
   SPEC and most of them are OAuth, i.e. item 1.
4. **A new capture policy, a `schema_version` bump, or heuristic mail detection.** N5, N6, and
   §3.5's measured reasons.
5. **Encryption at rest for solution memory.** `SPEC-KEYCHAIN-001` §8 item 1 closed this by
   **impossibility**: the image's crypto-adjacent stdlib is `crypt`, `ssl`, `hashlib`, `hmac`,
   `secrets` — all one-way or transport-only. A stdlib-only cipher is a hand-rolled cipher, which is
   worse than none because it looks like protection.
6. **Static screening, an import allowlist, or an egress restriction for generated code.** §3.6.
   §4.5 names this as one of the two things that would actually reduce §4. It is out because it
   changes the sandbox's contract for every turn of every session and must be specified against
   `tech.md` §7.1 and §7.2 as a whole — **not because it is unnecessary**.
7. **A test mailbox in CI.** A5 is manual and not-CI **by design and from the start** (`plan.md`
   §1). Provisioning credentials into CI to test a feature whose entire accounting is about
   credential exposure would be self-defeating.
8. **Rewriting `_HTML_RESULT_RE`.** `SPEC-PROMPT-001` §8 item 2, with its reason.
9. **Retry-on-refusal, and model selection.** `SPEC-MODEL-001`, under outcome M-b.

---

## 9. Traceability

| Artefact | Location |
|---|---|
| Requirements | this file, §6 (U1–U6, E1–E6, S1–S6, N1–N9, O1–O4) |
| The gate this SPEC waits on | `.moai/specs/SPEC-PROMPT-001/verification-T3.md` §5 |
| Design decisions with costs | this file, §3 (D0–D5) |
| The prior on D1, labelled as a prior | this file, §HISTORY and §3.2 |
| The security accounting | this file, §4; the honest summary at §4.4; what would fix it at §4.5 |
| The capture-policy category shift | this file, §5; the trace at §2.3 |
| The measurement record | `.moai/specs/SPEC-ACCOUNT-001/verification-A1.md` |
| Task decomposition, critical path, risks | `.moai/specs/SPEC-ACCOUNT-001/plan.md` |
| Acceptance criteria | `.moai/specs/SPEC-ACCOUNT-001/acceptance.md` |
| The SPEC this extends | `.moai/specs/SPEC-PROMPT-001/spec.md` |
| The parameter machinery reused unchanged | `params.py:72-80`, `:184-207`, `:309-324`, `:327-342`, `:372-390`, `:398-431` |
| The capture path traced | `settings.py:75`; `main.py:1054`, `:1061`, `:1063-1065`, `:1099`, `:1103-1109` |
| The store and who can reach it | `docker-compose.yml:74-75`, `:114-115`; `Dockerfile:42-46`; `product.md` §6.11; `main.py:1008` |
| The absent controls, quoted | `tech.md` §7.2 |
| The constraints adopted verbatim | `SPEC-KEYCHAIN-001` N2 (`spec.md:840`); `SPEC-INPUT-001` N3, N7 |
| The schema decision and its measured reasons | `SPEC-KEYCHAIN-001` §3.4; `settings.py:202-207`, `:216-224` |
| Explicitly not amended | `requirements.txt` (U3); `settings.json` schema (N5); `docker-compose.yml`; the `@param` passage (N2) |
| Documentation to be written | `README.md`; `product.md` §4 and a new §6.x; `tech.md` §7.2 |
| Project context | `.moai/project/product.md`, `.moai/project/structure.md`, `.moai/project/tech.md` |

| Requirement group | Primary acceptance criteria |
|---|---|
| N1, S1 | **AC-GATED** |
| U6, S6, N8, E4 | **AC-MEASURE-A1** |
| S2, S3, §3.2 | **AC-D1** |
| U1, U2, E1, E2, N2, N3 | **AC-CRED** |
| U4, E5, §4 | **AC-EXPOSE** |
| U5, S4, S5, N9, §5 | **AC-CAPTURE** |
| U3, N5, N6, N7 | **AC-NODEP** |
| §7 item 1, A5 | **AC-ROUNDTRIP** |
| E6 | **AC-FLOOR** |
