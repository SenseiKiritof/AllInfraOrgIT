# Targeted load tests

Script `scripts/loadtest.py` (stdlib only) measures latency and throughput on lists, topology and a create/delete mutation. It is not a saturation test: it uses a small, deterministic load.

## Prerequisites

`full` stack running (`make full`) and a SystemAdmin user. The session loads roles at login: the role must be assigned before login.

```bash
docker compose -f ../InfraOrgITDocker/compose.yaml \
  -f ../InfraOrgITDocker/compose.full.yaml --profile full exec -T mysql \
  sh -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD" infraorgit -e "
    INSERT INTO Users (Name,Surname,Username,CreatedAt,UpdatedAt,Version)
    VALUES (\"Dev\",\"Admin\",\"admin\",UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),0);
    INSERT INTO RoleUser (RolesId,UsersId)
    SELECT 3,Id FROM Users WHERE Username=\"admin\";"'
```

## Run

```bash
cd AllInfraOrgIT
INSECURE_TLS=1 make load-test   # localhost with self-signed certificate
REQUESTS=100 CONCURRENCY=10 INSECURE_TLS=1 make load-test
BASE_URL=https://other-host LOADTEST_USER=... LOADTEST_PASSWORD=... make load-test
```

Variables: `REQUESTS` (default 30), `CONCURRENCY` (5), `MAX_AVG_MS` (1000), `INSECURE_TLS=1` for self-signed certificates. TLS verification is not disabled by default.

Endpoints: `GET /api/menus`, `GET /api/providers`, `GET /api/topology`, `POST /api/providers`, `DELETE /api/providers/{id}`. The login goes through Keycloak and the first access to the realm may answer 503 during bootstrap: the script retries.

## Result 2026-10-27

Isolated stack (`ds-loadtest`), 12 requests per endpoint, concurrency 4:

| Endpoint | ok | avg | p95 | max |
|---|---|---|---|---|
| GET /api/menus | 12 | 22 ms | 64 ms | 64 ms |
| GET /api/providers | 12 | 11 ms | 25 ms | 25 ms |
| GET /api/topology | 12 | 26 ms | 67 ms | 67 ms |
| POST /api/providers | 5 | 15 ms | 51 ms | 51 ms |
| DELETE /api/providers | 5 | 9 ms | 20 ms | 20 ms |

Exit code 0 (no errors, average below 1000 ms).

## Limits

- Numbers on a single Docker machine, empty database: they do not represent production or representative data.
- The load is short and does not raise concurrency up to the knee; real capacity needs a representative dataset and longer tests.
- Each request opens a new TLS connection; keep-alive is not measured.
