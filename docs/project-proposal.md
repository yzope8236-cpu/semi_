# Technical proposal — YieldScope STDF/ATDF Analytics MVP

**Reference:** IC/PTS/25/001  
**Solution name:** YieldScope  
**Status:** implementation-ready MVP

## 1. Technical approach

YieldScope separates parsing/analytics from integration policy. FastAPI owns data acquisition, ATDF parsing, validation and analytical API contracts. ClickHouse stores immutable, traceable test facts and supports high-cardinality wafer/test analysis. Spring Boot is the secure service boundary for external consumers and is designed to host authentication, authorization, request auditing and rate controls. The React dashboard gives engineering teams an immediate lot → wafer → die diagnostic path.

### Parsing and quality control

The current implementation accepts ATDF, rebuilds MIR → WIR → PIR → PTR/PRR parent-child context, supports retest count, preserves source-level lineage, and produces structured validation findings. It handles malformed/unknown lines safely and does not silently accept binary STDF. A vendor-validated STDF decoder is intentionally isolated behind the parser adapter boundary, allowing FAR/MIR/WIR/PIR/PRR/PTR/WRR/TSR mapping to the same canonical model.

Controls include mandatory MIR detection, orphan device/test detection, malformed PTR detection, unknown-record warnings, unit conversion, SHA-256 duplicate protection and file-level validation event logs.

### Storage and ETL

The canonical schema uses `ingest_files`, `wafers`, `devices`, `test_results`, and `validation_events`. It retains identifiers through each hierarchy level and uses ClickHouse order keys suitable for lot/wafer/test drill-down. Test facts are monthly partitioned. The next scale stage is materialized aggregate views for wafer, lot and test rollups plus an object-storage/Kafka intake layer and horizontally scaled parser workers.

### Analytics and visualisation

Delivered deterministic analytics cover yield, failed die count, average test time, yield trend, DPPM, low-yield alerts, test/pin failure ranking, spatial die maps and edge/corner failure indicators. The dashboard uses Plotly interactions for wafer selection and die hover detail. The device endpoint provides a direct failure-analysis drill-down with its complete parameter history.

## 2. Execution plan

| Phase | Duration | Deliverables | Acceptance |
|---|---:|---|---|
| Foundation | Week 1 | Docker environment, ClickHouse schema, FastAPI service shell, ATDF golden fixtures | Services boot; health and schema checks pass |
| Ingest and data quality | Week 2 | Parser, normalization, idempotency, validation events, source lineage | Re-upload does not change counts; golden ATDF field checks pass |
| Analytics | Week 3 | KPI, wafer, failure, alert and spatial APIs; analytic test suite | Wafer aggregates match golden data within 0.01% |
| Product experience | Week 4 | React dashboard, Spring integration boundary, API documentation, user runbook | Lot → wafer → die drill-down demonstrated |
| Hardening | Week 5 | Auth integration, STDF decoder validation, load tests, CI gates, backup/recovery drill | Security and performance benchmark sign-off |

## 3. Resource effort estimate

| Role | MVP effort | Primary ownership |
|---|---:|---|
| Data/backend engineer | 8 person-days | ATDF/STDF adapter, ETL, ClickHouse queries |
| Full-stack engineer | 7 person-days | FastAPI contracts, React dashboard, Spring gateway |
| QA/data validation engineer | 4 person-days | Golden datasets, parser/aggregate tests, defect triage |
| DevOps/security engineer | 3 person-days | Container deployment, CI, secret/TLS/RBAC baseline |
| Technical lead | 3 person-days | Architecture, reviews, handover |

**Total MVP:** 25 person-days. Dependencies: representative golden STDF/ATDF files, tester/program mapping conventions, RBAC identity-provider details, and target deployment environment.

## 4. Risks and mitigation

| Risk | Mitigation |
|---|---|
| Vendor-specific binary STDF variations | Validate each decoder/mapping version against golden files; retain raw source checksum and mapping version; reject unvalidated binary payloads. |
| Inconsistent units/test naming | Use versioned mapping bundles, canonical unit conversion and exception reports for unmapped data. |
| High-volume query pressure | Partition facts, add materialized rollups, enforce date/lot filters, and benchmark representative workloads. |
| Loss or duplicate intake | SHA-256 idempotency, durable object-store landing zone, replayable event queue, backup/restore drills. |
| Sensitive manufacturing data | TLS, encryption at rest, least-privilege service accounts, gateway RBAC, audit trail and secret rotation. |

## 5. Handover package

The repository includes the Docker deployment, database DDL, API documentation, parser tests, CI workflow, sample ATDF fixture, architecture description, data dictionary, and operations runbook. A final handover should additionally include approved STDF mappings, an identity-provider configuration, benchmark results, backup evidence and recorded user training.
