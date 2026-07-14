# SAP OData Connector — Runbook

Connect the digital-twin system to a **real SAP S/4HANA** OData service, use the
`$metadata` schema to drive mapping, and run the twin off live SAP data — with the
LLM never connecting to SAP and never seeing row data.

This runbook covers the full flow: bring up the stack → connect an LLM/embedder →
add & discover a SAP source → recommend endpoints → map → confirm → refresh the twin.

## Architecture & security boundary

```
Real SAP ──GET──► ODataClient (deterministic; holds creds in-memory)
                    │ fetch $metadata → EdmxParser → SourceSchema (metadata only)
                    │                      ├─► .agent-mappings/schemas/{id}.json  (UI browse)
                    │                      └─► "source-schema" RAG corpus
                    │                                        │ (retrieve metadata only)
entity rows ──GET──► ODataClient (runtime /refresh)        ▼
                    │                          Recommender + mapping_engine (LLM-over-RAG)
                    ▼                                        │
         MappingDrivenFactory ◄── confirmed mapping ◄────────┘
         (deterministic: fetch rows, resolve units, coerce, build CMSD)
```

- The **LLM never connects to SAP** and never holds credentials.
- The LLM sees **metadata only** (entity/property names, `sap:label`, types, keys,
  navigation properties) via the `source-schema` RAG corpus.
- **Row data never leaves the factory**: only `MappingDrivenFactory` (runtime) and the
  local-only `/sources/{id}/sample` browser preview read rows. Neither is sent to the LLM.
- **Credentials are encrypted at rest** (Fernet) with `SAP_CRED_KEY`; both services
  share the key via env.

## Prerequisites

- Docker + Docker Compose.
- SAP S/4HANA OData credentials (HTTP Basic). The reference system is
  `https://a33p.ucc.cloud` client `200`, service `API_PRODUCTION_ROUTING`.
- An LLM chat provider + an embedding provider (e.g. Ollama for embeddings). The
  recommender and mapping need both; discovery needs the embedder (to index the
  `source-schema` chunks).

## Step 1 — Generate the credential key

```bash
cd sap-mes-cmsd-twin
python -c "from shared.crypto import generate_key; print(generate_key())"
```

Export it in the shell you run `docker compose` from (or put it in a `.env` next to
`docker-compose.yml`):

```bash
export SAP_CRED_KEY="<the printed key>"
```

If `SAP_CRED_KEY` is unset, the system runs in **dev/no-key mode**: credentials are
stored as plaintext normalized auth in the mapping `source.auth` block (fine for local
mocks, not for production).

## Step 2 — Bring up the stack

```bash
docker compose up -d --build
# containers: mysql, mock-sap-api, mock-mes-api, ai-agent, cmsd-twin-service, web-dashboard
docker compose ps
```

- ai-agent → http://localhost:8003
- cmsd-twin-service → http://localhost:8000
- web-dashboard → http://localhost:5173

The containers need network egress to `https://a33p.ucc.cloud`. If a corporate proxy is
required, add `HTTP_PROXY`/`HTTPS_PROXY` to the `ai-agent` and `cmsd-twin-service` env
blocks in `docker-compose.yml`.

## Step 3 — Connect an LLM + embedding provider

In the dashboard (**Setup Wizard → Step 1: Connect LLM**), or via API:

```bash
curl -X POST http://localhost:8003/api/agent/v1/agent/connect \
  -H 'Content-Type: application/json' \
  -d '{"chat":{"provider_type":"deepseek","host":"https://api.deepseek.com","api_key":"...","chat_model":"deepseek-chat"},
       "embed":{"provider_type":"ollama","host":"http://host.docker.internal:11434","chat_model":"","embed_model":"qwen3-embedding:4b"}}'
```

Confirm: `GET /api/agent/v1/agent/status` → `connected: true`.

## Step 4 — Add & discover the SAP source

In the dashboard (**Setup Wizard → Step 2: Connect Sources**):

1. Click **🔵 Real SAP** — pre-fills `https://a33p.ucc.cloud/sap/opu/odata/sap/API_PRODUCTION_ROUTING`,
   Basic auth, `extra_headers: {sap-client: "200"}`.
2. Enter your SAP **username** and **password**.
3. Click **Test Connection** (the mock-style health probe may report failure for SAP —
   that's fine; SAP OData services don't expose `/health`. The Discover step is the real
   connectivity test.)
4. Click **🔍 Discover SAP** → fetches `$metadata`, parses it, indexes the
   `source-schema` RAG corpus. You'll see "Discovered N entity sets; indexed M chunks."
5. The **EntitySetBrowser** appears: browse entity sets (e.g.
   `ProductionRoutingOperation` with `StandardWorkQuantity1` + `sap:unit=StandardWorkQuantityUnit1`),
   expand properties, click **Sample 3** for a LOCAL-ONLY row preview (never sent to the
   LLM), and tick the entity sets you want available for mapping.

