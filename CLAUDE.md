# Krushimitra AI (कृषीमित्र AI)

**"Your Personal AI Agriculture Copilot"** — a voice-first AI agronomist for Maharashtra farmers,
built for low-end Android on weak networks. A farmer speaks (Marathi/Hindi/English) and/or
photographs a crop, and the AI answers in voice + text. The wedge is **Disease Severity
Intelligence** (how bad / how fast / what to do now), not just disease detection — plus a
**Digital Crop Twin** (per-cycle image timeline + health score) that compounds into a data moat.

> **This repo = the React Native/Expo app (the frontend).** The venture's Python brain lives in a
> separate `krushimitra-backend/` repo (FastAPI + Postgres/pgvector + PyTorch + RAG). The full
> startup blueprint is in [`docs/`](docs/): PRD, ARCHITECTURE, AI_ARCHITECTURE, DATASET, ROADMAP.
> Read those before backend work. The app's `src/services/*` interfaces point at the mock today and
> will point at the FastAPI backend (not Supabase) once it exists.

## Scope

### Phase 1 MVP — IN SCOPE (build only these 5, in priority order)
1. **Crop disease detection** — photo → likely disease/pest with cause, treatment, prevention (Marathi).
2. **Marathi voice + text chatbot** — ask by voice or text; answer in Marathi (text + read aloud).
3. **Weather forecast** — by location: rain, temp, humidity, alerts + "what this means for your crop".
4. **Irrigation advice** — how much water and when, based on crop + weather.
5. **Mandi prices** — latest prices for selected crops from nearest markets.

### Phase 2 — requested 2026-11-17 (reverses the earlier "out of scope")
6. **Crop twin** — sowing → harvest timeline, health score. *(built)*
7. **Sell crops / input-dealer tie-ups** — *(not built)*. Code is the easy half: these need real
   buyers and real dealers signed up. An "order medicine" screen with an empty directory costs
   more trust than not having one, so this stays a business problem first.

## Key product decisions (locked with the user)
- **Auth (locked 2026-11-17, reverses the earlier "no auth" decision):** phone-OTP login, because
  crop tracking is personal data and has to belong to someone. **Login is required only for the
  crop twin** — diagnosis, chat, weather, irrigation and mandi prices all work signed out. Asking
  for a phone number before a farmer has seen value is the fastest way to lose them at the door.
  **The OTP is not really sent yet** (no SMS provider): any phone + `DEV_OTP` logs in, and both
  `/health` (`auth_otp_is_real`) and the OTP response say so rather than faking "check your SMS".
  Wire a provider before launch.
- **Crops (now):** कांदा (Onion), सोयाबीन (Soybean), डाळिंब (Pomegranate). **Future:** टोमॅटो (Tomato),
  मका (Maize). Defined in `src/constants/crops.ts` — keep this list to the 3 active crops, and keep it
  in step with the backend taxonomy in `krushimitra-backend/app/services/vision/labels.py` (a crop with
  no labels there gets a less precise, all-crops diagnosis).
- **Dosage policy (locked):** name the **active ingredient** and the cultural steps; **never** state a
  quantity, dilution or spray volume. Dose depends on formulation %, crop stage, sprayer and the local
  label — a wrong number poisons a crop or a person. Every chemical recommendation carries `DOSE_NOTE`
  pointing the farmer to their **KVK / Krishi Seva Kendra** for the number. Enforced in
  `krushimitra-backend/app/services/knowledge.py`; the app renders it as a separate red block.
- **Abstain policy (locked):** below `VISION_MIN_CONFIDENCE` (default 0.55), or when no crop is in the
  photo, the API returns `identified=false` with **no treatment and no severity**, plus how to retake the
  photo. A wrong diagnosis costs a farmer money and a crop, so "I'm not sure" is the correct answer, not a
  failure state. Enforced once, in the abstain gate in `krushimitra-backend/app/api/vision.py`.
- **Honest badging (locked):** "is this real?" is answered by `model_version`, never by whether the backend
  replied — a reachable backend can still serve mocks. Anything starting with `mock` is sample data and the
  app badges it "नमुना माहिती". `GET /health` reports `vision_provider` and `vision_is_real`.
