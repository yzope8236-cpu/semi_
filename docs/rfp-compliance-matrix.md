# RFP compliance matrix — YieldScope

This matrix maps the supplied STDF/ATDF analytics RFP to the repository as it exists today. It distinguishes **implemented MVP** capability from requirements that must be validated against customer-provided STDF corpora, infrastructure, identity systems, or performance targets. It intentionally does not represent unmeasured targets as completed.

| RFP requirement | Status | Repository evidence / completion path |
|---|---|---|
| Modular ingest → parse → canonicalize → store → analytics → UI/API architecture | **Implemented** | `apps/api`, `clickhouse`, `apps/gateway`, `apps/web`, Docker Compose. |
| Manual multipart file upload | **Implemented** | `POST /api/v1/ingest/files`; gateway preserves multipart uploads. |
| `.gz`, `.zip`, `.tar.gz` auto-decompression | **Implemented, single payload/archive** | `unpack_payload()` in `app/main.py`; archives with multiple files are rejected deliberately to preserve idempotent lineage. |
| SFTP/SMB/NFS and S3/Azure/GCS file-drop connectors | **Deployment extension** | Connector interfaces/object-store landing zone are documented in architecture; credentials and target endpoint are required. |
| Kafka/queue notification | **Deployment extension** | Designed for replayable worker scale; needs broker target and operations configuration. |
| ATDF parser, FAR/MIR/WIR/PIR/PTR/PRR flow | **Implemented** | `app/parsers.py`; mandatory FAR/MIR/WIR checks, raw record offsets, validation events. |
| Binary STDF parser | **Implemented (MVP)** | Validated against synthetic STDF V4 fixtures. Core records supported; requires customer-approved golden data for production acceptance. |
| Streaming large-file parser/recovery/DLQ | **Partially implemented** | Record-level validation and continuation implemented for ATDF. Convert `UploadFile.read()` and parser to chunk iterator; provide queue/DLQ with target broker during hardening. |
| Immutable raw record provenance | **Implemented in ClickHouse** | `raw_records` includes file, source offset/type/fields and parser version. Production raw original/object-store retention remains deployment configuration. |
| SHA-256 duplicate idempotency | **Implemented** | `ingest_files.sha256` check before writes. |
| Parser/mapping version provenance | **Implemented baseline** | `parser_version`, `mapping_version` and source URI persisted per ingest. Versioned mapping-bundle UI is next admin feature. |
| Canonical units/original value/unit preservation | **Implemented baseline** | Voltage/current/resistance/time conversions; original unit stored. Add customer unit dictionary/mapping bundle for full program coverage. |
| Normalized files/wafers/devices/test results data model | **Implemented** | ClickHouse DDL and hierarchy-preserving keys in `001_schema.sql`. |
| ClickHouse OLAP warehouse, partition/order strategy | **Implemented** | Monthly test-result partitions, drill-down order key. |
| Postgres metadata catalog / schema evolution | **Deployment extension** | MVP keeps operational metadata in ClickHouse; production recommendation is Postgres + migration history. |
| Wafer/lot yield, DPPM, retest, test failure ranking | **Implemented** | Dashboard and analytics routes. |
| Wafer heat map and missing die points | **Implemented baseline** | Plotly die-coordinate map; absent coordinates are naturally absent. |
| DBSCAN/connected-component cluster detection and hotspot statistic | **Partially implemented** | Deterministic edge/corner spatial signal delivered. Add `scikit-learn` DBSCAN/Moran's I after real wafer-map conventions are supplied. |
| Test correlation/contingency analysis | **Planned extension** | Requires statistically adequate sample corpus; API/table schema supports it. |
| Pin/channel/tester root-cause ranking | **Partially implemented** | Test/pin ranking and tester metadata captured; cross-lot attribution requires fixture population. |
| SPC P-chart/EWMA/CUSUM/change points | **Planned extension** | Requires historical timestamped lots; intentionally deferred rather than returning misleading metrics on one lot. |
| Predictive/unsupervised ML, registry, SHAP | **Extension with data dependency** | Requires labeled historical test data and approved outcome definition. The RFP's AUC acceptance must be measured on supplied data. |
| REST OpenAPI | **Implemented** | FastAPI `/docs` and `/openapi.json`. |
| GraphQL, sandboxed custom SQL | **Planned security-sensitive extension** | Only implement after RBAC/query-cost policy is agreed; raw SQL must not be exposed by default. |
| CSV/JSON/Parquet/PDF export | **Partial** | JSON is native. CSV/Parquet/PDF report workers are next deliverable. |
| Interactive dashboard and lot → wafer → die → test path | **Implemented baseline** | Dashboard and die-details API; richer breadcrumb UI is next visual enhancement. |
| Side-by-side comparison, control charts, event annotation | **Planned extension** | Needs historical lots/event data. |
| Alert center/rule configuration | **Partial** | Low-yield alert candidate endpoint exists; persistence/notification targets require identity and notification service. |
| OAuth2/SAML/LDAP and Admin/Yield Engineer/Data Scientist/Viewer RBAC | **Integration required** | Spring gateway is the policy boundary. Wire to customer's IdP; do not ship invented credentials. |
| Query/dataset audit log | **Implemented baseline** | Spring gateway emits request-ID audit events. Production needs immutable centralized sink and retention policy. |
| Prometheus/OpenTelemetry/central logs | **Partial** | Spring actuator health and FastAPI health present; add Prometheus/OTel collector configuration at deployment. |
| Docker, Kubernetes/Helm | **Docker implemented; Helm planned** | `docker-compose.yml`; Helm needs target cluster namespace, ingress and secret strategy. |
| Documentation, runbooks, API docs, data dictionary | **Implemented baseline** | `docs/` plus FastAPI Swagger. |
| 10 binary + 10 ATDF goldens; 99.9% correctness | **Validation pending customer corpus** | Parser test suite exists; production acceptance fixtures and independently measured results must be added when files are available. |
| 10GB performance / <2s query benchmark | **Validation pending hardware/corpus** | Must be measured in target sizing environment; no fabricated result is claimed. |

## Current acceptance evidence

- Parser unit tests run locally: mandatory-record and normalization logic are covered.
- Frontend TypeScript production build succeeds.
- Idempotency is implemented through source-content SHA-256 and should be verified in integration testing against ClickHouse.
- A reproducible synthetic demo is supplied at `samples/demo.atdf` and through `POST /api/v1/demo/seed`.

## Completion definition for an RFP production submission

Before claiming full compliance, provide golden STDF/ATDF test files, test-program mapping rules, device/bin semantics, expected rollups, hardware sizing, data retention values, cloud/on-prem placement, IdP details, and alert destinations. Then run a documented acceptance suite and attach its benchmark/accuracy report to this matrix.