## Step 5 — Recommend endpoints → map → confirm

In the dashboard (**Setup Wizard → Step 3: Guided Builder**):

1. Pick a CMSD entity (e.g. **Process**).
2. The **🎯 Endpoint recommendation** panel appears. Click **Recommend endpoints** →
   the LLM (over the `source-schema` RAG) proposes a covering set of OData endpoints with
   per-field attribution, join keys, coverage gaps, and `unit_from_field` for `sap:unit`
   fields.
3. Click **Approve & pre-fill** → the endpoints list is populated.
4. **Fire All** to fetch the (live SAP) payloads → approve → **Map** (the LLM now maps
   with source-side `sap:label` semantics + target CMSD, so cryptic fields resolve).
5. Review flagged fields, apply transforms, **Confirm**. The mapping is written to
   `.agent-mappings/{id}.json` with `source.auth_encrypted` (Fernet) + `source.headers`
   (`Accept`, `DataServiceVersion`) + `source.params` (`sap-client`, `$format`).

## Step 6 — Run the twin off live SAP

From the dashboard **Mapping Registry** tab → **Generate**, or via API:

```bash
curl -X POST http://localhost:8000/api/cmsd/v1/refresh \
  -H 'Content-Type: application/json' \
  -d '{"mapping_ids":["<your-confirmed-mapping-id>"]}'
curl http://localhost:8000/api/cmsd/v1/digital-twin/full
```

`MappingDrivenFactory` fetches live SAP rows (OData v2 `d.results`), resolves
`unit_from_field` deterministically (e.g. `5 MIN` → `Duration(300 seconds)`), coerces
types, and builds CMSD instances. `_connection.source_url` on each instance points at
`a33p.ucc.cloud`, not the mock.

## Step 7 — Automated smoke

With the stack up + LLM connected:

```bash
SAP_E2E=1 \
SAP_BASE_URL=https://a33p.ucc.cloud/sap/opu/odata/sap/API_PRODUCTION_ROUTING \
SAP_CLIENT=200 SAP_USERNAME=<user> SAP_PASSWORD=<pass> \
python -m pytest tests/test_e2e_real_sap.py -v -s
```

This exercises: create SAP source → `/discover` (asserts `ProductionRoutingOperation`
indexed) → `/schema` (asserts metadata-only, no creds) → `/mapping/recommend-endpoints`
(asserts covering-set structure, no creds). Skips gracefully if `SAP_E2E` unset or the
LLM isn't connected.

## Troubleshooting

- **`/discover` returns 0 chunks indexed** → the embedder isn't connected or failed
  (chunks fall back to zero vectors, which makes retrieval useless). Confirm
  `/agent/status` shows an embed provider and `GET /rag/stats` shows a non-zero count.
- **`/discover` 502 / connection error** → the `ai-agent` container can't reach
  `a33p.ucc.cloud`. Check DNS/egress/proxy from inside the container
  (`docker exec ai-agent curl -I https://a33p.ucc.cloud`).
- **`/refresh` auth fails / 401** → the confirmed mapping has `auth_encrypted` but the
  `cmsd-twin-service` container doesn't have the same `SAP_CRED_KEY` (decrypt fails →
  falls back to `{"type":"none"}`). Ensure both services share the key.
- **Sources vanish after an `ai-agent` restart** → `SAP_CRED_KEY` changed or is unset;
  the encrypted store can't be decrypted and starts empty. Use a stable key.
- **`unit_from_field` leaves the value unconverted** → the SAP unit code isn't in the
  time-units table yet (`shared/odata/units.py` covers SEC/MIN/HUR/DAY). Extend the table
  for weight/length codes; unknown codes produce a `field_warning` (no crash, no guess).
- **Pre-existing `tsc` errors** → the dashboard has 8 pre-existing TypeScript errors
  unrelated to this feature (Vite dev doesn't typecheck, so it still runs). This
  feature's files are tsc-clean.

## Files added / changed (summary)

New: `shared/odata/{__init__,source_schema,parser,client,units,auth}.py`, `shared/crypto.py`,
`ai_agent/odata_ingest.py`, `ai_agent/recommender.py`, `web_dashboard/src/components/{EntitySetBrowser,EndpointRecommendation}.tsx`,
`scripts/sap_metadata_probe.py`, `tests/test_e2e_real_sap.py`, `SAP_ODATA_RUNBOOK.md`.
Tests: `ai_agent/tests/{test_odata_parser,test_crypto,test_connection_manager_persistence,test_mapping_factory_runtime,test_recommender,test_coerce_backfill}.py`.
Changed: `ai_agent/{routes,retriever,mapping_engine,connection_manager}.py`,
`cmsd_twin_service/{api_client,mapping_factory}.py`, `shared/coerce.py`,
`web_dashboard/src/{services/agentApi.ts,components/{ConnectSources,MappingWizard}.tsx}`,
`docker-compose.yml`.