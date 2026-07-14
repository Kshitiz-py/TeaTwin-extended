# Run TeaTwin-extended locally — step-by-step

> **Audience:** you just pulled `feature/sap-odata-connector` (or `main`) and want to run the whole project on your machine for the first time.
> This is a click-by-click guide. For architecture depth, read [`README.md`](README.md). For real-SAP specifics, read [`sap-mes-cmsd-twin/SAP_ODATA_RUNBOOK.md`](sap-mes-cmsd-twin/SAP_ODATA_RUNBOOK.md).

The project runs as **6 Docker containers** (MySQL + mock SAP + mock MES + AI agent + CMSD twin service + web dashboard). You don't need Python or Node installed on your host — Docker brings everything up. You only need an LLM if you want the AI mapping features (there's a free local option).

---

## 0. Prerequisites (install once)

| Tool | Why | Notes |
|---|---|---|
| **Git** | clone the repo | |
| **Docker Desktop** | runs the 6 containers | Start Docker Desktop before continuing. On Windows, use the WSL2 backend. |
| **An LLM** (optional) | powers endpoint recommendation + field mapping | Free local option: **Ollama**. Or any API key: OpenAI / DeepSeek / Anthropic / OpenRouter / etc. Without an LLM you can still browse, but mapping/recommendation won't run. |
| Python 3.12 (optional) | only if you want to run the unit tests locally | Not needed to run the stack. |

If you go with **local Ollama**, install it and pull a chat + embedding model once:
```bash
ollama pull llama3.1          # chat model (or qwen2.5, etc.)
ollama pull qwen3-embedding:4b  # embedding model
```

---

## 1. Clone & checkout the branch

```bash
git clone https://github.com/Kshitiz-py/TeaTwin-extended.git
cd TeaTwin-extended
git checkout feature/sap-odata-connector
```
> Already cloned? `git pull && git checkout feature/sap-odata-connector`.

You should now see (among others): `sap-mes-cmsd-twin/`, `cmsd-pydantic-master/`, `PROCS_ISM_LATEX_Template/`, `README.md`, and this file.

---

## 2. (Optional) Pre-configure the LLM for auto-connect

You can skip this and configure the LLM in the dashboard later (Step 6). To auto-connect on startup instead:

```bash
cd sap-mes-cmsd-twin
cp .env.example .env
```
Edit `.env` and set the `LLM_*` values for your provider, e.g. for local Ollama:
```env
LLM_PROVIDER=ollama
LLM_HOST=http://host.docker.internal:11434
LLM_CHAT_MODEL=llama3.1
LLM_EMBED_MODEL=nomic-embed-text
```
> **Important:** the AI agent runs *inside* Docker, so a local Ollama on your host is reached at `http://host.docker.internal:11434` (not `localhost`). For Ollama Cloud or any hosted provider, use their URL + `LLM_API_KEY`.

You do **not** need `SAP_CRED_KEY` for the mock-data run (see Step 8 for real SAP).

---

## 3. Bring up the stack

```bash
cd sap-mes-cmsd-twin
docker compose up -d --build
```
The first build takes a few minutes (pip install for the 4 Python services, npm install for the dashboard, MySQL image pull). Subsequent starts are fast.

---

## 4. Verify all containers are up

```bash
docker compose ps
```
You should see 6 services. `mysql`, `ai-agent`, and `cmsd-twin-service` show `(healthy)` after ~30s; the rest show `Up`:

| Service | Port on your host | Status |
|---|---|---|
| `cmsd-dashboard` (web) | **http://localhost:5173** | Up |
| `cmsd-twin-service` | http://localhost:8000 | Up (healthy) |
| `ai-agent` | http://localhost:8003 | Up (healthy) |
| `mock-sap-api` | http://localhost:8001 | Up |
| `mock-mes-api` | http://localhost:8002 | Up |
| `factory-mysql` | localhost:3306 | Up (healthy) |

If something isn't up, check its logs: `docker compose logs <service>`.

---

## 5. Open the dashboard

Open **http://localhost:5173** in your browser. You'll land on the **Setup Wizard**.

---

## 6. Setup Wizard — Step 1: Connect the LLM

- If you pre-configured `.env` in Step 2, the agent is already connected — you'll see a green "connected" pill. Skip to Step 7.
- Otherwise, in the **AgentConnect** panel:
  - **Provider:** pick one (`ollama`, `openai`, `deepseek`, `anthropic`, …).
  - **Host / API key / Chat model / Embed model:** fill per your provider.
    - Local Ollama → host `http://host.docker.internal:11434`, chat model `llama3.1`, embed model `nomic-embed-text`.
    - API-key providers → host + key + model (embed fields can be blank to reuse the chat provider).
  - Click **Test** → should succeed.
  - Click **Connect**.

---

## 7. Setup Wizard — Step 2: Connect data sources

- Click **"Pre-fill Mock SAP and Mock MES sources"**.
  This adds two sources: `http://mock-sap-api:8001/api/sap/v1` and `http://mock-mes-api:8002/api/mes/v1`.
  > These use the in-container hostnames because the **AI agent container** fetches them (not your browser). Don't change them to `localhost`.
- Click **Test** on each source → both should turn green.

---

## 8. Setup Wizard — Step 3: Guided Builder (map an entity)

This is the core flow — map a mock API to a CMSD entity.

