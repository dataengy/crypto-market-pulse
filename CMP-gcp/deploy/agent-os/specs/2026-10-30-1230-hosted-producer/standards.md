# Standards for Hosted producer + dashboard

- [gcp/cost-guardrails](../../standards/gcp/cost-guardrails.md): paused Scheduler, bounded job, AR cleanup, labels
- [gcp/auth-no-keys](../../standards/gcp/auth-no-keys.md): the job runs as `producer-sa`; no keys in the image
- [gcp/terraform](../../standards/gcp/terraform.md): the job and Scheduler live in Terraform; the reviewed plan gate
- [global/config-strict](../../standards/global/config-strict.md): region, cron, timeouts and probe args from config
- [process/verification](../../standards/process/verification.md): the probe gate, gated unpause
