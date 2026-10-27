# Load test mirati

Script `scripts/loadtest.py` (solo stdlib) misura latenza e throughput su liste, topologia e una mutazione create/delete. Non è un test di saturazione: usa un carico piccolo e deterministico.

## Prerequisiti

Stack `full` attivo (`make full`) e un utente SystemAdmin. La sessione carica i ruoli al login: il ruolo va assegnato prima del login.

```bash
docker compose -f ../infraorgit-docker/compose.yaml \
  -f ../infraorgit-docker/compose.full.yaml --profile full exec -T mysql \
  sh -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD" infraorgit -e "
    INSERT INTO Users (Name,Surname,Username,CreatedAt,UpdatedAt,Version)
    VALUES (\"Dev\",\"Admin\",\"admin\",UTC_TIMESTAMP(6),UTC_TIMESTAMP(6),0);
    INSERT INTO RoleUser (RolesId,UsersId)
    SELECT 3,Id FROM Users WHERE Username=\"admin\";"'
```

## Esecuzione

```bash
cd AllInfraOrgIT
INSECURE_TLS=1 make load-test   # localhost con certificato self-signed
REQUESTS=100 CONCURRENCY=10 INSECURE_TLS=1 make load-test
BASE_URL=https://altro-host LOADTEST_USER=... LOADTEST_PASSWORD=... make load-test
```

Variabili: `REQUESTS` (default 30), `CONCURRENCY` (5), `MAX_AVG_MS` (1000), `INSECURE_TLS=1` per certificati self-signed. La verifica TLS non è disattivata di default.

Endpoint: `GET /api/menus`, `GET /api/providers`, `GET /api/topology`, `POST /api/providers`, `DELETE /api/providers/{id}`. Il login passa da Keycloak e il primo accesso al realm può rispondere 503 durante il bootstrap: lo script riprova.

## Risultato 2026-10-27

Stack isolato (`ds-loadtest`), 12 richieste per endpoint, concorrenza 4:

| Endpoint | ok | avg | p95 | max |
|---|---|---|---|---|
| GET /api/menus | 12 | 22 ms | 64 ms | 64 ms |
| GET /api/providers | 12 | 11 ms | 25 ms | 25 ms |
| GET /api/topology | 12 | 26 ms | 67 ms | 67 ms |
| POST /api/providers | 5 | 15 ms | 51 ms | 51 ms |
| DELETE /api/providers | 5 | 9 ms | 20 ms | 20 ms |

Exit code 0 (nessun errore, media sotto 1000 ms).

## Limiti

- Numeri su una singola macchina Docker, database vuoto: non rappresentano produzione né dati rappresentativi.
- Il carico è breve e non alza la concorrenza fino al ginocchio; per capacità reale servono dataset rappresentativo e test più lunghi.
- Ogni richiesta apre una nuova connessione TLS; il keep-alive non è misurato.
