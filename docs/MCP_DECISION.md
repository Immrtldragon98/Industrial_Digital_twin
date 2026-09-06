# MCP decision for Reliability Twin

MCP is not required for the core application. FastAPI, PostgreSQL/pgvector, Ollama and the RAG services should continue to handle the dashboard, parameter history, history cards and reliability coaching directly.

Add an MCP boundary when Reliability Twin must connect an AI host to external systems:

- read-only SAP equipment, notification, order and measurement-point queries;
- controlled plant document-library search;
- condition-monitoring or historian queries;
- exposing approved Reliability Twin resources and analysis tools to ChatGPT, VS Code or another MCP host.

Recommended future MCP resources:

- `equipment://{equipment_number}/twin`
- `equipment://{equipment_number}/history-card`
- `equipment://{equipment_number}/parameters`
- `document://{document_id}`

Recommended future read-only tools:

- `search_sap_notifications`
- `get_maintenance_orders`
- `get_condition_readings`
- `calculate_reliability_metrics`

Do not expose SAP write operations initially. Any later mutation must require authentication, role checks, explicit human confirmation and an immutable audit record.
