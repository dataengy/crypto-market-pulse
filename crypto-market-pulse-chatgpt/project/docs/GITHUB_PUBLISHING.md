# Publish verified stages to dataengy/crypto-market-pulse

## Why the archive includes an offline Git bundle

The GitHub connector could read the repository, but both attempted writes received **403 Resource not accessible by integration**. The repository may need renewed/expanded GitHub App **Contents: write** permission. Nothing has been pushed by ChatGPT. The offline Git bundle stores Conventional Commits grouped by implementation readiness.

**Do not force-push**, replace unrelated branches, or reset your checkout. Verify owner/remotes and permission first. The desired destination is `https://github.com/dataengy/crypto-market-pulse`.

## One-time import into an empty target repo (preferred)

After extracting this one ZIP, the local file `handoff/crypto-market-pulse-offline.bundle` is a valid Git bundle containing branches `main` and `feat/crypto-market-pulse-mvp`.

```bash
# On your Mac, outside any unrelated working tree:
gh auth status -h github.com
# Re-authenticate through the browser if necessary: gh auth login -h github.com

git clone ./handoff/crypto-market-pulse-offline.bundle crypto-market-pulse-staging
cd crypto-market-pulse-staging
git branch -a

git remote rename origin offline-bundle
git remote add origin https://github.com/dataengy/crypto-market-pulse.git
git ls-remote origin
# ONLY if the remote repo really has no commits:
git push origin main
git push -u origin feat/crypto-market-pulse-mvp
# Optionally, after confirming ownership, branch and diffs:
gh pr create --draft --base main --head feat/crypto-market-pulse-mvp \
  --title 'feat: Crypto Market Pulse multi-engine streaming MVP' \
  --body 'Offline unit tests passed; Kafka/Spark/Beam/Databricks/cloud E2E need runtime validation. See docs/VALIDATION_REPORT.md.'
```

If `git ls-remote origin` shows **any** existing refs, **stop**; do not push bundled `main` blindly. Inspect existing history and use a fresh feature branch based on `origin/main`, copying project files and committing in stages; do not overwrite existing work.

## Stages preserved in Git history

1. **Bootstrap specification + honest validation** (main). L0 status only.
2. **Core domain/parser/config/replay/fixture + tests**. L0 offline-verified.
3. **ClickHouse local SQL, Kafka consumer and dashboard**. Requires real service E2E.
4. **Spark and Databricks SQL, dashboard-as-code**. Requires Spark/DFE tests.
5. **Beam/GCP local and cloud draft**. Requires Beam/Emulator and cloud permission.
6. **Operator manual, run/debug guide, workbooks, CI and Weather baseline**. Documentation ready; CI not executed on GitHub.

For a manual source import without the bundle, copy `project/` contents into a fresh authorized checkout instead. Keep `.env` and cloud credentials out of commits. Do not auto-create billable cloud resources.
