# Contract: portable SQL model (`sql/models/<NN>_<name>_select.sql`)

The renderer is [`src/cmp/sql_models.py`](../../../src/cmp/sql_models.py). The generator is [`scripts/build.py`](../../../scripts/build.py).

- A model is one `SELECT` with **exactly one** `{{source}}` placeholder. It has no DDL, and a trailing `;` is stripped.
- `source` is substituted by the caller:

| Caller | `source` value |
|---|---|
| local Spark | `` delta.`<lake>/<table>` `` |
| MiniLake | `catalog.schema.table` |
| Lakeflow silver | `STREAM(trades_bronze)` |
| Lakeflow MVs | the upstream table name |

- `valid_trade.sql` is a boolean expression only; `--` comment lines are stripped. It becomes `EXPECT (…) ON VIOLATION DROP ROW` in the cloud and `WHERE (…)` locally.
- Use only the SQL dialect shared by Spark and Databricks SQL. DuckDB (MiniLake) gaps are reported as `DIALECT GAP`, never forked.
- Every edit is followed by `just build`. `test_generated_files_are_in_sync` enforces it.
