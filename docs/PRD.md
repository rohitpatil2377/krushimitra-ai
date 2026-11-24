# KrushiMitra AI — Product Requirements Document (PRD)

> **Product:** KrushiMitra AI — "Your Personal AI Agriculture Copilot"
> **One-liner:** A voice-first AI agronomist that doesn't just *name* a crop disease — it tells the
> farmer **how bad it is, how fast it's spreading, and exactly what to do this week**, in Marathi/Hindi/English.

## Vision
Build an AI agronomist that works 24×7 for every farmer — monitoring the **full crop lifecycle**
(growth, disease progression, severity, irrigation, health, weather risk, yield, market), not a
one-shot disease-detection app.

## The wedge (why we win)
Detection is commoditized; farmers often already know the disease. The unmet need is **decision
support at the right severity and crop stage**: *"what do I do now, and what happens if I don't?"*
Our core innovation is **Disease Severity Intelligence**, not disease detection.

> **Reality note:** calibrated severity needs expert-labeled, longitudinal data that does not exist
> publicly for our crops. Sequence: ship a useful copilot now (LLM + public-dataset detection) →
> collect severity data via the founder's farmer network → train the severity model that becomes the moat.
> Severity is the destination, not the day-1 MVP.

## Target user (Phase 1)
Smallholder **onion / soybean / pomegranate** farmers in Maharashtra (Nashik, Pune, Solapur,
Ahmednagar belts). Android, low typing comfort, high voice + WhatsApp comfort.

## Markets & crops
- **Phase 1:** Maharashtra. **Phase 2:** India.
- **Crops now:** Onion (कांदा), Soybean (सोयाबीन), Pomegranate (डाळिंब).
- **Future crops:** Tomato, Maize. *(Do not build other crops initially.)*

## Languages
- **Internal pivot language:** English (STT → translate → reason/RAG in English → translate → user language).
- **User languages:** Marathi, Hindi, English. All AI output in the user's selected language.

## Core product philosophy — Photo + Voice + AI
Voice-first. Typing is always optional, never required. App opens to a **large microphone button**.
Farmer speaks (mr/hi/en) and/or uploads a crop photo; AI replies in **voice + text**.

## Digital Crop Twin
Every farmer gets a per-crop-cycle timeline. Every uploaded image is stored as a timeline event.
The system understands crop stage, disease progression, treatment history, growth trend, weather
impact, health score, yield potential.

## MVP features (re-prioritized for buildability)
| Pri | Feature | MVP reality | Built on |
|-----|---------|-------------|----------|
| P0 | Voice-first copilot | STT (Bhashini/IndicWhisper) → LLM+RAG → TTS, mr/hi/en | Hosted LLM + Bhashini |
| P0 | Disease detection | Fine-tuned classifier per crop → disease + confidence | Public datasets + PyTorch |
| P1 | Severity (v1 = beta) | Ordinal Healthy→Critical; v1 via vision-LLM rubric, v2 via lesion-area segmentation % | LLM, then seg model |
| P1 | Treatment advisor | RAG over agronomy KB, conditioned on crop+disease+severity+stage | LLM + KB |
| P2 | Crop journey / Digital Twin | Store every image under a crop-cycle timeline; progression view | Postgres + S3 |
| P2 | Crop Health Score (0–100) | Transparent formula (severity, stage, history) — not a black box | Backend rule → ML |

### Severity levels
Healthy · Mild · Moderate · Severe · Critical (+ severity %, risk level, recommended action).

### Treatment advisor output
Treatment plan · spray recommendation (dosage **only** from retrieved labels) · prevention strategy ·
follow-up schedule · source citations.

## Out of scope (MVP)
Marketplace, satellite, IoT, drones, insurance, yield prediction, weather/irrigation/fertilizer as
full features, KrushiGPT-as-platform, Tomato/Maize. (All on the future roadmap.)

## Success metrics (MVP)
100 real farmers (founder's network) · ≥40% week-2 retention · ≥500 labeled crop images collected ·
≥70% "advice was useful". These are **data-collection + trust** metrics, not downloads.

## Key risks
Advice liability (cite sources, hedge dosages, defer to KVK) · Marathi dialect STT/TTS quality ·
trust takes months · cannot out-engineer funded teams → win the narrow wedge and own the data.

See also: [ARCHITECTURE.md](ARCHITECTURE.md) · [AI_ARCHITECTURE.md](AI_ARCHITECTURE.md) ·
[DATASET.md](DATASET.md) · [ROADMAP.md](ROADMAP.md).
