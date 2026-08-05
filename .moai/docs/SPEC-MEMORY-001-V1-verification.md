# V1 Verification Result — SPEC-MEMORY-001

**Question**: Does Docker propagate image-directory ownership into an empty named volume,
so that chown-before-`USER runner` in the Dockerfile genuinely fixes the root-owned-volume
trap (AC-5)?

**Verdict: CONFIRMED. T12 as designed is correct. No fallback needed.**

Run 2026-08-02 against `python:3.11-slim`, non-root `runner` (uid/gid 1000), empty named volumes.

## Case A — mount path EXISTS in the image and is chowned to `runner`

```dockerfile
FROM python:3.11-slim
RUN useradd -m -s /bin/bash runner \
 && mkdir -p /home/runner/.coderunner \
 && chown -R runner:runner /home/runner/.coderunner
USER runner
```

```
$ docker run --rm -v v1-empty:/home/runner/.coderunner v1-voltest \
    sh -c 'id -un; ls -ldn /home/runner/.coderunner; touch .../probe'
runner
drwxr-xr-x 2 1000 1000 4096 /home/runner/.coderunner
WRITE: OK
```

Docker copied the image directory's ownership (1000:1000) into the empty volume at
initialization. `runner` can write. `memory.db` opens read-write.

## Case B (control) — mount path does NOT exist in the image

```
$ docker run --rm -v v1-ctl:/home/runner/.nosuchdir v1-voltest \
    sh -c 'ls -ldn /home/runner/.nosuchdir; touch .../probe'
drwxr-xr-x 2 0 0 4096 /home/runner/.nosuchdir
touch: cannot touch '/home/runner/.nosuchdir/probe': Permission denied
WRITE: DENIED
```

Volume created **root-owned**. `runner` cannot write. This is exactly the failure mode
`manager-spec` predicted: the database would never open, the graceful-degradation path would
swallow the error, and the feature would appear to work while being permanently inert.

## Consequences for the SPEC

- **T12 is load-bearing and correct as specified.** The `mkdir -p` + `chown` MUST occur in
  `Dockerfile` BEFORE `USER runner` (`Dockerfile:28-30`). Adding the volume to
  `docker-compose.yml` without the Dockerfile change produces Case B.
- **The entrypoint-time-`mkdir` fallback contemplated in V1 is not required.** Drop it.
- **AC-5 must assert ownership, not merely writability** — `ls -ldn` showing 1000:1000, plus an
  explicit assertion that the degradation path was NOT taken. A test that only checks "the DB
  opened" would pass in Case A and would also pass in Case B if degradation is silent.

---

# V2 Verification Result

**Question**: Does `client.embed(...)["embeddings"][0]` work on the oldest client the
`requirements.txt:2` floor permits (`ollama==0.3.0`), justifying leaving that floor untouched?

**Verdict: CONFIRMED — and subscript access is not merely safe, it is the ONLY portable form.**

Inspected the `ollama-0.3.0-py3-none-any.whl` artifact directly.

## The floor is valid

```
ollama/_client.py:250   def embed(self, model: str = '', input: Union[str, Sequence[AnyStr]] = '', ...)
ollama/_client.py:273   def embeddings(...)          # the older, single-input endpoint
ollama/_client.py:668   async def embed(...)
```

`embed()` exists at the floor. `requirements.txt:2` (`ollama>=0.3.0`) **stays untouched**.

## Why subscript is mandatory, not optional

The response type changed shape across the permitted range:

| Version | Response type | `resp["embeddings"]` | `resp.embeddings` |
| --- | --- | --- | --- |
| `0.3.0` | `TypedDict` (`_types.py:12` onward — plain `dict` at runtime) | works | **AttributeError** |
| `0.6.2` | `SubscriptableBaseModel` (pydantic) | works | works |

So the attribute form that reads more naturally would **crash on the oldest supported client**.
Subscript is the only access pattern valid across the whole `>=0.3.0` range.

