# Crypto Market Pulse — single archive handoff

Read `project/README.md`, `project/docs/SPEC.md`, `project/docs/RUN_AND_DEBUG_GUIDE.md`, and `project/docs/VALIDATION_REPORT.md`.

The directory `project/` contains the complete source, tests, SQL, CI, dashboard, operator manual, Jupyter workbooks and Weather DFE reference.
`handoff/crypto-market-pulse-offline.bundle` contains staged Git history: bootstrap `main` + `feat/crypto-market-pulse-mvp`.

IMPORTANT: GitHub connector writes to `dataengy/crypto-market-pulse` failed with `403 Resource not accessible by integration`. No code was pushed to GitHub. See `project/docs/GITHUB_PUBLISHING.md` for non-destructive instructions to publish once authenticated.

Offline tests: 18 passed; the first Jupyter notebook executed. Redpanda/ClickHouse, PySpark, Beam, and cloud E2E remain unverified.
