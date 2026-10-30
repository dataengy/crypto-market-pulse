---
status: accepted (pending the probe, GCP-C06)
date: 2026-10-30
decision-makers: owner
---
# 0002 — Run the hosted producer as a Cloud Run job in `europe-west1`

## Context and Problem Statement
The producer holds a Bybit V5 WebSocket open. Bybit restricts some jurisdictions by IP. Where can a bounded GCP producer run so that Bybit accepts it, and close to the Pub/Sub and BigQuery location?

## Decision Drivers
- **Bybit:** "IP addresses located in the US or Mainland China are restricted and will return a 403" ([V5 guide](https://bybit-exchange.github.io/docs/v5/guide), verified 2026-10-30).
  - Excluded jurisdictions also include **Hong Kong, Singapore and Canada**, among others ([Help Center](https://www.bybit.com/en/help-center/article/Service-Restricted-Countries/trade/spot), updated 2026-10-16, checked 2026-10-30). The list is about service to users; assume the IP block may follow it.
  - A third-party report says Bybit's CloudFront blocks cloud egress by country ([dev.to, 2026-10-13](https://dev.to/brojinga/what-i-learned-building-a-funding-rate-comparison-tool-and-where-exchange-apis-get-weird-j13)). **Unverified**, hence the probe gate.
- The same region as Pub/Sub and BigQuery avoids cross-region transfer.
- Cloud Run jobs Free Tier applies (240k vCPU-s, 450k GiB-s per month; [run/pricing](https://cloud.google.com/run/pricing), verified 2026-10-30). Whether `europe-west1` is a Tier-1 price region is **unverified**: check the [locations page](https://docs.cloud.google.com/run/docs/locations).

## Considered Options
1. A Cloud Run job in `europe-west1` (Belgium)
2. A Cloud Run job in `asia-southeast1` (Singapore; lowest latency to Bybit's AWS ap-southeast-1)
3. An e2-micro in `us-central1/us-west1/us-east1` (the only Free Tier VM regions)
4. Keep the laptop as the producer

## Decision Outcome
Chosen: **option 1**, with `deploy.run.fallback_regions` (e.g. `europe-west4`, `europe-west3`) tried **only by the user's decision** after a failed probe. Option 4 is the final fallback.

### Consequences
- Good: EU region, not on any Bybit list; co-located with the data.
- Bad: more latency to Bybit than from Singapore (estimated ~150–200 ms, unmeasured). Irrelevant for 1-minute bars.
- Risk: a cloud-IP block regardless of country. The probe ([hosted-producer Task 3](../../agent-os/specs/2026-10-30-1230-hosted-producer/plan.md)) detects it before any schedule is turned on.

### Confirmation
The probe job execution is `Succeeded` with trade lines in Cloud Logging.

## Pros and Cons of the Options
- **Singapore:** best latency, but a restricted jurisdiction. Rejected.
- **US e2-micro:** free, but US IPs get a 403. Rejected (backlog [GCP-C14](../../../../docs/plans/gcp/tasks.md#gcp-c14) stays as "close as blocked").
- **Laptop:** works today, but is not "hosted".