Specify exactly, with no fallback branch:

```python
resp = client.embed(model=EMBED_MODEL, input=text, keep_alive="10m")
vector = list(resp["embeddings"][0])
```

This also matches existing house style — `main.py:144` already duck-types the chat stream the
same way (`chunk.get("message", {}).get("content", "")`).

**Consequence for the SPEC**: T5 must state the subscript requirement and the reason. A reviewer
who "tidies" it to attribute access would silently break every environment resolving below 0.4.0,
and the failure would land in `recall.py`'s broad `except` — surfacing as permanent silent
degradation, exactly the R7 failure mode.

---

---

# V3 Verification Result

**Question**: What is the real cold/warm embed latency for `nomic-embed-text:latest`, so risk R1
carries a measured number and `keep_alive` is set on evidence?

**Verdict: latency is a non-issue. But the measurement exposed a serious defect in the
`min_similarity = 0.75` default.**

Pull: **274 MB in 12.3s** into `coderunner_ollama_data` (matches the SPEC's stated size).
Measured 2026-08-02 inside the `coderunner-ai:latest` image over the compose network, model
force-unloaded via `ollama stop` immediately before the cold call.

## Latency — R1 resolved

| Metric | Value |
| --- | ---: |
| Cold (first call after unload) | **906.4 ms** |
| Warm mean (12 calls) | **49.2 ms** |
| Warm median | **40.3 ms** |
| Warm min / max | 22.3 / 153.9 ms |

`DIM 768` — confirms the dimension assumed by the cosine-scan benchmark, so the 13 ms @ 500
records figure stands unmodified. `SUBSCRIPT_OK True` on `ollama 0.6.2`, corroborating V2.
`keep_alive="10m"` accepted.

**R1 is closed.** A warm embed at ~40 ms is invisible beside a multi-second LLM stream. The
sub-second cold load is paid at most once per 10-minute window, and the empty-store
short-circuit (M3) means a cold start pays **zero**. No mitigation beyond `keep_alive` is needed.

## The threshold defect — action required

Cosine similarity over L2-normalised vectors, five representative task strings:

| Pair | Similarity |
| --- | ---: |
| **"weather in Seoul in Celsius" vs "temperature in Busan right now"** | **0.7540** |
| "weather in Seoul" vs "list vs tuple" | 0.2973 |
| "weather in Seoul" vs "scrape HN headlines" | 0.3571 |
| "weather in Seoul" vs "200th Fibonacci" | 0.3362 |
| "scrape HN headlines" vs "200th Fibonacci" | 0.3954 |

The first row **is AC-2** — the SPEC's canonical reuse scenario, verbatim. It scores **0.7540
against a 0.75 threshold: a margin of 0.004.**

This is the worst possible placement. The default sits essentially *on top of* the one worked
example the specification uses to demonstrate the feature. Consequences:

1. **AC-2 is flaky by construction.** A 0.5% shift from rephrasing, an `ollama` update, or a
   model re-quantisation flips a passing acceptance test to failing with no code change.
2. **The feature would appear broken in normal use.** Genuine paraphrases would land just under
   the line and inject nothing, and — because a miss is silent by design — the user would see a
   memory that simply never fires.

The measured distribution argues for a much lower default. Unrelated pairs cluster at
**0.297–0.395**; the related pair sits at **0.754**. The gap between noise and signal is enormous,
and *nothing* occupies 0.40–0.75.

**Recommendation: `CODERUNNER_MEMORY_MIN_SIMILARITY = 0.65`.** That leaves 0.255 of headroom above
the highest unrelated pair and 0.104 below the true positive — comfortable margin on both sides,
where 0.75 has margin on neither.

Caveat on scope: five task strings are an indication, not a distribution. `nomic-embed-text` also
publishes `search_query:` / `search_document:` task prefixes which were **not** used here and
would shift absolute scores; adopting them is a separate decision. The revisit-after-T16 note in
the SPEC stands regardless.