1. In **RichEntityPicker**, pick a CMSD entity — start with **`Resource`**.
2. Click **Recommend endpoints** → the LLM (over RAG) proposes a covering set of SAP OData endpoints for `Resource`, with per-field attribution and join keys.
3. Click **Approve** → the endpoint rows pre-fill.
4. Click **Fire All** (fetch) → raw JSON payloads load; inspect in the PayloadViewer.
5. The LLM proposes a **field mapping** (streamed) → review it in the **Mapping Table**.
   - Use **TransformSelector** per field if a value needs a transform (e.g. `unit_conversion`, `enum_map`, `to_decimal`).
   - Approve fields, flag uncertain ones, or edit. Use **MappingChat** to ask the LLM to adjust.
6. Click **Confirm** → the mapping is saved to the Review Queue (`.agent-mappings/*.json`).

Repeat for another entity (e.g. `PartType`, `Order`) if you like.

---

## 9. Setup Wizard — Step 5: Review Queue → Generate

1. Open the **Review Queue**.
2. Click **Pre-flight** → checks dependency closure, relations, field coverage, API reachability. Resolve any blockers.
3. Click **Generate** → runs the build pipeline through 6 phases:
   `preflight → fetching APIs → building entities → merging with twin → detecting changes → applying to twin`.
4. When it finishes, the twin is live.

---

## 10. Switch to Dashboard mode and watch the twin

- The app switches to **Dashboard** mode once a source exists.
- **Factory Topology** tab: an SVG floor plan with resources placed from the layout, color-coded by live status, plus material-flow connection edges.
- KPI cards: resources / resource classes / part types / orders / jobs / connections.
- **Change Log** tab: live change events streamed over WebSocket.
- Use the **Refresh** toolbar to re-run a mapping cycle, or enable auto-poll (10s / 30s / 60s / 5m).

---

## 11. Verify it worked (quick checks)

From your host:
```bash
# Twin summary — JSON with entity counts
curl http://localhost:8000/api/cmsd/v1/digital-twin/summary

# Agent health
curl http://localhost:8003/api/agent/v1/health

# Mock SAP has data
curl http://localhost:8001/api/sap/v1/resources | head -c 200
```
Or just look at the dashboard — if the Factory Topology shows resources and the Change Log has entries, you're running.

---

## 12. (Optional) Point it at real SAP instead of the mocks

Follow [`sap-mes-cmsd-twin/SAP_ODATA_RUNBOOK.md`](sap-mes-cmsd-twin/SAP_ODATA_RUNBOOK.md). In short:
1. Generate a Fernet key and export it:
   ```bash
   python -c "from shared.crypto import generate_key; print(generate_key())"
   export SAP_CRED_KEY="<that key>"
   ```
2. Restart the stack with `SAP_CRED_KEY` set (so SAP credentials are encrypted at rest).
3. In the dashboard, add the real SAP source (base URL + client + Basic auth) → **Discover** ingests the `$metadata` → recommend → map → generate.

The LLM never connects to SAP and never sees row data — only metadata (see README §6).

---

## 13. Stop / reset

```bash
cd sap-mes-cmsd-twin
docker compose down        # stop + remove containers; DATA VOLUMES KEPT (mysql_data, chromadb_data, agent_mappings)
docker compose down -v     # ALSO wipe the data volumes → completely fresh start (re-seeds MySQL, re-indexes RAG)
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `port is already allocated` (3306 / 5173 / 8000-8003) | Stop the host service using that port, or remap it in `docker-compose.yml`. |
| `mysql` not healthy | First init takes ~30-60s. Check `docker compose logs mysql`. If it never gets healthy, `docker compose down -v` and re-up. |
| Dashboard loads but "cannot reach agent/twin" | Ensure all containers are up (`docker compose ps`); the dashboard proxies to the in-container service names. |
| LLM **Test** fails (local Ollama) | Use host `http://host.docker.internal:11434` (not `localhost`), and confirm `ollama list` shows the model you named. |
| LLM **Test** fails (API provider) | Check the API key and that the host URL is reachable from inside the container (hosted providers are fine; corporate proxies may block egress). |
| Endpoint **Test** fails for a mock source | The mock sources must stay as `http://mock-sap-api:8001/...` / `http://mock-mes-api:8002/...` (container names). Don't use `localhost`. |
| `cmsd_schema` / `cmsd-pydantic` import error (local Python) | It's pip-installed **in Docker only**. For local Python runs, run from the repo root; the in-code `sys.path` inserts handle it. See README §12. |
| Code changes not reflected | Python twin service hot-reloads (`uvicorn --reload`). For image/dependency changes: `docker compose up -d --build`. |

---

## Where to go next

- **Architecture & concepts:** [`README.md`](README.md) (the big picture, the two instantiation paths, RAG/LLM, security boundary).
- **Multi-API mapping spec:** [`sap-mes-cmsd-twin/PRD_MultiAPI_Mapping.md`](sap-mes-cmsd-twin/PRD_MultiAPI_Mapping.md).
- **Real SAP runbook:** [`sap-mes-cmsd-twin/SAP_ODATA_RUNBOOK.md`](sap-mes-cmsd-twin/SAP_ODATA_RUNBOOK.md).
- **Run the unit tests** (optional, needs local Python 3.12):
  ```bash
  cd sap-mes-cmsd-twin
  python -m pytest ai_agent/tests/ -v     # mocks chromadb/ollama — no Docker needed
  ```

Happy mapping. 🚀