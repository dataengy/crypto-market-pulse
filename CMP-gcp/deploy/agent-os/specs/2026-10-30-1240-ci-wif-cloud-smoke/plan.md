# CI cloud smoke via WIF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A manually triggered GitHub Actions workflow authenticates to GCP through WIF as `smoke-sa`, runs `just deploy::smoke`, and uploads the evidence log.

**Architecture:**
- The WIF pool, provider and SA binding already exist (spec 1).
- Repo variables hold the IDs.
- The workflow is checkout → uv → `google-github-actions/auth@v3` → just recipe → upload artifact.

**Tech Stack:** GitHub Actions, `google-github-actions/auth@v3`, `astral-sh/setup-uv`, `extractions/setup-just`, gh CLI (account `dataengy`).

**Spec:** [shape.md](shape.md) · tasks: [GCP-C04](../../../../../docs/plans/gcp/tasks.md#gcp-c04) (CI part), [GCP-C09](../../../../../docs/plans/gcp/tasks.md#gcp-c09)

## Global Constraints
- Triggers: `workflow_dispatch` only. `permissions: { contents: read, id-token: write }` on this workflow only.
- Third-party actions are pinned to a full commit SHA, with the version tag in a comment.
- No `credentials_json` and no secrets for GCP. Only repo variables: `GCP_PROJECT_ID`, `GCP_WIF_PROVIDER`, `GCP_SMOKE_SA`.
- `gh` calls use `GH_TOKEN=$(gh auth token --user dataengy)`. Never `gh auth switch`.

## Review Focus
1. **Workflow started from a fork or a PR:** impossible, because there is no PR trigger. The verify step checks `on:` for exactly `workflow_dispatch`.
2. **A repo variable is missing:** the first step fails naming the variable (`test -n "${{ vars.X }}" || { echo "missing repo variable X"; exit 1; }`).
3. **The loader requires `.env.secrets` to exist:** the CI run fails at produce. Fixed in the local lane (L02), and checked by this plan's dry run.
4. **WIF propagation delay (up to 5 min after apply):** the first run may fail with `PERMISSION_DENIED`. Retry once after 5 minutes before debugging ([auth README](https://github.com/google-github-actions/auth/blob/main/README.md)).
5. **Two smoke runs at once:** the concurrency group serializes them. Both would still pass, because dedup by `event_id` keeps FX the same.

---

### Task 1: Save spec documentation
- [x] Done (2026-10-30).

### Task 2: Repo variables from Terraform outputs
- [ ] **Step 1:** Recipe `deploy::gh-vars` sets each variable as the `dataengy` account: `GH_TOKEN=$(gh auth token --user dataengy) gh variable set GCP_WIF_PROVIDER --repo <deploy.wif.repository> --body "$(terraform -chdir=terraform output -raw wif_provider_name)"`. Do the same for `GCP_SMOKE_SA` and `GCP_PROJECT_ID`.
- [ ] **Verify:** `GH_TOKEN=… gh variable list --repo <repo>` shows the 3 variables.

### Task 3: Workflow file (GCP-C09)

**Files:** Create: `.github/workflows/cmp-gcp-cloud-smoke.yml` (repo root)

**Interfaces:**
- Consumes: `just deploy::smoke` (spec 3). It reads `GOOGLE_CLOUD_PROJECT` from env and impersonation from ADC set by the auth action.
- Produces: the artifact `cmp-gcp-smoke-evidence` (`CMP-gcp/.tmp/evidence/*.log`).

- [ ] **Step 1:**
  - `on: workflow_dispatch`, plus `permissions` and `concurrency` as in the Global Constraints
  - job env `GOOGLE_CLOUD_PROJECT: ${{ vars.GCP_PROJECT_ID }}` and `CMP_PROFILE: cloud`
  - steps: check the vars → checkout → setup-uv → setup-just → `google-github-actions/auth@v3` (`workload_identity_provider: ${{ vars.GCP_WIF_PROVIDER }}`, `service_account: ${{ vars.GCP_SMOKE_SA }}`) → `just -f CMP-gcp/justfile deploy::smoke` → `actions/upload-artifact` with `if: always()`
- [ ] **Step 2:** In CI the recipe must **not** set `CLOUDSDK_AUTH_IMPERSONATE_SERVICE_ACCOUNT`, because the auth action already yields `smoke-sa`. The recipe sets it only when `CI` is unset (a one-line `if` with a `ponytail:` comment).
- [ ] **Verify (local):**
  - `actionlint .github/workflows/cmp-gcp-cloud-smoke.yml` reports nothing, if actionlint is installed (otherwise note that it was skipped)
  - `grep -E '^on:' -A2` shows only `workflow_dispatch`
  - `grep -c credentials_json` is `0`

### Task 4: First CI run (user-gated push)
- [ ] **Step 1:** The user confirms the push of the feature branch (`feat/<topic>`, per the git workflow rule). Then: `GH_TOKEN=… gh workflow run cmp-gcp-cloud-smoke.yml --repo <repo> --ref <branch>`.
- [ ] **Verify:** `gh run watch` ends with `completed success`. `gh run download -n cmp-gcp-smoke-evidence` contains a C05 log with `PASS` and the FX row. Run `gcloud logging read 'protoPayload.authenticationInfo.principalEmail="<smoke_sa>"' --freshness=1h --limit=5` to show the CI calls. BigQuery data-access logs are on by default; for Pub/Sub, publishing needs Data Access logs enabled, and the plan does not turn those on.
