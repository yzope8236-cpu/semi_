# Data dictionary

| Table | Grain | Key columns | Purpose |
|---|---|---|---|
| `ingest_files` | source file version | `sha256`, `file_id` | File lineage, `source_format` (ATDF/STDF), parser status and quality summary. |
| `wafers` | one wafer in a source run | `lot_id`, `wafer_id` | Tester/mask/time context. |
| `devices` | one completed die attempt | `lot_id`, `wafer_id`, `device_id` | Coordinates, site/channel, bin, pass state and retest count. |
| `test_results` | one parameter result | `device_id`, `test_num` | Measurement, limits, normalized unit/value, pin and pass state. |
| `validation_events` | one validation finding | `file_id`, `event_id` | Parser/data quality evidence with source line. |

**Yield:** `100 × passed devices / tested devices`. **DPPM:** `1,000,000 × failed devices / tested devices`. `passed` is represented as `UInt8` (0/1) for ClickHouse aggregation. Source fields are immutable after ingestion; corrective mappings should create an auditable derived ingestion version.
