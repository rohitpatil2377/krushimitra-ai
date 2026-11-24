# KrushiMitra AI — Backend (FastAPI)

The Python brain for KrushiMitra AI: voice-first copilot, crop disease detection + severity,
Digital Crop Twin, and treatment advice. See ../docs for the full blueprint
(PRD, ARCHITECTURE, AI_ARCHITECTURE, DATASET, ROADMAP).

> **Runs end-to-end with zero API keys** — every AI service has a mock implementation
> (`USE_MOCKS=true`). Flip to real (Claude/Bhashini) by adding keys to `.env` and setting `USE_MOCKS=false`.

## Quick start (no database needed — mock endpoints)
```bash
cd krushimitra-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
# open http://localhost:8000/docs
```
Try `POST /copilot/ask` with form field `text=कांद्याला किती पाणी द्यावे?` → Marathi answer.
Try `POST /vision/diagnose` with an image + `crop=pomegranate`.

## With the database (Digital Twin + auth endpoints)
```bash
docker compose up -d db           # Postgres 16 + pgvector
python -m scripts.init_db         # create extension + tables (dev)
# or, real migrations:
alembic revision --autogenerate -m "init"
alembic upgrade head
```

## Run everything in Docker
```bash
docker compose up --build         # api on :8000, db on :5432
```

## Tests
```bash
pip install pytest
pytest -q                         # smoke tests (no DB required)
```

## Architecture
```
app/
  main.py                FastAPI app + /health
  api/                   auth, copilot, vision, crop_cycles, recommend
  core/                  config, db, security (JWT), s3 (local storage)
  models/                SQLAlchemy ORM (Digital Crop Twin) + enums
  schemas/               pydantic request/response
  services/              swappable: stt/ tts/ vision/ llm/  (mock -> real)
  ml/                    training/ datasets/ checkpoints/ (real models later)
```
Every external/AI capability sits behind an interface with a **mock** and a **real** impl, chosen by
a factory (`get_stt`, `get_copilot`, `get_detector`, ...). Same pattern as the Expo app.

## Service status
| Capability | Mock (now) | Real (TODO) |
|---|---|---|
| Copilot LLM | keyword Marathi answers | Claude + RAG (`services/llm/claude_copilot.py`, `rag.py`) |
| Disease detection | crop→sample disease | Claude vision → fine-tuned PyTorch (`services/vision`) |
| Severity | confidence-derived band | vision-LLM rubric → lesion-area segmentation |
| STT | rotating sample question | Bhashini/IndicWhisper (`services/stt/bhashini.py`) |
| TTS | none (app uses on-device) | Bhashini Indic-TTS |
| Auth OTP | dev OTP `123456` | SMS/WhatsApp provider |
