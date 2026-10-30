# Contract: landing file (DBX-A02)

- **Name**: `{topic}-{partition}-{first_offset}-{last_offset}.jsonl`. It is deterministic, so a re-ship of the same offsets overwrites the same file (`overwrite=True`).
- **Body**: UTF-8 JSONL. Each line is one [trade event v1](../../001-local-kafka-spark-delta/contracts/kafka-trade-event.md), exactly as encoded by `encode_event`.
- **Size**: ≤ `volume.max_batch_bytes`. The flush happens at the size limit or at `volume.max_wait_s`, whichever comes first.
- **Ordering**: within a file, Kafka offset order. Across files, no ordering is guaranteed, because dedup and event-time bars do not need it.
- **Commit rule**: the shipper commits the offsets only after the upload succeeds.
- **Fixture mode** (`--source fixture`): the file uses the same naming, with partition `0` and the offsets = the line index.
