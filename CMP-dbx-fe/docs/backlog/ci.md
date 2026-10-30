# DBX-B7 — CI

**Goal:** every push runs the checks that need no cloud. ← [tasks](../../../docs/plans/dbx-fe/tasks.md#dbx-b7)

**Steps**
- [ ] `.github/workflows/cmp-dbx-fe.yml` (paths: `CMP-dbx-fe/**`): setup-uv → `uv sync` → `just verify` (build-sync + unit) → `uv run pytest -m spark` (Java 17 via setup-java; cache `~/.ivy2`)
- [ ] Optional job (`workflow_dispatch`): `docker compose up -d --wait` → `just it` → `just minilake-smoke`
- [ ] Optional: `databricks bundle validate` with an OIDC/service-principal secret (needs a non-Free workspace or a user token, so manual only)

**Acceptance:** green on the PR; the Spark job is under 5 min with a warm ivy cache.
