# Operations runbook

## Startup and smoke test

```bash
docker compose up --build -d
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/demo/seed
curl http://localhost:8000/api/v1/dashboard/overview
```

## Failure handling

- **Duplicate upload**: API returns `status: duplicate`; no facts are inserted.
- **Validation errors**: inspect `GET /api/v1/quality/files/{file_id}`. The raw source should be retained in controlled object storage by the production ingestion connector.
- **ClickHouse unavailable**: FastAPI health reports `degraded`; do not accept production uploads until storage recovers. Queue files durably in object storage/event bus rather than memory.
- **Low yield**: query wafer map, inspect clustered dies, then failure attribution by test/pin/site. A production alert should trigger below agreed yield threshold.

## Production security checklist

- Terminate TLS 1.2+ before gateway; use OIDC authentication and role checks at the gateway.
- Replace `.env` secrets with a secret manager; rotate service credentials and API keys.
- Create least-privilege ClickHouse users; encrypt disks/backups and restrict private network access.
- Ship structured audit logs (`request_id`, actor, action, lot/file ID) to immutable monitoring.
- Back up incrementally daily and full weekly; test restores against stated RPO/RTO.
