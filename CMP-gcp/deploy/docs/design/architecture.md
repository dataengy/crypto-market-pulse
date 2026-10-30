# Architecture — CMP-gcp cloud

The `live` and `smoke` envs are identical stacks (Terraform `for_each`). Only `live` has a hosted producer; only `smoke` is used by the laptop and CI. Dashed boxes are optional, gated, and off by default.

```mermaid
flowchart LR
  subgraph ext[External]
    BY[Bybit V5 WS<br/>publicTrade]
    GH[GitHub Actions<br/>dataengy/crypto-market-pulse]
    LT[Laptop<br/>owner ADC]
  end
  subgraph gcp[GCP project, region deploy.run.region / profiles.cloud.location]
    SCH[Cloud Scheduler<br/>paused] -->|run.invoker| JOB[Cloud Run job<br/>producer-sa, max-seconds]
    AR[(Artifact Registry)] -.image.-> JOB
    BY --> JOB
    JOB -->|publish| TL[topic live]
    TL --> SL[BQ subscription live] --> RL[(raw live<br/>part. publish_time)]
    SL -.write errors.-> DL[DLQ topic + pull sub]
    RL --> VL[views: dedup / 1m / latest / dq]
    VL --> LS[Looker Studio]
    TS[topic smoke] --> SS[BQ subscription smoke] --> RS[(raw smoke)] --> VS[views smoke]
    SS -.-> DS[DLQ smoke]
    WIF[WIF pool/provider<br/>repo condition] --> SSA[smoke-sa]
    DF[[Dataflow batch parity<br/>optional, walltime cap]] -.-> VS
    BUD[Billing budget alerts]
  end
  LT -->|terraform apply as owner| gcp
  LT -->|impersonate smoke-sa: produce fixture + assert FX| TS
  GH -->|OIDC → WIF → smoke-sa| TS
  SSA -.reads.-> VS
```

| Concern | Where |
|---|---|
| Ingest choice | [ADR-0001](../adr/0001-bq-subscription-over-dataflow.md) |
| Producer region | [ADR-0002](../adr/0002-cloud-run-job-region.md) |
| Identities | [ADR-0003](../adr/0003-keyless-auth-wif-impersonation.md) |
| Resource list | [terraform-foundation plan, Task 3](../../agent-os/specs/2026-10-30-1200-terraform-foundation/plan.md) |
| Local twin (emulators, shim, DirectRunner) | [01-local-dev-debug.md](../../../../docs/plans/gcp/01-local-dev-debug.md) |
