-- Execute in a BigQuery project where dataset crypto_pulse exists.
-- BigQuery Subscription WITHOUT topic/table schema stores payload in data BYTES.
CREATE TABLE IF NOT EXISTS crypto_pulse.trades_raw (
  data BYTES
) OPTIONS (description = 'Pub/Sub BigQuery subscription raw public market trades');
