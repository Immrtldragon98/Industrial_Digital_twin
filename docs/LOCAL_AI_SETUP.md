# Local AI setup

## 1. Install Ollama on the host PC

Download Ollama for Windows, then open PowerShell:

```powershell
ollama pull qwen3:1.7b
ollama pull embeddinggemma
ollama run qwen3:1.7b
```

Exit the chat after the model responds. Ollama continues serving its local API. The application reaches the Windows host through `host.docker.internal:11434`.

## 2. Start Reliability Twin

```powershell
Copy-Item .env.example .env
docker compose up --build
```

EmbeddingGemma runs through the same Ollama service as Qwen. The backend container therefore stays small and does not install PyTorch, SentenceTransformers or a CUDA toolkit.

## 3. Use the knowledge workspace

1. Import the equipment hierarchy first.
2. Select an exact mapped equipment.
3. Open **AI knowledge**.
4. Choose document type and import a PDF, DOCX, Excel, CSV, TXT or Markdown file.
5. Ask an equipment-scoped question.
6. Review the answer and expand its cited source excerpts.

Documents with an unknown equipment number are rejected. Duplicate files are detected by SHA-256. If Ollama is down, the system returns retrieved evidence and labels the model offline. If EmbeddingGemma cannot load, keyword retrieval remains available.

## Model sizing

`qwen3:1.7b` is the laptop default for an 8 GB RAM / 4 GB VRAM machine. No database migration is required when changing Qwen.

## Privacy boundary

With local Ollama and EmbeddingGemma, document processing and generation remain on the configured plant machine/network. Do not configure a cloud endpoint unless plant data governance permits it.
