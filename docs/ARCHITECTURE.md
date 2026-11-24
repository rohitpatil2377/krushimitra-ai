# KrushiMitra AI — System Architecture

## Stack decision (locked with founder)
Hybrid: **keep the React Native/Expo app** (already built, Steps 1–3) + **add a FastAPI/Python brain**.
The founder is a Data Scientist (Python/ML/CV/GenAI/RAG/FastAPI) → effort goes into the backend.
Flutter was in the original blueprint but rejected (no advantage, throws away working code).

```
┌──────────────────────────┐
│  React Native / Expo app │  voice button, camera, crop timeline, offline cache
└─────────────┬────────────┘
              │ HTTPS (JWT)
┌─────────────▼────────────────────────────────────────────────┐
│  FastAPI backend (core)                                       │
│  ├─ /auth        phone OTP                                    │
│  ├─ /copilot     orchestrator: STT → intent → RAG/LLM → TTS   │
│  ├─ /vision      detection + severity inference               │
│  ├─ /crop-cycles digital twin CRUD + timeline                 │
│  ├─ /recommend   treatment plans (LLM+KB)                     │
│  └─ /health-score                                             │
└───┬───────────┬──────────────┬───────────────┬───────────────┘
┌───▼───┐  ┌────▼────┐   ┌─────▼─────┐   ┌──────▼──────┐
│Postgres│  │   S3    │   │ Model svc │   │ 3rd-party   │
│+pgvector│ │ images  │   │ (PyTorch) │   │ Bhashini,   │
│ twin+KB │ │         │   │ in-proc → │   │ LLM(Claude),│
│  vecs   │ │         │   │ GPU later │   │ Weather API │
└─────────┘ └─────────┘   └───────────┘   └─────────────┘
```

### Deliberate simplifications for a solo founder
- **pgvector inside Postgres** instead of a standalone FAISS service. One DB to operate. FAISS only
  past ~1M vectors (years away).
- **Models run in the FastAPI process (CPU)** at MVP volume. Split to a GPU model service
  (Triton/TorchServe) only when latency/volume demands it.
- **Async heavy work** via Celery/RQ + Redis (or FastAPI BackgroundTasks for the first weeks).
- Supabase Edge Functions (used in the app MVP) are **replaced** by FastAPI — Supabase can't run PyTorch.

## Database schema (Digital Crop Twin core)
```sql
farmers(id PK, phone UNIQUE, name, preferred_lang ENUM('mr','hi','en'), village, district, created_at)
farms(id PK, farmer_id FK, name, lat, lng, area_acres)

crop_cycles(id PK, farm_id FK, crop ENUM('onion','soybean','pomegranate'),
            variety, sowing_date, expected_harvest, status ENUM('active','harvested','abandoned'),
            current_health_score INT, created_at)

crop_events(id PK, crop_cycle_id FK,
            type ENUM('image','voice','diagnosis','treatment','note','weather'),
            day_index INT,            -- days since sowing
            created_at)

images(id PK, crop_event_id FK, s3_key, width, height, captured_at)

diagnoses(id PK, image_id FK, crop, disease, confidence FLOAT, model_version, created_at)

severity_assessments(id PK, diagnosis_id FK,
            level ENUM('healthy','mild','moderate','severe','critical'),
            severity_pct FLOAT, risk_level, method ENUM('llm','segmentation'),
            model_version, created_at)

recommendations(id PK, crop_cycle_id FK, diagnosis_id FK NULL,
            treatment_plan JSONB, spray JSONB, prevention JSONB,
            followup_date DATE, source_citations JSONB, lang, created_at)

health_scores(id PK, crop_cycle_id FK, score INT, breakdown JSONB, created_at)

conversations(id PK, farmer_id FK, crop_cycle_id FK NULL, created_at)
messages(id PK, conversation_id FK, role ENUM('user','assistant'),
            text, audio_s3_key NULL, lang, created_at)

kb_documents(id PK, source, crop, title, url, created_at)
kb_chunks(id PK, kb_document_id FK, content, embedding VECTOR(1024))   -- pgvector

expert_labels(id PK, image_id FK, labeler_id, disease, severity_level,
            severity_pct, bbox_or_mask JSONB, verified BOOL, created_at)  -- the data moat
```
`crop_events.day_index` is what makes this a **twin, not CRUD**: progression over time per cycle
powers journey reports, health trends, and later yield prediction.

## API specification (key endpoints)
```
POST /auth/otp/request   {phone}                 → sends OTP
POST /auth/otp/verify    {phone, otp}            → {jwt}

POST /copilot/ask        multipart: audio? text? image? crop_cycle_id?
                         → {transcript, reply_text, reply_audio_url, lang,
                            diagnosis?, severity?, recommendation?}
   # THE product behind one call — what the voice button hits

POST /vision/diagnose    multipart: image, crop?  → {crop, disease, confidence}
POST /vision/severity    {diagnosis_id}           → {level, severity_pct, risk, action}

POST /crop-cycles        {farm_id, crop, sowing_date, variety} → crop_cycle
GET  /crop-cycles/{id}/timeline       → [crop_events + images/diagnoses]
GET  /crop-cycles/{id}/health-score   → {score, breakdown, trend}

POST /recommendations    {crop_cycle_id, diagnosis_id} → treatment plan (RAG)
POST /feedback           {message_id, useful: bool, correction?}   # fuels the moat
```
Auth: JWT via phone OTP (no passwords). Write endpoints idempotent where possible (flaky rural nets).

## Backend folder structure (new sibling repo: `krushimitra-backend/`)
```
krushimitra-backend/
  app/
    main.py
    api/        auth.py copilot.py vision.py crop_cycles.py recommend.py
    core/       config.py security.py db.py s3.py
    models/     sqlalchemy ORM (schema above)
    schemas/    pydantic request/response
    services/
      stt/      bhashini.py whisper.py base.py     # swappable, like the app
      tts/      bhashini.py base.py
      vision/   detector.py severity.py base.py    # mock → llm → trained
      llm/      copilot.py rag.py prompts/
      weather/  openweather.py
    workers/    celery_app.py tasks.py
    ml/         training/ notebooks/ datasets/ checkpoints/
  alembic/      migrations
  tests/
  Dockerfile  docker-compose.yml  pyproject.toml  .env.example
```
The Expo app's `src/services/*` (already built as swappable interfaces) now point at FastAPI — the
app barely changes. That is the payoff of the interface pattern.

## Deployment & CI/CD
**MVP (cheap, boring, reliable):**
- App: Expo EAS build + OTA; distribute APK via WhatsApp groups first, Play Store later.
- Backend: one Dockerized FastAPI on a small VM (Lightsail / Hetzner / Railway / Fly.io).
- Managed Postgres + pgvector (Supabase Postgres / Neon / RDS). S3 for images. Models in-process (CPU).
- CI/CD: GitHub Actions → lint/test → build Docker → deploy on merge to `main`; `alembic upgrade` on deploy.

**Scale-up (only when metrics demand):** GPU model service (ECS/Fargate or k8s), Redis+Celery,
CloudFront CDN, read replicas. Do not pre-build.
