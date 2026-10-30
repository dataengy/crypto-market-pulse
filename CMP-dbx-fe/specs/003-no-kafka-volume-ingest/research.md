# Research: No-Kafka ingest

The option table (Volume + Auto Loader, warehouse INSERT, Zerobus, REST proxy, producer → Volume) and its sources are in [alt-no-kafka.md › Decision](../../../docs/plans/dbx-fe/alt-no-kafka.md#a-decision) and [› Risks](../../../docs/plans/dbx-fe/alt-no-kafka.md#risks--unverified).

Open questions, all checked by DBX-A01 or A06:
1. Can a Volume be created and read via `dbutils.fs.ls` from Free Edition serverless?
2. What is the Files API per-request limit? It sets `volume.max_batch_bytes`.
3. Does Auto Loader's schema/checkpoint location under the pipeline storage work on Free Edition?
4. Is any Kafka REST endpoint (443) on the trusted list? Probe it only; don't build on it.
