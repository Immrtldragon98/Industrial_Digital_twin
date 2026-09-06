# Reliability Twin v0.2

Equipment digital-twin foundation for maintenance engineers and planners. It maps the SAP technical-object hierarchy and keeps actual condition, maintenance, failure and component-change history attached to each asset.

## Run locally

Install Docker Desktop, copy `.env.example` to `.env`, then run `docker compose up --build`. Open `http://localhost:3000`; API docs are at `http://localhost:8000/docs`.

Before the first authenticated startup, replace `AUTH_SECRET` and `ADMIN_PASSWORD` in `.env`. The first Admin account is created from those values. There is no public registration; Admin creates Viewer and Engineer accounts from the Accounts tab.

| Role | Access |
|---|---|
| Viewer | Read dashboards, parameters, history cards and reliability answers |
| Engineer | Viewer access plus condition/history/document imports |
| Admin | Full access including hierarchy imports and account creation |

AI starts disabled so the core application can be verified independently. After Ollama has `qwen3:1.7b` and `embeddinggemma`, set `AI_ENABLED=true` and restart the backend.

The backend intentionally parses DOCX files using Python's standard library. It does not install `python-docx`/`lxml`, avoiding a large, unnecessary dependency that commonly timed out during Docker builds.

Plant exports, uploaded documents and `.env` files are deliberately excluded from Git. Keep real SAP and equipment data local, especially when the repository is public.

## Implemented

- React + TypeScript planner dashboard and FastAPI REST service
- PostgreSQL + pgvector data layer (free/local)
- SAP-style hierarchy import anchored by equipment number
- Excel imports for condition readings, maintenance, failures and component changes
- Per-equipment twin combining latest condition and history
- MTBF, MTTR, availability, failure count, downtime and risk summary
- Import audit jobs with skipped-row/error reporting
- Provider-neutral RAG-ready document schema
- Working equipment-scoped RAG: knowledge upload, laptop-safe EmbeddingGemma, pgvector retrieval, Ollama/Qwen answers and source excerpts
- Keyword fallback and explicit offline status when local AI is unavailable

## Excel contracts

Every non-hierarchy sheet needs `Equipment Number` (aliases such as Equipment, Equipment No, Eq No and Technical Object are recognized).

| Import | Required | Useful optional columns |
|---|---|---|
| Condition | Equipment Number, Timestamp, Value | Parameter Code, Parameter Name, Unit, Quality, Normal/Warning/Critical Min/Max |
| Maintenance | Equipment Number | Order Number, Description, Actual Start, Actual End, Downtime Hours |
| Failure | Equipment Number | Notification Number, Description, Cause, Start, End, Downtime Hours |
| Changes | Equipment Number, Component | Timestamp, Reason, Order Number |

Unknown equipment rows are skipped and reported; the system never guesses asset mappings.

The equipment twin shows the latest value, source, quality, status, last-update age, operating limits and recent history for every parameter on the selected asset and all assemblies/components below it. The history card combines SAP maintenance orders, failure notifications, downtime and component changes in one timeline.

Reliability metrics do not assume a fixed one-year window. The calculation begins from an available commissioning/installation date or dated failure history. Missing observation evidence is reported instead of producing a false KPI.

## WRM hierarchy model

The structured `SAP Hierarchy` workbook is imported as an unlimited-depth tree:

`WRM functional location → WRM line equipment → sub-equipment → assembly → component`

Examples include `Finishing Mill → Gearbox 1 Assembly → Input Shaft → Bearing` and `Finishing Mill → Stand Assembly → Roll Assembly → Sleeve`. Every installed object needs a unique Object ID. Reusable SAP material codes belong in BOM/component metadata and must not be used as the physical asset identity. The current pilot intentionally imports only the CH2/WRM branch; other CH2 areas are ignored.

## AI direction

Recommended laptop stack: PostgreSQL + pgvector, multilingual `embeddinggemma` served by Ollama, and Qwen served by Ollama. This avoids installing PyTorch/CUDA libraries inside the API container. A production server can later use BGE-M3 behind the same embedding interface. RAG answers must cite source, date and equipment scope and state when plant evidence is insufficient.

Start with one pilot system, validate mappings and reliability calculations, then expand. See `docs/DATA_REQUEST.md`.

Local AI installation is documented in `docs/LOCAL_AI_SETUP.md`. The Qwen model is configurable; do not finalize its size until the host PC RAM/GPU is known.
