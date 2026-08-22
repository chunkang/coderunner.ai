# ==============================================================================
#  CodeRunner.AI  ::  the probe harness
# ------------------------------------------------------------------------------
#  Author  : Chun Kang <ck@strpy.com>
#  Project : SPEC-PROMPT-001, task T1
#
#  This package is the project's FIRST behavioural instrument of any kind. It
#  drives a real model against a real prompt variant and records what routing
#  decision the model made, using the production predicate rather than a copy of
#  it.
#
#  IT IS NOT A TEST SUITE AND IT MUST NEVER BECOME ONE. pytest.ini sets
#  `testpaths = tests`, so nothing in here is ever collected. That is
#  deliberate: .github/workflows/ci.yml asserts `skipped == 0`, so a
#  model-dependent test placed under tests/ would either skip on a GitHub runner
#  (red pipeline) or block forever waiting for a model that is not there. The
#  structure of this package IS gated, by tests/test_probe.py, which runs fully
#  offline against a fake client and carries no importorskip and no marker.
#
#  It is also NOT copied into the image (Dockerfile:43). The product never
#  imports it.
# ==============================================================================
