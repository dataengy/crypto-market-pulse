# Standards for Terraform foundation

Linked rather than copied (see the [README deviation note](../../../README.md#method)):
- [global/config-strict](../../standards/global/config-strict.md): `yamldecode`, no `default`, `TF_VAR_*` from `.env.secrets`
- [global/ponytail-minimal](../../standards/global/ponytail-minimal.md): fix the reference file, 4 `.tf` files, no modules
- [gcp/terraform](../../standards/gcp/terraform.md): provider `~> 8.9`, the fmt/validate/plan gate, no `-auto-approve`
- [gcp/auth-no-keys](../../standards/gcp/auth-no-keys.md): SA set, WIF condition
- [gcp/cost-guardrails](../../standards/gcp/cost-guardrails.md): budget, labels, retention
- [process/verification](../../standards/process/verification.md): evidence logs, gates
