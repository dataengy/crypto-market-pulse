# Workbook 5 — Failure injection, observability and acceptance evidence

This is an **experiment log template**, not proof that any runtime has passed. Use only dedicated project-owned services and synthetic fixtures. Do not inject faults into a shared or production service.

## Preparation

- [ ] Document UTC timestamp, Git SHA, local OS/architecture, Python/Java/Spark/Beam versions.
- [ ] Identify Docker context, Colima profile and project-owned service/container names.
- [ ] Verify `CMP_*` endpoints point to disposable test resources; no private credentials printed.
- [ ] Save baseline raw/unique counts, Kafka offsets, fixture file checksum and reference OHLCV.

## Experiments

| ID | Failure | Procedure (in your isolated test setup) | Success criterion | Observed / evidence |
| --- | --- | --- | --- | --- |
| F1 | Duplicate replay | Publish fixture twice | Raw grows; dedup and minute mart stable | NOT RUN |
| F2 | Out-of-order trade | Shuffle fixture, preserve event times | Open/close ordered by `(time,id)` | NOT RUN |
| F3 | Consumer crash | Crash after sink insert/before offset commit | Replay harmless in dedup mart | NOT RUN |
| F4 | Consumer pause | Pause own consumer; continue bounded producer | Lag rises, then falls within retention | NOT RUN |
| F5 | Poison message | Send invalid JSON to test topic | No silent ACK, failure actionable | NOT RUN |
| F6 | WS disconnect | Stop producer network only in scratch environment | Retry/backoff observed; source gap documented | NOT RUN |
| F7 | Late event | Add earlier timestamp than current window | Defined correction/drop policy visible | NOT RUN |
| F8 | Schema drift | Add optional and invalid fields separately | Version/validation response documented | NOT RUN |
| F9 | Cross-engine parity | Apply same fixture in CH, Spark, Beam and BQ | Expected OHLCV/VWAP equivalent at chosen precision | NOT RUN |
| F10 | Dashboard staleness | Pause ingestion and observe latest event time | Displayed age grows, alerts truthful | NOT RUN |

## Measurements (fill in; no assumed numbers)

- Producer event throughput (`events/s`): ____
- Consumer throughput (`events/s`): ____
- Kafka consumer lag (partition-offset based): ____
- Source-to-receive latency p50/p95 (`ms`): ____
- Receive-to-sink latency p50/p95 (`ms`): ____
- Sink-to-dashboard latency p50/p95 (`ms`): ____
- Unique IDs / raw events / duplicate ratio: ____ / ____ / ____
- Spark batch duration and state rows: ____
- Beam late-event correction/dropped count: ____
- Test runtime and cost estimate (cloud-only): ____

## Run record

```text
UTC timestamp:
Git SHA:
Environment + versions:
Project-owned endpoint (non-secret):
Exact command:
Expected result:
Actual result:
Logs/artifacts (redacted):
Status: PASS / FAIL / NOT RUN
Follow-up fix/issue:
```

**Acceptance rule:** do not promote a step or profile to READY without a captured run log and expected/actual comparison. Offline unit tests and a successful `docker compose up` are not substitutes for end-to-end verification.
