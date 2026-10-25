# Mappa UX e pagine

Verificata sul frontend legacy (`infra-org-it-fe/app`, Next.js) il 2026-10-25. Target: Vite + React Router, stessi flussi, route corrette (`/environments`, non `/enviroments`).

## Shell

- **Login**: `/api/auth/*` (BFF). Pagina pubblica `/login-error`. Nessun token leggibile da JavaScript.
- **Menu laterale**: caricato da `GET /api/menus`; nel legacy non è filtrato dal ruolo. Target: filtrato da `MenuRole`.
- **Header**: titolo della route, pulsante Indietro (tranne Home), dropdown utente con Logout.
- **Route detail**: il menu contiene voci padre (`/servers`) e figlie (`/servers/{id}`) con `HideBackButton=false`; il layout mostra la sidebar solo quando la route corrente ha `HideBackButton=true` (voci di primo livello).
- **Gestione errori**: popup centralizzato; 401 → rinnovo o login; errori API mostrati all'utente.
- **Tabelle**: `DataTable` con filtri, paginazione server-side (`/Paginated`), colonne per entità, azioni modifica/elimina.
- **Form**: `CrudModal` + `Input`/`MultiSelect`; niente React Hook Form nel legacy; target RHF + Zod.

## Pagine

| Route | Pagina | Contenuto e azioni | Accesso UI legacy |
|---|---|---|---|
| `/` | Home | placeholder "Landing page" | tutti |
| `/environments` | Ambienti | lista: id, nome, descrizione, provider; crea/modifica; **nessuna delete** | tutti |
| `/environments/{id}` | Dettaglio ambiente | nome, descrizione, provider collegati; salva | tutti |
| `/providers` | Provider | lista: id, nome, ambienti; crea/modifica/elimina | tutti |
| `/providers/{id}` | Dettaglio provider | nome, ambienti collegati; salva | tutti |
| `/servers` | Server | lista: id, nome, ambiente; crea/modifica/elimina | tutti |
| `/servers/{id}` | Dettaglio server | vedi flusso server | tutti; blocchi remoto condizionati |
| `/applications` | Applicazioni | lista: id, nome, descrizione, base path, porta; crea/modifica/elimina | tutti |
| `/applications/{id}` | Dettaglio applicazione | vedi flusso catalogo | tutti |
| `/projects` | Progetti | lista: id, nome, descrizione; crea/modifica/elimina | tutti |
| `/projects/{id}` | Dettaglio progetto | nome, descrizione, applicazioni collegate | tutti |
| `/diagrams` | Diagrammi | lista: id, nome, descrizione; apri, crea, elimina | tutti |
| `/diagrams/{id}` | Canvas diagramma | vedi flusso diagrammi; `id=0` = vista globale | tutti |
| `/users` | Utenti | lista: id, username, nome, cognome; crea/modifica/elimina | tutti (scrittura SystemAdmin) |
| `/users/{id}` | Dettaglio utente | username, nome, cognome, gruppi, ruoli | tutti |
| `/groups` | Gruppi | lista e CRUD nome | tutti (scrittura SystemAdmin) |
| `/roles` | Ruoli | lista e CRUD nome, label, scope | tutti (scrittura SystemAdmin) |
| `/menu` | Menu | lista e CRUD voci, path, ordine, visibilità | tutti (scrittura SystemAdmin) |
| `/credentials` | Credenziali | lista: nome, utente SSH, tipo, server; CRUD con secret write-only | tutti (API SystemAdmin) |
| `/commands` | Comandi base | lista e CRUD template; evidenzia i placeholder `{{Name}}` | tutti (API SystemAdmin) |
| `/reachability` | Test di rete | test globali; test per ambiente; run | tutti (API SystemAdmin/Operator) |
| `/executions` | Registro esecuzioni | lista paginata: data, utente, server, tipo, comando, exit; dettaglio output | tutti (API SystemAdmin) |
| `/login-error` | Errore login | messaggio e retry | pubblico |

