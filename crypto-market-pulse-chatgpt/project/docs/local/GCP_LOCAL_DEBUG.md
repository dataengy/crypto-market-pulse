# GCP native streaming + Beam local debug (draft runbook)

1. Inventory host `gcloud`, Python, Beam and Docker/Colima with read-only `scripts/discover_local_runtime.py`.
2. Pure offline: `pip install -r requirements-beam.txt`; `PYTHONPATH=src pytest -q tests/test_beam_optional.py`. This uses `TestStream` and `DirectRunner`, no GCP, covering event-time fixed windows, duplicates, out-of-order values.
3. Optional Pub/Sub transport: run existing Google Cloud SDK Pub/Sub emulator or start `gcloud beta emulators pubsub start --host-port=127.0.0.1:8085`, export `PUBSUB_EMULATOR_HOST=127.0.0.1:8085`, and run `python scripts/gcp_emulator_smoke.py`. This creates project-namespaced topic/subscription in the **emulator only**, publishes fixtures and verifies pull/ack. No credentials.
4. Optional managed MVP (explicit billing approval): `cd infra/gcp && terraform init && terraform plan -var project_id=...`; review IAM, BQ dataset location, storage/streaming cost, project permissions before `apply`. BigQuery Subscription ingests raw messages, then execute `sql/bigquery/*.sql` **except 001_raw.sql if Terraform already created raw table**. Views read `data BYTES` decoded JSON.
5. Advanced phase: create DataflowRunner Beam Pub/Sub → BigQuery streaming job with state/windowing, and compare watermarks, late events, costs and latency. This advanced runtime is **not yet implemented** in the archive.

**Emulator limitation:** BigQuery subscriptions may be created in the emulator but never deliver events to BigQuery. `TestStream` isn't a substitute for cloud Dataflow performance validation. Do not claim exactly-once delivery just from tests.
