# CMP-gcp/deploy — GCP cloud deploy & test (spec-driven)

This folder holds the specs, ADRs and runbooks for the **cloud** half of the GCP lane: GCP-C01…C11 in [tasks.md](../../docs/plans/gcp/tasks.md). The **local** half (GCP-L*, the emulators, `CMP-gcp/src`, `config/`, SQL, the producer) is owned by the local lane in `CMP-gcp/`. Cloud work starts only after the local gate [GCP-L09](../../docs/plans/gcp/tasks.md#gcp-l09) passes.

Status (2026-10-30): **specs only**. No implementation code, nothing applied, no cloud resources.

## Method
- **Agent OS v3.0** (Builder Methods), project layout hand-authored. The base install (`~/agent-os`, `project-install.sh`) and its `.claude/commands/agent-os/` were not installed, because they write outside this folder. Layout source: [agent-os `_autodocs`](https://github.com/buildermethods/agent-os/blob/main/_autodocs/types.md) (`config.yml version: 3.0`, checked 2026-10-30 via Context7).
  - `agent-os/product/`: [mission](agent-os/product/mission.md), [roadmap](agent-os/product/roadmap.md), [tech-stack](agent-os/product/tech-stack.md)
  - `agent-os/standards/`: [index.yml](agent-os/standards/index.yml) plus one file per standard
  - `agent-os/specs/YYYY-MM-DD-HHMM-<slug>/`: `plan.md`, `shape.md`, `standards.md`, `references.md`
  - **Deviation:** a spec's `standards.md` *links* the standards instead of copying their full text (link instead of copy).
- **superpowers:**
  - `shape.md` is the brainstorming record: the options and the pick.
  - `plan.md` follows `writing-plans`: header, Global Constraints, Review Focus, tasks.
  - Every task ends with a `verification-before-completion` step (a command plus its expected evidence).
- **ponytail:** the smallest complete change.
  - Terraform reads `config.yaml` directly with `yamldecode`, so there is no tfvars generator.
  - Views come from the local lane's `sql_apply.py`, not from Terraform.
  - No always-on compute.

## Specs (run in this order)
| # | Spec | Tasks |
|---|---|---|
| 1 | [terraform-foundation](agent-os/specs/2026-10-30-1200-terraform-foundation/plan.md) | GCP-C01, C02 (incl. SA + WIF resources), C11 (recipe) |
| 2 | [pubsub-bq-subscription](agent-os/specs/2026-10-30-1210-pubsub-bq-subscription/plan.md) | GCP-C03, C04 (laptop impersonation) |
| 3 | [cloud-smoke-verification](agent-os/specs/2026-10-30-1220-cloud-smoke-verification/plan.md) | GCP-C05 |
| 4 | [hosted-producer](agent-os/specs/2026-10-30-1230-hosted-producer/plan.md) | GCP-C06, C07, C08 |
| 5 | [ci-wif-cloud-smoke](agent-os/specs/2026-10-30-1240-ci-wif-cloud-smoke/plan.md) | GCP-C04 (CI part), C09 |
| 6 | [dataflow-parity-timeboxed](agent-os/specs/2026-10-30-1250-dataflow-parity-timeboxed/plan.md) | GCP-C10 (optional) |

## Docs
- ADRs:
  - [0001 BigQuery subscription over Dataflow](docs/adr/0001-bq-subscription-over-dataflow.md)
  - [0002 Cloud Run job region](docs/adr/0002-cloud-run-job-region.md)
  - [0003 Keyless auth](docs/adr/0003-keyless-auth-wif-impersonation.md)
- Design: [architecture.md](docs/design/architecture.md)
- Runbooks: [deploy-verify.md](docs/runbooks/deploy-verify.md), [teardown.md](docs/runbooks/teardown.md)

## Where implementation will go (planned, not created)
| Path | Owner |
|---|---|
| `CMP-gcp/deploy/terraform/*.tf`, `CMP-gcp/deploy/justfile`, `CMP-gcp/deploy/producer.Dockerfile` | this lane |
| `CMP-gcp/config/config.yaml` (new `deploy:` section) | shared with the local lane; coordinate before editing |
| `CMP-gcp/justfile` (one line: `mod deploy`) | shared with the local lane; coordinate before editing |
| `.github/workflows/cmp-gcp-cloud-smoke.yml` | GitHub requires workflows at the repo root |
