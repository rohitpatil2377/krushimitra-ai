# कृषीमित्र AI — Krushimitra AI

**A voice-first Marathi AI agronomist for Maharashtra farmers**, built for low-end Android on
weak networks. A farmer photographs a crop or asks a question in Marathi; the app answers in
Marathi, in text and voice.

The wedge is not disease *detection* — plenty of apps do that. It is **disease severity
intelligence** (how bad, how fast, what to do now) and a **Digital Crop Twin** that turns each
season into a timeline, and that timeline into a dataset nobody else has.

> **Status:** working end to end, not yet in farmers' hands. Disease detection runs against a
> real self-hosted vision model. Weather and mandi prices run on sample data until two free API
> keys are added. See [What is real today](#what-is-real-today).

---

## The one idea worth understanding

A wrong answer costs a farmer money and a crop. So every module is built so that
**"I don't know" is a first-class answer**, and so that sample data can never be mistaken for a
real one.

Four rules are enforced in code and pinned by tests, not left to convention:

| Rule | Where it lives |
|---|---|
| **Abstain.** Below `VISION_MIN_CONFIDENCE` (0.55), or when no crop is in the photo, the API returns `identified=false` with **no treatment and no severity** — plus how to retake the photo. | `app/api/vision.py` |
| **Never state a dose.** Name the active ingredient and the cultural steps; the quantity depends on a formulation percentage printed on a bottle we cannot see. Every chemical recommendation carries a KVK note. | `app/services/knowledge.py`, both copilot prompts |
| **Badge honestly.** "Is this real?" is answered by `model_version` / `source`, never by whether the backend replied — a reachable backend can still serve mocks. Anything starting with `mock` is badged **नमुना माहिती**. | every service |
| **Never predict a price.** Mandi rates are not forecastable. The app states the spread, the measured trend and the data's age, then sends the farmer to phone the APMC. | `app/services/market/advice.py` |

A worked example: told a photo was onion when it showed pomegranate, the live model returned
`not_a_plant` at 1.00 confidence and the app showed no treatment at all. That is the system
working, not failing.

---

## What is real today

| Module | Status | To make it live |
|---|---|---|
| **Disease detection** | **Real** — self-hosted multimodal model, measured | `VISION_BASE_URL` (done) |
| **Irrigation** | **Real maths** on sample weather | goes live with weather |
| Weather + crop advisories | Sample data | `OPENWEATHER_API_KEY` (free) |
| Mandi prices | Sample data | `DATAGOV_API_KEY` (free) |
| Marathi chatbot | Sample data | `LLM_BASE_URL` or `ANTHROPIC_API_KEY` |
| Crop twin + accounts | **Real** (SQLite) | — |

Nothing needs a code change to switch over: **presence of the key is the opt-in.** `GET /health`
reports which provider is actually serving each module.

**Accuracy is not yet measured.** The vision model answers correctly on a handful of photos;
that is encouraging, not a number. `scripts/probe_vision_model.py` scores top-1 against
ground-truth labels once there are enough real photos.

---

## Quick start

Requires **Node ≥ 22.13** (the repo pins Node 24 via `.nvmrc`) and **Python 3.13**.

```bash
# terminal 1 — backend (SQLite, no setup, runs with zero keys)
cd krushimitra-backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# terminal 2 — app
nvm use
npm install
npx expo start          # scan the QR with Expo Go
```

`--host 0.0.0.0` matters: without it your phone cannot reach the backend. The app derives the
backend URL from the Metro host, so it usually just works; a standalone build sets it in-app
under **⚙️ सर्व्हर जोडणी**.

Then open `http://localhost:8000/health` to see which providers are live.

### Tests

```bash
cd krushimitra-backend
PYTHONPATH=. .venv/bin/python -m pytest tests/ -q --ignore=tests/test_vision_pipeline.py   # 115
npx tsc --noEmit                                                                            # app
```

`test_vision_pipeline.py` is excluded because it is a *script*, not a pytest module — it needs a
stub model server running first. See `krushimitra-backend/tests/README.md`.

---

## How it is put together

```
app/                        Expo Router screens (file = route)
  (tabs)/                   Home dashboard + the 5 advisory screens
  cycle/                    Crop twin: add a crop, season timeline
  login.tsx                 Phone-OTP
src/
  services/                 One folder per external service: interface + real + mock
  store/                    Zustand (farm profile, auth, diagnosis)
  i18n/locales/{mr,en}/     Every user-facing string
  constants/                colors, crops, Maharashtra districts
krushimitra-backend/
  app/api/                  FastAPI routes
  app/services/
    vision/                 Closed 24-disease taxonomy + self-hosted VLM adapter
    knowledge.py            Marathi agronomy, keyed by DETECTED disease (not by crop)
    weather/advice.py       Spray windows + real Maharashtra disease pressure
    irrigation/             FAO-56 soil water balance (Hargreaves ET0, Kc by stage)
    market/                 Agmarknet + net-realisation ranking
    twin.py                 Growth stage + an auditable health score
docs/                       PRD, ARCHITECTURE, AI_ARCHITECTURE, DATASET, ROADMAP
```

**Every external service sits behind an interface** with a real and a mock implementation.
Features are built on the mock, then flipped live by adding a key. The app degrades gracefully —
it shows sample data rather than crashing, and says that is what it is doing.

A few decisions that are easy to get wrong and are deliberate here:

- **Advice is keyed by the detected disease, not the crop.** The original code gave every onion
  photo the purple-blotch treatment.
- **Irrigation uses Hargreaves, not Penman-Monteith** — the free weather tier has no solar
  radiation or wind, and FAO-56 Annex 4 names Hargreaves as the temperature-only fallback.
- **Drip is not a small flood.** It replaces daily consumption; flood refills a depleted profile.
  Treating them the same recommends a 10-day gap no pomegranate grower would accept.
- **Mandi prices rank by what the farmer nets after transport**, not the headline rate.
- **GPS never replaces the district picker** — a denied permission silently keeps the picker,
  which works offline.

---

## Privacy and secrets

- **No secret ever ships in the app.** `EXPO_PUBLIC_*` values are bundled into the APK and
  readable by anyone; every real key lives in `krushimitra-backend/.env` and the app calls the
  backend, never a vendor API.
- `.env`, farmer photos (`data/captures/`) and the SQLite database (phone numbers) are
  gitignored.
- Captured coordinates are rounded to ~110 m **before** storage — enough to map disease pressure
  onto a village, not enough to point at a household. `farmer_id` is an anonymous per-install id,
  never a phone number.

---

## Before this reaches a real farmer

- **OTP is not actually sent.** No SMS provider is wired; any phone plus the dev OTP logs in.
  `/health` reports `auth_otp_is_real: false` rather than faking it.
- **The backend is HTTP on a LAN**, and the APK enables cleartext traffic to reach it. Both must
  go before production.
- **Diagnosis accuracy is unmeasured.** Needs real photos with known labels.

---

## Docs

| | |
|---|---|
| [docs/PRD.md](docs/PRD.md) | What is being built and for whom |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design |
| [docs/AI_ARCHITECTURE.md](docs/AI_ARCHITECTURE.md) | Model strategy |
| [docs/DATASET.md](docs/DATASET.md) | The data moat, and why the split group matters |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Phasing |
| [CLAUDE.md](CLAUDE.md) | Locked product decisions and build log |

---

© 2026 Rohit Patil. All rights reserved — see [LICENSE](LICENSE).
