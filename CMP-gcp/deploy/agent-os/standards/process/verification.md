# Verification before completion

This is superpowers `verification-before-completion`, applied to cloud work.

- No "done", "works" or "passes" without **fresh output from this session**. Every task in a `plan.md` ends with a `Verify:` step that gives a command and the exact evidence expected.
- Evidence goes to `CMP-gcp/.tmp/evidence/<YYYYMMDD-HHMM>-<task-id>.log`, which is gitignored. Each log has the command, its output, the git SHA and the project ID with the last 4 characters redacted.
- **Fixture assertion (FX)** in the `smoke` env: BTCUSDT 2026-10-30 10:00 UTC gives `trade_count=4, volume=0.45, open_price=70000, high_price=70010, close_price=69990`. A rerun must leave these unchanged while the raw count doubles.
- **Gated steps** stop and wait for the user's explicit OK in this conversation:
  - linking billing
  - `terraform apply` or `destroy`
  - the first image build
  - unpausing the Scheduler
  - any Dataflow launch
  - `git push` or a PR
- A failure is reported with its evidence and the matching failure-mode row from [deploy-verify.md](../../../docs/runbooks/deploy-verify.md#failure-modes). Never retry by widening IAM or switching on defaults.
