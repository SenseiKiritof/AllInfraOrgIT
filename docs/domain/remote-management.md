# Gestione remota e audit

Fase 5, 2026-10-26. Riferimento funzionale: `../InfraOrgIT` in sola lettura. Le regole di permesso sono in `docs/security/permissions.md` (D7 = B).

## Credenziali SSH

- `ServerCredentials` conserva password o chiave privata **cifrate con AES-GCM**; il client riceve solo `hasSecret`, mai ciphertext o plaintext.
- Layout: `base64(nonce|tag|ciphertext)`, nonce 12 byte, tag 16 byte. Chiave di 32 byte per versione in `ServerAccess:CredentialKeys:<n>`; `ServerAccess:CurrentKeyVersion` sceglie la chiave di cifratura. La riga conserva `KeyVersion`, quindi una rotazione decrypta le righe vecchie.
- In sviluppo `scripts/env.sh` genera una chiave e la salva in `infraorgit-docker/.env` (ignorato). In produzione la chiave arriva da secret manager.
- Una chiave privata viene validata con SSH.NET prima del salvataggio; una password no.
- In modifica un segreto vuoto lascia invariato quello salvato; cambiare `AuthType` richiede il segreto.
- Una credenziale assegnata a server non si elimina (409). Assegnazione SSH e reset host key sono `SystemAdmin`.

## SSH

`SshConnector` usa SSH.NET:

- connessione 10 s; comando con timeout configurabile (`ServerAccess:CommandTimeoutMinutes`, 1–60, default 10);
- output massimo 1 MB (`MaxOutputBytes`), l'audit conserva gli ultimi 64 KB (`MaxAuditOutputBytes`);
- **host key TOFU**: alla prima connessione il fingerprint SHA256 viene salvato sul server; se cambia la connessione viene rifiutata con 409 `host_key_mismatch` e l'audit registra il tentativo. Il reset è solo `SystemAdmin`;
- gli errori non contengono segreti.

## Templating e azioni

- Placeholder `{{Name}}`; built-in: `ServerName`, `Hostname`, `IpAddress`, `ApplicationName`, `BasePath`, `Version`, `ExposedPort`.
- I built-in vincono sui valori custom e vengono controllati sia al salvataggio sia all'esecuzione.
- I valori sono racchiusi in apici singoli con escape di `'`; i caratteri attivi della shell (`$`, backtick, `\`, `"`, CR/LF) sono rifiutati nei valori dei placeholder usati, custom inclusi.
- Un'azione ha un template **oppure** uno script custom (solo `SystemAdmin`), con `ParameterValues` JSON.
- Configurazione azioni: `SystemAdmin`; elenco bottoni e run: `ServerOperator` sull'ambiente del deploy.
- Il run riserva la riga di audit con `Idempotency-Key` **prima** di eseguire: un doppio invio riceve 409 e non esegue. Se il comando o la connessione falliscono, l'audit viene comunque completato con l'errore.
- L'audit salva il template non renderizzato e nell'output sostituisce i valori custom con `***`.

## Reachability

- Test globali: CRUD `SystemAdmin`, eseguiti su ogni server. Test per server: CRUD `ServerAdmin`, lettura e run `ServerOperator`.
- Hostname validato (`[A-Za-z0-9.:-]`), porta 1–65535; il comando usa `timeout 5 bash -c '</dev/tcp/host/port>'` sul server, con timeout SSH di 10 s.
- Ogni server produce una riga di audit `Reachability` con l'esito aggregato.

## Esecuzioni e console

- `GET /api/command-executions` (`SystemAdmin`): paginato, filtrabile per server, tipo e testo; script e output sono redatti.
- Console WebSocket `/api/socket/servers/{id}/console`: cookie di sessione, **Origin** obbligatoria e ammessa, ruolo `ServerAdmin` sull'ambiente, durata massima 30 min. L'audit registra apertura/chiusura ed eventuale errore, mai i tasti digitati.

## Frontend

- `/credentials`: CRUD credenziali, segreto write-only, indicatore "impostato".
- `/commands`: CRUD template e conteggio placeholder.
- `/reachability`: test globali.
- `/executions`: registro con output espandibile.
- Dettaglio server: credenziale/porta SSH, reset host key, test reachability con run, azioni dei deploy, console.
- Dettaglio applicazione: configurazione azioni (template o script custom, parametri JSON, conferma).

## Configurazione

```text
ServerAccess__CurrentKeyVersion=1
ServerAccess__CredentialKeys__1=<base64 di 32 byte>
ServerAccess__CommandTimeoutMinutes=10
ServerAccess__MaxOutputBytes=1048576
ServerAccess__MaxAuditOutputBytes=65536
ServerAccess__ConsoleMaxMinutes=30
```

Le chiavi sono obbligatorie all'avvio: senza `CredentialKeys` l'API non parte.

## Test

- 11 unit: cifratura (round-trip, tamper, versione mancante), renderer (quote, placeholder mancanti, caratteri attivi), handler errori.
- 22 integrazione: credenziali cifrate e mai restituite, assegnazione SSH, host key, azioni con audit redatto e idempotenza, reachability, console con Origin estranea, **SSH reale su container OpenSSH usa-e-getta** con TOFU e mismatch.
- 4 E2E Playwright, inclusi credenziali, comandi, reachability, registro.

## Limiti noti

- La console mostra il terminale senza emulazione ANSI completa (sequenze rimosse) e ha solo il limite di durata, non un idle timeout separato.
- La rotazione delle chiavi si fa da configurazione, non da UI.
- La reachability esegue i server in sequenza; un ambiente molto grande richiede una coda.
- L'import delle credenziali legacy con la vecchia chiave resta in Fase 7; senza chiave si usa `NeedsReauth`.
