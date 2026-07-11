# workflow-automation

A small n8n/Zapier-style workflow automation engine: declarative YAML workflows,
DAG-ordered execution, `{{steps.x.output.y}}` templating between steps, and a
SQLite run-history audit trail.

Built as a portfolio piece modeled on real workflow-automation job specs
(webhook/schedule triggers, HTTP actions, conditional branches, run history).

## Architecture

```
src/workflow_automation/
  models.py       # StepDef/WorkflowDef (frozen, validates the DAG at construction —
                    # duplicate ids, unknown deps, self-deps are unrepresentable)
  templating.py     # resolves {{steps.<id>.output.<path>}} — no eval(), just dict/list walks
  engine.py          # topological sort + execute in order, stops on first failure,
                       # cascades SKIPPED through dependents of a skipped/failed step
  loader.py            # YAML/JSON dict -> validated WorkflowDef
  storage.py             # SQLite run-history (every run recorded, including failures)
  steps/
    base.py                # Step protocol — one new file per step type, engine untouched
    http_request.py          # network call is injected (HttpCaller callable)
    transform.py               # builds a named output from already-resolved values
    condition.py                 # fixed operator set (==, !=, <, >, <=, >=) — no eval()
    delay.py                       # sleep is injected
  http_caller.py                    # the one file that imports httpx (production only)
  cli.py                              # validate / run / list-runs
tests/                                 # no real network or real sleep — everything injected
examples/httpbin_status_check.yaml       # a real workflow that hits a live API
```

**Design choices, and why:**

- **The DAG is validated at construction, not at run time.** `WorkflowDef.__post_init__`
  rejects duplicate step ids, dependencies on unknown steps, and self-dependencies
  before the workflow object can even exist. `engine.topological_order()` still
  detects cycles (which per-step validation can't catch) and raises
  `CyclicWorkflowError` rather than looping forever.
- **No `eval()` anywhere, on purpose.** Templating (`templating.py`) only ever walks
  a dict/list tree by dotted path. Conditions (`condition.py`) only ever apply one
  of six fixed comparison operators. A workflow YAML file is data, never code —
  this is what keeps a user-authored workflow file from becoming an arbitrary
  code-execution vector.
- **Every Step's real dependency is injected.** `HttpRequestStep` takes an
  `HttpCaller` callable, `DelayStep` takes a `sleep` callable — production wires
  real `httpx`/`asyncio.sleep`, tests wire fakes. No test needs the network or
  needs to actually wait.
- **A `Step` instance is shared across every workflow step of its type**, so it
  cannot know which DAG node is currently executing — the engine always re-stamps
  `StepResult.step_id` from the actual `StepDef`, never trusting what a `Step`
  itself returns (a real bug caught during self-review: results all reported the
  constructor's placeholder id instead of the actual step id).
- **A failed or unmatched step doesn't just vanish downstream steps — it marks
  them `SKIPPED` explicitly** and they still appear in the run's step-by-step
  results and get persisted, so a run's audit trail always accounts for every
  step that was supposed to happen, not just the ones that did.

## Bugs found and fixed via self-review

**`StepResult.step_id` was reporting the wrong id.** Each `Step` (e.g.
`ConditionStep`) is constructed once and shared across every workflow step of that
type — the very first version of this project set a `step_id` on the *Step
instance itself* at construction time, so a workflow with two `condition` steps
would have both results report the same wrong id. Caught by a failing test
(`test_condition_false_skips_dependents` — the expected step id was a `KeyError`)
before any external report. Fixed by removing per-instance ids entirely and having
the engine always stamp `StepResult` with the real `StepDef.id` from the DAG.

## Install & run

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest tests/ -q                              # 24 tests, no network
.venv/bin/workflow-automation validate examples/httpbin_status_check.yaml
.venv/bin/workflow-automation run examples/httpbin_status_check.yaml --db runs.db
.venv/bin/workflow-automation list-runs --db runs.db
```

## Status

Four step types (HTTP request, transform, condition, delay), DAG validation and
execution, templating between steps, and run-history persistence are implemented
and verified both by 24 unit tests (fully offline) and by actually running the
example workflow against a live HTTP endpoint. Not yet implemented: a scheduler
for cron/webhook triggers (currently `run` is invoked manually or by an external
cron job) and a loop/iteration step type.