## Flusso server `/servers/{id}`

1. **Anagrafica**: nome, IP, hostname, ambiente (select `ProviderEnvironments`); salva. Se il server ha una credenziale e cambia indirizzo/ambiente, l'API richiede SystemAdmin.
2. **Applicazioni deployate**: lista `ServerApplications`; aggiungi versione applicazione + porta esposta; elimina deploy.
3. **Proxy**: lista connessioni in ingresso/uscita; crea connessione (source/target/direzione); elimina.
4. **SSH** (`SshBlock`): select credenziale, porta; salva; console se `ServerAdmin`; reset host key.
5. **Reachability** (`ReachabilityBlock`): test del server; crea/modifica/elimina se `ServerAdmin`; run se `ServerOperator`.
6. **Azioni deploy** (`DeployActions`): bottoni dell'applicazione; conferma se richiesta; run; output; visibili a `ServerOperator`.

## Flusso catalogo `/applications/{id}`

1. **Applicazione**: nome, descrizione, base path, porta in ascolto; salva; elimina.
2. **Versioni**: lista, crea, modifica, elimina; ogni versione ha un numero.
3. **API della versione**: verbo, URL, descrizione, body; CRUD.
4. **Query param dell'API**: nome, tipo; CRUD.
5. **Progetti collegati**: multi-select; aggiungi/rimuovi.
6. **Azioni applicazione** (`ActionsBlock`): label, ordine, template o script custom, valori dei placeholder, conferma; solo SystemAdmin. Gli operatori vedono solo i bottoni.

## Flusso diagrammi `/diagrams/{id}`

- Toolbar: selettore diagrammi, **Vista globale** (`id=0`), Salva, Salva come…, Export PNG, Fit, Ridisponi, zoom, Nodo.
- Filtri della vista globale: provider, ambiente, progetto; "Salva come…" li converte in `DiagramScopeItem` (`Provider`, `ProviderEnvironment`, `Project`).
- Canvas React Flow: nodi provider/ambiente/server/server-application; edge proxy con handle e bend; layout persistito.
- Azioni nodo: crea/modifica provider, ambiente, server, applicazione; elimina con anteprima impatti (`Topology/Nodes/{type}/{id}/DeletePreview`).
- Proxy: collega server; gestisci route (`Route`, `MappedTo`, target applicazione o connessione).
- Salvataggio: `PUT /Diagrams/{id}/Nodes` e `/Edges`; `GET /Diagrams/{id}/Graph` restituisce diagramma + topologia + nodi/edge in scope.
- Export PNG lato client. Import diagrammi non presente nel legacy; l'import legacy è l'importer di Fase 7.

## Differenze target

| Legacy | Target |
|---|---|
| Next.js App Router, JS | Vite + React Router 7, TypeScript |
| `/enviroments` (API) | `/api/environments` |
| Menu non filtrato | menu filtrato per ruolo |
| `id=0` per vista globale | `Diagram.IsDefault` + route esplicita `/diagrams/default` (niente id magico) |
| `Enviroments` typo nelle chiamate | nessun alias in v1; alias solo per client esterni (D10) |
| Tabelle con `totalCount/results` | `{items,total,page,pageSize}` |
| Nessuna delete ambiente | valutare DELETE con anteprima impatti |
| Stato server con `useServerAccess` | stesso modello, dati da `/api/server-access/me` |
| Form senza schema | RHF + Zod, errori RFC 7807 |

## Pagine che il target può semplificare

- Home: dashboard con diagrammi recenti o stato ambienti; il placeholder legacy non serve.
- Dettaglio provider/ambiente: la relazione è già gestita da `ProviderEnvironment`; evitare due form che modificano la stessa coppia.
- Diagrammi: separare `buildGraph`/layout (funzioni pure testabili) dal canvas.
- Admin: una pagina utenti con gruppi/ruoli inline; niente navigazione separata se non serve.
