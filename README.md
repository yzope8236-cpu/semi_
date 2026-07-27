# YieldScope — Semiconductor Test Analytics

An end-to-end MVP for STDF/ATDF semiconductor test analytics. It turns tester output into traceable lot → wafer → die → test data, exposes KPI and diagnostic APIs, and presents an interactive React dashboard.

> **MVP scope:** Complete ATDF ingestion and a production-oriented STDF V4 binary parsing adapter. STDF V4 core-record MVP support is validated against synthetic fixtures only. Real tester/vendor golden files are required for production accuracy, record-coverage, and performance acceptance.

## Architecture

```text
ATDF/STDF upload → FastAPI parser & validation → ClickHouse canonical tables
                          ↓                         ↑
                     analytics endpoints ← Spring Boot gateway/audit proxy
                          ↓
                  React + Plotly dashboard
```

- **FastAPI**: streaming ATDF parser, normalization, idempotent file ingest, data-quality results, KPI, wafer map, failure and trend analytics.
- **ClickHouse**: append-friendly event facts plus materialized wafer / lot rollups.
- **Spring Boot**: gateway boundary, request ID propagation and audit logging; `/api/**` proxies analytical traffic to FastAPI.
- **React/TypeScript**: dashboard designed for rapid lot-to-wafer diagnostics.

## Run locally

```bash
cp .env.example .env
# Set a real API_KEY before any non-demo deployment.
docker compose up --build
```

Open [http://localhost:5173](http://localhost:5173). API docs: [http://localhost:8000/docs](http://localhost:8000/docs). Gateway health: [http://localhost:8080/actuator/health](http://localhost:8080/actuator/health).

Seed the supplied demo dataset after startup:

```bash
curl -X POST http://localhost:8000/api/v1/demo/seed
# Or upload: curl -F 'file=@samples/demo.atdf' http://localhost:8000/api/v1/ingest/files
```

## Important endpoints

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/ingest/files` | Upload ATDF/STDF file; SHA-256 makes duplicate uploads idempotent |
| `GET /api/v1/dashboard/overview` | Fleet KPIs and yield trend |
| `GET /api/v1/wafers/{wafer_id}/map` | Die coordinates and pass/fail spatial map |
| `GET /api/v1/analytics/failures` | Failure ranking / test attribution |
| `GET /api/v1/analytics/alerts?threshold=95` | Low-yield wafer alert candidates with DPPM |
| `GET /api/v1/analytics/spatial/{wafer_id}` | Deterministic edge/corner failure signal |
| `GET /api/v1/devices/{device_id}` | Die-level drill-down including parameter results |
| `GET /api/v1/quality/files/{id}` | Validation findings and source traceability |

## Data model and security

See [architecture](docs/architecture.md), [data dictionary](docs/data-dictionary.md), [runbook](docs/runbook.md), [technical proposal](docs/project-proposal.md), and the requirement-by-requirement [RFP compliance matrix](docs/rfp-compliance-matrix.md). Docker defaults are intentionally easy to run locally; production must use TLS, secret injection, restricted ClickHouse users, encryption at rest, OIDC/RBAC at the gateway, backups, and network policies.

## Tests

```bash
cd apps/api && pip install -r requirements.txt && pytest
cd ../web && npm ci && npm run build
cd ../gateway && mvn test
```