- **Dataset split integrity (locked):** every diagnose call carries an optional `context`
  (`plot_id`/`farmer_id`, district, `sowing_date`, device). `plot_id`/`farmer_id` is the **split
  group** — one plot photographed weekly is the *same plant*, so without a grouping key those
  photos straddle train/test and any measured accuracy is fiction. It cannot be reconstructed
  later, so it is captured from the first user. `farmer_id` is an anonymous per-install id (never
  a phone number); coordinates are rounded to ~110 m **before** storage. Rule lives in
  `capture.normalize_context`; `GET /vision/dataset` reports `not_splittable` so the gap is
  visible. See `docs/DATASET.md`.
- **Languages:** app UI is Marathi-default (mr) with English; the venture adds **Hindi** and full
  voice in mr/hi/en. Backend reasons in **English internally** (pivot language), outputs in user's language.
- **Speech-to-text:** Bhashini (AI4Bharat) is the first real implementation, behind a swappable interface.
- **Run target:** Expo Go on a physical Android phone (use phone-hotspot trick on locked networks).

## Tech stack
- **Mobile:** React Native + Expo (SDK 58), TypeScript. Android-first. Requires **Node ≥22.13** (repo pins Node 24 via `.nvmrc`).
- **Navigation:** Expo Router (file-based, in `app/`).
- **State:** Zustand (`src/store/`).
- **Localization:** i18next + react-i18next. Default `mr` (Marathi), fallback `en`. Strings in `src/i18n/locales/`.
- **Backend (venture):** **FastAPI + Postgres/pgvector + S3 + PyTorch + RAG** in a separate
  `krushimitra-backend/` repo. This replaces Supabase Edge Functions (Supabase can't run PyTorch).
  Managed Postgres may still be Supabase/Neon/RDS. See `docs/ARCHITECTURE.md` + `docs/AI_ARCHITECTURE.md`.
- **AI / data services — each behind a swappable interface in `src/services/` (mock → real):**
  - Disease detection: a **self-hosted OpenAI-compatible VLM** (Gemma 3 4B/12B/27B — *1B is text-only and
    cannot do this*; also Qwen2.5-VL etc.), constrained to a closed disease taxonomy; then a **fine-tuned
    crop-disease model** (EfficientNet/YOLOv8-cls), then **severity** via lesion-area segmentation.
    Served by FastAPI `/vision`. Set `VISION_BASE_URL` to go live — no `USE_MOCKS` change needed.
  - Copilot chatbot: **LLM + RAG** over an agronomy KB, via FastAPI `/copilot/ask`.
  - Voice: **Bhashini/AI4Bharat** STT + Indic-TTS (device **Expo Speech** TTS as offline fallback).
  - Weather / Mandi prices (future app features): OpenWeatherMap / data.gov.in behind their interfaces.

## Architecture conventions
- **Every external service sits behind an interface** with: the interface, a real implementation,
  and a **mock implementation**. Features are built on the mock first, then flipped to live by
  adding an API key. The app must **degrade gracefully** (show cached/sample data, never crash).
- **Secrets never live in the app.** `EXPO_PUBLIC_*` vars are bundled into the app and readable by
  anyone — only low-risk keys (Supabase anon, free weather/market keys) go there. The
  **Anthropic and Bhashini keys are server-only** and live in a Supabase Edge Function; the app
  calls the function, not the vendor API directly. See `.env.example`.
- **Path alias:** `@/` → `src/` (configured in `tsconfig.json`). Import shared code as `@/...`.
- **UI:** Marathi-first, large readable text, simple emoji/icons, minimal typing, voice-friendly.
  Colors come from `src/constants/colors.ts`. Reuse `ScreenContainer` for page layout.
- **All user-facing text goes through i18next** (`t('...')`) — never hardcode Marathi/English in screens.

## Project structure
```
app/                      # Screens (Expo Router; file = route)
  _layout.tsx             # Root: boots i18n, providers
  (tabs)/_layout.tsx      # Bottom tab bar (Home + 5 features)
  (tabs)/index.tsx        # Home
  (tabs)/{diagnose,chat,weather,irrigation,market}.tsx
src/
  components/             # Reusable UI (ScreenContainer, FeatureCard, Placeholder, LanguageToggle)
  services/               # Swappable service modules (interface + real + mock) — added per step
  store/                  # Zustand stores
  i18n/                   # i18next config + locales/{mr,en}/translation.json
  constants/              # colors, crops
.env.example              # documents every key (copy to .env)
```

## Build plan (incremental; pause for approval between steps)
- **Step 1 (done)** — Expo+TS skeleton, Expo Router, i18next (Marathi), 6-tab nav, Home. Runs in Expo Go.
- **Step 2 (done — now genuinely AI, not mock)** — Disease detection, end to end:
  - **Closed disease taxonomy** (`backend app/services/vision/labels.py`): 24 real diseases/pests across the
    3 crops, each with the visual signs sent to the model as grounding, plus `healthy`, `unknown` and
    `not_a_plant` so the model *can* decline. Never asked an open "what disease is this?".
  - **Knowledge keyed by detected disease** (`backend app/services/knowledge.py`), not by crop — the old
    crop-keyed lookup gave every onion photo the purple-blotch treatment. `curable=False` marks problems no
    spray fixes (virus, wilt, sunscald) and the app says so instead of selling a useless bottle.
  - **Self-hosted VLM adapter** (`backend app/services/vision/selfhosted.py`): reasons in English (pivot
    language), tolerates markdown-fenced JSON and `confidence: 88`, retries without JSON mode for Ollama,
    and caps confidence when the model names a disease but reports no visible symptoms (= guessing).
  - **Severity** from measured affected-area %, banded in Python; the Marathi "what to do now" comes from
    templates, never from the model, so its quality never depends on the model's uneven Marathi.
  - **Dataset capture** (`backend app/services/capture.py`): every photo + prediction + the farmer's
    👍/👎 correction is saved. `GET /vision/dataset` counts the moat. `POST /vision/feedback` records it.
  - App side: abstain card, red dose-note block, English active-ingredient chips (a shopkeeper reads the
    bottle label), feedback buttons, and a badge driven by `model_version`.
- **Step 3 (done)** — Marathi chatbot: text chat (bubbles, suggestions), voice-OUT via Expo
  Speech (🔊 read aloud), voice-IN scaffolded behind `SpeechToTextService` (mock now, Bhashini stub).
  `ChatService` in `src/services/chat/`: `apiChatService` calls FastAPI `POST /copilot/ask`; mock fallback.
- **Backend wiring (done)** — app talks to `krushimitra-backend` (FastAPI). Backend URL auto-derived
  from `Constants.expoConfig.hostUri` → `http://<metro-host>:8000` (override `EXPO_PUBLIC_API_URL`).
  Run backend with `--host 0.0.0.0 --port 8000`. Visual tell: backend up → severity bar + no demo
  badge; backend down → mock + "नमुना माहिती" badge. (Supabase Edge Functions no longer used.)
- **Step 4 (done)** — Weather, location-based, with the advisory block as the point of the screen:
  - **District picker, not GPS** (`src/constants/locations.ts`, 35 Maharashtra districts with coords).
    No permission dialog, works with the radio off. The picked district also tags every captured
    photo, which is what makes disease pressure mappable. GPS can refine it later — nothing blocks it.
  - **Crop advisory engine** (`backend app/services/weather/advice.py`) — the differentiator. Any app
    shows 28°C; this says "आज फवारणी करू नका" with the reason. Spray-window rules (rain washes the
    spray off, wind drift, midday heat) apply to every crop; then real Maharashtra disease pressure
    per crop: onion blotch/downy/thrips, soybean waterlog/rust/dry-spell, pomegranate telya/cracking/
    anthracnose/sunscald. Each threshold carries the agronomy that justifies it.
  - Weather predicts **conditions favourable to** a disease, never the disease — wording is always
    "look for these signs", and the no-dosage policy is enforced by a test.
  - OpenWeatherMap **free tier** (`/weather` + `/forecast`), not paid One Call 3.0. Key server-only;
    set `OPENWEATHER_API_KEY` to go live. Mock is seasonally plausible and seeded per farm+day, so
    pull-to-refresh doesn't reshuffle the forecast. `source` badges sample data, same rule as vision.
  - Marathi prose uses Devanagari numerals (matching `knowledge.py`); the forecast cards use Latin.
- **Step 5 (done)** — Irrigation advice, from a real **FAO-56 soil water balance**, not a rule of thumb:
  - `ET0` via **Hargreaves-Samani** (`backend app/services/irrigation/et.py`), deliberately not
    Penman-Monteith: the free weather tier gives no solar radiation, wind or vapour pressure, and
    FAO-56 Annex 4 names Hargreaves as the recommended temperature-only fallback. Verified against
    published Maharashtra ranges (~4 mm/day Nov, ~7 May, lower in monsoon) by test.
  - `ETc = Kc x ET0`, Kc interpolated across growth stages from the sowing/bahar date; then
    `deficit += ETc - effective rain`, irrigate when `deficit >= AWC x root depth x p`
    (`params.py` carries the FAO-56 tables, each value sourced in a comment).
  - **Method changes the strategy, not just the efficiency.** Drip replaces daily consumption
    (short interval, small volume); flood/sprinkler refill a depleted profile. Treating drip as a
    small flood would recommend a 10-day gap no pomegranate grower would accept.
  - **A water number IS the right answer here** (unlike a chemical dose): it is computed from
    physics plus published coefficients, and the failure mode is recoverable. What we must not do
    is hide the uncertainty — every plan carries `confidence` and the hand-feel soil check.
  - **No last-watered day => `decision: "unsure"`**, not a guess. It still answers what it can
    (interval + depth per turn). Unsupported crop => 422, never an invented coefficient.
  - Outputs farmer units: mm, m³/acre, litres/plant and **drip run hours** — and when the run time
    exceeds 6 h it says the system is undersized instead of just printing "14 तास".
  - App side: days-ago **chips** instead of a date picker (no dependency, no typing, closer to how
    a sowing is remembered), an "आज पाणी दिले" button, and a collapsible "हिशोब कसा केला" block so
    the number is auditable. The sowing date also fills `sowing_date` in the capture context.
- **Step 6 (done)** — Mandi prices, ranked by **net realisation** rather than headline price:
  - A mandi paying ₹200/qtl more 200 km away **nets less** once the lorry is paid. So every quote
    carries distance, transport cost and `net_price`, and the board is sorted by net with the top
    one flagged `is_best`. That comparison is the reason to open the screen instead of asking a
    neighbour. Transport rate is the farmer's own (chips on screen), default ₹0.6/qtl/km.
  - **data.gov.in / Agmarknet** resource `9ef84268-d588-465a-a308-a864a43d0070`. Two real quirks
    handled in code rather than guessed: its filter spelling is undocumented
    (`filters[state]` vs `filters[state.keyword]` vs `filters[State]`) so the adapter **tries each
    form and keeps the one that returns rows**; and its commodity spellings are its own — soybean
    is listed as **"Soyabean"**, so each crop has a candidate list.
  - **The API serves only the current day** — no history, no backfill. So every real board is
    appended to `data/market/<crop>.jsonl` and trends come from what we accumulate (mock boards are
    never written, so sample data cannot contaminate the series). Until two days exist the answer
    is **"कल अज्ञात"**, not a direction inferred from one point. `GET /market/history` counts it.
  - **Never says sell or hold.** A mandi price is not forecastable, and a confident call that costs
    a farmer their crop's value is the same failure as a wrong diagnosis. The notes state the
    spread, the measured trend and the data's age, and always end by sending the farmer to phone
    the APMC before loading a vehicle. A test asserts the predictive phrasings never appear.
  - Prices are **₹ per quintal**, fixed in `base.py` — a silent quintal/kg mix-up would be a 100×
    error in the one number a farmer acts on.
  - District name **aliases** (`Nasik`, `Ahmadnagar`, `Aurangabad`, `Osmanabad`) resolve to current
    names, or an unmatched mandi would silently vanish from the list. Known mandis get Marathi
    names (`names.py`); unknown ones stay in English rather than being auto-transliterated wrongly.

- **Step 7 (done)** — Accounts + Digital Crop Twin:
  - **SQLite by default** (`DATABASE_URL`), so the backend runs with zero setup; Postgres+pgvector
    stays a one-env-var switch for production. The single pgvector column falls back to JSON.
  - **Phone-OTP auth** with normalised numbers (`+91`/`0`/spaces collapse to one account), JWT,
    `/auth/me`. Signing in **claims the anonymous device id**, so photos captured before login are
    attributed to that farmer instead of being stranded — only when the id is unclaimed, because
    two farmers sharing a handset must not inherit each other's captures.
  - **Plots** (`/farms`) hold district, soil, irrigation method and spacing **once**, instead of
    every advisory screen re-asking. **Cycles** (`/crop-cycles`) hold the season; events build the
    timeline; logging an irrigation updates `last_watered_date` so the irrigation plan stops asking.
  - **Health score is a transparent formula, not a model** (`app/services/twin.py`): every point
    deducted is itemised with date and reason. Abstained diagnoses deduct **nothing** — our
    uncertainty is not the farmer's fault. Penalties decay over ~30 days, but `curable=False`
    problems decay over 120: a virus does not heal because a month passed.
  - **Stage is reused from the FAO-56 irrigation tables**, so the twin, the irrigation plan and the
    weather advisory can never disagree about the same field on the same day.
  - Ownership returns **404, not 403**, for another farmer's data — a guessed id must not confirm
    that a plot exists.
  - **GPS auto-detect** (`expo-location`) via a shared `LocationBar`, with the district picker as
    the fallback, never the replacement: a denied permission or a failed fix silently keeps the
    picked district, which works offline. `Accuracy.Balanced` on purpose — weather and ET₀ do not
    change within 100 m, and a fast fix beats a precise one.
  - App: login screen, Home-as-dashboard (the twin above the feature cards — no 7th tab), add-crop
    flow, cycle detail with timeline and an auditable health breakdown.
- **Branding** — `assets/icon.png` is still the **stock Expo chevron with its design-grid lines
  visible**. A real logo exists as `assets/brand/logo.svg` (+ adaptive foreground); it needs one
  conversion step, see `assets/brand/README.md`. Must not ship as-is.

## Commands
- `npm start` — start the Expo dev server (scan QR with Expo Go).
- `npm run android` — open on connected Android / emulator.
- `npx tsc --noEmit` — type-check.
- `cd krushimitra-backend && PYTHONPATH=. .venv/bin/python -m pytest tests/ -q --ignore=tests/test_vision_pipeline.py`
  — backend tests (89). `test_vision_pipeline.py` is excluded because it is a **script**, not a
  pytest module: it needs the stub VLM server running first (see `tests/README.md`), and pytest
  fails at *collection* without it.
- **Verify the vision pipeline is honest** (no GPU or key needed) — 24 checks covering
  disease-keyed advice, the abstain gate, badging and capture: see `krushimitra-backend/tests/README.md`.
- **Probe a real self-hosted model** before trusting it, and measure its accuracy on your own photos:
  `cd krushimitra-backend && PYTHONPATH=. .venv/bin/python scripts/probe_vision_model.py --help`

## Notes / gotchas
- Project folder path contains a space (`KrushiMitra AI`). If Metro bundling acts up, rename the
  folder to `krushimitra-ai` (no space).
- npm uses `legacy-peer-deps=true` (`.npmrc`) to tolerate a benign react/react-dom peer pin.
- **Run `nvm use` before `npm start`** — SDK 58 (Metro 0.87 / RN 0.88) requires Node ≥22.13; `.nvmrc` pins 24. On Node 20 Metro fails to start.
- Always install Expo-native libs with `npx expo install <pkg>` (SDK-compatible versions), not plain `npm install`.
- **App loads then shows nothing / blank? Run `npx expo-doctor` FIRST.** A *minor* version drift in a
  native module that Expo Go also ships breaks the app at runtime while the bundle still compiles
  and serves at HTTP 200 — so it looks like broken code and is not. This bit us once with
  `react-native-safe-area-context` at 5.10.1 against Expo Go's 5.11.x: it wraps the whole app
  (`SafeAreaProvider` + every `ScreenContainer`), so the first render dies and the screen stays
  blank. Fix with `npx expo install --fix`, then restart Metro with `npx expo start -c`
  (a running Metro keeps serving the OLD dependency tree).
- **Debugging "QR scanned but nothing happens" without a phone:** fetch the manifest the way Expo Go
  does — `curl -s http://<lan-ip>:8081/ -H "expo-platform: android" -H "accept: application/json"`
  — then GET the `launchAsset.url` from it. A JSON body starting `{"type":"...Error"` is a bundling
  failure; a multi-MB JS body means the bundle is fine and the fault is runtime or native.
  (Note `/index.bundle` is NOT the entry for expo-router apps; `package.json` main is
  `expo-router/entry`.)

@AGENTS.md
