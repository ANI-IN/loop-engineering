# Module: Loop Engineering - Assignment 3: Event loop, starter files

The starter is the complete working class system for Section 3: Event loop, with nothing removed.
This assignment's code goes in `platform/src/datapilot/loop3_events/extension.py`. The router reads
its table `JOB_QUEUES` and the scheduler calls its `schedule()` on every start; both are empty, so
class runs are unchanged. The worker calls `run_job` only for a job the table names. Each place to
fill is marked `# EXTENSION POINT, TODO K (event-loop-K)`, and each function raises
`NotImplementedError` with a one-line hint.

| Extension point | What you fill | Who calls it | Step |
|---|---|---|---|
| `event-loop-1` | `schedule`, `anomaly_event_id`, `request_anomaly_check` | the scheduler, the check | 6 |
| `event-loop-2` | `measure`, `is_anomaly`, `alert_text`, `publish`, `run_job` | the worker | 3 to 6 |
| `event-loop-3` | `JOB_QUEUES`: the router table entry for the job | the router | 6 |

A job event is a `digest.requested` event whose payload names the job; the module's docstring
gives its fields. The router is a deterministic table, deliberately not an agent. Work through the
points in the order of the [assignment steps](../README.md#step-by-step), and run
`make check-assignment NAME=event-loop` after each one. Thresholds go in `pack.yaml`, never in code.
