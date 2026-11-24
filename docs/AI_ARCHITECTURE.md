# KrushiMitra AI — AI Architecture

Guiding principle: **every model sits behind an interface** (`DiseaseDetector`, `SeverityEstimator`,
`STT`, `TTS`), each with a `mock` → `llm` → `trained` implementation. Swap *up the ladder* as data
arrives — same swappable pattern the React Native app already uses.

## 1. Vision layer (realistic build order — do NOT start at ViT)
1. **Detection v1:** transfer-learn `EfficientNet-B0` or `YOLOv8-cls` (`timm` / `ultralytics`) per crop.
   Small, fast, CPU-friendly. Target ≥85% top-1 on onion/soybean/pomegranate.
2. **Severity v1 (label it "beta"):**
   - *Option A — week 1, zero training:* send the image to a **vision LLM** with a structured rubric →
     ordinal severity (Healthy/Mild/Moderate/Severe/Critical). Immediate, cheap, decent.
   - *Option B — the moat, months 3–6:* train **segmentation** (U-Net / SegFormer) to mask lesion area →
     `severity_pct = diseased_area / leaf_area`. Computable, explainable, defensible — needs the labeled
     data being collected via the farmer network.
3. **Crop-stage:** for MVP infer from the farmer's sowing date (asked once) — no model. Add a stage
   classifier later.

Later: Vision Transformers / larger detection+segmentation once the dataset is large enough to justify them.

## 2. Voice layer
- **STT:** Bhashini / AI4Bharat IndicWhisper for mr/hi/en (Indic-tuned, free-ish). Self-host
  Whisper-large-v3 only if cost/latency forces it.
- **Language detection:** Bhashini returns it; fallback fastText langid.
- **TTS:** Bhashini Indic-TTS / AI4Bharat Indic-TTS (natural Marathi/Hindi). Device TTS (Expo Speech,
  used in app Step 3) stays as the offline fallback.

## 3. LLM + RAG layer (the copilot brain)
- **English as internal pivot language:** STT → translate to English → reason + retrieve in English →
  generate → translate to the user's language. Keeps the KB and prompts single-language → far better RAG.
- **RAG corpus:** ICAR / KVK "Package of Practices" for the 3 crops, state agri-university advisories,
  pesticide labels + dosages, and the startup's own validated answers. Chunk → embed
  (multilingual-e5 / BGE, dim 1024) → store in **pgvector**.
- **Orchestration (agent loop):** classify intent (diagnosis / advice / weather / chit-chat) → call vision
  and/or retrieve KB → compose answer with **citations + dosage + safety + follow-up date**. Use a hosted
  frontier model (Claude) for reasoning — no GPUs to self-host a strong LLM yet.
- **Guardrails (liability is real):** pesticide dosages come **only** from retrieved labels; if not
  retrieved, say "consult your KVK." Never invent chemical advice.

## 4. Training pipeline
```
S3 raw images → label store (expert_labels) → versioned dataset (DVC) →
  train (PyTorch + timm/ultralytics; Colab/Kaggle free GPU at first) →
  eval vs frozen gold test set → register model + version →
  deploy behind DiseaseDetector/SeverityEstimator interface →
  shadow-test in prod (log predictions, compare to farmer corrections) → promote
```
- **Compute:** Colab/Kaggle free GPUs for MVP; rent spot GPUs (Lambda/Vast/RunPod) for bigger runs.
  Do not buy hardware.
- **Tracking:** Weights & Biases (free) + DVC for dataset versioning.
- **Cadence:** retrain monthly or per +1k new labels. Gate every promotion on the frozen gold set.

## Model serving
MVP: PyTorch models loaded in the FastAPI process (CPU). Scale: containerized GPU service
(Triton/TorchServe) only when volume/latency requires it.

See also: [DATASET.md](DATASET.md) for data collection & the moat that feeds these models.
