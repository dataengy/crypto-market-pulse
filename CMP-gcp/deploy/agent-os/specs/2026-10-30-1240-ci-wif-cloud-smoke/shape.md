# CI cloud smoke via WIF — Shaping Notes

## Scope
- **GCP-C04 (CI part):** GitHub Actions authenticates with WIF, no keys
- **GCP-C09:** a `workflow_dispatch`-only workflow runs the [cloud smoke](../2026-10-30-1220-cloud-smoke-verification/plan.md) and uploads the evidence

## Decisions
**WIF mode**
- Options: (a) direct WIF, the principal gets the roles itself; (b) WIF through `smoke-sa`.
- **Choice: (b).** The laptop already impersonates `smoke-sa` (spec 2), so one IAM surface is tested twice. Some APIs also have limits with direct federation ([WIF docs](https://cloud.google.com/iam/docs/workload-identity-federation), verified 2026-10-30).
- See [ADR-0003](../../../docs/adr/0003-keyless-auth-wif-impersonation.md).

**Restriction**
- The provider has `attribute_condition = assertion.repository == 'dataengy/crypto-market-pulse'`, and the binding uses `principalSet …/attribute.repository/<repo>`.
- No branch restriction, so a feature branch can run the smoke. `smoke-sa` can only touch `smoke`. `ponytail:` add `assertion.ref` once anything beyond smoke uses WIF.

**Trigger**
- `workflow_dispatch` only, never `pull_request`, because forks must not mint tokens and every run costs money.
- `concurrency: cmp-gcp-cloud-smoke`, `cancel-in-progress: false`.

**IDs in CI**
- The WIF provider name, SA email and project ID become GitHub **repository variables**, not secrets: they are identifiers. They are set from `terraform output` with the `dataengy` gh account.
- CI has no `.env.secrets`, so the local lane's loader must accept env that is already set (`load_dotenv(override=False)`) when the file is absent.
- **Coordinate with [L02](../../../../../docs/plans/gcp/tasks.md#gcp-l02).**

**Workflow location**
- `.github/workflows/cmp-gcp-cloud-smoke.yml` at the repo root, which GitHub requires. Written only in implementation; push and PR only after the user confirms.

## Context
- **Visuals:** [architecture.md](../../../docs/design/architecture.md).
- **References:** [references.md](references.md).
- **Product alignment:** roadmap phase 5. Depends on [L13](../../../../../docs/plans/gcp/tasks.md#gcp-l13), the hermetic CI.

## Standards Applied
See [standards.md](standards.md).
