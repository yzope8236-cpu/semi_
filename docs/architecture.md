# Architecture

## Request/data path

1. A user/service uploads a file to FastAPI. The service hashes the original bytes and checks `ingest_files` before parsing; this makes repeated uploads idempotent.
2. The ATDF parser reconstructs MIR → WIR → PIR → PTR/PRR context, emits typed records and non-fatal/fatal validation events.
3. Values are normalized where unambiguous (mV→V, kOhm→Ohm, seconds→milliseconds). Original value, limits and normalized value are retained for auditability.
4. Canonical facts land in ClickHouse. The application computes fast, warehouse-native aggregations for overview, wafer map and failure attribution routes.
5. Spring Boot is the external integration boundary; it propagates a request ID and writes audit logs before proxying dashboard reads to FastAPI. In production it is the natural OIDC/RBAC, rate-limit and policy-enforcement location.

## Scale plan

- Partition test facts monthly; order by `(lot_id, wafer_id, test_num, device_id)` to serve drill-down predicates.
- Add `AggregatingMergeTree` materialized views for lot/wafer/test daily rollups once volume approaches 100M rows.
- Put object storage/event notifications (S3/MinIO/Kafka) ahead of stateless parser workers for horizontal bulk ingest.
- Make decoder mappings versioned, tenant/program scoped bundles. Preserve raw file checksum and mapping version on each ingest.

## STDF boundary

STDF is a binary, revision- and vendor-sensitive format. The `/ingest/files` contract deliberately rejects `.std/.stdf` until an approved decoder is enabled. Implement `parse_stdf(bytes)` alongside `parse_atdf`, map decoded FAR/MIR/WIR/PIR/PRR/PTR/WRR/TSR records to the same `Parsed` model, and validate on golden fixtures before enabling the content type. This prevents silent, incorrect binary interpretation.
